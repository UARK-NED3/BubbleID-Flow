from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import LeaveOneGroupOut, LeaveOneOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


CASE_STYLE = {
    "5gs_22C": ("#0072B2", "o", "5 g/s, 22 degC"),
    "10gs_22C": ("#009E73", "s", "10 g/s, 22 degC"),
    "15gs_20C": ("#D55E00", "^", "15 g/s, 20 degC"),
    "25gs_20C": ("#CC79A7", "D", "25 g/s, 20 degC"),
}
BASELINE_FEATURES = [
    "heat_flux_mean_w_cm2",
    "mass_flux_kg_m2_s",
    "inlet_subcooling_mean_c",
]
OPTICAL_FEATURE = "vapor_area_fraction_aug9"
RESPONSE = "wall_temperature_mean_c"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test state-level thermal associations and heat-flux confounding."
    )
    parser.add_argument("--optical-summary", required=True)
    parser.add_argument("--thermal-summary", required=True)
    parser.add_argument("--temporal-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    optical = pd.read_csv(args.optical_summary)
    thermal = pd.read_csv(args.thermal_summary)
    temporal = pd.read_csv(args.temporal_summary)
    merged = thermal.merge(
        optical[["case_label", "state_voltage", OPTICAL_FEATURE]],
        on=["case_label", "state_voltage"],
        how="left",
        validate="one_to_one",
    )
    complete = merged.dropna(subset=BASELINE_FEATURES + [OPTICAL_FEATURE, RESPONSE]).copy()
    complete.to_csv(output_dir / "optical_thermal_state_summary.csv", index=False)

    case_rows = []
    for case, group in complete.groupby("case_label", sort=False):
        case_rows.append(
            {
                "case_label": case,
                "states": len(group),
                "spearman_voltage_vs_heat_flux": spearman(group["state_voltage"], group["heat_flux_mean_w_cm2"]),
                "spearman_heat_flux_vs_projected_area": spearman(group["heat_flux_mean_w_cm2"], group[OPTICAL_FEATURE]),
                "spearman_heat_flux_vs_mean_temperature": spearman(group["heat_flux_mean_w_cm2"], group[RESPONSE]),
                "spearman_projected_area_vs_mean_temperature": spearman(group[OPTICAL_FEATURE], group[RESPONSE]),
            }
        )
    case_summary = pd.DataFrame(case_rows)
    case_summary.to_csv(output_dir / "optical_thermal_case_associations.csv", index=False)

    cv_summary, predictions = cross_validated_incremental_test(complete)
    cv_summary.to_csv(output_dir / "optical_incremental_cv_summary.csv", index=False)
    predictions.to_csv(output_dir / "optical_incremental_cv_predictions.csv", index=False)

    x = complete[BASELINE_FEATURES].to_numpy(dtype=float)
    vapor_residual = OPTICAL_FEATURE + "_residual"
    temperature_residual = RESPONSE + "_residual"
    complete[vapor_residual] = complete[OPTICAL_FEATURE] - LinearRegression().fit(x, complete[OPTICAL_FEATURE]).predict(x)
    complete[temperature_residual] = complete[RESPONSE] - LinearRegression().fit(x, complete[RESPONSE]).predict(x)
    residual_correlation = float(np.corrcoef(complete[vapor_residual], complete[temperature_residual])[0, 1])

    manifest = {
        "thermal_response": "mean of seven measured test-section surface temperatures",
        "baseline_predictors": BASELINE_FEATURES,
        "augmented_predictors": BASELINE_FEATURES + [OPTICAL_FEATURE],
        "model": "standardized ridge regression with fixed alpha=1.0",
        "cross_validation": ["leave-one-state-out", "leave-one-case-out"],
        "states_with_complete_optical_thermal_data": int(len(complete)),
        "missing_thermal_state": "10gs_22C/45V",
        "residual_pearson_correlation_after_baseline_linear_adjustment": residual_correlation,
        "interpretation": (
            "screening test of incremental state-level association; not a causal or deployment model"
        ),
    }
    (output_dir / "optical_thermal_association_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    make_figure(merged, temporal, cv_summary, output_dir)
    print(case_summary.to_string(index=False))
    print(cv_summary.to_string(index=False))
    print(f"Residual correlation: {residual_correlation:.3f}")


def cross_validated_incremental_test(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    prediction_frames = []
    for cv_name, cv, groups in (
        ("leave-one-state-out", LeaveOneOut(), None),
        ("leave-one-case-out", LeaveOneGroupOut(), data["case_label"]),
    ):
        for model_name, features in (
            ("thermal baseline", BASELINE_FEATURES),
            ("thermal baseline + projected area", BASELINE_FEATURES + [OPTICAL_FEATURE]),
        ):
            estimator = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
            prediction = cross_val_predict(
                estimator,
                data[features],
                data[RESPONSE],
                cv=cv,
                groups=groups,
            )
            rmse = float(mean_squared_error(data[RESPONSE], prediction) ** 0.5)
            mae = float(np.mean(np.abs(data[RESPONSE] - prediction)))
            rows.append(
                {
                    "cross_validation": cv_name,
                    "model": model_name,
                    "states": len(data),
                    "rmse_c": rmse,
                    "mae_c": mae,
                    "prediction_correlation": float(np.corrcoef(data[RESPONSE], prediction)[0, 1]),
                }
            )
            prediction_frames.append(
                data[["case_label", "state_label", "state_voltage", RESPONSE]].assign(
                    cross_validation=cv_name,
                    model=model_name,
                    predicted_temperature_c=prediction,
                    residual_c=data[RESPONSE].to_numpy() - prediction,
                )
            )
    return pd.DataFrame(rows), pd.concat(prediction_frames, ignore_index=True)


def spearman(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 2:
        return float("nan")
    return float(spearmanr(x, y).statistic)


def make_figure(
    merged: pd.DataFrame,
    temporal: pd.DataFrame,
    cv_summary: pd.DataFrame,
    output_dir: Path,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 10,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 8.5,
            "axes.linewidth": 0.8,
            "axes.edgecolor": "black",
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
            "mathtext.bf": "Arial:bold",
            "savefig.dpi": 300,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.5), constrained_layout=True)
    for case, (color, marker, label) in CASE_STYLE.items():
        group = merged[merged["case_label"] == case].sort_values("state_voltage")
        valid = group.dropna(subset=["heat_flux_mean_w_cm2", OPTICAL_FEATURE])
        axes[0, 0].plot(
            valid["heat_flux_mean_w_cm2"],
            valid[OPTICAL_FEATURE],
            marker=marker,
            color=color,
            linewidth=1.1,
            linestyle="--",
            markersize=4.5,
            label=label,
        )
        thermal_valid = group.dropna(subset=["heat_flux_mean_w_cm2", RESPONSE])
        axes[0, 1].errorbar(
            thermal_valid["heat_flux_mean_w_cm2"],
            thermal_valid[RESPONSE],
            yerr=thermal_valid["wall_temperature_std_c"],
            marker=marker,
            color=color,
            linewidth=1.1,
            linestyle="--",
            markersize=4.5,
            capsize=2,
            label=label,
        )
        association = group.dropna(subset=[OPTICAL_FEATURE, RESPONSE])
        axes[1, 0].scatter(
            association[OPTICAL_FEATURE],
            association[RESPONSE],
            marker=marker,
            facecolor=color,
            edgecolor="white",
            linewidth=0.4,
            s=28,
            label=label,
        )

    for case, row in temporal.set_index("case_label").iterrows():
        color, marker, _ = CASE_STYLE[case]
        thermal_row = merged[(merged["case_label"] == case) & np.isclose(merged["state_voltage"], 45.0)]
        if thermal_row.empty or thermal_row["heat_flux_mean_w_cm2"].isna().all():
            continue
        x = float(thermal_row["heat_flux_mean_w_cm2"].iloc[0])
        mean = float(row["mean_vapor_area_fraction"])
        axes[0, 0].errorbar(
            [x],
            [mean],
            yerr=[[mean - float(row["ci95_lower"])], [float(row["ci95_upper"]) - mean]],
            fmt=marker,
            color=color,
            capsize=3,
            markersize=5,
        )

    axes[0, 0].set(xlabel="Mean heat flux (W cm-2)", ylabel="Projected vapor coverage")
    axes[0, 0].legend(frameon=False, ncol=2)
    axes[0, 1].set(xlabel="Mean heat flux (W cm-2)", ylabel="Mean measured test-section temperature (degC)")
    axes[1, 0].set(xlabel="Projected vapor coverage", ylabel="Mean measured test-section temperature (degC)")

    cv_order = ["leave-one-state-out", "leave-one-case-out"]
    model_order = ["thermal baseline", "thermal baseline + projected area"]
    x = np.arange(len(cv_order))
    width = 0.34
    for index, model in enumerate(model_order):
        values = [
            float(cv_summary[(cv_summary["cross_validation"] == cv) & (cv_summary["model"] == model)]["rmse_c"].iloc[0])
            for cv in cv_order
        ]
        axes[1, 1].bar(
            x + (index - 0.5) * width,
            values,
            width,
            label=("Thermal baseline" if index == 0 else "Baseline + coverage"),
            color=("#777777" if index == 0 else "#0072B2"),
        )
    axes[1, 1].set_xticks(x, ["Leave one state out", "Leave one case out"])
    axes[1, 1].set(ylabel="Cross-validated temperature RMSE (degC)")
    axes[1, 1].legend(frameon=False)

    for label, axis in zip("abcd", axes.ravel(), strict=True):
        axis.text(0.0, 1.03, f"({label})", transform=axis.transAxes, va="bottom", clip_on=False)
        axis.grid(False)
        axis.tick_params(direction="in", top=True, right=True)
        for spine in axis.spines.values():
            spine.set_visible(True)
            spine.set_color("black")
    for suffix in ("pdf", "png"):
        fig.savefig(output_dir / f"Figure_6_optical_thermal_association.{suffix}", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
