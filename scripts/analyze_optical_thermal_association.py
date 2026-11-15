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
    "5gs_22C": ("#0072B2", "o", "5 g/s, 22 $^\\circ$C"),
    "10gs_22C": ("#009E73", "s", "10 g/s, 22 $^\\circ$C"),
    "15gs_20C": ("#D55E00", "^", "15 g/s, 20 $^\\circ$C"),
    "25gs_20C": ("#CC79A7", "D", "25 g/s, 20 $^\\circ$C"),
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
    # The canonical public table intentionally uses the generic engineering
    # quantity name. Preserve support for the older manuscript-only column.
    if OPTICAL_FEATURE not in optical and "vapor_area_fraction" in optical:
        optical = optical.rename(columns={"vapor_area_fraction": OPTICAL_FEATURE})
    if OPTICAL_FEATURE not in optical:
        raise ValueError(
            f"Optical summary must contain '{OPTICAL_FEATURE}' or 'vapor_area_fraction'."
        )
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
    fold_metrics = cross_validated_fold_metrics(predictions)
    fold_metrics.to_csv(output_dir / "optical_incremental_cv_fold_metrics.csv", index=False)

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
        "fold_metrics": "optical_incremental_cv_fold_metrics.csv",
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


def cross_validated_fold_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarize held-out errors by experimental case without pooling folds."""
    rows = []
    for (cv_name, model, case), group in predictions.groupby(
        ["cross_validation", "model", "case_label"], sort=False
    ):
        residual = group["residual_c"].to_numpy(dtype=float)
        rows.append(
            {
                "cross_validation": cv_name,
                "model": model,
                "held_out_case": case,
                "states": int(len(group)),
                "rmse_c": float(np.sqrt(np.mean(residual**2))),
                "mae_c": float(np.mean(np.abs(residual))),
                "mean_residual_c": float(np.mean(residual)),
            }
        )
    return pd.DataFrame(rows)


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
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.85), constrained_layout=True)
    for case, (color, marker, label) in CASE_STYLE.items():
        group = merged[merged["case_label"] == case].sort_values("state_voltage")
        valid = group.dropna(subset=["heat_flux_mean_w_cm2", OPTICAL_FEATURE])
        thermal_valid = group.dropna(subset=["heat_flux_mean_w_cm2", RESPONSE])
        axes[0].errorbar(
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
        axes[1].scatter(
            association[OPTICAL_FEATURE],
            association[RESPONSE],
            marker=marker,
            facecolor=color,
            edgecolor="white",
            linewidth=0.4,
            s=28,
            label=label,
        )

    axes[0].set(xlabel="Mean heat flux (W/cm$^2$)", ylabel="Mean measured test-section temperature ($^\\circ$C)")
    axes[1].set(xlabel="Vapor area fraction", ylabel="Mean measured test-section temperature ($^\\circ$C)")

    cv_order = ["leave-one-state-out", "leave-one-case-out"]
    model_order = ["thermal baseline", "thermal baseline + projected area"]
    x = np.arange(len(cv_order))
    width = 0.34
    for index, model in enumerate(model_order):
        values = [
            float(cv_summary[(cv_summary["cross_validation"] == cv) & (cv_summary["model"] == model)]["rmse_c"].iloc[0])
            for cv in cv_order
        ]
        axes[2].bar(
            x + (index - 0.5) * width,
            values,
            width,
            label=("Thermal baseline" if index == 0 else "Baseline + vapor area fraction"),
            color=("#777777" if index == 0 else "#0072B2"),
        )
    axes[2].set_xticks(x, ["Leave-one-\nstate-out", "Leave-one-\ncase-out"])
    axes[2].set(ylabel="Cross-validated temperature RMSE ($^\\circ$C)")

    for label, axis in zip("abc", axes, strict=True):
        axis.text(0.0, 1.03, f"({label})", transform=axis.transAxes, va="bottom", clip_on=False)
        axis.grid(False)
        axis.tick_params(direction="in", top=True, right=True)
        for spine in axis.spines.values():
            spine.set_visible(True)
            spine.set_color("black")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.01))
    for suffix in ("pdf", "png"):
        fig.savefig(output_dir / f"Figure_6_optical_thermal_association.{suffix}", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
