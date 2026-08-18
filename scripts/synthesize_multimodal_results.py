from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bubbleid_flow.vapor_fraction import DEFAULT_ACTIVE_COLUMN_THRESHOLD


ACTIVE_LENGTH_THRESHOLD_PREFIX = "active_length_fraction_thr_"


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize multimodal state summaries.")
    parser.add_argument("--summary", action="append", required=True, help="State summary CSV.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--active-column-threshold",
        type=float,
        default=DEFAULT_ACTIVE_COLUMN_THRESHOLD,
        help=(
            "Projected vapor occupancy threshold used for active-length metrics. "
            "Used to annotate legacy summary files that do not already record it."
        ),
    )
    parser.add_argument(
        "--ae-verification-status",
        help=(
            "Optional CSV with case_label, trigger_synchronization_verified, "
            "sensor_coupling_verified, and optional verification_notes columns."
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_paths = [Path(path) for path in args.summary]
    data = load_summaries(
        summary_paths,
        active_column_threshold=args.active_column_threshold,
    )
    frame_metrics = load_frame_metrics(summary_paths)
    combined_path = output_dir / "combined_multimodal_state_summary.csv"
    analysis_path = output_dir / "combined_multimodal_analysis_states.csv"
    trend_path = output_dir / "cross_case_trend_summary.csv"
    sensitivity_path = output_dir / "cross_case_trend_sensitivity.csv"
    sampling_path = output_dir / "cross_case_sampling_uncertainty.csv"
    active_threshold_path = output_dir / "cross_case_active_threshold_sensitivity.csv"
    thermal_response_path = output_dir / "cross_case_thermal_response_checks.csv"
    segmentation_plan_path = output_dir / "cross_case_segmentation_validation_plan.csv"
    ae_verification_path = output_dir / "cross_case_ae_verification_status.csv"
    ae_evidence_path = output_dir / "cross_case_ae_evidence_tiers.csv"
    ae_readiness_path = output_dir / "cross_case_ae_readiness_matrix.csv"
    ae_remediation_path = output_dir / "cross_case_ae_remediation_plan.csv"
    claim_matrix_path = output_dir / "cross_case_claim_evidence_matrix.csv"
    analysis_data = data[data["multimodal_complete"]].copy()
    ae_verification_status = build_ae_verification_status(
        analysis_data,
        Path(args.ae_verification_status) if args.ae_verification_status else None,
    )
    trend_summary = build_trend_summary(analysis_data)
    trend_sensitivity = build_trend_sensitivity(analysis_data)
    sampling_uncertainty = build_sampling_uncertainty(analysis_data, frame_metrics)
    active_threshold_sensitivity = build_active_threshold_sensitivity(
        analysis_data,
        frame_metrics,
    )
    analysis_data = attach_sampling_uncertainty_columns(
        analysis_data,
        sampling_uncertainty,
    )
    thermal_response = build_thermal_response_checks(analysis_data)
    segmentation_plan = build_segmentation_validation_plan(
        analysis_data,
        sampling_uncertainty,
    )
    ae_evidence_tiers = build_ae_evidence_tiers(
        analysis_data,
        trend_summary,
        trend_sensitivity,
        verification_status=ae_verification_status,
    )
    ae_readiness = build_ae_readiness_matrix(
        analysis_data,
        ae_evidence_tiers,
        verification_status=ae_verification_status,
    )
    ae_remediation = build_ae_remediation_plan(
        analysis_data,
        trend_sensitivity,
        ae_readiness,
        ae_verification_status,
    )
    claim_matrix = build_claim_evidence_matrix(
        analysis_data,
        trend_summary,
        trend_sensitivity,
        sampling_uncertainty,
        thermal_response,
        segmentation_plan,
        ae_evidence_tiers,
        ae_readiness,
        active_threshold_sensitivity,
    )
    data.to_csv(combined_path, index=False)
    analysis_data.to_csv(analysis_path, index=False)
    trend_summary.to_csv(trend_path, index=False)
    trend_sensitivity.to_csv(sensitivity_path, index=False)
    sampling_uncertainty.to_csv(sampling_path, index=False)
    active_threshold_sensitivity.to_csv(active_threshold_path, index=False)
    thermal_response.to_csv(thermal_response_path, index=False)
    segmentation_plan.to_csv(segmentation_plan_path, index=False)
    ae_verification_status.to_csv(ae_verification_path, index=False)
    ae_evidence_tiers.to_csv(ae_evidence_path, index=False)
    ae_readiness.to_csv(ae_readiness_path, index=False)
    ae_remediation.to_csv(ae_remediation_path, index=False)
    claim_matrix.to_csv(claim_matrix_path, index=False)

    plot_cross_case_story(analysis_data, output_dir / "cross_case_multimodal_story.png")
    plot_state_map(analysis_data, output_dir / "cross_case_state_map.png")
    write_key_numbers(
        analysis_data,
        trend_summary,
        trend_sensitivity,
        sampling_uncertainty,
        active_threshold_sensitivity,
        thermal_response,
        segmentation_plan,
        ae_verification_status,
        ae_evidence_tiers,
        ae_readiness,
        ae_remediation,
        claim_matrix,
        output_dir / "cross_case_key_numbers.txt",
    )

    print(f"Wrote {combined_path}")
    print(f"Wrote {analysis_path}")
    print(f"Wrote {trend_path}")
    print(f"Wrote {sensitivity_path}")
    print(f"Wrote {sampling_path}")
    print(f"Wrote {active_threshold_path}")
    print(f"Wrote {thermal_response_path}")
    print(f"Wrote {segmentation_plan_path}")
    print(f"Wrote {ae_verification_path}")
    print(f"Wrote {ae_evidence_path}")
    print(f"Wrote {ae_readiness_path}")
    print(f"Wrote {ae_remediation_path}")
    print(f"Wrote {claim_matrix_path}")
    print(f"Wrote {output_dir / 'cross_case_multimodal_story.png'}")
    print(f"Wrote {output_dir / 'cross_case_state_map.png'}")


def load_summaries(paths: list[Path], active_column_threshold: float) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        case = path.name.replace("_multimodal_state_summary.csv", "")
        frame["case_label"] = case
        frame = annotate_active_column_threshold(frame, active_column_threshold)
        if case.startswith("5gs"):
            frame["mass_flow_g_s"] = 5.0
            frame["subcooling_nominal_c"] = 22.0
        elif case.startswith("10gs"):
            frame["mass_flow_g_s"] = 10.0
            frame["subcooling_nominal_c"] = 22.0
        elif case.startswith("15gs"):
            frame["mass_flow_g_s"] = 15.0
            frame["subcooling_nominal_c"] = 20.0
        elif case.startswith("25gs"):
            frame["mass_flow_g_s"] = 25.0
            frame["subcooling_nominal_c"] = 20.0
        frame["multimodal_complete"] = has_complete_multimodal_state(frame)
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["mass_flow_g_s", "state_voltage"]).reset_index(drop=True)
    return annotate_ae_window_quality(data)


def load_frame_metrics(summary_paths: list[Path]) -> pd.DataFrame:
    """Load per-frame image metrics stored beside each state summary, when available."""
    frames = []
    for summary_path in summary_paths:
        case = summary_path.name.replace("_multimodal_state_summary.csv", "")
        metrics_path = summary_path.with_name(f"{case}_image_frame_metrics.csv")
        if not metrics_path.exists():
            continue
        frame = pd.read_csv(metrics_path)
        frame["case_label"] = case
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build_ae_verification_status(
    data: pd.DataFrame,
    source_path: Path | None = None,
) -> pd.DataFrame:
    """Create case-level trigger/coupling verification flags for AE readiness gates."""
    case_series = data.get("case_label", pd.Series(dtype=object))
    cases = sorted(str(case) for case in case_series.dropna().unique())
    rows = [
        {
            "case_label": case,
            "trigger_synchronization_verified": False,
            "sensor_coupling_verified": False,
            "verification_source": "not_provided",
            "verification_notes": (
                "No case-level trigger or sensor-coupling verification record supplied."
            ),
        }
        for case in cases
    ]
    status = pd.DataFrame(rows)
    if source_path is None or not source_path.exists():
        return status

    supplied = pd.read_csv(source_path)
    if "case_label" not in supplied.columns:
        raise ValueError("AE verification status CSV must include a case_label column.")

    optional_defaults = {
        "trigger_synchronization_verified": False,
        "sensor_coupling_verified": False,
        "verification_notes": "",
    }
    for column, default in optional_defaults.items():
        if column not in supplied.columns:
            supplied[column] = default
    supplied = supplied[
        [
            "case_label",
            "trigger_synchronization_verified",
            "sensor_coupling_verified",
            "verification_notes",
        ]
    ].copy()
    supplied["case_label"] = supplied["case_label"].astype(str)
    supplied["trigger_synchronization_verified"] = supplied[
        "trigger_synchronization_verified"
    ].map(parse_bool_value)
    supplied["sensor_coupling_verified"] = supplied["sensor_coupling_verified"].map(
        parse_bool_value
    )
    supplied["verification_source"] = source_path.as_posix()

    merged = status.drop(columns=["verification_source", "verification_notes"]).merge(
        supplied,
        on="case_label",
        how="left",
        suffixes=("", "_supplied"),
    )
    for column in ["trigger_synchronization_verified", "sensor_coupling_verified"]:
        supplied_column = f"{column}_supplied"
        merged[column] = merged[supplied_column].combine_first(merged[column]).map(parse_bool_value)
        merged = merged.drop(columns=[supplied_column])
    merged["verification_source"] = merged["verification_source"].fillna("not_provided")
    merged["verification_notes"] = merged["verification_notes"].fillna(
        "No case-level trigger or sensor-coupling verification record supplied."
    )
    return merged


def annotate_active_column_threshold(frame: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Ensure active-length outputs carry the threshold used to compute them."""
    if not 0 <= threshold <= 1:
        raise ValueError("active_column_threshold must be between 0 and 1")

    annotated = frame.copy()
    if "active_column_threshold" not in annotated.columns:
        annotated["active_column_threshold"] = threshold
        annotated["active_column_threshold_source"] = "synthesis_argument"
        return annotated

    if "active_column_threshold_source" not in annotated.columns:
        annotated["active_column_threshold_source"] = "case_summary"
    missing = annotated["active_column_threshold"].isna()
    if missing.any():
        annotated.loc[missing, "active_column_threshold"] = threshold
        annotated.loc[missing, "active_column_threshold_source"] = "synthesis_argument"
    return annotated


def has_complete_multimodal_state(frame: pd.DataFrame) -> pd.Series:
    required = [
        "image_frames",
        "thermal_rows",
        "heat_flux_mean_w_cm2",
        "htc_mean_w_m2k",
        "ae_abs_energy_rate",
        "vapor_area_fraction_mean",
        "active_length_fraction_mean",
    ]
    complete = pd.Series(True, index=frame.index)
    for column in required:
        if column not in frame.columns:
            return pd.Series(False, index=frame.index)
        complete &= frame[column].notna()
    complete &= frame["image_frames"] > 0
    complete &= frame["thermal_rows"] > 0
    return complete


def annotate_ae_window_quality(data: pd.DataFrame, long_window_s: float = 120.0) -> pd.DataFrame:
    """Classify whether AE windows are suitable for manuscript-level interpretation."""
    annotated = data.copy()
    annotated["ae_window_quality"] = "not_assessed"
    annotated["ae_window_quality_reason"] = "missing_time_window_columns"
    annotated["ae_window_overlaps_previous_state"] = ""
    annotated["ae_interpretation_weight"] = np.nan

    required = {"case_label", "state_label", "time_start_s", "time_end_s"}
    if not required <= set(annotated.columns):
        return annotated

    start = pd.to_numeric(annotated["time_start_s"], errors="coerce")
    end = pd.to_numeric(annotated["time_end_s"], errors="coerce")
    annotated["thermal_window_span_s"] = end - start
    valid_windows = annotated.dropna(subset=["time_start_s", "time_end_s"]).copy()

    overlap_previous: dict[int, str] = {}
    for _, group in valid_windows.sort_values(["case_label", "time_start_s"]).groupby("case_label"):
        previous_end = None
        previous_label = None
        for row in group.itertuples():
            if previous_end is not None and float(row.time_start_s) < previous_end:
                overlap_previous[row.Index] = str(previous_label)
            previous_end = float(row.time_end_s)
            previous_label = row.state_label

    for index, row in annotated.iterrows():
        reasons = []
        if pd.isna(row.get("time_start_s")) or pd.isna(row.get("time_end_s")):
            annotated.at[index, "ae_window_quality"] = "not_assessed"
            annotated.at[index, "ae_window_quality_reason"] = "missing_time_window"
            continue

        if index in overlap_previous:
            reasons.append("overlaps_previous_state")
            annotated.at[index, "ae_window_overlaps_previous_state"] = overlap_previous[index]

        if float(row.get("thermal_window_span_s", 0.0)) > long_window_s:
            reasons.append(f"long_window_gt_{long_window_s:.0f}s")

        selection = row.get("thermal_window_selection")
        if pd.isna(selection):
            reasons.append("legacy_no_contiguous_window_metadata")
        elif str(selection).startswith("fallback"):
            reasons.append(str(selection))

        if any(
            reason.startswith("overlaps") or reason.startswith("fallback")
            for reason in reasons
        ):
            quality = "blocked"
            weight = 0.0
        elif reasons:
            quality = "caution"
            weight = 0.5
        else:
            quality = "pass"
            weight = 1.0

        annotated.at[index, "ae_window_quality"] = quality
        annotated.at[index, "ae_window_quality_reason"] = ";".join(reasons) if reasons else "none"
        annotated.at[index, "ae_interpretation_weight"] = weight
    return annotated


def build_trend_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Summarize rank-order trend strength behind manuscript-level claims."""
    rows = []
    for case, group in data.groupby("case_label", sort=False):
        ordered = group.sort_values("state_voltage").copy()
        nonblocked = quality_subset(ordered, excluded_quality="blocked")
        quality_counts = ordered.get(
            "ae_window_quality", pd.Series(index=ordered.index, dtype=object)
        )
        quality_counts = quality_counts.fillna("unknown").value_counts()
        vapor_max = ordered.loc[ordered["vapor_area_fraction_mean"].idxmax()]
        final_state = ordered.iloc[-1]
        rows.append(
            {
                "case_label": case,
                "states": len(ordered),
                "ae_pass_states": int(quality_counts.get("pass", 0)),
                "ae_caution_states": int(quality_counts.get("caution", 0)),
                "ae_blocked_states": int(quality_counts.get("blocked", 0)),
                "spearman_heat_flux_vapor_area": spearman_rank(
                    ordered, "heat_flux_mean_w_cm2", "vapor_area_fraction_mean"
                ),
                "spearman_heat_flux_active_length": spearman_rank(
                    ordered, "heat_flux_mean_w_cm2", "active_length_fraction_mean"
                ),
                "spearman_vapor_area_ae_all_states": spearman_rank(
                    ordered, "vapor_area_fraction_mean", "ae_abs_energy_rate"
                ),
                "spearman_vapor_area_ae_nonblocked": spearman_rank(
                    nonblocked, "vapor_area_fraction_mean", "ae_abs_energy_rate"
                ),
                "ae_nonblocked_states": len(nonblocked),
                "max_vapor_state": vapor_max["state_label"],
                "max_vapor_area_fraction": vapor_max["vapor_area_fraction_mean"],
                "heat_flux_at_max_vapor_w_cm2": vapor_max["heat_flux_mean_w_cm2"],
                "final_state": final_state["state_label"],
                "final_vapor_area_fraction": final_state["vapor_area_fraction_mean"],
                "final_heat_flux_w_cm2": final_state["heat_flux_mean_w_cm2"],
                "final_ae_abs_energy_rate": final_state["ae_abs_energy_rate"],
            }
        )
    return pd.DataFrame(rows)


def build_trend_sensitivity(data: pd.DataFrame) -> pd.DataFrame:
    """Report how strongly each trend depends on a single operating state."""
    relationships = [
        {
            "relationship": "heat_flux_vs_vapor_area",
            "x_column": "heat_flux_mean_w_cm2",
            "y_column": "vapor_area_fraction_mean",
            "exclude_blocked_ae": False,
        },
        {
            "relationship": "heat_flux_vs_active_length",
            "x_column": "heat_flux_mean_w_cm2",
            "y_column": "active_length_fraction_mean",
            "exclude_blocked_ae": False,
        },
        {
            "relationship": "vapor_area_vs_ae_nonblocked",
            "x_column": "vapor_area_fraction_mean",
            "y_column": "ae_abs_energy_rate",
            "exclude_blocked_ae": True,
        },
    ]
    rows = []
    for case, group in data.groupby("case_label", sort=False):
        ordered = group.sort_values("state_voltage").copy()
        for spec in relationships:
            subset = ordered
            if spec["exclude_blocked_ae"]:
                subset = quality_subset(ordered, excluded_quality="blocked")
            base_rho = spearman_rank(subset, spec["x_column"], spec["y_column"])
            loo = leave_one_state_out_spearman(subset, spec["x_column"], spec["y_column"])
            if loo.empty:
                rows.append(
                    {
                        "case_label": case,
                        "relationship": spec["relationship"],
                        "states_used": len(subset),
                        "baseline_spearman": base_rho,
                        "leave_one_out_min": np.nan,
                        "leave_one_out_max": np.nan,
                        "max_abs_delta": np.nan,
                        "most_influential_removed_state": "",
                        "spearman_without_most_influential_state": np.nan,
                        "removed_state_ae_quality": "",
                    }
                )
                continue

            deltas = (loo["spearman_without_state"] - base_rho).abs()
            most_influential_index = deltas.idxmax()
            most_influential = loo.loc[most_influential_index]
            rows.append(
                {
                    "case_label": case,
                    "relationship": spec["relationship"],
                    "states_used": len(subset),
                    "baseline_spearman": base_rho,
                    "leave_one_out_min": float(loo["spearman_without_state"].min()),
                    "leave_one_out_max": float(loo["spearman_without_state"].max()),
                    "max_abs_delta": float(deltas.loc[most_influential_index]),
                    "most_influential_removed_state": most_influential["removed_state_label"],
                    "spearman_without_most_influential_state": most_influential[
                        "spearman_without_state"
                    ],
                    "removed_state_ae_quality": most_influential.get(
                        "removed_state_ae_quality", ""
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_sampling_uncertainty(
    summary_data: pd.DataFrame,
    frame_metrics: pd.DataFrame | None = None,
    *,
    expected_frames: int = 8,
    relative_ci_warn: float = 0.25,
) -> pd.DataFrame:
    """Quantify sampled-frame uncertainty behind state-level optical metrics."""
    if frame_metrics is not None and not frame_metrics.empty:
        rows = build_sampling_uncertainty_from_frames(frame_metrics)
    else:
        rows = build_sampling_uncertainty_from_summary(summary_data)
    if rows.empty:
        return rows

    context_columns = [
        "case_label",
        "state_label",
        "state_voltage",
        "heat_flux_mean_w_cm2",
        "multimodal_complete",
    ]
    context = summary_data[[column for column in context_columns if column in summary_data.columns]]
    if {"case_label", "state_label"} <= set(context.columns):
        rows = rows.merge(context, on=["case_label", "state_label"], how="left")

    rows["sampling_warning"] = rows.apply(
        lambda row: sampling_warning(row, expected_frames, relative_ci_warn),
        axis=1,
    )
    sort_columns = [
        column for column in ["case_label", "state_voltage", "state_label"] if column in rows
    ]
    return rows.sort_values(sort_columns).reset_index(drop=True)


def attach_sampling_uncertainty_columns(
    data: pd.DataFrame,
    sampling_uncertainty: pd.DataFrame,
) -> pd.DataFrame:
    """Attach sampled-frame confidence intervals to state-level rows for plotting."""
    keys = ["case_label", "state_label"]
    if data.empty or sampling_uncertainty.empty:
        return data.copy()
    if not set(keys) <= set(data.columns) or not set(keys) <= set(sampling_uncertainty.columns):
        return data.copy()

    uncertainty_columns = [
        "image_frames_from_metrics",
        "vapor_area_fraction_ci95_half_width",
        "vapor_area_fraction_relative_ci95_half_width",
        "active_length_fraction_ci95_half_width",
        "active_length_fraction_relative_ci95_half_width",
        "sampling_warning",
    ]
    available = keys + [
        column for column in uncertainty_columns if column in sampling_uncertainty.columns
    ]
    existing = [column for column in available if column not in keys and column in data.columns]
    merged = data.drop(columns=existing, errors="ignore")
    return merged.merge(sampling_uncertainty[available], on=keys, how="left")


def build_active_threshold_sensitivity(
    summary_data: pd.DataFrame,
    frame_metrics: pd.DataFrame | None = None,
    *,
    sensitivity_delta_warn: float = 0.10,
) -> pd.DataFrame:
    """Audit whether active-length trends depend strongly on one threshold."""
    columns = [
        "case_label",
        "state_label",
        "state_voltage",
        "baseline_active_column_threshold",
        "active_threshold_sensitivity_status",
        "active_thresholds_evaluated",
        "active_length_baseline_mean",
        "active_length_min_mean",
        "active_length_max_mean",
        "active_length_threshold_range",
        "active_length_max_abs_delta_from_baseline",
        "most_sensitive_threshold",
        "threshold_sensitivity_limit",
        "next_verification_needed",
    ]
    if summary_data.empty:
        return pd.DataFrame(columns=columns)

    threshold_columns = active_threshold_columns(frame_metrics)
    if frame_metrics is None or frame_metrics.empty or not threshold_columns:
        rows = []
        for row in summary_data.itertuples():
            rows.append(
                {
                    "case_label": row.case_label,
                    "state_label": row.state_label,
                    "state_voltage": getattr(row, "state_voltage", np.nan),
                    "baseline_active_column_threshold": getattr(
                        row,
                        "active_column_threshold",
                        DEFAULT_ACTIVE_COLUMN_THRESHOLD,
                    ),
                    "active_threshold_sensitivity_status": "missing_threshold_sweep",
                    "active_thresholds_evaluated": "",
                    "active_length_baseline_mean": getattr(
                        row,
                        "active_length_fraction_mean",
                        np.nan,
                    ),
                    "active_length_min_mean": np.nan,
                    "active_length_max_mean": np.nan,
                    "active_length_threshold_range": np.nan,
                    "active_length_max_abs_delta_from_baseline": np.nan,
                    "most_sensitive_threshold": np.nan,
                    "threshold_sensitivity_limit": (
                        "per-frame active-length threshold sweep missing"
                    ),
                    "next_verification_needed": (
                        "Rerun per-case image analysis with "
                        "--active-column-sensitivity-thresholds."
                    ),
                }
            )
        return pd.DataFrame(rows)[columns]

    summary_lookup = summary_data.set_index(["case_label", "state_label"]).to_dict("index")
    rows = []
    for (case, state), group in frame_metrics.groupby(["case_label", "state_label"], sort=False):
        if (case, state) not in summary_lookup:
            continue
        summary_row = summary_lookup[(case, state)]
        if summary_row and not bool(summary_row.get("multimodal_complete", True)):
            continue
        threshold_means = {
            threshold_from_active_column(column): float(
                pd.to_numeric(group[column], errors="coerce").mean()
            )
            for column in threshold_columns
        }
        threshold_means = {
            threshold: value
            for threshold, value in threshold_means.items()
            if np.isfinite(threshold) and np.isfinite(value)
        }
        baseline_threshold = float(
            summary_row.get("active_column_threshold", DEFAULT_ACTIVE_COLUMN_THRESHOLD)
        )
        baseline_mean = value_at_threshold(
            threshold_means,
            baseline_threshold,
            summary_row.get("active_length_fraction_mean", np.nan),
        )

        if not threshold_means:
            status = "missing_threshold_sweep"
            active_min = np.nan
            active_max = np.nan
            active_range = np.nan
            max_delta = np.nan
            most_sensitive = np.nan
            limit = "per-frame active-length threshold sweep missing"
            next_needed = "Rerun per-case image analysis with threshold-sweep outputs."
        elif len(threshold_means) < 2 or not np.isfinite(baseline_mean):
            status = "partial_threshold_sweep"
            active_min = finite_min(pd.Series(list(threshold_means.values())))
            active_max = finite_max(pd.Series(list(threshold_means.values())))
            active_range = active_max - active_min if np.isfinite(active_max) else np.nan
            max_delta = np.nan
            most_sensitive = np.nan
            limit = "threshold sweep lacks a comparable baseline"
            next_needed = "Include the manuscript baseline threshold in the sweep."
        else:
            deltas = {
                threshold: abs(value - baseline_mean)
                for threshold, value in threshold_means.items()
            }
            most_sensitive = max(deltas, key=deltas.get)
            max_delta = float(deltas[most_sensitive])
            active_min = float(min(threshold_means.values()))
            active_max = float(max(threshold_means.values()))
            active_range = active_max - active_min
            status = "checked"
            if max_delta > sensitivity_delta_warn:
                limit = "active length is threshold-sensitive in this state"
                next_needed = (
                    "Treat active length as threshold-conditioned and inspect manual masks."
                )
            else:
                limit = "active length is not strongly threshold-sensitive over tested sweep"
                next_needed = "Retain threshold-conditioned wording and rerun after denser sampling."

        rows.append(
            {
                "case_label": case,
                "state_label": state,
                "state_voltage": summary_row.get("state_voltage", np.nan),
                "baseline_active_column_threshold": baseline_threshold,
                "active_threshold_sensitivity_status": status,
                "active_thresholds_evaluated": ";".join(
                    f"{threshold:.6g}" for threshold in sorted(threshold_means)
                ),
                "active_length_baseline_mean": baseline_mean,
                "active_length_min_mean": active_min,
                "active_length_max_mean": active_max,
                "active_length_threshold_range": active_range,
                "active_length_max_abs_delta_from_baseline": max_delta,
                "most_sensitive_threshold": most_sensitive,
                "threshold_sensitivity_limit": limit,
                "next_verification_needed": next_needed,
            }
        )

    output = pd.DataFrame(rows)
    if output.empty:
        return pd.DataFrame(columns=columns)
    return output[columns].sort_values(["case_label", "state_voltage", "state_label"])


def active_threshold_columns(frame_metrics: pd.DataFrame | None) -> list[str]:
    if frame_metrics is None or frame_metrics.empty:
        return []
    columns = [
        column
        for column in frame_metrics.columns
        if column.startswith(ACTIVE_LENGTH_THRESHOLD_PREFIX)
    ]
    return sorted(columns, key=threshold_from_active_column)


def threshold_from_active_column(column: str) -> float:
    suffix = column.replace(ACTIVE_LENGTH_THRESHOLD_PREFIX, "", 1)
    try:
        return float(suffix.replace("m", "-").replace("p", "."))
    except ValueError:
        return np.nan


def value_at_threshold(
    threshold_means: dict[float, float],
    target_threshold: float,
    fallback: object,
) -> float:
    for threshold, value in threshold_means.items():
        if abs(threshold - target_threshold) < 1e-12:
            return value
    fallback_value = pd.to_numeric(pd.Series([fallback]), errors="coerce").iloc[0]
    return float(fallback_value) if pd.notna(fallback_value) else np.nan


def build_thermal_response_checks(
    data: pd.DataFrame,
    *,
    heat_flux_drop_tol: float = 1e-9,
    htc_rho_warn: float = 0.50,
) -> pd.DataFrame:
    """Check which thermal-response claims are supported by reduced state summaries."""
    required = {
        "case_label",
        "state_voltage",
        "heat_flux_mean_w_cm2",
        "htc_mean_w_m2k",
        "pressure_drop_mean_kpa",
        "quality_x7_mean",
        "thermal_rows",
    }
    if data.empty or not required <= set(data.columns):
        return pd.DataFrame()

    rows = []
    for case, group in data.groupby("case_label", sort=False):
        ordered = group.sort_values("state_voltage").copy()
        heat_flux = pd.to_numeric(ordered["heat_flux_mean_w_cm2"], errors="coerce")
        htc = pd.to_numeric(ordered["htc_mean_w_m2k"], errors="coerce")
        pressure_drop = pd.to_numeric(ordered["pressure_drop_mean_kpa"], errors="coerce")
        quality = pd.to_numeric(ordered["quality_x7_mean"], errors="coerce")
        thermal_rows = pd.to_numeric(ordered["thermal_rows"], errors="coerce")

        heat_flux_drops = int((heat_flux.diff().dropna() < -heat_flux_drop_tol).sum())
        voltage_heat_flux_rho = spearman_rank(
            ordered,
            "state_voltage",
            "heat_flux_mean_w_cm2",
        )
        heat_flux_htc_rho = spearman_rank(
            ordered,
            "heat_flux_mean_w_cm2",
            "htc_mean_w_m2k",
        )
        heat_flux_quality_rho = spearman_rank(
            ordered,
            "heat_flux_mean_w_cm2",
            "quality_x7_mean",
        )
        heat_flux_pressure_rho = spearman_rank(
            ordered,
            "heat_flux_mean_w_cm2",
            "pressure_drop_mean_kpa",
        )

        reasons = []
        if heat_flux_drops:
            reasons.append("heat_flux_not_monotonic_with_voltage")
        if not np.isfinite(voltage_heat_flux_rho) or voltage_heat_flux_rho < 0.95:
            reasons.append("weak_voltage_heat_flux_rank")
        if not np.isfinite(heat_flux_htc_rho) or heat_flux_htc_rho < htc_rho_warn:
            reasons.append("weak_heat_flux_htc_rank")

        status = "state_level_supported" if not reasons else "needs_review"
        limiting_factors = reasons + [
            "mean_htc_averaged_over_seven_positions",
            "heat_loss_and_thermocouple_uncertainty_not_propagated",
            "camera_to_thermocouple_registration_missing",
        ]

        rows.append(
            {
                "case_label": case,
                "states": len(ordered),
                "heat_flux_min_w_cm2": finite_min(heat_flux),
                "heat_flux_max_w_cm2": finite_max(heat_flux),
                "htc_min_w_m2k": finite_min(htc),
                "htc_max_w_m2k": finite_max(htc),
                "pressure_drop_min_kpa": finite_min(pressure_drop),
                "pressure_drop_max_kpa": finite_max(pressure_drop),
                "quality_x7_min": finite_min(quality),
                "quality_x7_max": finite_max(quality),
                "spearman_voltage_heat_flux": voltage_heat_flux_rho,
                "spearman_heat_flux_htc": heat_flux_htc_rho,
                "spearman_heat_flux_quality_x7": heat_flux_quality_rho,
                "spearman_heat_flux_pressure_drop": heat_flux_pressure_rho,
                "heat_flux_drop_count_vs_voltage": heat_flux_drops,
                "minimum_thermal_rows": finite_min(thermal_rows),
                "maximum_thermal_window_span_s": finite_max(
                    pd.to_numeric(
                        ordered.get("thermal_window_span_s", pd.Series(dtype=float)),
                        errors="coerce",
                    )
                ),
                "thermal_context_status": status,
                "allowed_scope": (
                    "state-level reduced-thermal context; not local optical-thermal "
                    "registration or full HTC uncertainty validation"
                ),
                "limiting_factors": ";".join(limiting_factors),
            }
        )
    return pd.DataFrame(rows)


def build_ae_evidence_tiers(
    data: pd.DataFrame,
    trend_summary: pd.DataFrame,
    trend_sensitivity: pd.DataFrame,
    *,
    min_pass_fraction: float = 0.50,
    sensitivity_delta_warn: float = 0.30,
    verification_status: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Classify the manuscript-safe claim strength for each case's AE evidence."""
    sensitivity = trend_sensitivity[
        trend_sensitivity["relationship"] == "vapor_area_vs_ae_nonblocked"
    ].copy()
    sensitivity = sensitivity.set_index("case_label") if not sensitivity.empty else sensitivity
    verification = ae_verification_lookup(verification_status)

    rows = []
    for trend_row in trend_summary.sort_values("case_label").itertuples():
        case = trend_row.case_label
        case_verification = verification.get(str(case), {})
        trigger_synchronization_verified = bool(
            case_verification.get("trigger_synchronization_verified", False)
        )
        sensor_coupling_verified = bool(
            case_verification.get("sensor_coupling_verified", False)
        )
        states = int(trend_row.states)
        pass_states = int(trend_row.ae_pass_states)
        caution_states = int(trend_row.ae_caution_states)
        blocked_states = int(trend_row.ae_blocked_states)
        nonblocked_states = int(trend_row.ae_nonblocked_states)
        pass_fraction = pass_states / states if states else np.nan
        blocked_fraction = blocked_states / states if states else np.nan
        nonblocked_fraction = nonblocked_states / states if states else np.nan

        max_delta = np.nan
        influential_state = ""
        if not sensitivity.empty and case in sensitivity.index:
            max_delta = float(sensitivity.loc[case, "max_abs_delta"])
            influential_state = str(
                sensitivity.loc[case, "most_influential_removed_state"]
            )

        reasons = []
        if blocked_states:
            reasons.append("overlap_blocked_windows")
        if pass_states == 0:
            reasons.append("no_pass_quality_windows")
        elif pass_fraction < min_pass_fraction:
            reasons.append("low_pass_quality_fraction")
        if np.isfinite(max_delta) and max_delta > sensitivity_delta_warn:
            reasons.append("state_sensitive_vapor_ae_rank")
        if nonblocked_states < 5:
            reasons.append("few_nonblocked_states")
        if not trigger_synchronization_verified:
            reasons.append("trigger_synchronization_unverified")
        if not sensor_coupling_verified:
            reasons.append("sensor_coupling_unverified")

        if blocked_states:
            tier = "blocked_mixed_window_snapshot"
            claim_scope = (
                "state-matched screening only; exclude blocked windows from AE correlations"
            )
        elif pass_states == 0:
            tier = "exploratory_legacy_window_snapshot"
            claim_scope = "state-matched exploratory comparison only"
        elif np.isfinite(max_delta) and max_delta > sensitivity_delta_warn:
            tier = "state_sensitive_screening"
            claim_scope = "screening comparison with explicit influential-state caveat"
        elif pass_fraction < min_pass_fraction:
            tier = "limited_screening"
            claim_scope = "limited screening comparison after trigger and coupling audit"
        else:
            tier = "screening_supported"
            claim_scope = "screening-level AE/optical agreement, not a regime classifier"

        rows.append(
            {
                "case_label": case,
                "ae_evidence_tier": tier,
                "recommended_claim_scope": claim_scope,
                "states": states,
                "ae_pass_states": pass_states,
                "ae_caution_states": caution_states,
                "ae_blocked_states": blocked_states,
                "ae_nonblocked_states": nonblocked_states,
                "ae_pass_fraction": pass_fraction,
                "ae_blocked_fraction": blocked_fraction,
                "ae_nonblocked_fraction": nonblocked_fraction,
                "vapor_ae_spearman_nonblocked": trend_row.spearman_vapor_area_ae_nonblocked,
                "vapor_ae_max_abs_delta": max_delta,
                "most_influential_removed_state": influential_state,
                "trigger_synchronization_verified": trigger_synchronization_verified,
                "sensor_coupling_verified": sensor_coupling_verified,
                "limiting_factors": ";".join(reasons),
            }
        )
    return pd.DataFrame(rows)


def build_ae_readiness_matrix(
    data: pd.DataFrame,
    ae_evidence_tiers: pd.DataFrame,
    *,
    min_pass_states: int = 3,
    min_pass_fraction: float = 0.50,
    min_nonblocked_states: int = 5,
    verification_status: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Audit whether AE evidence is ready for quantitative manuscript claims."""
    if data.empty or "case_label" not in data:
        return pd.DataFrame()

    tier_lookup = {}
    if not ae_evidence_tiers.empty and "case_label" in ae_evidence_tiers:
        tier_lookup = ae_evidence_tiers.set_index("case_label").to_dict("index")
    verification = ae_verification_lookup(verification_status)

    rows = []
    for case, group in data.groupby("case_label", sort=True):
        case_verification = verification.get(str(case), {})
        states = len(group)
        quality = group.get("ae_window_quality", pd.Series("unknown", index=group.index))
        quality = quality.fillna("unknown").astype(str)
        pass_states = int((quality == "pass").sum())
        caution_states = int((quality == "caution").sum())
        blocked_states = int((quality == "blocked").sum())
        nonblocked_states = states - blocked_states
        pass_fraction = pass_states / states if states else np.nan
        blocked_fraction = blocked_states / states if states else np.nan
        nonblocked_fraction = nonblocked_states / states if states else np.nan

        reasons = group.get(
            "ae_window_quality_reason",
            pd.Series("", index=group.index),
        )
        reasons = reasons.fillna("").astype(str)
        overlap_blocked_states = int(reasons.str.contains("overlaps_previous_state").sum())
        long_window_states = int(reasons.str.contains("long_window_gt").sum())
        legacy_metadata_states = int(
            reasons.str.contains("legacy_no_contiguous_window_metadata").sum()
        )

        contiguous_metadata_states = 0
        if "thermal_window_selection" in group:
            selections = group["thermal_window_selection"].fillna("").astype(str).str.strip()
            contiguous_metadata_states = int((selections != "").sum())
        contiguous_metadata_fraction = contiguous_metadata_states / states if states else np.nan

        tier_row = tier_lookup.get(case, {})
        tier = str(tier_row.get("ae_evidence_tier", "not_assessed"))
        tier_limits = str(tier_row.get("limiting_factors", ""))

        trigger_synchronization_verified = bool(
            case_verification.get("trigger_synchronization_verified", False)
        )
        sensor_coupling_verified = bool(
            case_verification.get("sensor_coupling_verified", False)
        )
        enough_pass_windows = (
            pass_states >= min_pass_states
            and np.isfinite(pass_fraction)
            and pass_fraction >= min_pass_fraction
        )
        enough_nonblocked_states = nonblocked_states >= min_nonblocked_states
        no_overlap_blockers = blocked_states == 0 and overlap_blocked_states == 0
        contiguous_metadata_complete = contiguous_metadata_states == states
        quantitative_ready = all(
            [
                enough_pass_windows,
                enough_nonblocked_states,
                no_overlap_blockers,
                contiguous_metadata_complete,
                trigger_synchronization_verified,
                sensor_coupling_verified,
            ]
        )
        screening_ready = enough_nonblocked_states and nonblocked_states > 0

        blockers = []
        if not enough_pass_windows:
            blockers.append("insufficient_pass_quality_windows")
        if not no_overlap_blockers:
            blockers.append("overlap_blocked_windows")
        if not contiguous_metadata_complete:
            blockers.append("missing_contiguous_window_metadata")
        if not trigger_synchronization_verified:
            blockers.append("trigger_synchronization_unverified")
        if not sensor_coupling_verified:
            blockers.append("sensor_coupling_unverified")
        if not enough_nonblocked_states:
            blockers.append("few_nonblocked_states")
        if "state_sensitive_vapor_ae_rank" in tier_limits:
            blockers.append("state_sensitive_vapor_ae_rank")

        if quantitative_ready:
            status = "quantitative_ready"
            action = "AE may be used for quantitative state-matched screening claims."
        elif blocked_states:
            status = "blocked_for_quantitative_use"
            action = (
                "Exclude overlap-blocked windows and rerun summaries with contiguous "
                "window selection."
            )
        elif legacy_metadata_states or contiguous_metadata_states < states:
            status = "legacy_screening_only"
            action = (
                "Regenerate per-case summaries with contiguous-window provenance "
                "before strengthening AE claims."
            )
        elif not enough_nonblocked_states:
            status = "insufficient_state_coverage"
            action = "Add enough nonblocked AE states before reporting AE trends."
        else:
            status = "screening_only_pending_trigger_coupling"
            action = "Verify trigger timing and AE sensor coupling before quantitative use."

        rows.append(
            {
                "case_label": case,
                "ae_evidence_tier": tier,
                "ae_readiness_status": status,
                "quantitative_ae_ready": quantitative_ready,
                "screening_ae_ready": screening_ready,
                "states": states,
                "ae_pass_states": pass_states,
                "ae_caution_states": caution_states,
                "ae_blocked_states": blocked_states,
                "ae_nonblocked_states": nonblocked_states,
                "ae_pass_fraction": pass_fraction,
                "ae_blocked_fraction": blocked_fraction,
                "ae_nonblocked_fraction": nonblocked_fraction,
                "minimum_pass_states_required": min_pass_states,
                "minimum_pass_fraction_required": min_pass_fraction,
                "minimum_nonblocked_states_required": min_nonblocked_states,
                "overlap_blocked_states": overlap_blocked_states,
                "long_window_states": long_window_states,
                "legacy_no_contiguous_metadata_states": legacy_metadata_states,
                "contiguous_window_metadata_states": contiguous_metadata_states,
                "contiguous_window_metadata_fraction": contiguous_metadata_fraction,
                "trigger_synchronization_verified": trigger_synchronization_verified,
                "sensor_coupling_verified": sensor_coupling_verified,
                "blocking_criteria": ";".join(blockers) if blockers else "none",
                "recommended_next_action": action,
            }
        )
    return pd.DataFrame(rows)


def build_ae_remediation_plan(
    data: pd.DataFrame,
    trend_sensitivity: pd.DataFrame,
    ae_readiness_matrix: pd.DataFrame,
    verification_status: pd.DataFrame,
) -> pd.DataFrame:
    """Turn AE readiness failures into auditable case-level next actions."""
    if data.empty or ae_readiness_matrix.empty:
        return pd.DataFrame()

    verification = ae_verification_lookup(verification_status)
    sensitivity = trend_sensitivity[
        trend_sensitivity["relationship"] == "vapor_area_vs_ae_nonblocked"
    ].copy()
    sensitivity = sensitivity.set_index("case_label") if not sensitivity.empty else sensitivity

    rows = []
    for row in ae_readiness_matrix.sort_values("case_label").itertuples():
        case = str(row.case_label)
        group = data[data["case_label"].astype(str) == case].copy()
        reasons = group.get("ae_window_quality_reason", pd.Series("", index=group.index))
        reasons = reasons.fillna("").astype(str)
        quality = group.get("ae_window_quality", pd.Series("", index=group.index))
        quality = quality.fillna("").astype(str)
        blocked = group[quality == "blocked"]
        long_window = group[reasons.str.contains("long_window_gt", regex=False)]
        legacy = group[reasons.str.contains("legacy_no_contiguous_window_metadata", regex=False)]

        influential_state = ""
        influential_delta = np.nan
        if not sensitivity.empty and case in sensitivity.index:
            influential_state = str(sensitivity.loc[case, "most_influential_removed_state"])
            influential_delta = float(sensitivity.loc[case, "max_abs_delta"])

        blocking_criteria = str(row.blocking_criteria)
        has_overlap = "overlap_blocked_windows" in blocking_criteria
        has_state_sensitivity = "state_sensitive_vapor_ae_rank" in blocking_criteria
        missing_metadata = "missing_contiguous_window_metadata" in blocking_criteria
        trigger_missing = "trigger_synchronization_unverified" in blocking_criteria
        coupling_missing = "sensor_coupling_unverified" in blocking_criteria

        if has_overlap or has_state_sensitivity:
            priority = 1
        elif missing_metadata:
            priority = 2
        elif trigger_missing or coupling_missing:
            priority = 3
        else:
            priority = 4

        if has_overlap:
            primary_action = (
                "rerun per-case analysis with contiguous-window selection and remove "
                "or replace remaining overlap-blocked AE windows"
            )
        elif missing_metadata:
            primary_action = (
                "rerun per-case analysis so thermal_window_selection provenance is "
                "present for every state"
            )
        else:
            primary_action = "verify trigger timing and AE sensor coupling records"

        verification_actions = []
        if trigger_missing:
            verification_actions.append("attach acquisition trigger or shared-timebase evidence")
        if coupling_missing:
            verification_actions.append("audit AE sensor mounting/coupling for both channels")
        if has_state_sensitivity and influential_state:
            verification_actions.append(
                f"inspect waveform and matching window for influential state {influential_state}"
            )

        rows.append(
            {
                "case_label": case,
                "remediation_priority": priority,
                "current_ae_readiness_status": row.ae_readiness_status,
                "blocked_state_labels": join_state_labels(blocked),
                "long_window_state_labels": join_state_labels(long_window),
                "legacy_metadata_state_count": len(legacy),
                "contiguous_window_metadata_fraction": row.contiguous_window_metadata_fraction,
                "most_influential_ae_state": influential_state,
                "most_influential_ae_delta_rho": influential_delta,
                "trigger_synchronization_verified": bool(
                    verification.get(case, {}).get("trigger_synchronization_verified", False)
                ),
                "sensor_coupling_verified": bool(
                    verification.get(case, {}).get("sensor_coupling_verified", False)
                ),
                "primary_rerun_action": primary_action,
                "verification_actions": ";".join(verification_actions)
                if verification_actions
                else "none",
                "minimum_quantitative_gate": (
                    f">={row.minimum_pass_states_required} pass-quality states; "
                    f">={row.minimum_pass_fraction_required:.0%} pass fraction; "
                    "0 overlap blockers; complete contiguous-window metadata; "
                    "trigger_synchronization_verified=True; sensor_coupling_verified=True"
                ),
                "manuscript_rule_until_closed": (
                    "Keep AE claims screening-only and exclude blocked windows from "
                    "quantitative AE correlations."
                ),
            }
        )
    return pd.DataFrame(rows)


def build_segmentation_validation_plan(
    data: pd.DataFrame,
    sampling_uncertainty: pd.DataFrame | None = None,
    *,
    minimum_manual_masks: int = 8,
    relative_ci_priority: float = 0.25,
) -> pd.DataFrame:
    """Select held-out manual-mask targets needed before instance-level claims."""
    columns = [
        "case_label",
        "state_label",
        "validation_role",
        "selection_reasons",
        "state_voltage",
        "heat_flux_mean_w_cm2",
        "vapor_area_fraction_mean",
        "active_length_fraction_mean",
        "image_frames",
        "vapor_area_fraction_relative_ci95_half_width",
        "sampling_warning",
        "minimum_manual_masks",
        "recommended_annotation_action",
        "validation_status",
        "claim_gate_until_complete",
    ]
    if data.empty:
        return pd.DataFrame(columns=columns)

    plan_data = data.copy()
    if sampling_uncertainty is not None and not sampling_uncertainty.empty:
        keys = ["case_label", "state_label"]
        merge_columns = [
            "case_label",
            "state_label",
            "vapor_area_fraction_relative_ci95_half_width",
            "sampling_warning",
        ]
        available = [column for column in merge_columns if column in sampling_uncertainty.columns]
        if set(keys) <= set(available):
            for column in available:
                if column not in keys and column in plan_data.columns:
                    plan_data = plan_data.drop(columns=[column])
            plan_data = plan_data.merge(sampling_uncertainty[available], on=keys, how="left")

    rows = []
    for case, group in plan_data.groupby("case_label", sort=False):
        ordered = group.sort_values("state_voltage").copy()
        candidates: dict[tuple[str, str], dict[str, object]] = {}

        add_segmentation_candidate(
            candidates,
            ordered.iloc[0],
            "onset_or_low_vapor",
            "lowest-voltage state anchors false-positive and near-onset performance",
            minimum_manual_masks,
        )

        voltage = pd.to_numeric(ordered["state_voltage"], errors="coerce")
        if voltage.notna().any():
            median_index = (voltage - voltage.median()).abs().idxmin()
            mid_row = ordered.loc[median_index]
        else:
            mid_row = ordered.iloc[len(ordered) // 2]
        add_segmentation_candidate(
            candidates,
            mid_row,
            "developed_mid_sweep",
            "mid-sweep state tests developed-boiling mask separation",
            minimum_manual_masks,
        )

        vapor = pd.to_numeric(ordered["vapor_area_fraction_mean"], errors="coerce")
        if vapor.notna().any():
            high_vapor_row = ordered.loc[vapor.idxmax()]
        else:
            high_vapor_row = ordered.iloc[-1]
        add_segmentation_candidate(
            candidates,
            high_vapor_row,
            "high_vapor_or_chf_adjacent",
            "highest projected-vapor state tests dense-mask merging near CHF-adjacent conditions",
            minimum_manual_masks,
        )

        relative = pd.to_numeric(
            ordered.get(
                "vapor_area_fraction_relative_ci95_half_width",
                pd.Series(np.nan, index=ordered.index),
            ),
            errors="coerce",
        )
        warnings = ordered.get("sampling_warning", pd.Series("none", index=ordered.index))
        has_warning = warnings.fillna("none").astype(str) != "none"
        if relative.notna().any() and (
            float(relative.max()) > relative_ci_priority or bool(has_warning.any())
        ):
            uncertainty_row = ordered.loc[relative.idxmax()]
            add_segmentation_candidate(
                candidates,
                uncertainty_row,
                "highest_sampling_uncertainty",
                (
                    "largest projected-vapor relative 95% CI targets sampling-sensitive "
                    "mask behavior"
                ),
                minimum_manual_masks,
            )

        rows.extend(finalize_segmentation_candidates(candidates))

    if not rows:
        return pd.DataFrame(columns=columns)
    plan = pd.DataFrame(rows)
    return plan[columns].sort_values(["case_label", "state_voltage", "state_label"])


def add_segmentation_candidate(
    candidates: dict[tuple[str, str], dict[str, object]],
    row: pd.Series,
    role: str,
    reason: str,
    minimum_manual_masks: int,
) -> None:
    key = (str(row.get("case_label", "")), str(row.get("state_label", "")))
    if key not in candidates:
        image_frames = numeric_value(row.get("image_frames", np.nan))
        action = (
            f"Annotate at least {minimum_manual_masks} held-out ROI masks for this "
            "state and compare model masks against manual masks."
        )
        if np.isfinite(image_frames) and image_frames < minimum_manual_masks:
            action = (
                f"Annotate all {int(image_frames)} tracked frames and add raw-sequence "
                f"frames if available to reach {minimum_manual_masks} held-out masks."
            )
        candidates[key] = {
            "case_label": key[0],
            "state_label": key[1],
            "validation_role": [],
            "selection_reasons": [],
            "state_voltage": row.get("state_voltage", np.nan),
            "heat_flux_mean_w_cm2": row.get("heat_flux_mean_w_cm2", np.nan),
            "vapor_area_fraction_mean": row.get("vapor_area_fraction_mean", np.nan),
            "active_length_fraction_mean": row.get("active_length_fraction_mean", np.nan),
            "image_frames": row.get("image_frames", np.nan),
            "vapor_area_fraction_relative_ci95_half_width": row.get(
                "vapor_area_fraction_relative_ci95_half_width",
                np.nan,
            ),
            "sampling_warning": row.get("sampling_warning", "none"),
            "minimum_manual_masks": minimum_manual_masks,
            "recommended_annotation_action": action,
            "validation_status": "planned_not_complete",
            "claim_gate_until_complete": (
                "Do not report individual bubble count, size, coalescence, or "
                "instance-separation statistics."
            ),
        }
    record = candidates[key]
    roles = record["validation_role"]
    reasons = record["selection_reasons"]
    if role not in roles:
        roles.append(role)
    if reason not in reasons:
        reasons.append(reason)


def finalize_segmentation_candidates(
    candidates: dict[tuple[str, str], dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for record in candidates.values():
        row = record.copy()
        row["validation_role"] = ";".join(row["validation_role"])
        row["selection_reasons"] = ";".join(row["selection_reasons"])
        rows.append(row)
    return rows


def build_claim_evidence_matrix(
    data: pd.DataFrame,
    trend_summary: pd.DataFrame,
    trend_sensitivity: pd.DataFrame,
    sampling_uncertainty: pd.DataFrame,
    thermal_response: pd.DataFrame,
    segmentation_plan: pd.DataFrame,
    ae_evidence_tiers: pd.DataFrame,
    ae_readiness_matrix: pd.DataFrame,
    active_threshold_sensitivity: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Convert generated evidence into manuscript-safe claim boundaries."""
    sampling_warning_count = 0
    max_relative_ci = np.nan
    max_relative_ci_label = ""
    if not sampling_uncertainty.empty and "sampling_warning" in sampling_uncertainty:
        sampling_warning_count = int(
            (sampling_uncertainty["sampling_warning"].fillna("none") != "none").sum()
        )
        if "vapor_area_fraction_relative_ci95_half_width" in sampling_uncertainty:
            relative = pd.to_numeric(
                sampling_uncertainty["vapor_area_fraction_relative_ci95_half_width"],
                errors="coerce",
            )
            if relative.notna().any():
                index = relative.idxmax()
                row = sampling_uncertainty.loc[index]
                max_relative_ci = float(relative.loc[index])
                max_relative_ci_label = f"{row.case_label}/{row.state_label}"

    vapor_rhos = numeric_column(trend_summary, "spearman_heat_flux_vapor_area")
    active_rhos = numeric_column(trend_summary, "spearman_heat_flux_active_length")
    vapor_min_loo = sensitivity_minimum(
        trend_sensitivity,
        "heat_flux_vs_vapor_area",
        "leave_one_out_min",
    )
    active_min_loo = sensitivity_minimum(
        trend_sensitivity,
        "heat_flux_vs_active_length",
        "leave_one_out_min",
    )
    vapor_max_delta = sensitivity_maximum(
        trend_sensitivity,
        "heat_flux_vs_vapor_area",
        "max_abs_delta",
    )
    active_max_delta = sensitivity_maximum(
        trend_sensitivity,
        "heat_flux_vs_active_length",
        "max_abs_delta",
    )
    active_threshold_status_summary = "missing"
    active_threshold_missing_count = 0
    active_threshold_checked_count = 0
    active_threshold_max_delta = np.nan
    active_threshold_max_delta_label = ""
    active_threshold_limits = "active_threshold_sensitivity_missing"
    if active_threshold_sensitivity is not None and not active_threshold_sensitivity.empty:
        status_counts = (
            active_threshold_sensitivity["active_threshold_sensitivity_status"]
            .fillna("unknown")
            .value_counts()
            .sort_index()
        )
        active_threshold_status_summary = ", ".join(
            f"{status}={count}" for status, count in status_counts.items()
        )
        active_threshold_missing_count = int(
            (
                active_threshold_sensitivity["active_threshold_sensitivity_status"].fillna("")
                != "checked"
            ).sum()
        )
        active_threshold_checked_count = int(
            (
                active_threshold_sensitivity["active_threshold_sensitivity_status"].fillna("")
                == "checked"
            ).sum()
        )
        if "active_length_max_abs_delta_from_baseline" in active_threshold_sensitivity:
            deltas = pd.to_numeric(
                active_threshold_sensitivity["active_length_max_abs_delta_from_baseline"],
                errors="coerce",
            )
            if deltas.notna().any():
                index = deltas.idxmax()
                row = active_threshold_sensitivity.loc[index]
                active_threshold_max_delta = float(deltas.loc[index])
                active_threshold_max_delta_label = f"{row.case_label}/{row.state_label}"
        active_threshold_limits = collapse_reasons(
            active_threshold_sensitivity["threshold_sensitivity_limit"]
            .fillna("")
            .astype(str)
            .tolist()
        )

    ae_tiers = []
    ae_limits = []
    ae_pass_states = 0
    ae_blocked_states = 0
    ae_sensitive_cases = []
    if not ae_evidence_tiers.empty:
        for row in ae_evidence_tiers.sort_values("case_label").itertuples():
            ae_tiers.append(f"{row.case_label}={row.ae_evidence_tier}")
            ae_limits.append(str(row.limiting_factors))
            ae_pass_states += int(row.ae_pass_states)
            ae_blocked_states += int(row.ae_blocked_states)
            delta = float(row.vapor_ae_max_abs_delta)
            if np.isfinite(delta) and delta > 0.30:
                ae_sensitive_cases.append(f"{row.case_label}/{row.most_influential_removed_state}")

    ae_readiness_statuses = []
    ae_readiness_limits = []
    ae_quantitative_ready_cases = 0
    if not ae_readiness_matrix.empty:
        for row in ae_readiness_matrix.sort_values("case_label").itertuples():
            ae_readiness_statuses.append(f"{row.case_label}={row.ae_readiness_status}")
            ae_readiness_limits.append(str(row.blocking_criteria))
            if bool(row.quantitative_ae_ready):
                ae_quantitative_ready_cases += 1

    thermal_status = "incomplete_evidence"
    thermal_summary = "Thermal response check is missing."
    thermal_limits = "thermal_response_check_missing"
    if not thermal_response.empty:
        htc_rhos = numeric_column(thermal_response, "spearman_heat_flux_htc")
        voltage_rhos = numeric_column(thermal_response, "spearman_voltage_heat_flux")
        heat_flux_min = finite_min(thermal_response["heat_flux_min_w_cm2"])
        heat_flux_max = finite_max(thermal_response["heat_flux_max_w_cm2"])
        htc_min = finite_min(thermal_response["htc_min_w_m2k"])
        htc_max = finite_max(thermal_response["htc_max_w_m2k"])
        quality_min = finite_min(thermal_response["quality_x7_min"])
        quality_max = finite_max(thermal_response["quality_x7_max"])
        window_max = finite_max(thermal_response["maximum_thermal_window_span_s"])
        status_values = thermal_response["thermal_context_status"].fillna("unknown")
        if bool((status_values == "state_level_supported").all()):
            thermal_status = "supported_with_limits"
        else:
            thermal_status = "state_sensitive_or_mixed"
        thermal_summary = (
            f"heat-flux range {heat_flux_min:.2f} to {heat_flux_max:.2f} W/cm2; "
            f"rho(voltage, q'') range {format_range(voltage_rhos)}; "
            f"rho(q'', mean HTC) range {format_range(htc_rhos)}; "
            f"quality_x7 range {quality_min:.2f} to {quality_max:.2f}; "
            f"maximum thermal window span {window_max:.1f} s."
        )
        thermal_limits = collapse_reasons(
            thermal_response["limiting_factors"].fillna("").astype(str).tolist()
        )

    segmentation_plan_rows = 0
    segmentation_plan_cases = 0
    segmentation_status_summary = "missing"
    segmentation_roles = "missing"
    if not segmentation_plan.empty:
        segmentation_plan_rows = len(segmentation_plan)
        segmentation_plan_cases = segmentation_plan["case_label"].nunique()
        segmentation_status_summary = ", ".join(
            f"{status}={count}"
            for status, count in segmentation_plan["validation_status"]
            .fillna("unknown")
            .value_counts()
            .sort_index()
            .items()
        )
        segmentation_roles = collapse_reasons(
            segmentation_plan["validation_role"].fillna("").astype(str).tolist()
        )

    complete_states = len(data)
    rows = [
        {
            "claim_id": "optical_heat_flux_trend",
            "manuscript_claim": (
                "Projected vapor area generally increases with heat flux across the "
                "current four-case operating-state dataset."
            ),
            "support_status": support_status_from_positive_rhos(vapor_rhos, vapor_min_loo),
            "allowed_scope": (
                "State-level, projected 2D vapor-occupation trend in the current "
                "ROI and operating-state snapshot."
            ),
            "evidence_artifacts": (
                "cross_case_trend_summary.csv; cross_case_trend_sensitivity.csv; "
                "cross_case_sampling_uncertainty.csv; "
                "cross_case_segmentation_validation_plan.csv"
            ),
            "evidence_summary": (
                f"{complete_states} complete states; "
                f"rho(q'', alpha_A) range {format_range(vapor_rhos)}; "
                f"leave-one-state-out minimum {format_float(vapor_min_loo)}; "
                f"max |delta rho| {format_float(vapor_max_delta)}; "
                f"manual-mask validation targets={segmentation_plan_rows}."
            ),
            "blocking_or_limiting_factors": (
                f"{sampling_warning_count} sampling-warning states; largest relative "
                f"95% CI {format_float(max_relative_ci)} at {max_relative_ci_label}; "
                "projected area is not volumetric void fraction; manual segmentation "
                "validation remains incomplete."
            ),
            "next_verification_needed": (
                "Complete the generated segmentation-validation plan and regenerate from "
                "denser or full image sequences."
            ),
        },
        {
            "claim_id": "active_length_heat_flux_trend",
            "manuscript_claim": (
                "Active vapor-covered streamwise length generally increases with heat flux."
            ),
            "support_status": support_status_from_positive_rhos(active_rhos, active_min_loo),
            "allowed_scope": (
                "State-level active-length metric using phi_thr=0.05 within the current ROI."
            ),
            "evidence_artifacts": (
                "cross_case_trend_summary.csv; cross_case_trend_sensitivity.csv; "
                "cross_case_active_threshold_sensitivity.csv; "
                "combined_multimodal_analysis_states.csv"
            ),
            "evidence_summary": (
                f"rho(q'', L_A) range {format_range(active_rhos)}; "
                f"leave-one-state-out minimum {format_float(active_min_loo)}; "
                f"max |delta rho| {format_float(active_max_delta)}; "
                f"threshold-sensitivity statuses: {active_threshold_status_summary}; "
                f"checked states={active_threshold_checked_count}; "
                f"max active-length threshold delta="
                f"{format_float(active_threshold_max_delta)} at "
                f"{active_threshold_max_delta_label if active_threshold_max_delta_label else 'n/a'}."
            ),
            "blocking_or_limiting_factors": (
                "Active length depends on the stated phi_thr=0.05 criterion and camera ROI; "
                f"{active_threshold_missing_count} states lack completed threshold-sweep "
                f"evidence; {active_threshold_limits}."
            ),
            "next_verification_needed": (
                "Regenerate per-case image metrics with active-column threshold sweeps "
                "and check camera-field registration."
            ),
        },
        {
            "claim_id": "state_level_thermal_response",
            "manuscript_claim": (
                "Reduced thermal measurements provide state-level heat-flux and mean-HTC "
                "context for interpreting vapor trends."
            ),
            "support_status": thermal_status,
            "allowed_scope": (
                "State-level reduced-thermal context from voltage-matched workbook rows; "
                "not local optical-thermal registration."
            ),
            "evidence_artifacts": (
                "cross_case_thermal_response_checks.csv; "
                "combined_multimodal_analysis_states.csv"
            ),
            "evidence_summary": thermal_summary,
            "blocking_or_limiting_factors": thermal_limits,
            "next_verification_needed": (
                "Audit heat-loss correction, HTC equations, thermocouple uncertainty, "
                "and camera-to-thermocouple registration."
            ),
        },
        {
            "claim_id": "ae_screening_comparison",
            "manuscript_claim": (
                "AE absolute-energy trends can be compared with visible vapor metrics as "
                "quality-tagged screening diagnostics."
            ),
            "support_status": "screening_only",
            "allowed_scope": (
                "State-matched, quality-tagged AE screening comparison; exclude blocked "
                "windows from quantitative AE correlations."
            ),
            "evidence_artifacts": (
                "cross_case_ae_readiness_matrix.csv; "
                "cross_case_ae_remediation_plan.csv; "
                "cross_case_ae_verification_status.csv; "
                "cross_case_ae_evidence_tiers.csv; cross_case_trend_sensitivity.csv"
            ),
            "evidence_summary": (
                f"AE tiers: {'; '.join(ae_tiers)}; pass states={ae_pass_states}; "
                f"blocked states={ae_blocked_states}; sensitive cases="
                f"{'; '.join(ae_sensitive_cases) if ae_sensitive_cases else 'none'}; "
                f"readiness statuses: "
                f"{'; '.join(ae_readiness_statuses) if ae_readiness_statuses else 'missing'}; "
                f"quantitative-ready cases={ae_quantitative_ready_cases}."
            ),
            "blocking_or_limiting_factors": collapse_reasons(
                ae_limits + ae_readiness_limits
            ),
            "next_verification_needed": (
                "Verify acquisition triggers, rerun per-case summaries with contiguous "
                "windows, and audit AE sensor coupling."
            ),
        },
        {
            "claim_id": "ae_regime_classifier_or_lead_lag",
            "manuscript_claim": (
                "AE features classify boiling regime or provide optical/acoustic lead-lag timing."
            ),
            "support_status": "not_supported_current_snapshot",
            "allowed_scope": (
                "Do not make quantitative AE regime-classifier, timing, or lead-lag claims."
            ),
            "evidence_artifacts": (
                "cross_case_ae_readiness_matrix.csv; "
                "cross_case_ae_remediation_plan.csv; "
                "cross_case_ae_verification_status.csv; "
                "cross_case_ae_evidence_tiers.csv; Figure_7_synchronization_audit.pdf"
            ),
            "evidence_summary": (
                f"No cases pass quantitative AE readiness in the tracked snapshot; "
                f"pass-quality AE windows={ae_pass_states}; "
                f"{ae_blocked_states} AE states are overlap-blocked."
            ),
            "blocking_or_limiting_factors": (
                "trigger_synchronization_unverified; sensor_coupling_unverified; "
                "legacy_no_contiguous_window_metadata"
            ),
            "next_verification_needed": (
                "Use trigger records or acquisition metadata and waveform-level AE checks."
            ),
        },
        {
            "claim_id": "bubble_instance_statistics",
            "manuscript_claim": (
                "Detected masks support individual bubble count, size, or coalescence "
                "statistics."
            ),
            "support_status": "not_supported_current_snapshot",
            "allowed_scope": (
                "Limit image claims to projected vapor coverage and active streamwise length."
            ),
            "evidence_artifacts": (
                "cross_case_segmentation_validation_plan.csv; "
                "docs/model_artifact_manifest.csv; model/evaluation artifacts"
            ),
            "evidence_summary": (
                f"Manual-mask validation plan lists {segmentation_plan_rows} target "
                f"states across {segmentation_plan_cases} cases; statuses: "
                f"{segmentation_status_summary}; roles: {segmentation_roles}."
            ),
            "blocking_or_limiting_factors": (
                "manual_segmentation_validation_missing; dense-vapor instance separation "
                "uncertain; archived_detectron2_eval_metrics_missing"
            ),
            "next_verification_needed": (
                "Complete held-out manual masks for the planned onset, developed, "
                "high-vapor, and high-uncertainty states, then archive segmentation "
                "metrics and representative validation overlays."
            ),
        },
        {
            "claim_id": "local_optical_thermal_coupling",
            "manuscript_claim": (
                "Local vapor structures are quantitatively registered to local thermocouple/HTC "
                "positions."
            ),
            "support_status": "not_supported_current_snapshot",
            "allowed_scope": (
                "Use global state-level optical/thermal comparisons only."
            ),
            "evidence_artifacts": (
                "cross_case_thermal_response_checks.csv; "
                "combined_multimodal_analysis_states.csv; facility geometry notes"
            ),
            "evidence_summary": (
                "State-level thermal context is checked, but camera-to-thermocouple "
                "registration and thermal uncertainty are not yet audited."
            ),
            "blocking_or_limiting_factors": (
                "camera_registration_missing; thermal_uncertainty_audit_missing"
            ),
            "next_verification_needed": (
                "Map camera field of view to heater coordinates and audit HTC/heat-loss equations."
            ),
        },
    ]
    return pd.DataFrame(rows)


def numeric_column(data: pd.DataFrame, column: str) -> pd.Series:
    if data.empty or column not in data:
        return pd.Series(dtype=float)
    return pd.to_numeric(data[column], errors="coerce").dropna()


def numeric_value(value: object) -> float:
    converted = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(converted) if pd.notna(converted) else np.nan


def parse_bool_value(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "verified"}


def ae_verification_lookup(
    verification_status: pd.DataFrame | None,
) -> dict[str, dict[str, object]]:
    if verification_status is None or verification_status.empty:
        return {}
    if "case_label" not in verification_status:
        return {}
    lookup: dict[str, dict[str, object]] = {}
    for row in verification_status.itertuples(index=False):
        case = str(getattr(row, "case_label"))
        lookup[case] = {
            "trigger_synchronization_verified": parse_bool_value(
                getattr(row, "trigger_synchronization_verified", False)
            ),
            "sensor_coupling_verified": parse_bool_value(
                getattr(row, "sensor_coupling_verified", False)
            ),
            "verification_source": getattr(row, "verification_source", "not_provided"),
            "verification_notes": getattr(row, "verification_notes", ""),
        }
    return lookup


def finite_min(values: pd.Series) -> float:
    valid = pd.to_numeric(values, errors="coerce").dropna()
    return float(valid.min()) if not valid.empty else np.nan


def finite_max(values: pd.Series) -> float:
    valid = pd.to_numeric(values, errors="coerce").dropna()
    return float(valid.max()) if not valid.empty else np.nan


def sensitivity_minimum(data: pd.DataFrame, relationship: str, column: str) -> float:
    if data.empty or column not in data:
        return np.nan
    subset = data[data["relationship"] == relationship]
    values = pd.to_numeric(subset[column], errors="coerce").dropna()
    return float(values.min()) if not values.empty else np.nan


def sensitivity_maximum(data: pd.DataFrame, relationship: str, column: str) -> float:
    if data.empty or column not in data:
        return np.nan
    subset = data[data["relationship"] == relationship]
    values = pd.to_numeric(subset[column], errors="coerce").dropna()
    return float(values.max()) if not values.empty else np.nan


def support_status_from_positive_rhos(rhos: pd.Series, leave_one_out_min: float) -> str:
    if rhos.empty or not np.isfinite(leave_one_out_min):
        return "incomplete_evidence"
    if bool((rhos > 0).all()) and leave_one_out_min > 0:
        return "supported_with_limits"
    return "state_sensitive_or_mixed"


def format_range(values: pd.Series) -> str:
    if values.empty:
        return "n/a"
    return f"{values.min():.2f} to {values.max():.2f}"


def format_float(value: float) -> str:
    return f"{value:.2f}" if np.isfinite(value) else "n/a"


def collapse_reasons(reason_strings: list[str]) -> str:
    reasons: list[str] = []
    for text in reason_strings:
        for reason in str(text).split(";"):
            reason = reason.strip()
            if reason and reason not in reasons:
                reasons.append(reason)
    return ";".join(reasons) if reasons else "none"


def join_state_labels(data: pd.DataFrame) -> str:
    if data.empty or "state_label" not in data:
        return "none"
    return ";".join(str(label) for label in data["state_label"].tolist())


def build_sampling_uncertainty_from_frames(frame_metrics: pd.DataFrame) -> pd.DataFrame:
    required = {"case_label", "state_label", "vapor_area_fraction", "active_length_fraction"}
    if not required <= set(frame_metrics.columns):
        return pd.DataFrame()
    rows = []
    for (case, state), group in frame_metrics.groupby(["case_label", "state_label"], sort=False):
        vapor = pd.to_numeric(group["vapor_area_fraction"], errors="coerce").dropna()
        active = pd.to_numeric(group["active_length_fraction"], errors="coerce").dropna()
        row = {
            "case_label": case,
            "state_label": state,
            "image_frames_from_metrics": len(group),
        }
        row.update(metric_uncertainty_fields("vapor_area_fraction", vapor))
        row.update(metric_uncertainty_fields("active_length_fraction", active))
        rows.append(row)
    return pd.DataFrame(rows)


def build_sampling_uncertainty_from_summary(summary_data: pd.DataFrame) -> pd.DataFrame:
    required = {"case_label", "state_label", "image_frames", "vapor_area_fraction_mean"}
    if not required <= set(summary_data.columns):
        return pd.DataFrame()
    rows = []
    for row in summary_data.itertuples():
        n = int(getattr(row, "image_frames"))
        vapor_mean = float(getattr(row, "vapor_area_fraction_mean"))
        vapor_std = getattr(row, "vapor_area_fraction_std", np.nan)
        fields = metric_uncertainty_from_stats("vapor_area_fraction", n, vapor_mean, vapor_std)
        fields.update(
            {
                "case_label": row.case_label,
                "state_label": row.state_label,
                "image_frames_from_metrics": n,
                "active_length_fraction_mean": np.nan,
                "active_length_fraction_std": np.nan,
                "active_length_fraction_sem": np.nan,
                "active_length_fraction_ci95_half_width": np.nan,
                "active_length_fraction_relative_ci95_half_width": np.nan,
            }
        )
        rows.append(fields)
    return pd.DataFrame(rows)


def metric_uncertainty_fields(prefix: str, values: pd.Series) -> dict[str, float]:
    n = len(values)
    if n == 0:
        return metric_uncertainty_from_stats(prefix, 0, np.nan, np.nan)
    return metric_uncertainty_from_stats(prefix, n, float(values.mean()), float(values.std(ddof=1)))


def metric_uncertainty_from_stats(
    prefix: str,
    n: int,
    mean: float,
    std: float,
) -> dict[str, float]:
    sem = std / np.sqrt(n) if n > 1 and np.isfinite(std) else np.nan
    ci_half_width = student_t_critical_95(n - 1) * sem if n > 1 and np.isfinite(sem) else np.nan
    if np.isfinite(mean) and abs(mean) > 0:
        relative_ci = ci_half_width / abs(mean)
    else:
        relative_ci = np.nan
    return {
        f"{prefix}_n": n,
        f"{prefix}_mean": mean,
        f"{prefix}_std": std,
        f"{prefix}_sem": sem,
        f"{prefix}_ci95_half_width": ci_half_width,
        f"{prefix}_relative_ci95_half_width": relative_ci,
    }


def sampling_warning(row: pd.Series, expected_frames: int, relative_ci_warn: float) -> str:
    reasons = []
    n = row.get("vapor_area_fraction_n", row.get("image_frames_from_metrics", np.nan))
    if pd.notna(n) and float(n) < expected_frames:
        reasons.append("short_sample")
    vapor_relative_ci = row.get("vapor_area_fraction_relative_ci95_half_width", np.nan)
    if pd.notna(vapor_relative_ci) and float(vapor_relative_ci) > relative_ci_warn:
        reasons.append("wide_vapor_ci")
    active_relative_ci = row.get("active_length_fraction_relative_ci95_half_width", np.nan)
    if pd.notna(active_relative_ci) and float(active_relative_ci) > relative_ci_warn:
        reasons.append("wide_active_length_ci")
    return ";".join(reasons) if reasons else "none"


def student_t_critical_95(df: int) -> float:
    """Two-sided 95% Student-t critical value without requiring scipy at runtime."""
    values = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.080,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.060,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
    }
    if df <= 0:
        return np.nan
    return values.get(df, 1.960)


def leave_one_state_out_spearman(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
) -> pd.DataFrame:
    if len(data) < 4:
        return pd.DataFrame()
    rows = []
    for index, row in data.iterrows():
        subset = data.drop(index=index)
        rho = spearman_rank(subset, x_column, y_column)
        if np.isnan(rho):
            continue
        rows.append(
            {
                "removed_state_label": row.get("state_label", ""),
                "removed_state_voltage": row.get("state_voltage", np.nan),
                "removed_state_ae_quality": row.get("ae_window_quality", ""),
                "spearman_without_state": rho,
            }
        )
    return pd.DataFrame(rows)


def quality_subset(data: pd.DataFrame, excluded_quality: str) -> pd.DataFrame:
    if "ae_window_quality" not in data.columns:
        return data.copy()
    return data[data["ae_window_quality"].fillna("unknown") != excluded_quality].copy()


def spearman_rank(data: pd.DataFrame, x_column: str, y_column: str) -> float:
    if len(data) < 3 or not {x_column, y_column} <= set(data.columns):
        return np.nan
    x = pd.to_numeric(data[x_column], errors="coerce")
    y = pd.to_numeric(data[y_column], errors="coerce")
    valid = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(valid) < 3:
        return np.nan
    return float(valid["x"].rank().corr(valid["y"].rank()))


def plot_cross_case_story(data: pd.DataFrame, output_path: Path) -> None:
    colors = {
        "5gs_22C": "#1b9e77",
        "10gs_22C": "#377eb8",
        "15gs_20C": "#d95f02",
        "25gs_20C": "#6a3d9a",
    }
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    ax00, ax01, ax10, ax11 = axes.ravel()

    for case, group in data.groupby("case_label", sort=False):
        color = colors.get(case, None)
        label = case.replace("_", " ")
        ax00.errorbar(
            group["heat_flux_mean_w_cm2"],
            group["vapor_area_fraction_mean"],
            yerr=vapor_uncertainty_for_plot(group),
            marker="o",
            linewidth=1.8,
            capsize=2.5,
            color=color,
            label=label,
        )
        plot_quality_tagged_ae_panel(ax01, group, color=color)
        ax10.plot(
            group["vapor_area_fraction_mean"],
            group["htc_mean_w_m2k"],
            marker="s",
            linewidth=1.8,
            color=color,
            label=label,
        )
        ax11.plot(
            group["heat_flux_mean_w_cm2"],
            group["active_length_fraction_mean"],
            marker="^",
            linewidth=1.8,
            color=color,
            label=label,
        )

    ax00.set_title("Visual vapor coverage rises with thermal forcing")
    ax00.set_xlabel("Heat flux (W/cm$^2$)")
    ax00.set_ylabel("Projected vapor area fraction")
    ax00.grid(True, alpha=0.3)
    ax00.text(
        0.03,
        0.97,
        "bars: 95% CI",
        transform=ax00.transAxes,
        va="top",
        ha="left",
        fontsize=8,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999999", alpha=0.9),
    )

    ax01.set_title("AE energy versus visual vapor, quality tagged")
    ax01.set_xlabel("Projected vapor area fraction")
    ax01.set_ylabel("AE absolute-energy rate")
    ax01.set_yscale("log")
    ax01.grid(True, alpha=0.3)
    if "ae_window_quality" in data.columns:
        ax01.text(
            0.03,
            0.03,
            "open: caution\nx: overlap-blocked",
            transform=ax01.transAxes,
            va="bottom",
            ha="left",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999999", alpha=0.9),
        )

    ax10.set_title("Thermal response versus visual vapor metric")
    ax10.set_xlabel("Projected vapor area fraction")
    ax10.set_ylabel("Mean HTC (W/m$^2$ K)")
    ax10.grid(True, alpha=0.3)

    ax11.set_title("Vapor-covered streamwise length versus heat flux")
    ax11.set_xlabel("Heat flux (W/cm$^2$)")
    ax11.set_ylabel("Active vapor length fraction")
    ax11.grid(True, alpha=0.3)

    handles, labels = ax00.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4)
    fig.suptitle("Cross-case multimodal flow-boiling signatures", fontsize=14)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_quality_tagged_ae_panel(ax: plt.Axes, group: pd.DataFrame, *, color: str | None) -> None:
    if "ae_window_quality" not in group.columns:
        ax.scatter(
            group["vapor_area_fraction_mean"],
            group["ae_abs_energy_rate"].clip(lower=1e-3),
            s=40 + group["state_voltage"] * 1.2,
            color=color,
            alpha=0.75,
        )
        return

    for quality, quality_group in group.groupby("ae_window_quality", sort=False):
        size = 40 + quality_group["state_voltage"] * 1.2
        y = quality_group["ae_abs_energy_rate"].clip(lower=1e-3)
        if quality == "blocked":
            ax.scatter(
                quality_group["vapor_area_fraction_mean"],
                y,
                marker="x",
                color="#990000",
                s=size,
                linewidths=1.4,
            )
        elif quality == "caution":
            ax.scatter(
                quality_group["vapor_area_fraction_mean"],
                y,
                marker="o",
                facecolors="none",
                edgecolors=color,
                s=size,
                linewidths=1.2,
            )
        else:
            ax.scatter(
                quality_group["vapor_area_fraction_mean"],
                y,
                marker="o",
                color=color,
                s=size,
                alpha=0.8,
            )


def vapor_uncertainty_for_plot(group: pd.DataFrame) -> pd.Series | None:
    """Prefer sampled-frame 95% CI bars, falling back to frame standard deviation."""
    if "vapor_area_fraction_ci95_half_width" in group.columns:
        ci = pd.to_numeric(group["vapor_area_fraction_ci95_half_width"], errors="coerce")
        if ci.notna().any():
            return ci.fillna(0.0)
    if "vapor_area_fraction_std" in group.columns:
        std = pd.to_numeric(group["vapor_area_fraction_std"], errors="coerce")
        if std.notna().any():
            return std.fillna(0.0)
    return None


def plot_state_map(data: pd.DataFrame, output_path: Path) -> None:
    labels, metric_labels, scaled = state_map_scaled_values(data)

    fig, ax = plt.subplots(figsize=(8, max(6, 0.22 * len(labels))), constrained_layout=True)
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#eeeeee")
    im = ax.imshow(np.ma.masked_invalid(scaled), aspect="auto", cmap=cmap, vmin=0, vmax=1)
    ax.set_yticks(range(len(labels)), labels=labels, fontsize=7)
    ax.set_xticks(
        range(len(metric_labels)),
        labels=metric_labels,
        rotation=25,
        ha="right",
    )
    ax.set_title("Normalized multimodal state map")
    if "ae_window_quality" in data.columns:
        ax.text(
            0.01,
            -0.09,
            "Gray AE-energy cells are overlap-blocked; AE quality weight is 0, 0.5, or 1.",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=7,
        )
    cbar = fig.colorbar(im, ax=ax, fraction=0.025)
    cbar.set_label("Column-normalized value; AE quality is absolute")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def state_map_scaled_values(data: pd.DataFrame) -> tuple[list[str], list[str], np.ndarray]:
    plot_data = data.copy()
    metrics = [
        ("heat_flux_mean_w_cm2", "Heat flux"),
        ("vapor_area_fraction_mean", "Vapor area"),
        ("active_length_fraction_mean", "Active length"),
        ("ae_abs_energy_rate", "AE energy"),
        ("htc_mean_w_m2k", "HTC"),
    ]
    if "ae_window_quality" in plot_data.columns:
        plot_data["ae_abs_energy_rate_screening"] = pd.to_numeric(
            plot_data["ae_abs_energy_rate"],
            errors="coerce",
        )
        blocked = plot_data["ae_window_quality"].fillna("unknown") == "blocked"
        plot_data.loc[blocked, "ae_abs_energy_rate_screening"] = np.nan
        if "ae_interpretation_weight" in plot_data.columns:
            plot_data["ae_quality_weight"] = pd.to_numeric(
                plot_data["ae_interpretation_weight"],
                errors="coerce",
            )
        else:
            plot_data["ae_quality_weight"] = plot_data["ae_window_quality"].map(
                {"blocked": 0.0, "caution": 0.5, "pass": 1.0}
            )
        metrics = [
            ("heat_flux_mean_w_cm2", "Heat flux"),
            ("vapor_area_fraction_mean", "Vapor area"),
            ("active_length_fraction_mean", "Active length"),
            ("ae_abs_energy_rate_screening", "AE energy\nscreening"),
            ("ae_quality_weight", "AE quality\nweight"),
            ("htc_mean_w_m2k", "HTC"),
        ]

    labels = [f"{row.case_label} | {row.state_label}" for row in plot_data.itertuples()]
    columns = [column for column, _ in metrics]
    values = plot_data[columns].to_numpy(dtype=float)
    scaled = scale_state_map_values(values)
    if "ae_quality_weight" in columns:
        weight_index = columns.index("ae_quality_weight")
        scaled[:, weight_index] = np.clip(values[:, weight_index], 0.0, 1.0)
    return labels, [label for _, label in metrics], scaled


def scale_state_map_values(values: np.ndarray) -> np.ndarray:
    scaled = np.full(values.shape, np.nan, dtype=float)
    for column_index in range(values.shape[1]):
        column = values[:, column_index]
        valid = np.isfinite(column)
        if not valid.any():
            continue
        column_min = np.nanmin(column[valid])
        column_max = np.nanmax(column[valid])
        if column_max > column_min:
            scaled[valid, column_index] = (column[valid] - column_min) / (
                column_max - column_min
            )
        else:
            scaled[valid, column_index] = 0.5
    return scaled


def write_key_numbers(
    data: pd.DataFrame,
    trend_summary: pd.DataFrame,
    trend_sensitivity: pd.DataFrame,
    sampling_uncertainty: pd.DataFrame,
    active_threshold_sensitivity: pd.DataFrame,
    thermal_response: pd.DataFrame,
    segmentation_plan: pd.DataFrame,
    ae_verification_status: pd.DataFrame,
    ae_evidence_tiers: pd.DataFrame,
    ae_readiness_matrix: pd.DataFrame,
    ae_remediation_plan: pd.DataFrame,
    claim_matrix: pd.DataFrame,
    output_path: Path,
) -> None:
    lines = []
    if "ae_window_quality" in data.columns:
        counts = data["ae_window_quality"].fillna("unknown").value_counts().sort_index()
        lines.append("AE window quality")
        for quality, count in counts.items():
            lines.append(f"  {quality}: {count}")
        blocked = data[data["ae_window_quality"] == "blocked"]
        if not blocked.empty:
            labels = ", ".join(
                f"{row.case_label}/{row.state_label}" for row in blocked.itertuples()
            )
            lines.append(f"  blocked states: {labels}")
        lines.append("")
    if not trend_summary.empty:
        lines.append("Cross-case trend summary")
        for row in trend_summary.itertuples():
            lines.append(
                "  "
                f"{row.case_label}: rho(q'', alpha_A)={row.spearman_heat_flux_vapor_area:.2f}, "
                f"rho(q'', L_A)={row.spearman_heat_flux_active_length:.2f}, "
                f"rho(alpha_A, AE) nonblocked={row.spearman_vapor_area_ae_nonblocked:.2f}"
            )
        lines.append("")
    if not trend_sensitivity.empty:
        lines.append("Leave-one-state-out trend sensitivity")
        ae_sensitivity = trend_sensitivity[
            trend_sensitivity["relationship"] == "vapor_area_vs_ae_nonblocked"
        ]
        for row in ae_sensitivity.itertuples():
            lines.append(
                "  "
                f"{row.case_label}: baseline rho={row.baseline_spearman:.2f}, "
                f"without {row.most_influential_removed_state} "
                f"rho={row.spearman_without_most_influential_state:.2f}, "
                f"max |delta|={row.max_abs_delta:.2f}"
            )
        lines.append("")
    if not sampling_uncertainty.empty:
        lines.append("Frame-sampling uncertainty")
        warning_count = int((sampling_uncertainty["sampling_warning"] != "none").sum())
        lines.append(f"  states with sampling warnings: {warning_count}")
        if "vapor_area_fraction_relative_ci95_half_width" in sampling_uncertainty.columns:
            relative = pd.to_numeric(
                sampling_uncertainty["vapor_area_fraction_relative_ci95_half_width"],
                errors="coerce",
            )
            if relative.notna().any():
                wide_count = int((relative > 0.25).sum())
                index = relative.idxmax()
                row = sampling_uncertainty.loc[index]
                lines.append(f"  states with vapor relative 95% CI half-width > 0.25: {wide_count}")
                lines.append(
                    "  "
                    f"largest vapor 95% CI half-width: {row.case_label}/{row.state_label}, "
                    f"relative={relative.loc[index]:.2f}, "
                    f"absolute={row.vapor_area_fraction_ci95_half_width:.3f}"
                )
        lines.append("")
    if not active_threshold_sensitivity.empty:
        lines.append("Active-length threshold sensitivity")
        statuses = (
            active_threshold_sensitivity["active_threshold_sensitivity_status"]
            .fillna("unknown")
            .value_counts()
            .sort_index()
        )
        for status, count in statuses.items():
            lines.append(f"  {status}: {count}")
        if "active_length_max_abs_delta_from_baseline" in active_threshold_sensitivity.columns:
            deltas = pd.to_numeric(
                active_threshold_sensitivity["active_length_max_abs_delta_from_baseline"],
                errors="coerce",
            )
            if deltas.notna().any():
                index = deltas.idxmax()
                row = active_threshold_sensitivity.loc[index]
                lines.append(
                    "  "
                    f"largest active-length threshold delta: {row.case_label}/{row.state_label}, "
                    f"delta={deltas.loc[index]:.3f}"
                )
        lines.append("")
    if not thermal_response.empty:
        lines.append("Thermal response checks")
        for row in thermal_response.sort_values("case_label").itertuples():
            lines.append(
                "  "
                f"{row.case_label}: status={row.thermal_context_status}; "
                f"rho(voltage, q'')={row.spearman_voltage_heat_flux:.2f}; "
                f"rho(q'', HTC)={row.spearman_heat_flux_htc:.2f}; "
                f"q''={row.heat_flux_min_w_cm2:.2f} to "
                f"{row.heat_flux_max_w_cm2:.2f} W/cm2"
            )
        lines.append("")
    if not segmentation_plan.empty:
        lines.append("Segmentation validation plan")
        status_counts = segmentation_plan["validation_status"].fillna("unknown").value_counts()
        lines.append(
            "  validation targets: "
            f"{len(segmentation_plan)} states across "
            f"{segmentation_plan['case_label'].nunique()} cases"
        )
        lines.append(
            "  statuses: "
            + ", ".join(f"{status}={count}" for status, count in status_counts.items())
        )
        for row in segmentation_plan.sort_values(["case_label", "state_voltage"]).itertuples():
            lines.append(
                "  "
                f"{row.case_label}/{row.state_label}: roles={row.validation_role}; "
                f"minimum_masks={row.minimum_manual_masks}; "
                f"status={row.validation_status}"
            )
        lines.append("")
    if not ae_verification_status.empty:
        lines.append("AE verification status")
        for row in ae_verification_status.itertuples():
            lines.append(
                "  "
                f"{row.case_label}: trigger_verified="
                f"{row.trigger_synchronization_verified}; "
                f"sensor_coupling_verified={row.sensor_coupling_verified}; "
                f"source={row.verification_source}"
            )
        lines.append("")
    if not ae_evidence_tiers.empty:
        lines.append("AE evidence tiers")
        for row in ae_evidence_tiers.itertuples():
            lines.append(
                "  "
                f"{row.case_label}: {row.ae_evidence_tier}; "
                f"{row.recommended_claim_scope}; "
                f"limits={row.limiting_factors}"
            )
        lines.append("")
    if not ae_readiness_matrix.empty:
        lines.append("AE readiness matrix")
        for row in ae_readiness_matrix.itertuples():
            lines.append(
                "  "
                f"{row.case_label}: status={row.ae_readiness_status}; "
                f"quantitative_ready={row.quantitative_ae_ready}; "
                f"pass_fraction={row.ae_pass_fraction:.2f}; "
                f"nonblocked={row.ae_nonblocked_states}/{row.states}; "
                f"limits={row.blocking_criteria}"
            )
        lines.append("")
    if not ae_remediation_plan.empty:
        lines.append("AE remediation plan")
        for row in ae_remediation_plan.sort_values(
            ["remediation_priority", "case_label"]
        ).itertuples():
            lines.append(
                "  "
                f"P{row.remediation_priority} {row.case_label}: "
                f"{row.primary_rerun_action}; "
                f"blocked={row.blocked_state_labels}; "
                f"long={row.long_window_state_labels}; "
                f"verify={row.verification_actions}"
            )
        lines.append("")
    if not claim_matrix.empty:
        lines.append("Claim-evidence matrix")
        for row in claim_matrix.itertuples():
            lines.append(
                "  "
                f"{row.claim_id}: {row.support_status}; "
                f"scope={row.allowed_scope}; "
                f"limits={row.blocking_or_limiting_factors}"
            )
        lines.append("")
    for case, group in data.groupby("case_label", sort=False):
        low = group.iloc[0]
        high = group.iloc[-1]
        lines.append(f"{case}")
        lines.append(
            f"  heat flux range: {group['heat_flux_mean_w_cm2'].min():.2f} to "
            f"{group['heat_flux_mean_w_cm2'].max():.2f} W/cm2"
        )
        lines.append(
            f"  vapor area fraction range: {group['vapor_area_fraction_mean'].min():.3f} to "
            f"{group['vapor_area_fraction_mean'].max():.3f}"
        )
        lines.append(
            f"  first state {low['state_label']}: vapor={low['vapor_area_fraction_mean']:.3f}, "
            f"AE energy rate={low['ae_abs_energy_rate']:.1f}"
        )
        lines.append(
            f"  final state {high['state_label']}: vapor={high['vapor_area_fraction_mean']:.3f}, "
            f"AE energy rate={high['ae_abs_energy_rate']:.1f}"
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
