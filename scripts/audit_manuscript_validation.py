from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_MODEL_DIR = (
    r"C:\Users\hanhu\Box\NED3_Share\0_BubbleID\BubbleID-Flow"
    r"\detectron2_flow_mrcnn_roi485_70"
)


@dataclass(frozen=True)
class Finding:
    level: str
    item: str
    detail: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit manuscript validation readiness.")
    parser.add_argument(
        "--combined-summary",
        default="outputs/multimodal/cross_case_synthesis/combined_multimodal_state_summary.csv",
    )
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    parser.add_argument("--model-manifest", default="docs/model_artifact_manifest.csv")
    parser.add_argument("--report", default="docs/manuscript_validation_audit.md")
    parser.add_argument("--current-evidence-root", default="outputs/aug9_model_analysis")
    parser.add_argument(
        "--legacy-multimodal",
        action="store_true",
        help="Run the superseded acoustic/multimodal validation audit.",
    )
    parser.add_argument("--expected-frames-per-state", type=int, default=8)
    parser.add_argument("--long-window-s", type=float, default=120.0)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on blockers.")
    args = parser.parse_args()

    if not args.legacy_multimodal:
        run_current_validation(args)
        return

    findings: list[Finding] = []
    metrics: list[str] = []
    tables: list[str] = []

    summary_path = Path(args.combined_summary)
    if not summary_path.exists():
        findings.append(Finding("ERROR", "State summary", f"Missing {summary_path}"))
        data = pd.DataFrame()
    else:
        data = pd.read_csv(summary_path)
        findings.append(Finding("PASS", "State summary", f"Found {summary_path}"))

    if not data.empty:
        analysis = data[complete_state_mask(data)].copy()
        check_state_completeness(data, analysis, findings, metrics)
        check_frame_sampling(analysis, args.expected_frames_per_state, findings, metrics, tables)
        check_active_length_traceability(analysis, findings, metrics)
        check_thermal_windows(analysis, args.long_window_s, findings, metrics, tables)
        add_cross_modal_diagnostics(analysis, metrics, tables)
        check_sampling_uncertainty_artifact(
            summary_path.parent / "cross_case_sampling_uncertainty.csv",
            findings,
            metrics,
            tables,
        )
        check_active_threshold_sensitivity(
            summary_path.parent / "cross_case_active_threshold_sensitivity.csv",
            findings,
            metrics,
            tables,
        )
        check_segmentation_validation_plan(
            summary_path.parent / "cross_case_segmentation_validation_plan.csv",
            findings,
            metrics,
            tables,
        )
        check_thermal_response_checks(
            summary_path.parent / "cross_case_thermal_response_checks.csv",
            findings,
            metrics,
            tables,
        )
        check_ae_evidence_tiers(
            summary_path.parent / "cross_case_ae_evidence_tiers.csv",
            findings,
            metrics,
            tables,
        )
        check_ae_readiness_matrix(
            summary_path.parent / "cross_case_ae_readiness_matrix.csv",
            findings,
            metrics,
            tables,
        )
        check_ae_verification_status(
            summary_path.parent / "cross_case_ae_verification_status.csv",
            findings,
            metrics,
            tables,
        )
        check_ae_remediation_plan(
            summary_path.parent / "cross_case_ae_remediation_plan.csv",
            findings,
            metrics,
            tables,
        )
        check_claim_evidence_matrix(
            summary_path.parent / "cross_case_claim_evidence_matrix.csv",
            findings,
            metrics,
            tables,
        )

    check_model_artifacts(Path(args.model_dir), Path(args.model_manifest), findings, metrics)

    report = build_report(findings, metrics, tables)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    blockers = [finding for finding in findings if finding.level == "BLOCKER"]
    errors = [finding for finding in findings if finding.level == "ERROR"]
    print(f"Wrote {report_path}")
    print(f"Validation audit findings: {len(errors)} errors, {len(blockers)} blockers")
    if errors or (args.strict and blockers):
        raise SystemExit(1)


def run_current_validation(args: argparse.Namespace) -> None:
    """Audit the evidence actually used by the revised optical/thermal manuscript."""
    root = Path(args.current_evidence_root)
    paths = {
        "robustness": root / "segmentation_robustness" / "segmentation_robustness_summary.json",
        "baselines": root / "segmentation_baselines" / "segmentation_baseline_summary.csv",
        "temporal": root / "aug9_temporal_summary_45V.csv",
        "partial sequences": root / "full_sequences" / "full_sequence_state_summary.csv",
        "thermal manifest": root / "thermal_audit" / "thermal_reduction_manifest.json",
        "association": root / "optical_thermal_association" / "optical_incremental_cv_summary.csv",
    }
    findings: list[Finding] = []
    metrics: list[str] = []
    tables: list[str] = []
    missing = [f"{label}: {path}" for label, path in paths.items() if not path.exists()]
    if missing:
        findings.append(Finding("ERROR", "Current evidence", "; ".join(missing)))
    else:
        import json

        robustness = json.loads(paths["robustness"].read_text(encoding="utf-8"))
        baselines = pd.read_csv(paths["baselines"])
        temporal = pd.read_csv(paths["temporal"])
        partial = pd.read_csv(paths["partial sequences"])
        thermal_manifest = json.loads(paths["thermal manifest"].read_text(encoding="utf-8"))
        association = pd.read_csv(paths["association"])

        split = robustness["split_audit"]
        metrics.append(
            "- Same-sequence holdout proximity: "
            f"{split['holdout_with_training_frame_within_one_index']} of "
            f"{split['holdout_images']} images"
        )
        findings.append(
            Finding(
                "BLOCKER",
                "Experiment-held-out segmentation validation",
                "The current holdout is one source sequence; a new operating run must be annotated and held out.",
            )
        )

        baseline_errors = baselines.set_index("method")["mean_absolute_area_fraction_error"]
        if baseline_errors["Mask R-CNN"] < baseline_errors["Pixel Gaussian"]:
            findings.append(Finding("PASS", "Segmentation baselines", "Deep-model coverage error is lower than the training-only learned baseline."))
        else:
            findings.append(Finding("ERROR", "Segmentation baselines", "Baseline ordering is inconsistent."))

        completed = {
            (str(row.case_label), float(row.state_voltage))
            for row in temporal.itertuples()
        }
        completed.update(
            (str(row.case_label), float(row.state_voltage))
            for row in partial.itertuples()
        )
        remaining = 37 - len(completed)
        metrics.append(f"- Complete regenerated state sequences: {len(completed)} of 37")
        findings.append(
            Finding(
                "BLOCKER",
                "Complete state-sequence validation",
                f"{remaining} archived state summaries still lack complete regenerated frame outputs.",
            )
        )

        if temporal["uncertainty_method"].str.contains("moving-block bootstrap").all():
            findings.append(Finding("PASS", "Temporal dependence", "All common 45 V states use moving-block intervals."))
        else:
            findings.append(Finding("ERROR", "Temporal dependence", "One or more primary intervals ignore serial dependence."))

        uncertainty_scope = str(thermal_manifest.get("uncertainty_scope", ""))
        if "not supplied" in uncertainty_scope:
            findings.append(
                Finding(
                    "BLOCKER",
                    "Thermal measurement uncertainty",
                    "Instrument calibration, heat-loss, and uncertainty records are required before derived heat-transfer endpoints can be validated.",
                )
            )
        else:
            findings.append(Finding("ERROR", "Thermal measurement uncertainty", "Thermal uncertainty scope is missing."))
        if thermal_manifest.get("excluded_from_validation"):
            findings.append(Finding("PASS", "Thermal claim boundary", "Unsupported derived thermal endpoints are enumerated and excluded."))

        pivot = association.pivot(index="cross_validation", columns="model", values="rmse_c")
        if (pivot["thermal baseline + projected area"] >= pivot["thermal baseline"]).all():
            findings.append(Finding("PASS", "Incremental optical validation", "Projected coverage does not improve either cross-validated thermal model."))
        else:
            findings.append(Finding("ERROR", "Incremental optical validation", "Association result conflicts with the revised claim."))

        findings.append(Finding("WARN", "Spatial registration", "Camera-to-heater and camera-to-sensor registration remain unavailable."))
        findings.append(Finding("WARN", "Transition labels", "No objective onset, dryout, or CHF criterion was supplied; operator labels remain non-quantitative."))

    check_model_artifacts(Path(args.model_dir), Path(args.model_manifest), findings, metrics)
    report = build_report(findings, metrics, tables)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    blockers = [finding for finding in findings if finding.level == "BLOCKER"]
    errors = [finding for finding in findings if finding.level == "ERROR"]
    print(f"Wrote {report_path}")
    print(f"Validation audit findings: {len(errors)} errors, {len(blockers)} blockers")
    if errors or (args.strict and blockers):
        raise SystemExit(1)


def check_state_completeness(
    data: pd.DataFrame,
    analysis: pd.DataFrame,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    metrics.append(f"- Raw state-summary rows: {len(data)}")
    metrics.append(f"- Complete multimodal analysis rows: {len(analysis)}")
    incomplete = data[~complete_state_mask(data)]
    if incomplete.empty:
        findings.append(Finding("PASS", "Complete-state filter", "No incomplete states found."))
    else:
        labels = ", ".join(f"{row.case_label}/{row.state_label}" for row in incomplete.itertuples())
        findings.append(
            Finding("WARN", "Complete-state filter", f"Excluded from analysis figures: {labels}")
        )


def check_frame_sampling(
    data: pd.DataFrame,
    expected_frames: int,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if "image_frames" not in data.columns:
        findings.append(Finding("ERROR", "Frame sampling", "Missing image_frames column."))
        return
    image_frames = pd.to_numeric(data["image_frames"], errors="coerce")
    metrics.append(
        "- Image frames per complete state: "
        f"{int(image_frames.min())} to {int(image_frames.max())}"
    )
    short = data[image_frames < expected_frames]
    if short.empty:
        findings.append(
            Finding(
                "PASS",
                "Frame sampling",
                f"All complete states include {expected_frames} frames.",
            )
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Frame sampling",
                f"{len(short)} complete states use fewer than {expected_frames} sampled frames.",
            )
        )
        counts = short.groupby("case_label")["state_label"].count().sort_index()
        tables.append("### States below requested frame count\n")
        tables.append(markdown_table(counts.reset_index(name="states_below_requested_count")))

    if {"vapor_area_fraction_mean", "vapor_area_fraction_std"} <= set(data.columns):
        variability = data.copy()
        mean = pd.to_numeric(variability["vapor_area_fraction_mean"], errors="coerce")
        std = pd.to_numeric(variability["vapor_area_fraction_std"], errors="coerce")
        variability["vapor_area_fraction_cv"] = std / mean.replace(0, np.nan)
        top = variability.sort_values("vapor_area_fraction_cv", ascending=False).head(5)
        tables.append("\n### Highest frame-to-frame vapor-area variability\n")
        tables.append(
            markdown_table(
                top[
                    [
                        "case_label",
                        "state_label",
                        "image_frames",
                        "vapor_area_fraction_mean",
                        "vapor_area_fraction_std",
                        "vapor_area_fraction_cv",
                    ]
                ],
                floatfmt=".3f",
            )
        )


def complete_state_mask(data: pd.DataFrame) -> pd.Series:
    if "multimodal_complete" not in data.columns:
        return pd.Series(True, index=data.index)
    return data["multimodal_complete"].astype(bool)


def check_active_length_traceability(
    data: pd.DataFrame,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    if "active_column_threshold" not in data.columns:
        findings.append(Finding("WARN", "Active length", "Missing active_column_threshold column."))
        return
    thresholds = sorted(
        round(float(value), 6) for value in data["active_column_threshold"].dropna().unique()
    )
    metrics.append(f"- Active-column thresholds in complete states: {thresholds}")
    if thresholds == [0.05]:
        findings.append(Finding("PASS", "Active length", "Complete states record phi_thr = 0.05."))
    else:
        findings.append(
            Finding("WARN", "Active length", f"Unexpected threshold values: {thresholds}")
        )


def check_thermal_windows(
    data: pd.DataFrame,
    long_window_s: float,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not {"time_start_s", "time_end_s", "case_label", "state_label"} <= set(data.columns):
        findings.append(Finding("WARN", "Thermal windows", "Missing time-window columns."))
        return

    windows = data.dropna(subset=["time_start_s", "time_end_s"]).copy()
    windows["thermal_window_span_s"] = windows["time_end_s"] - windows["time_start_s"]
    metrics.append(
        "- Thermal window span range: "
        f"{windows['thermal_window_span_s'].min():.1f} to "
        f"{windows['thermal_window_span_s'].max():.1f} s"
    )
    long_windows = windows[windows["thermal_window_span_s"] > long_window_s]
    if not long_windows.empty:
        findings.append(
            Finding(
                "WARN",
                "Long thermal windows",
                f"{len(long_windows)} complete states span more than {long_window_s:.0f} s.",
            )
        )

    overlaps = []
    for case, group in windows.sort_values(["case_label", "time_start_s"]).groupby("case_label"):
        previous_end = None
        previous_label = None
        for row in group.itertuples():
            if previous_end is not None and row.time_start_s < previous_end:
                overlaps.append(
                    {
                        "case_label": case,
                        "state_label": row.state_label,
                        "time_start_s": row.time_start_s,
                        "time_end_s": row.time_end_s,
                        "overlaps_previous_state": previous_label,
                    }
                )
            previous_end = row.time_end_s
            previous_label = row.state_label
    if overlaps:
        findings.append(
            Finding(
                "BLOCKER",
                "Thermal/AE window alignment",
                f"{len(overlaps)} complete states overlap earlier voltage windows.",
            )
        )
        tables.append("\n### Overlapping thermal windows in tracked outputs\n")
        tables.append(markdown_table(pd.DataFrame(overlaps), floatfmt=".1f"))
    else:
        findings.append(
            Finding("PASS", "Thermal/AE window alignment", "No overlapping windows found.")
        )

    if "thermal_window_selection" not in data.columns:
        findings.append(
            Finding(
                "WARN",
                "Thermal window provenance",
                "Tracked summaries predate contiguous-window selection metadata.",
            )
        )

    if "ae_window_quality" in data.columns:
        counts = data["ae_window_quality"].fillna("unknown").value_counts().sort_index()
        metrics.append(
            "- AE window quality counts: "
            + ", ".join(f"{quality}={count}" for quality, count in counts.items())
        )
        blocked = data[data["ae_window_quality"] == "blocked"]
        caution = data[data["ae_window_quality"] == "caution"]
        if not blocked.empty:
            tables.append("\n### AE interpretation-blocked states\n")
            tables.append(
                markdown_table(
                    blocked[
                        [
                            "case_label",
                            "state_label",
                            "time_start_s",
                            "time_end_s",
                            "ae_window_overlaps_previous_state",
                            "ae_window_quality_reason",
                        ]
                    ],
                    floatfmt=".1f",
                )
            )
            findings.append(
                Finding(
                    "BLOCKER",
                    "AE confidence",
                    f"{len(blocked)} states are blocked for AE interpretation.",
                )
            )
        if not caution.empty:
            findings.append(
                Finding(
                    "WARN",
                    "AE confidence",
                    f"{len(caution)} states require cautious AE interpretation.",
                )
            )


def add_cross_modal_diagnostics(data: pd.DataFrame, metrics: list[str], tables: list[str]) -> None:
    required = {
        "case_label",
        "heat_flux_mean_w_cm2",
        "vapor_area_fraction_mean",
        "active_length_fraction_mean",
        "ae_abs_energy_rate",
    }
    if not required <= set(data.columns):
        return
    rows = []
    for case, group in data.groupby("case_label"):
        if len(group) < 3:
            continue
        nonblocked = group
        if "ae_window_quality" in group.columns:
            nonblocked = group[group["ae_window_quality"].fillna("unknown") != "blocked"]
        rows.append(
            {
                "case_label": case,
                "spearman_heat_flux_vs_vapor": spearman_rank(
                    group, "heat_flux_mean_w_cm2", "vapor_area_fraction_mean"
                ),
                "spearman_heat_flux_vs_active_length": spearman_rank(
                    group, "heat_flux_mean_w_cm2", "active_length_fraction_mean"
                ),
                "spearman_vapor_vs_ae_all_states": spearman_rank(
                    group, "vapor_area_fraction_mean", "ae_abs_energy_rate"
                ),
                "spearman_vapor_vs_ae_nonblocked": spearman_rank(
                    nonblocked, "vapor_area_fraction_mean", "ae_abs_energy_rate"
                ),
                "states": len(group),
                "ae_nonblocked_states": len(nonblocked),
            }
        )
    if rows:
        table = pd.DataFrame(rows).sort_values("case_label")
        metrics.append(
            "- Spearman rho, heat flux vs vapor area: "
            + ", ".join(
                f"{row.case_label}={row.spearman_heat_flux_vs_vapor:.2f}"
                for row in table.itertuples()
            )
        )
        metrics.append(
            "- Spearman rho, heat flux vs active length: "
            + ", ".join(
                f"{row.case_label}={row.spearman_heat_flux_vs_active_length:.2f}"
                for row in table.itertuples()
            )
        )
        metrics.append(
            "- Spearman rho, vapor area vs AE energy (nonblocked): "
            + ", ".join(
                f"{row.case_label}={row.spearman_vapor_vs_ae_nonblocked:.2f}"
                for row in table.itertuples()
            )
        )
        tables.append("\n### Quality-gated cross-modal rank agreement\n")
        tables.append(markdown_table(table, floatfmt=".2f"))
        sensitivity = build_leave_one_state_out_table(data)
        if not sensitivity.empty:
            tables.append("\n### Leave-one-state-out trend sensitivity\n")
            tables.append(markdown_table(sensitivity, floatfmt=".2f"))


def check_sampling_uncertainty_artifact(
    sampling_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
    *,
    relative_ci_warn: float = 0.25,
) -> None:
    if not sampling_path.exists():
        findings.append(Finding("WARN", "Sampling uncertainty", f"Missing {sampling_path}"))
        return

    sampling = pd.read_csv(sampling_path)
    required = {
        "case_label",
        "state_label",
        "vapor_area_fraction_ci95_half_width",
        "vapor_area_fraction_relative_ci95_half_width",
        "sampling_warning",
    }
    missing = sorted(required - set(sampling.columns))
    if missing:
        findings.append(Finding("ERROR", "Sampling uncertainty", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "Sampling uncertainty", f"Found {sampling_path}"))
    relative = pd.to_numeric(
        sampling["vapor_area_fraction_relative_ci95_half_width"],
        errors="coerce",
    )
    metrics.append(
        "- Sampling uncertainty warnings: "
        f"{int((sampling['sampling_warning'].fillna('none') != 'none').sum())} states"
    )
    if relative.notna().any():
        index = relative.idxmax()
        row = sampling.loc[index]
        metrics.append(
            "- Max vapor-area relative 95% half-width: "
            f"{row.case_label}/{row.state_label}={relative.loc[index]:.2f}"
        )
    warnings = sampling[sampling["sampling_warning"].fillna("none") != "none"]
    if warnings.empty:
        findings.append(
            Finding("PASS", "Sampling uncertainty", "All states pass sampling warning criteria.")
        )
    else:
        wide = warnings[
            pd.to_numeric(
                warnings["vapor_area_fraction_relative_ci95_half_width"],
                errors="coerce",
            )
            > relative_ci_warn
        ]
        findings.append(
            Finding(
                "WARN",
                "Sampling uncertainty",
                f"{len(warnings)} states have short samples or wide 95% intervals.",
            )
        )
        tables.append("\n### Sampling-uncertainty warning states\n")
        table_columns = [
            "case_label",
            "state_label",
            "image_frames_from_metrics",
            "vapor_area_fraction_mean",
            "vapor_area_fraction_ci95_half_width",
            "vapor_area_fraction_relative_ci95_half_width",
            "active_length_fraction_relative_ci95_half_width",
            "sampling_warning",
        ]
        available = [column for column in table_columns if column in warnings.columns]
        tables.append(markdown_table(warnings[available], floatfmt=".3f"))
        if not wide.empty:
            labels = ", ".join(f"{row.case_label}/{row.state_label}" for row in wide.itertuples())
            findings.append(
                Finding(
                    "WARN",
                    "Sampling uncertainty",
                    f"Wide vapor-area intervals exceed {relative_ci_warn:.0%}: {labels}",
                )
            )


def check_active_threshold_sensitivity(
    sensitivity_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
    *,
    sensitivity_delta_warn: float = 0.10,
) -> None:
    if not sensitivity_path.exists():
        findings.append(
            Finding("WARN", "Active threshold sensitivity", f"Missing {sensitivity_path}")
        )
        return

    sensitivity = pd.read_csv(sensitivity_path)
    required = {
        "case_label",
        "state_label",
        "baseline_active_column_threshold",
        "active_threshold_sensitivity_status",
        "active_thresholds_evaluated",
        "active_length_max_abs_delta_from_baseline",
        "threshold_sensitivity_limit",
        "next_verification_needed",
    }
    missing = sorted(required - set(sensitivity.columns))
    if missing:
        findings.append(
            Finding("ERROR", "Active threshold sensitivity", f"Missing columns: {missing}")
        )
        return

    findings.append(Finding("PASS", "Active threshold sensitivity", f"Found {sensitivity_path}"))
    status_counts = (
        sensitivity["active_threshold_sensitivity_status"]
        .fillna("unknown")
        .value_counts()
        .sort_index()
    )
    metrics.append(
        "- Active-length threshold sensitivity statuses: "
        + ", ".join(f"{status}={count}" for status, count in status_counts.items())
    )
    deltas = pd.to_numeric(
        sensitivity["active_length_max_abs_delta_from_baseline"],
        errors="coerce",
    )
    if deltas.notna().any():
        index = deltas.idxmax()
        row = sensitivity.loc[index]
        metrics.append(
            "- Max active-length threshold delta: "
            f"{row.case_label}/{row.state_label}={deltas.loc[index]:.3f}"
        )

    unchecked = sensitivity[
        sensitivity["active_threshold_sensitivity_status"].fillna("") != "checked"
    ]
    sensitive = sensitivity[deltas > sensitivity_delta_warn] if deltas.notna().any() else sensitivity.iloc[0:0]
    if unchecked.empty and sensitive.empty:
        findings.append(
            Finding(
                "PASS",
                "Active threshold sensitivity",
                "All active-length threshold sweeps are checked within tolerance.",
            )
        )
    else:
        if not unchecked.empty:
            findings.append(
                Finding(
                    "WARN",
                    "Active threshold sensitivity",
                    f"{len(unchecked)} states lack completed active-threshold sweeps.",
                )
            )
            tables.append("\n### Active-length threshold sensitivity gaps\n")
            tables.append(
                markdown_table(
                    unchecked[
                        [
                            "case_label",
                            "state_label",
                            "baseline_active_column_threshold",
                            "active_threshold_sensitivity_status",
                            "threshold_sensitivity_limit",
                            "next_verification_needed",
                        ]
                    ],
                    floatfmt=".3f",
                )
            )
        if not sensitive.empty:
            labels = ", ".join(
                f"{row.case_label}/{row.state_label}" for row in sensitive.itertuples()
            )
            findings.append(
                Finding(
                    "WARN",
                    "Active threshold sensitivity",
                    (
                        f"Active-length delta exceeds {sensitivity_delta_warn:.2f} "
                        f"for: {labels}."
                    ),
                )
            )


def check_segmentation_validation_plan(
    plan_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not plan_path.exists():
        findings.append(
            Finding("WARN", "Segmentation validation plan", f"Missing {plan_path}")
        )
        return

    plan = pd.read_csv(plan_path)
    required = {
        "case_label",
        "state_label",
        "validation_role",
        "minimum_manual_masks",
        "validation_status",
        "claim_gate_until_complete",
    }
    missing = sorted(required - set(plan.columns))
    if missing:
        findings.append(
            Finding("ERROR", "Segmentation validation plan", f"Missing columns: {missing}")
        )
        return

    findings.append(Finding("PASS", "Segmentation validation plan", f"Found {plan_path}"))
    status_counts = plan["validation_status"].fillna("unknown").value_counts().sort_index()
    metrics.append(
        "- Segmentation validation targets: "
        f"{len(plan)} states across {plan['case_label'].nunique()} cases"
    )
    metrics.append(
        "- Segmentation validation statuses: "
        + ", ".join(f"{status}={count}" for status, count in status_counts.items())
    )

    complete = plan["validation_status"].fillna("") == "complete"
    if bool(complete.all()) and not plan.empty:
        findings.append(
            Finding(
                "PASS",
                "Manual segmentation validation",
                "All planned held-out mask validation targets are complete.",
            )
        )
    else:
        pending = plan[~complete]
        findings.append(
            Finding(
                "WARN",
                "Manual segmentation validation",
                f"{len(pending)} planned mask-validation targets remain incomplete.",
            )
        )
        table_columns = [
            "case_label",
            "state_label",
            "validation_role",
            "image_frames",
            "vapor_area_fraction_relative_ci95_half_width",
            "sampling_warning",
            "minimum_manual_masks",
            "validation_status",
        ]
        available = [column for column in table_columns if column in pending.columns]
        tables.append("\n### Segmentation validation plan\n")
        tables.append(markdown_table(pending[available], floatfmt=".3f"))


def check_thermal_response_checks(
    thermal_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not thermal_path.exists():
        findings.append(Finding("WARN", "Thermal response checks", f"Missing {thermal_path}"))
        return

    thermal = pd.read_csv(thermal_path)
    required = {
        "case_label",
        "thermal_context_status",
        "spearman_voltage_heat_flux",
        "spearman_heat_flux_htc",
        "heat_flux_drop_count_vs_voltage",
        "heat_flux_min_w_cm2",
        "heat_flux_max_w_cm2",
        "limiting_factors",
    }
    missing = sorted(required - set(thermal.columns))
    if missing:
        findings.append(Finding("ERROR", "Thermal response checks", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "Thermal response checks", f"Found {thermal_path}"))
    status_counts = thermal["thermal_context_status"].fillna("unknown").value_counts().sort_index()
    metrics.append(
        "- Thermal response statuses: "
        + ", ".join(f"{status}={count}" for status, count in status_counts.items())
    )
    if "spearman_heat_flux_htc" in thermal.columns:
        htc_rho = pd.to_numeric(thermal["spearman_heat_flux_htc"], errors="coerce")
        if htc_rho.notna().any():
            metrics.append(
                "- Thermal response, heat-flux/HTC rho range: "
                f"{htc_rho.min():.2f} to {htc_rho.max():.2f}"
            )

    not_supported = thermal[
        thermal["thermal_context_status"].fillna("") != "state_level_supported"
    ]
    if not_supported.empty:
        findings.append(
            Finding(
                "PASS",
                "Thermal response checks",
                "All cases support state-level reduced-thermal context.",
            )
        )
    else:
        labels = ", ".join(not_supported["case_label"].astype(str))
        findings.append(
            Finding(
                "WARN",
                "Thermal response checks",
                f"Thermal state-level context needs review for: {labels}.",
            )
        )

    findings.append(
        Finding(
            "WARN",
            "Thermal response limits",
            "Mean HTC remains state-level only; local registration and uncertainty are unaudited.",
        )
    )
    tables.append("\n### Thermal response check summary\n")
    tables.append(
        markdown_table(
            thermal[
                [
                    "case_label",
                    "thermal_context_status",
                    "heat_flux_min_w_cm2",
                    "heat_flux_max_w_cm2",
                    "spearman_voltage_heat_flux",
                    "spearman_heat_flux_htc",
                    "heat_flux_drop_count_vs_voltage",
                    "limiting_factors",
                ]
            ],
            floatfmt=".2f",
        )
    )


def check_ae_evidence_tiers(
    evidence_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not evidence_path.exists():
        findings.append(Finding("WARN", "AE evidence tiers", f"Missing {evidence_path}"))
        return

    evidence = pd.read_csv(evidence_path)
    required = {
        "case_label",
        "ae_evidence_tier",
        "recommended_claim_scope",
        "ae_pass_states",
        "ae_blocked_states",
        "vapor_ae_spearman_nonblocked",
        "vapor_ae_max_abs_delta",
        "limiting_factors",
    }
    missing = sorted(required - set(evidence.columns))
    if missing:
        findings.append(Finding("ERROR", "AE evidence tiers", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "AE evidence tiers", f"Found {evidence_path}"))
    tier_counts = evidence["ae_evidence_tier"].fillna("unknown").value_counts().sort_index()
    metrics.append(
        "- AE evidence tiers: "
        + ", ".join(f"{tier}={count}" for tier, count in tier_counts.items())
    )
    no_pass = evidence[pd.to_numeric(evidence["ae_pass_states"], errors="coerce") == 0]
    if not no_pass.empty:
        labels = ", ".join(no_pass["case_label"].astype(str))
        findings.append(
            Finding(
                "WARN",
                "AE evidence tiers",
                f"No case-level AE evidence has pass-quality windows: {labels}.",
            )
        )
    restricted = evidence[
        evidence["ae_evidence_tier"].fillna("") != "screening_supported"
    ].copy()
    if not restricted.empty:
        findings.append(
            Finding(
                "WARN",
                "AE evidence tiers",
                "AE claims remain restricted to exploratory or caveated screening scope.",
            )
        )
        tables.append("\n### AE evidence-tier limits\n")
        tables.append(
            markdown_table(
                restricted[
                    [
                        "case_label",
                        "ae_evidence_tier",
                        "recommended_claim_scope",
                        "ae_pass_states",
                        "ae_blocked_states",
                        "vapor_ae_spearman_nonblocked",
                        "vapor_ae_max_abs_delta",
                        "limiting_factors",
                    ]
                ],
                floatfmt=".2f",
            )
        )


def check_ae_readiness_matrix(
    readiness_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not readiness_path.exists():
        findings.append(Finding("WARN", "AE readiness matrix", f"Missing {readiness_path}"))
        return

    readiness = pd.read_csv(readiness_path)
    required = {
        "case_label",
        "ae_readiness_status",
        "quantitative_ae_ready",
        "screening_ae_ready",
        "ae_pass_states",
        "ae_blocked_states",
        "ae_pass_fraction",
        "ae_nonblocked_states",
        "blocking_criteria",
        "recommended_next_action",
    }
    missing = sorted(required - set(readiness.columns))
    if missing:
        findings.append(Finding("ERROR", "AE readiness matrix", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "AE readiness matrix", f"Found {readiness_path}"))
    status_counts = readiness["ae_readiness_status"].fillna("unknown").value_counts()
    status_counts = status_counts.sort_index()
    metrics.append(
        "- AE readiness statuses: "
        + ", ".join(f"{status}={count}" for status, count in status_counts.items())
    )

    quantitative_ready = truthy_series(readiness["quantitative_ae_ready"])
    screening_ready = truthy_series(readiness["screening_ae_ready"])
    metrics.append(
        "- AE quantitative-ready cases: "
        f"{int(quantitative_ready.sum())} of {len(readiness)}"
    )
    metrics.append(
        "- AE screening-ready cases: "
        f"{int(screening_ready.sum())} of {len(readiness)}"
    )

    not_quantitative = readiness[~quantitative_ready].copy()
    if not_quantitative.empty:
        findings.append(
            Finding(
                "PASS",
                "AE readiness matrix",
                "All cases satisfy quantitative AE readiness criteria.",
            )
        )
    else:
        if int(quantitative_ready.sum()) == 0:
            detail = "No current case satisfies quantitative AE readiness criteria."
        else:
            detail = (
                f"{len(not_quantitative)} cases do not satisfy quantitative AE "
                "readiness criteria."
            )
        findings.append(
            Finding(
                "BLOCKER",
                "AE readiness matrix",
                detail,
            )
        )
        tables.append("\n### AE readiness blockers\n")
        tables.append(
            markdown_table(
                not_quantitative[
                    [
                        "case_label",
                        "ae_readiness_status",
                        "ae_pass_states",
                        "ae_blocked_states",
                        "ae_nonblocked_states",
                        "blocking_criteria",
                        "recommended_next_action",
                    ]
                ],
                floatfmt=".2f",
            )
        )


def check_ae_verification_status(
    verification_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not verification_path.exists():
        findings.append(Finding("WARN", "AE verification status", f"Missing {verification_path}"))
        return

    verification = pd.read_csv(verification_path)
    required = {
        "case_label",
        "trigger_synchronization_verified",
        "sensor_coupling_verified",
        "verification_source",
        "verification_notes",
    }
    missing = sorted(required - set(verification.columns))
    if missing:
        findings.append(Finding("ERROR", "AE verification status", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "AE verification status", f"Found {verification_path}"))
    trigger_verified = truthy_series(verification["trigger_synchronization_verified"])
    coupling_verified = truthy_series(verification["sensor_coupling_verified"])
    metrics.append(
        "- AE trigger-verified cases: "
        f"{int(trigger_verified.sum())} of {len(verification)}"
    )
    metrics.append(
        "- AE sensor-coupling-verified cases: "
        f"{int(coupling_verified.sum())} of {len(verification)}"
    )
    if not bool(trigger_verified.any()) or not bool(coupling_verified.any()):
        findings.append(
            Finding(
                "WARN",
                "AE verification status",
                (
                    "No supplied case-level trigger or sensor-coupling verification "
                    "closes the AE gate."
                ),
            )
        )
    tables.append("\n### AE verification status\n")
    tables.append(
        markdown_table(
            verification[
                [
                    "case_label",
                    "trigger_synchronization_verified",
                    "sensor_coupling_verified",
                    "verification_source",
                    "verification_notes",
                ]
            ]
        )
    )


def check_ae_remediation_plan(
    remediation_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not remediation_path.exists():
        findings.append(Finding("WARN", "AE remediation plan", f"Missing {remediation_path}"))
        return

    remediation = pd.read_csv(remediation_path)
    required = {
        "case_label",
        "remediation_priority",
        "current_ae_readiness_status",
        "blocked_state_labels",
        "long_window_state_labels",
        "legacy_metadata_state_count",
        "primary_rerun_action",
        "verification_actions",
        "minimum_quantitative_gate",
        "manuscript_rule_until_closed",
    }
    missing = sorted(required - set(remediation.columns))
    if missing:
        findings.append(Finding("ERROR", "AE remediation plan", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "AE remediation plan", f"Found {remediation_path}"))
    priorities = remediation["remediation_priority"].value_counts().sort_index()
    metrics.append(
        "- AE remediation priorities: "
        + ", ".join(f"P{priority}={count}" for priority, count in priorities.items())
    )
    open_actions = remediation[
        remediation["current_ae_readiness_status"].fillna("") != "quantitative_ready"
    ]
    if not open_actions.empty:
        findings.append(
            Finding(
                "WARN",
                "AE remediation plan",
                f"{len(open_actions)} cases still require AE remediation before quantitative use.",
            )
        )
        tables.append("\n### AE remediation plan\n")
        tables.append(
            markdown_table(
                open_actions[
                    [
                        "case_label",
                        "remediation_priority",
                        "current_ae_readiness_status",
                        "blocked_state_labels",
                        "long_window_state_labels",
                        "primary_rerun_action",
                        "verification_actions",
                    ]
                ],
                floatfmt=".2f",
            )
        )


def check_claim_evidence_matrix(
    matrix_path: Path,
    findings: list[Finding],
    metrics: list[str],
    tables: list[str],
) -> None:
    if not matrix_path.exists():
        findings.append(Finding("WARN", "Claim-evidence matrix", f"Missing {matrix_path}"))
        return

    matrix = pd.read_csv(matrix_path)
    required = {
        "claim_id",
        "manuscript_claim",
        "support_status",
        "allowed_scope",
        "evidence_artifacts",
        "blocking_or_limiting_factors",
        "next_verification_needed",
    }
    missing = sorted(required - set(matrix.columns))
    if missing:
        findings.append(Finding("ERROR", "Claim-evidence matrix", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "Claim-evidence matrix", f"Found {matrix_path}"))
    status_counts = matrix["support_status"].fillna("unknown").value_counts().sort_index()
    metrics.append(
        "- Claim-evidence statuses: "
        + ", ".join(f"{status}={count}" for status, count in status_counts.items())
    )
    restricted = matrix[
        matrix["support_status"].fillna("").isin(
            ["screening_only", "not_supported_current_snapshot", "state_sensitive_or_mixed"]
        )
    ].copy()
    if restricted.empty:
        findings.append(
            Finding("PASS", "Claim-evidence matrix", "All tracked claims are supported.")
        )
    else:
        labels = ", ".join(restricted["claim_id"].astype(str))
        findings.append(
            Finding(
                "WARN",
                "Claim-evidence matrix",
                f"Restricted or unsupported claims require scoped wording: {labels}.",
            )
        )
        tables.append("\n### Claim-evidence matrix restricted rows\n")
        tables.append(
            markdown_table(
                restricted[
                    [
                        "claim_id",
                        "support_status",
                        "allowed_scope",
                        "blocking_or_limiting_factors",
                        "next_verification_needed",
                    ]
                ]
            )
        )


def spearman_rank(data: pd.DataFrame, x_column: str, y_column: str) -> float:
    if len(data) < 3:
        return np.nan
    values = pd.DataFrame(
        {
            "x": pd.to_numeric(data[x_column], errors="coerce"),
            "y": pd.to_numeric(data[y_column], errors="coerce"),
        }
    ).dropna()
    if len(values) < 3:
        return np.nan
    return float(values["x"].rank().corr(values["y"].rank()))


def build_leave_one_state_out_table(data: pd.DataFrame) -> pd.DataFrame:
    relationships = [
        (
            "heat_flux_vs_vapor_area",
            "heat_flux_mean_w_cm2",
            "vapor_area_fraction_mean",
            False,
        ),
        (
            "heat_flux_vs_active_length",
            "heat_flux_mean_w_cm2",
            "active_length_fraction_mean",
            False,
        ),
        (
            "vapor_area_vs_ae_nonblocked",
            "vapor_area_fraction_mean",
            "ae_abs_energy_rate",
            True,
        ),
    ]
    rows = []
    for case, group in data.groupby("case_label"):
        for relationship, x_column, y_column, exclude_blocked in relationships:
            subset = group
            if exclude_blocked and "ae_window_quality" in subset.columns:
                subset = subset[subset["ae_window_quality"].fillna("unknown") != "blocked"]
            if len(subset) < 4:
                continue
            baseline = spearman_rank(subset, x_column, y_column)
            leave_one_out = []
            for index, row in subset.iterrows():
                rho = spearman_rank(subset.drop(index=index), x_column, y_column)
                if np.isfinite(rho):
                    leave_one_out.append(
                        {
                            "removed_state": row["state_label"],
                            "rho_without_state": rho,
                            "delta": abs(rho - baseline),
                        }
                    )
            if not leave_one_out:
                continue
            loo = pd.DataFrame(leave_one_out)
            most = loo.loc[loo["delta"].idxmax()]
            rows.append(
                {
                    "case_label": case,
                    "relationship": relationship,
                    "baseline_spearman": baseline,
                    "leave_one_out_min": loo["rho_without_state"].min(),
                    "leave_one_out_max": loo["rho_without_state"].max(),
                    "most_influential_removed_state": most["removed_state"],
                    "spearman_without_most_influential_state": most["rho_without_state"],
                    "max_abs_delta": most["delta"],
                }
            )
    return pd.DataFrame(rows).sort_values(["relationship", "case_label"])


def check_model_artifacts(
    model_dir: Path,
    manifest_path: Path,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    metrics.append(f"- Model artifact directory checked: {model_dir}")
    metrics.append(f"- Model artifact manifest checked: {manifest_path}")
    expected = [
        model_dir / "model_final.pth",
        model_dir / "config.yaml",
        model_dir / "metrics.json",
        model_dir / "eval" / "coco_instances_results.json",
    ]
    missing = []
    for path in expected:
        try:
            exists = path.exists()
        except PermissionError:
            if check_model_artifact_manifest(manifest_path, findings):
                findings.append(
                    Finding(
                        "WARN",
                        "Local model artifacts",
                        f"Permission denied for local Box artifact: {path}",
                    )
                )
            else:
                findings.append(
                    Finding("BLOCKER", "Model validation artifacts", f"Permission denied: {path}")
                )
            return
        if not exists:
            missing.append(path.relative_to(model_dir).as_posix())
    if missing:
        if check_model_artifact_manifest(manifest_path, findings):
            findings.append(
                Finding(
                    "WARN",
                    "Local model artifacts",
                    "Local model/evaluation files are missing or inaccessible: "
                    + ", ".join(missing),
                )
            )
        else:
            findings.append(
                Finding(
                    "BLOCKER",
                    "Model validation artifacts",
                    f"Missing or inaccessible model/evaluation files: {', '.join(missing)}",
                )
            )
    else:
        findings.append(
            Finding("PASS", "Model validation artifacts", "Model and eval files are present.")
        )


def check_model_artifact_manifest(
    manifest_path: Path,
    findings: list[Finding],
) -> bool:
    """Check repo-tracked model archive metadata when local Box artifacts are unavailable."""
    if not manifest_path.exists():
        findings.append(
            Finding(
                "WARN",
                "Model artifact manifest",
                f"No repo-tracked manifest found at {manifest_path}.",
            )
        )
        return False

    manifest = pd.read_csv(manifest_path)
    required = {
        "artifact",
        "availability_status",
        "location_or_url",
        "sha256_or_version",
        "validation_role",
    }
    missing_columns = sorted(required - set(manifest.columns))
    if missing_columns:
        findings.append(
            Finding(
                "WARN",
                "Model artifact manifest",
                f"Manifest is missing columns: {missing_columns}",
            )
        )
        return False

    by_artifact = manifest.set_index("artifact")
    if "model_final.pth" not in by_artifact.index:
        findings.append(
            Finding("WARN", "Model artifact manifest", "Manifest does not list model_final.pth.")
        )
        return False

    weights = by_artifact.loc["model_final.pth"]
    status = str(weights["availability_status"]).strip().lower()
    url = str(weights["location_or_url"]).strip()
    digest = str(weights["sha256_or_version"]).strip()
    archive_ok = (
        status == "public_archive_documented"
        and url.startswith(("http://", "https://"))
        and len(digest) >= 32
    )
    if not archive_ok:
        findings.append(
            Finding(
                "WARN",
                "Model artifact manifest",
                "model_final.pth lacks public archive URL or checksum metadata.",
            )
        )
        return False

    findings.append(
        Finding(
            "PASS",
            "Model artifact manifest",
            "Public model-weight archive and checksum are documented.",
        )
    )

    validation_artifacts = {"metrics.json", "eval/coco_instances_results.json"}
    missing_validation = []
    for artifact in sorted(validation_artifacts):
        if artifact not in by_artifact.index:
            missing_validation.append(artifact)
            continue
        artifact_status = str(by_artifact.loc[artifact, "availability_status"]).strip().lower()
        if artifact_status not in {"public_archive_documented", "repo_tracked"}:
            missing_validation.append(artifact)
    if missing_validation:
        findings.append(
            Finding(
                "WARN",
                "Model validation metrics",
                "Evaluation artifacts are not yet archived or repo-tracked: "
                + ", ".join(missing_validation),
            )
        )

    if "manual_validation_panel" in by_artifact.index:
        manual_status = str(
            by_artifact.loc["manual_validation_panel", "availability_status"]
        ).strip().lower()
        if manual_status == "complete_internal_holdout":
            findings.append(
                Finding(
                    "PASS",
                    "Manual segmentation validation",
                    "Internal-holdout manual-mask evaluation is documented.",
                )
            )
            findings.append(
                Finding(
                    "WARN",
                    "Segmentation generalization",
                    "Experiment-held-out manual-mask validation remains pending.",
                )
            )
        elif manual_status != "complete":
            findings.append(
                Finding(
                    "WARN",
                    "Manual segmentation validation",
                    "Held-out manual-mask validation remains pending.",
                )
            )
    return True


def build_report(findings: list[Finding], metrics: list[str], tables: list[str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counts = {
        level: sum(1 for finding in findings if finding.level == level)
        for level in levels(findings)
    }
    lines = [
        "# Manuscript Validation Readiness Audit",
        "",
        f"Generated: {now}",
        "",
        "## Summary",
        "",
    ]
    for level, count in counts.items():
        lines.append(f"- {level}: {count}")
    lines.extend(["", "## Metrics", ""])
    lines.extend(metrics if metrics else ["- No metrics generated."])
    lines.extend(["", "## Findings", ""])
    for finding in findings:
        lines.append(f"- **{finding.level} - {finding.item}:** {finding.detail}")
    if tables:
        lines.extend(["", "## Detail Tables", ""])
        lines.extend(tables)
    lines.append("")
    return "\n".join(lines)


def markdown_table(data: pd.DataFrame, *, floatfmt: str | None = None) -> str:
    if data.empty:
        return "_No rows._"
    columns = [str(column) for column in data.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in data.itertuples(index=False):
        values = [format_table_value(value, floatfmt=floatfmt) for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def format_table_value(value: object, *, floatfmt: str | None = None) -> str:
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            return ""
        return format(float(value), floatfmt) if floatfmt else str(float(value))
    return str(value)


def truthy_series(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])


def levels(findings: list[Finding]) -> list[str]:
    preferred = ["ERROR", "BLOCKER", "WARN", "PASS"]
    present = {finding.level for finding in findings}
    return [level for level in preferred if level in present]


if __name__ == "__main__":
    main()
