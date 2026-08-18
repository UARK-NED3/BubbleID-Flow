from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


REQUIRED_FIGURES = [
    "Figure_1_facility_data_streams.pdf",
    "Figure_2_dataset_preparation_pipeline.pdf",
    "Figure_3_finetuning_architecture.pdf",
    "Figure_4_aug9_model_outputs.pdf",
    "Figure_5_segmentation_robustness.pdf",
    "Figure_6_segmentation_baselines.pdf",
    "Figure_5_aug9_optical_results.pdf",
    "Figure_7_optical_thermal_association.pdf",
    "Graphical_Abstract.pdf",
]

FIGURE_OUTPUT_PATHS = {
    "Figure_1_facility_data_streams.pdf": "ate_submission/figures/Figure_1_facility_data_streams.pdf",
    "Figure_2_dataset_preparation_pipeline.pdf": "aug9_model_analysis/abrar_schematic_slide_1.pdf",
    "Figure_3_finetuning_architecture.pdf": "aug9_model_analysis/abrar_schematic_slide_2.pdf",
    "Figure_4_aug9_model_outputs.pdf": "aug9_model_analysis/Figure_4_aug9_model_outputs.pdf",
    "Figure_5_segmentation_robustness.pdf": "aug9_model_analysis/segmentation_robustness/Figure_5_segmentation_robustness.pdf",
    "Figure_6_segmentation_baselines.pdf": "aug9_model_analysis/segmentation_baselines/Figure_segmentation_baselines.pdf",
    "Figure_5_aug9_optical_results.pdf": "aug9_model_analysis/Figure_5_aug9_optical_results.pdf",
    "Figure_7_optical_thermal_association.pdf": "aug9_model_analysis/optical_thermal_association/Figure_6_optical_thermal_association.pdf",
    "Graphical_Abstract.pdf": "aug9_model_analysis/Graphical_Abstract.pdf",
}

REQUIRED_SECTIONS = [
    "CRediT authorship contribution statement",
    "Declaration of competing interest",
    "Funding",
    "Data availability",
    "Declaration of generative AI and AI-assisted technologies",
]

VERSIONED_EVIDENCE_ARTIFACTS = [
    "aug9_model_analysis/aug9_state_vapor_fraction.csv",
    "aug9_model_analysis/aug9_temporal_summary_45V.csv",
    "aug9_model_analysis/full_sequences/full_sequence_frame_metrics.csv",
    "aug9_model_analysis/full_sequences/full_sequence_state_summary.csv",
    "aug9_model_analysis/internal_holdout_evaluation/coco_evaluation_results.json",
    "aug9_model_analysis/segmentation_robustness/segmentation_robustness_summary.json",
    "aug9_model_analysis/segmentation_baselines/segmentation_baseline_summary.csv",
    "aug9_model_analysis/segmentation_baselines/pixel_gaussian_baseline.json",
    "aug9_model_analysis/thermal_audit/thermal_state_audit.csv",
    "aug9_model_analysis/thermal_audit/thermal_reduction_manifest.json",
    "aug9_model_analysis/optical_thermal_association/optical_incremental_cv_summary.csv",
    "aug9_model_analysis/optical_thermal_association/optical_thermal_case_associations.csv",
    "aug9_model_analysis/optical_thermal_association/optical_thermal_association_manifest.json",
]

SUBMISSION_BLOCKER_PHRASES = [
    "should be confirmed by all authors before submission",
    "should be inserted and verified before submission",
    "should be inserted before final submission",
    "should be finalized after confirming",
    "contribution roles to be confirmed",
    "all roles require author confirmation",
    "all authors must confirm",
    "remain to be verified before submission",
    "should be finalized with all contributors",
]

UNSUPPORTED_CLAIM_LANGUAGE_RULES = {
    "ae_regime_classifier_or_lead_lag": {
        "label": "AE classifier/timing language",
        "patterns": [
            r"\b(?:ae|acoustic(?:-emission)?)\b.{0,120}"
            r"\b(?:classif(?:y|ies|ication|ier)|regime classifier|regime "
            r"classification|lead[- ]lag|timing|time delay|precedes?|lags?)\b",
            r"\b(?:classif(?:y|ies|ication|ier)|regime classifier|regime "
            r"classification|lead[- ]lag|timing|time delay|precedes?|lags?)\b"
            r".{0,120}\b(?:ae|acoustic(?:-emission)?)\b",
        ],
    },
    "bubble_instance_statistics": {
        "label": "bubble instance-statistic language",
        "patterns": [
            r"\b(?:quantif(?:y|ies|ied)|measure[sd]?|extract[sed]?|resolve[sd]?|"
            r"track[sed]?|report[sed]?)\b.{0,120}\b(?:individual bubble|"
            r"bubble count|bubble size|bubble diameter|coalescence|instance-level)\b",
            r"\b(?:individual bubble|bubble count|bubble size|bubble diameter|"
            r"coalescence|instance-level)\b.{0,120}\b(?:quantif(?:y|ies|ied)|"
            r"measure[sd]?|extract[sed]?|resolve[sd]?|track[sed]?|report[sed]?)\b",
        ],
    },
    "local_optical_thermal_coupling": {
        "label": "local optical-thermal coupling language",
        "patterns": [
            r"\b(?:camera|optical|vapor|roi)\b.{0,140}\b(?:registered|aligned|"
            r"mapped|coupled)\b.{0,80}\b(?:thermocouple|local htc|local heat)\b",
            r"\b(?:thermocouple|local htc|local heat)\b.{0,140}\b(?:registered|"
            r"aligned|mapped|coupled)\b.{0,80}\b(?:camera|optical|vapor|roi)\b",
        ],
    },
}

CLAIM_SCOPE_GUARD_TERMS = [
    "not",
    "no ",
    "without",
    "cannot",
    "can not",
    "should not",
    "must not",
    "do not",
    "does not",
    "not supported",
    "unsupported",
    "blocked",
    "unverified",
    "missing",
    "pending",
    "screening",
    "provisional",
    "cautious",
    "caveat",
    "requires",
    "require",
    "required",
    "before",
    "until",
    "rather than",
    "avoid",
    "reject",
    "flag",
    "gate",
    "audit",
    "remain open",
]


@dataclass(frozen=True)
class Finding:
    level: str
    item: str
    detail: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the Applied Thermal Engineering package.")
    parser.add_argument("--overleaf-dir", default="overleaf_applied_thermal_engineering")
    parser.add_argument("--outputs-root", default="outputs")
    parser.add_argument("--report", default="docs/ate_submission_package_audit.md")
    parser.add_argument(
        "--strict", action="store_true", help="Exit nonzero on submission blockers."
    )
    args = parser.parse_args()

    overleaf_dir = Path(args.overleaf_dir)
    outputs_root = Path(args.outputs_root)
    report_path = Path(args.report)
    main_tex = overleaf_dir / "main.tex"
    references_bib = overleaf_dir / "references.bib"
    highlights_tex = overleaf_dir / "highlights.tex"

    findings: list[Finding] = []
    metrics: list[str] = []
    main_text = read_text(main_tex, findings, "main.tex")
    bib_text = read_text(references_bib, findings, "references.bib")
    highlights_text = read_text(highlights_tex, findings, "highlights.tex")

    if main_text:
        check_abstract(main_text, findings, metrics)
        check_keywords(main_text, findings, metrics)
        check_required_sections(main_text, findings)
        check_submission_blockers(main_text, findings)
        check_figures(main_text, overleaf_dir, outputs_root, findings)
    if main_text and bib_text:
        check_citations(main_text, bib_text, findings, metrics)
    if highlights_text:
        check_highlights(highlights_text, findings, metrics)

    check_output_tables(outputs_root, main_text, findings, metrics)
    check_aug9_optical_evidence(outputs_root, main_text, findings, metrics)
    check_versioned_evidence_artifacts(outputs_root, findings, metrics)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(findings, metrics), encoding="utf-8")

    errors = [finding for finding in findings if finding.level == "ERROR"]
    blockers = [finding for finding in findings if finding.level == "BLOCKER"]
    print(f"Wrote {report_path}")
    print(f"Audit findings: {len(errors)} errors, {len(blockers)} submission blockers")
    if errors or (args.strict and blockers):
        raise SystemExit(1)


def read_text(path: Path, findings: list[Finding], label: str) -> str:
    if not path.exists():
        findings.append(Finding("ERROR", label, f"Missing required file: {path}"))
        return ""
    findings.append(Finding("PASS", label, f"Found {path.as_posix()}"))
    return path.read_text(encoding="utf-8")


def check_abstract(text: str, findings: list[Finding], metrics: list[str]) -> None:
    abstract = extract_environment(text, "abstract")
    if not abstract:
        findings.append(Finding("ERROR", "Abstract", "Could not find abstract environment."))
        return
    words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", strip_latex(abstract))
    metrics.append(f"- Abstract word count: {len(words)}")
    if len(words) <= 250:
        findings.append(Finding("PASS", "Abstract", "Abstract is within the 250-word ATE limit."))
    else:
        findings.append(Finding("ERROR", "Abstract", f"Abstract has {len(words)} words."))


def check_keywords(text: str, findings: list[Finding], metrics: list[str]) -> None:
    keywords = extract_environment(text, "keyword")
    if not keywords:
        findings.append(Finding("ERROR", "Keywords", "Could not find keyword environment."))
        return
    items = [strip_latex(item).strip() for item in keywords.split(r"\sep") if item.strip()]
    metrics.append(f"- Keyword count: {len(items)} ({', '.join(items)})")
    if 3 <= len(items) <= 8:
        findings.append(Finding("PASS", "Keywords", "Keyword count is in a normal journal range."))
    else:
        findings.append(Finding("WARN", "Keywords", "Keyword count is unusual; check ATE limits."))


def check_highlights(text: str, findings: list[Finding], metrics: list[str]) -> None:
    items = re.findall(r"\\item\s+(.+)", text)
    metrics.append(f"- Highlight count: {len(items)}")
    if len(items) == 5:
        findings.append(Finding("PASS", "Highlights", "Five highlights are present."))
    else:
        findings.append(
            Finding("ERROR", "Highlights", f"Expected five highlights, found {len(items)}.")
        )
    for index, item in enumerate(items, start=1):
        plain = strip_latex(item).strip()
        metrics.append(f"- Highlight {index} length: {len(plain)} characters")
        if len(plain) <= 85:
            findings.append(Finding("PASS", f"Highlight {index}", "Within 85 characters."))
        else:
            findings.append(Finding("ERROR", f"Highlight {index}", f"{len(plain)} characters."))


def check_required_sections(text: str, findings: list[Finding]) -> None:
    for section in REQUIRED_SECTIONS:
        if section.lower() in text.lower():
            findings.append(Finding("PASS", "Required sections", f"Found: {section}"))
        else:
            findings.append(Finding("ERROR", "Required sections", f"Missing: {section}"))


def check_submission_blockers(text: str, findings: list[Finding]) -> None:
    lower = text.lower()
    for phrase in SUBMISSION_BLOCKER_PHRASES:
        start = 0
        while True:
            index = lower.find(phrase, start)
            if index < 0:
                break
            line = text[:index].count("\n") + 1
            findings.append(
                Finding(
                    "BLOCKER",
                    "Submission placeholder",
                    f"Line {line}: contains '{phrase}'.",
                )
            )
            start = index + len(phrase)
    if not any(f.item == "Submission placeholder" for f in findings):
        findings.append(
            Finding("PASS", "Submission placeholders", "No known blocker phrases found.")
        )


def check_figures(
    text: str,
    overleaf_dir: Path,
    outputs_root: Path,
    findings: list[Finding],
) -> None:
    included = set(re.findall(r"\\includegraphics(?:\[[^\]]+\])?\{([^}]+)\}", text))
    for figure in REQUIRED_FIGURES:
        if (overleaf_dir / figure).exists():
            findings.append(Finding("PASS", "Figure package", f"Found Overleaf file: {figure}"))
        else:
            findings.append(Finding("ERROR", "Figure package", f"Missing Overleaf file: {figure}"))
        if figure in included or figure == "Graphical_Abstract.pdf":
            findings.append(
                Finding("PASS", "Figure inclusion", f"Referenced or packaged: {figure}")
            )
        else:
            findings.append(
                Finding("WARN", "Figure inclusion", f"Not referenced in main.tex: {figure}")
            )
        output_path = outputs_root / FIGURE_OUTPUT_PATHS[figure]
        if output_path.exists():
            findings.append(Finding("PASS", "Figure outputs", f"Found generated file: {figure}"))
        else:
            findings.append(
                Finding("WARN", "Figure outputs", f"Missing source output: {output_path}")
            )


def check_citations(
    text: str,
    bib_text: str,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    cite_keys = set()
    for group in re.findall(r"\\cite(?:[a-zA-Z]*)?(?:\[[^\]]*\])?\{([^}]+)\}", text):
        cite_keys.update(key.strip() for key in group.split(",") if key.strip())
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib_text))
    missing = sorted(cite_keys - bib_keys)
    unused = sorted(bib_keys - cite_keys)
    metrics.append(f"- Citation keys used: {len(cite_keys)}")
    metrics.append(f"- Bibliography entries: {len(bib_keys)}")
    if missing:
        findings.append(Finding("ERROR", "Citations", f"Missing bib entries: {', '.join(missing)}"))
    else:
        findings.append(Finding("PASS", "Citations", "All cited keys exist in references.bib."))
    if unused:
        findings.append(Finding("WARN", "Citations", f"Unused bib entries: {', '.join(unused)}"))


def check_output_tables(
    outputs_root: Path,
    main_text: str,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    root = outputs_root / "aug9_model_analysis"
    paths = {
        "optical state summary": root / "aug9_state_vapor_fraction.csv",
        "45 V temporal summary": root / "aug9_temporal_summary_45V.csv",
        "partial full-sequence summary": root / "full_sequences" / "full_sequence_state_summary.csv",
        "segmentation baselines": root / "segmentation_baselines" / "segmentation_baseline_summary.csv",
        "thermal audit": root / "thermal_audit" / "thermal_state_audit.csv",
        "optical-thermal cross-validation": root / "optical_thermal_association" / "optical_incremental_cv_summary.csv",
        "case associations": root / "optical_thermal_association" / "optical_thermal_case_associations.csv",
    }
    missing = [f"{label}: {path}" for label, path in paths.items() if not path.exists()]
    if missing:
        findings.append(Finding("ERROR", "Current evidence package", "; ".join(missing)))
        return

    optical = pd.read_csv(paths["optical state summary"])
    temporal = pd.read_csv(paths["45 V temporal summary"])
    partial = pd.read_csv(paths["partial full-sequence summary"])
    baselines = pd.read_csv(paths["segmentation baselines"])
    thermal = pd.read_csv(paths["thermal audit"])
    cv = pd.read_csv(paths["optical-thermal cross-validation"])
    associations = pd.read_csv(paths["case associations"])

    required_cases = {"5gs_22C", "10gs_22C", "15gs_20C", "25gs_20C"}
    if required_cases <= set(optical["case_label"].dropna()):
        findings.append(Finding("PASS", "State summaries", "All four cases are present."))
    else:
        findings.append(Finding("ERROR", "State summaries", "One or more manuscript cases are missing."))
    metrics.append(f"- Optical states: {len(optical)}")

    expected_methods = {"Otsu morphology", "Pixel Gaussian", "Mask R-CNN"}
    baseline_methods = set(baselines["method"])
    if baseline_methods == expected_methods:
        errors = baselines.set_index("method")["mean_absolute_area_fraction_error"]
        metrics.append(
            "- Baseline coverage MAE: "
            + ", ".join(f"{name}={errors[name]:.4f}" for name in sorted(expected_methods))
        )
        if errors["Mask R-CNN"] < errors["Pixel Gaussian"] < errors["Otsu morphology"]:
            findings.append(Finding("PASS", "Segmentation baselines", "Mask R-CNN outperforms both holdout baselines."))
        else:
            findings.append(Finding("ERROR", "Segmentation baselines", "Baseline error ordering does not match the manuscript."))
    else:
        findings.append(Finding("ERROR", "Segmentation baselines", f"Unexpected methods: {sorted(baseline_methods)}"))

    temporal_required = {
        "ci95_half_width",
        "iid_student_t_ci95_half_width",
        "tau_int_frames",
        "effective_sample_size",
        "uncertainty_method",
    }
    if temporal_required <= set(temporal.columns):
        dependent = temporal["ci95_half_width"] > temporal["iid_student_t_ci95_half_width"]
        method_ok = temporal["uncertainty_method"].str.contains("moving-block bootstrap").all()
        neff_ok = (temporal["effective_sample_size"] < temporal["frames"]).all()
        metrics.append(
            f"- Temporal effective sample size range: {temporal['effective_sample_size'].min():.2f} to {temporal['effective_sample_size'].max():.2f}"
        )
        if dependent.all() and method_ok and neff_ok:
            findings.append(Finding("PASS", "Temporal uncertainty", "All complete sequences use wider autocorrelation-aware intervals."))
        else:
            findings.append(Finding("ERROR", "Temporal uncertainty", "Moving-block interval checks failed."))
    else:
        findings.append(Finding("ERROR", "Temporal uncertainty", f"Missing columns: {sorted(temporal_required - set(temporal.columns))}"))

    partial_join = partial.merge(
        optical[["case_label", "state_voltage", "vapor_area_fraction_aug9"]],
        on=["case_label", "state_voltage"],
        how="left",
    )
    partial_delta = (
        partial_join["vapor_area_fraction_mean"]
        - partial_join["vapor_area_fraction_aug9"]
    ).abs()
    metrics.append(f"- Additional complete state sequences: {len(partial_join)}")
    if (
        len(partial_join) == 3
        and set(partial_join["case_label"]) == {"5gs_22C"}
        and partial_join["vapor_area_fraction_aug9"].notna().all()
        and partial_delta.between(0.0011, 0.0030).all()
    ):
        findings.append(Finding("PASS", "Partial all-state rerun", "Three additional complete sequences remain separate and traceable."))
    else:
        findings.append(Finding("ERROR", "Partial all-state rerun", "Additional sequence evidence no longer matches the manuscript."))

    matched = thermal[thermal["thermal_rows"].fillna(0).astype(float) > 0]
    unmatched = thermal[thermal["thermal_rows"].fillna(0).astype(float) <= 0]
    max_delta = matched["heat_flux_reconstruction_delta_w_cm2"].abs().max()
    metrics.append(f"- Thermally matched states: {len(matched)}")
    metrics.append(f"- Maximum heat-flux reconstruction delta: {max_delta:.3e} W/cm2")
    expected_unmatched = (
        len(unmatched) == 1
        and unmatched.iloc[0]["case_label"] == "10gs_22C"
        and abs(float(unmatched.iloc[0]["state_voltage"]) - 45.0) < 1e-9
    )
    if len(matched) == 36 and expected_unmatched and max_delta < 1e-10:
        findings.append(Finding("PASS", "Thermal provenance", "Electrical heat flux is reconstructed and the single unmatched optical state is explicit."))
    else:
        findings.append(Finding("ERROR", "Thermal provenance", "Thermal state count or heat-flux reconstruction is inconsistent."))

    if (associations["spearman_voltage_vs_heat_flux"] == 1.0).all():
        findings.append(Finding("PASS", "Forcing confounding", "Voltage and heat flux are perfectly rank-confounded in all cases."))
    else:
        findings.append(Finding("ERROR", "Forcing confounding", "Association table no longer supports the stated confounding result."))

    pivot = cv.pivot(index="cross_validation", columns="model", values="rmse_c")
    cv_models = {"thermal baseline", "thermal baseline + projected area"}
    if cv_models <= set(pivot.columns) and (pivot["thermal baseline + projected area"] >= pivot["thermal baseline"]).all():
        findings.append(Finding("PASS", "Incremental optical test", "Projected coverage does not improve either cross-validated thermal baseline."))
    else:
        findings.append(Finding("ERROR", "Incremental optical test", "Cross-validation result conflicts with the manuscript."))

    lower = main_text.lower()
    scope_checks = {
        "working fluid": "fc-72" in lower and "deionized water" not in lower,
        "projected quantity": "not a volumetric void fraction" in lower,
        "operator labels": "operator-labeled endpoint" in lower and "chf-adjacent" not in lower,
        "thermal exclusions": "heat-transfer coefficient, vapor quality, friction factor, or energy-balance" in lower,
        "acoustic claim boundary": (
            "timestamp registration, not a common hardware trigger" in lower
            and "rather than trigger-synchronized or causal coupling" in lower
        ),
    }
    for label, passed in scope_checks.items():
        findings.append(Finding("PASS" if passed else "ERROR", "Claim scope", f"{label}: {'synchronized' if passed else 'missing or inconsistent'}"))

    check_figure_evidence_wording(main_text, findings)


def check_aug9_optical_evidence(
    outputs_root: Path,
    main_text: str,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    root = outputs_root / "aug9_model_analysis"
    state_path = root / "aug9_case_trend_summary.csv"
    temporal_path = root / "aug9_temporal_summary_45V.csv"
    evaluation_path = root / "internal_holdout_evaluation" / "coco_evaluation_results.json"
    robustness_path = root / "segmentation_robustness" / "segmentation_robustness_summary.json"
    sensitivity_path = (
        root / "segmentation_robustness" / "segmentation_operating_point_sensitivity.csv"
    )
    required = (state_path, temporal_path, evaluation_path, robustness_path, sensitivity_path)
    missing = [path for path in required if not path.exists()]
    if missing:
        findings.append(
            Finding("ERROR", "Aug. 9 optical evidence", f"Missing: {', '.join(map(str, missing))}")
        )
        return

    state = pd.read_csv(state_path).set_index("case_label")
    temporal = pd.read_csv(temporal_path)
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    robustness = json.loads(robustness_path.read_text(encoding="utf-8"))
    sensitivity = pd.read_csv(sensitivity_path)
    mae_45v = float(temporal["mean_minus_workbook"].abs().mean())
    coverage = evaluation["coverage"]
    split = robustness["split_audit"]
    selected = sensitivity[
        (sensitivity["score_threshold"] == 0.30)
        & (sensitivity["detection_cap"] == 300)
    ]
    if len(selected) != 1:
        findings.append(
            Finding("ERROR", "Segmentation robustness", "Missing unique 0.30/300 operating point.")
        )
        return
    checks = {
        "5 g/s peak coverage": f"{state.loc['5gs_22C', 'vapor_area_fraction_max']:.3f}",
        "15 g/s peak coverage": f"{state.loc['15gs_20C', 'vapor_area_fraction_max']:.3f}",
        "10 g/s peak coverage": f"{state.loc['10gs_22C', 'vapor_area_fraction_max']:.3f}",
        "25 g/s peak coverage": f"{state.loc['25gs_20C', 'vapor_area_fraction_max']:.3f}",
        "45 V reproduction MAE": f"{mae_45v:.5f}",
        "holdout mean IoU": f"{coverage['mean_union_mask_iou']:.3f}",
        "holdout mean Dice": f"{coverage['mean_union_mask_dice']:.3f}",
        "holdout projected-area MAE": f"{coverage['mean_absolute_area_fraction_error']:.4f}",
        "same-index holdout images": str(split["holdout_with_same_nominal_frame_in_training"]),
        "adjacent-index holdout images": str(split["holdout_with_training_frame_within_one_index"]),
    }
    metrics.extend(f"- {label}: {value}" for label, value in checks.items())
    missing_values = [f"{label}={value}" for label, value in checks.items() if value not in main_text]
    if missing_values:
        findings.append(
            Finding(
                "WARN",
                "Aug. 9 result synchronization",
                "Values not found verbatim in main.tex: " + ", ".join(missing_values),
            )
        )
    else:
        findings.append(
            Finding(
                "PASS",
                "Aug. 9 result synchronization",
                "Checkpoint, holdout, and complete-sequence headline values are synchronized.",
            )
        )

    if abs(float(selected.iloc[0]["mean_absolute_area_fraction_error"]) - coverage["mean_absolute_area_fraction_error"]) < 1e-12:
        findings.append(
            Finding(
                "PASS",
                "Segmentation robustness",
                "Archived predictions reproduce the selected 0.30/300 coverage metric and include split and threshold audits.",
            )
        )
    else:
        findings.append(
            Finding(
                "ERROR",
                "Segmentation robustness",
                "Selected robustness result does not reproduce the archived coverage metric.",
            )
        )
def check_versioned_evidence_artifacts(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    git_ignore_checker=None,
) -> None:
    """Check that manuscript evidence tables are not hidden by ignore rules."""
    checker = git_ignore_checker or git_path_is_ignored
    missing = []
    ignored = []
    visible_count = 0
    unknown_count = 0

    for artifact in VERSIONED_EVIDENCE_ARTIFACTS:
        path = outputs_root / artifact
        if not path.exists():
            missing.append(artifact)
            continue
        ignored_status = checker(path)
        if ignored_status is True:
            ignored.append(artifact)
        elif ignored_status is False:
            visible_count += 1
        else:
            unknown_count += 1

    metrics.append(
        "- Versioned current evidence artifacts visible to git: "
        f"{visible_count} of {len(VERSIONED_EVIDENCE_ARTIFACTS)}"
    )
    if unknown_count:
        metrics.append(
            "- Versioned current evidence artifacts with unknown git status: "
            f"{unknown_count}"
        )

    if missing:
        findings.append(
            Finding(
                "WARN",
                "Evidence artifact versioning",
                "Missing expected current evidence artifacts: " + ", ".join(missing),
            )
        )
    if ignored:
        findings.append(
            Finding(
                "BLOCKER",
                "Evidence artifact versioning",
                "Current evidence artifacts are present but git-ignored: "
                + ", ".join(ignored),
            )
        )
    elif not missing and unknown_count == 0:
        findings.append(
            Finding(
                "PASS",
                "Evidence artifact versioning",
                "Current manuscript evidence artifacts are versionable.",
            )
        )


def git_path_is_ignored(path: Path) -> bool | None:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", str(path)],
            check=False,
            cwd=Path.cwd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def check_trend_summary(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    trend_path = outputs_root / "multimodal" / "cross_case_synthesis"
    trend_path = trend_path / "cross_case_trend_summary.csv"
    if not trend_path.exists():
        findings.append(Finding("WARN", "Trend summary", f"Missing {trend_path}"))
        return

    trend = pd.read_csv(trend_path)
    required = {
        "case_label",
        "spearman_heat_flux_vapor_area",
        "spearman_heat_flux_active_length",
        "spearman_vapor_area_ae_nonblocked",
        "ae_blocked_states",
    }
    missing = sorted(required - set(trend.columns))
    if missing:
        findings.append(Finding("ERROR", "Trend summary", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "Trend summary", f"Found {trend_path}"))
    metrics.append(
        "- Trend summary, heat-flux/vapor rho: "
        + ", ".join(
            f"{row.case_label}={row.spearman_heat_flux_vapor_area:.2f}"
            for row in trend.sort_values("case_label").itertuples()
        )
    )
    metrics.append(
        "- Trend summary, heat-flux/active-length rho: "
        + ", ".join(
            f"{row.case_label}={row.spearman_heat_flux_active_length:.2f}"
            for row in trend.sort_values("case_label").itertuples()
        )
    )
    metrics.append(
        "- Trend summary, vapor/AE nonblocked rho: "
        + ", ".join(
            f"{row.case_label}={row.spearman_vapor_area_ae_nonblocked:.2f}"
            for row in trend.sort_values("case_label").itertuples()
        )
    )
    if "Spearman" in main_text:
        findings.append(
            Finding("PASS", "Trend summary", "Manuscript cites rank-agreement metrics.")
        )
    else:
        findings.append(
            Finding("WARN", "Trend summary", "Manuscript does not cite rank-agreement metrics.")
        )


def check_frame_sampling(data: pd.DataFrame, findings: list[Finding]) -> None:
    short = data[data["image_frames"] < 8]
    if short.empty:
        findings.append(
            Finding("PASS", "Image sampling", "Every analysis state uses eight sampled frames.")
        )
    else:
        counts = short.groupby("case_label")["state_label"].count().sort_index()
        detail = ", ".join(f"{case}: {count}" for case, count in counts.items())
        findings.append(
            Finding(
                "WARN",
                "Image sampling",
                f"Some states use fewer than eight sampled frames ({detail}).",
            )
        )


def check_thermal_window_alignment(
    data: pd.DataFrame,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    required = {"case_label", "state_label", "time_start_s", "time_end_s"}
    if not required <= set(data.columns):
        findings.append(Finding("WARN", "Thermal/AE windows", "Missing time-window columns."))
        return

    windows = data.dropna(subset=["time_start_s", "time_end_s"]).copy()
    windows["thermal_window_span_s"] = windows["time_end_s"] - windows["time_start_s"]
    metrics.append(
        "- Thermal window span range: "
        f"{windows['thermal_window_span_s'].min():.1f} to "
        f"{windows['thermal_window_span_s'].max():.1f} s"
    )
    long_windows = windows[windows["thermal_window_span_s"] > 120.0]
    if not long_windows.empty:
        findings.append(
            Finding(
                "WARN",
                "Thermal/AE windows",
                f"{len(long_windows)} states span more than 120 s.",
            )
        )

    overlaps = []
    for case, group in windows.sort_values(["case_label", "time_start_s"]).groupby("case_label"):
        previous_end = None
        previous_label = None
        for row in group.itertuples():
            if previous_end is not None and row.time_start_s < previous_end:
                overlaps.append(f"{case}/{row.state_label} overlaps {previous_label}")
            previous_end = row.time_end_s
            previous_label = row.state_label
    if overlaps:
        findings.append(
            Finding(
                "BLOCKER",
                "Thermal/AE windows",
                "Overlapping voltage-matched windows in tracked outputs: " + "; ".join(overlaps),
            )
        )
    else:
        findings.append(
            Finding("PASS", "Thermal/AE windows", "No overlapping state windows found.")
        )

    if "thermal_window_selection" not in data.columns:
        findings.append(
            Finding(
                "WARN",
                "Thermal/AE windows",
                "Tracked summaries do not yet include contiguous-window selection metadata.",
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
            labels = ", ".join(
                f"{row.case_label}/{row.state_label}" for row in blocked.itertuples()
            )
            findings.append(
                Finding("BLOCKER", "AE confidence", f"Blocked AE windows in figure data: {labels}")
            )
        if not caution.empty:
            findings.append(
                Finding(
                    "WARN",
                    "AE confidence",
                    f"{len(caution)} analysis states require cautious AE interpretation.",
                )
        )


def check_trend_sensitivity(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    sensitivity_path = outputs_root / "multimodal" / "cross_case_synthesis"
    sensitivity_path = sensitivity_path / "cross_case_trend_sensitivity.csv"
    if not sensitivity_path.exists():
        findings.append(Finding("WARN", "Trend sensitivity", f"Missing {sensitivity_path}"))
        return

    sensitivity = pd.read_csv(sensitivity_path)
    required = {
        "case_label",
        "relationship",
        "baseline_spearman",
        "most_influential_removed_state",
        "spearman_without_most_influential_state",
        "max_abs_delta",
    }
    missing = sorted(required - set(sensitivity.columns))
    if missing:
        findings.append(Finding("ERROR", "Trend sensitivity", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "Trend sensitivity", f"Found {sensitivity_path}"))
    ae = sensitivity[sensitivity["relationship"] == "vapor_area_vs_ae_nonblocked"].copy()
    if ae.empty:
        findings.append(Finding("WARN", "Trend sensitivity", "Missing vapor/AE sensitivity rows."))
        return

    metrics.append(
        "- Trend sensitivity, vapor/AE max |delta rho|: "
        + ", ".join(
            f"{row.case_label}={row.most_influential_removed_state} ({row.max_abs_delta:.2f})"
            for row in ae.sort_values("case_label").itertuples()
        )
    )
    sensitive = ae[pd.to_numeric(ae["max_abs_delta"], errors="coerce") > 0.30]
    if sensitive.empty:
        findings.append(
            Finding("PASS", "Trend sensitivity", "No vapor/AE case exceeds |delta rho| > 0.30.")
        )
    else:
        labels = ", ".join(
            f"{row.case_label}/{row.most_influential_removed_state}"
            for row in sensitive.itertuples()
        )
        findings.append(
            Finding(
                "WARN",
                "Trend sensitivity",
                f"Vapor/AE agreement is state-sensitive for: {labels}.",
            )
        )

    if "leave-one-state-out" in main_text.lower():
        findings.append(
            Finding("PASS", "Trend sensitivity", "Manuscript cites leave-one-state-out checks.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Trend sensitivity",
                "Manuscript does not cite leave-one-state-out checks.",
            )
        )


def check_sampling_uncertainty(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    sampling_path = outputs_root / "multimodal" / "cross_case_synthesis"
    sampling_path = sampling_path / "cross_case_sampling_uncertainty.csv"
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
    warnings = sampling[sampling["sampling_warning"].fillna("none") != "none"]
    relative = pd.to_numeric(
        sampling["vapor_area_fraction_relative_ci95_half_width"],
        errors="coerce",
    )
    if relative.notna().any():
        max_index = relative.idxmax()
        max_row = sampling.loc[max_index]
        metrics.append(
            "- Sampling uncertainty, max vapor relative 95% half-width: "
            f"{max_row.case_label}/{max_row.state_label}={relative.loc[max_index]:.2f}"
        )
    metrics.append(f"- Sampling uncertainty warnings: {len(warnings)} states")
    if warnings.empty:
        findings.append(
            Finding("PASS", "Sampling uncertainty", "No sampled states exceed warning criteria.")
        )
    else:
        labels = ", ".join(f"{row.case_label}/{row.state_label}" for row in warnings.itertuples())
        findings.append(
            Finding("WARN", "Sampling uncertainty", f"Warning states: {labels}")
        )

    if "sampling uncertainty" in main_text.lower() or "95\\%" in main_text:
        findings.append(
            Finding("PASS", "Sampling uncertainty", "Manuscript cites sampling uncertainty.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Sampling uncertainty",
                "Manuscript does not cite the sampling-uncertainty check.",
            )
        )


def check_active_threshold_sensitivity(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
    *,
    sensitivity_delta_warn: float = 0.10,
) -> None:
    sensitivity_path = outputs_root / "multimodal" / "cross_case_synthesis"
    sensitivity_path = sensitivity_path / "cross_case_active_threshold_sensitivity.csv"
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
    unchecked = sensitivity[
        sensitivity["active_threshold_sensitivity_status"].fillna("") != "checked"
    ]
    deltas = pd.to_numeric(
        sensitivity["active_length_max_abs_delta_from_baseline"],
        errors="coerce",
    )
    if deltas.notna().any():
        index = deltas.idxmax()
        row = sensitivity.loc[index]
        metrics.append(
            "- Active-length max threshold delta: "
            f"{row.case_label}/{row.state_label}={deltas.loc[index]:.3f}"
        )
    sensitive = sensitivity[deltas > sensitivity_delta_warn] if deltas.notna().any() else sensitivity.iloc[0:0]
    if unchecked.empty and sensitive.empty:
        findings.append(
            Finding(
                "PASS",
                "Active threshold sensitivity",
                "Active-length threshold sweeps are checked within tolerance.",
            )
        )
    else:
        if not unchecked.empty:
            findings.append(
                Finding(
                    "WARN",
                    "Active threshold sensitivity",
                    f"{len(unchecked)} states lack active-threshold sweep results.",
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

    text = main_text.lower()
    if (
        "active-threshold sensitivity" in text
        or "active threshold sensitivity" in text
        or "cross\\_case\\_active\\_threshold\\_sensitivity" in text
    ):
        findings.append(
            Finding(
                "PASS",
                "Active threshold sensitivity",
                "Manuscript cites the active-threshold sensitivity check.",
            )
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Active threshold sensitivity",
                "Manuscript does not cite the active-threshold sensitivity check.",
            )
        )


def check_segmentation_validation_plan(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    plan_path = outputs_root / "multimodal" / "cross_case_synthesis"
    plan_path = plan_path / "cross_case_segmentation_validation_plan.csv"
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
        findings.append(
            Finding(
                "WARN",
                "Manual segmentation validation",
                f"{int((~complete).sum())} planned mask-validation targets remain incomplete.",
            )
        )

    text = main_text.lower()
    if (
        "segmentation-validation plan" in text
        or "cross\\_case\\_segmentation\\_validation\\_plan" in text
    ):
        findings.append(
            Finding(
                "PASS",
                "Segmentation validation plan",
                "Manuscript cites the segmentation-validation plan.",
            )
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Segmentation validation plan",
                "Manuscript does not cite the segmentation-validation plan.",
            )
        )


def check_thermal_response_checks(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    thermal_path = outputs_root / "multimodal" / "cross_case_synthesis"
    thermal_path = thermal_path / "cross_case_thermal_response_checks.csv"
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
        "limiting_factors",
    }
    missing = sorted(required - set(thermal.columns))
    if missing:
        findings.append(Finding("ERROR", "Thermal response checks", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "Thermal response checks", f"Found {thermal_path}"))
    metrics.append(
        "- Thermal response statuses: "
        + ", ".join(
            f"{status}={count}"
            for status, count in thermal["thermal_context_status"]
            .fillna("unknown")
            .value_counts()
            .sort_index()
            .items()
        )
    )
    htc_rho = pd.to_numeric(thermal["spearman_heat_flux_htc"], errors="coerce")
    if htc_rho.notna().any():
        metrics.append(
            "- Thermal response, heat-flux/HTC rho range: "
            f"{htc_rho.min():.2f} to {htc_rho.max():.2f}"
        )
    needs_review = thermal[
        thermal["thermal_context_status"].fillna("") != "state_level_supported"
    ]
    if needs_review.empty:
        findings.append(
            Finding(
                "PASS",
                "Thermal response checks",
                "All cases support state-level thermal-context use.",
            )
        )
    else:
        labels = ", ".join(needs_review["case_label"].astype(str))
        findings.append(
            Finding(
                "WARN",
                "Thermal response checks",
                f"Thermal context needs review for: {labels}.",
            )
        )

    text = main_text.lower()
    if "thermal-response check" in text or "thermal response check" in text:
        findings.append(
            Finding("PASS", "Thermal response checks", "Manuscript cites the check.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Thermal response checks",
                "Manuscript does not cite the thermal-response check.",
            )
        )


def check_ae_evidence_tiers(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    evidence_path = outputs_root / "multimodal" / "cross_case_synthesis"
    evidence_path = evidence_path / "cross_case_ae_evidence_tiers.csv"
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
    metrics.append(
        "- AE evidence tiers: "
        + ", ".join(
            f"{row.case_label}={row.ae_evidence_tier}"
            for row in evidence.sort_values("case_label").itertuples()
        )
    )
    no_pass = evidence[pd.to_numeric(evidence["ae_pass_states"], errors="coerce") == 0]
    if not no_pass.empty:
        findings.append(
            Finding(
                "WARN",
                "AE evidence tiers",
                "No case currently has pass-quality AE windows.",
            )
        )
    restricted = evidence[
        evidence["ae_evidence_tier"].fillna("") != "screening_supported"
    ]
    if not restricted.empty:
        labels = ", ".join(
            f"{row.case_label}/{row.ae_evidence_tier}"
            for row in restricted.sort_values("case_label").itertuples()
        )
        findings.append(
            Finding(
                "WARN",
                "AE evidence tiers",
                f"AE claim scope remains restricted: {labels}.",
            )
        )

    text = main_text.lower()
    if "ae evidence tier" in text or "exploratory" in text:
        findings.append(
            Finding("PASS", "AE evidence tiers", "Manuscript cites AE evidence-tier limits.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "AE evidence tiers",
                "Manuscript does not cite AE evidence-tier limits.",
            )
        )


def check_ae_readiness_matrix(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    readiness_path = outputs_root / "multimodal" / "cross_case_synthesis"
    readiness_path = readiness_path / "cross_case_ae_readiness_matrix.csv"
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
    }
    missing = sorted(required - set(readiness.columns))
    if missing:
        findings.append(Finding("ERROR", "AE readiness matrix", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "AE readiness matrix", f"Found {readiness_path}"))
    metrics.append(
        "- AE readiness statuses: "
        + ", ".join(
            f"{row.case_label}={row.ae_readiness_status}"
            for row in readiness.sort_values("case_label").itertuples()
        )
    )

    quantitative_ready = truthy_series(readiness["quantitative_ae_ready"])
    metrics.append(
        "- AE quantitative-ready cases: "
        f"{int(quantitative_ready.sum())} of {len(readiness)}"
    )
    if not bool(quantitative_ready.any()):
        findings.append(
            Finding(
                "WARN",
                "AE readiness matrix",
                "No case satisfies quantitative AE readiness; keep AE wording screening-only.",
            )
        )
    else:
        findings.append(
            Finding("PASS", "AE readiness matrix", "At least one case is quantitative-ready.")
        )

    text = main_text.lower()
    if "ae readiness" in text or "cross\\_case\\_ae\\_readiness\\_matrix" in text:
        findings.append(
            Finding("PASS", "AE readiness matrix", "Manuscript cites AE readiness limits.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "AE readiness matrix",
                "Manuscript does not cite the AE readiness matrix.",
            )
        )


def check_ae_verification_status(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    verification_path = outputs_root / "multimodal" / "cross_case_synthesis"
    verification_path = verification_path / "cross_case_ae_verification_status.csv"
    if not verification_path.exists():
        findings.append(Finding("WARN", "AE verification status", f"Missing {verification_path}"))
        return

    verification = pd.read_csv(verification_path)
    required = {
        "case_label",
        "trigger_synchronization_verified",
        "sensor_coupling_verified",
        "verification_source",
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
                "No case has supplied trigger/coupling verification in the tracked package.",
            )
        )

    text = main_text.lower()
    if "ae verification status" in text or "cross\\_case\\_ae\\_verification\\_status" in text:
        findings.append(
            Finding("PASS", "AE verification status", "Manuscript cites AE verification status.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "AE verification status",
                "Manuscript does not cite the AE verification-status artifact.",
            )
        )


def check_ae_remediation_plan(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    remediation_path = outputs_root / "multimodal" / "cross_case_synthesis"
    remediation_path = remediation_path / "cross_case_ae_remediation_plan.csv"
    if not remediation_path.exists():
        findings.append(Finding("WARN", "AE remediation plan", f"Missing {remediation_path}"))
        return

    remediation = pd.read_csv(remediation_path)
    required = {
        "case_label",
        "remediation_priority",
        "current_ae_readiness_status",
        "primary_rerun_action",
        "verification_actions",
        "minimum_quantitative_gate",
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
                f"{len(open_actions)} cases remain on the AE remediation path.",
            )
        )

    text = main_text.lower()
    if "ae remediation" in text or "cross\\_case\\_ae\\_remediation\\_plan" in text:
        findings.append(
            Finding("PASS", "AE remediation plan", "Manuscript cites AE remediation plan.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "AE remediation plan",
                "Manuscript does not cite the AE remediation-plan artifact.",
            )
        )


def check_claim_evidence_matrix(
    outputs_root: Path,
    findings: list[Finding],
    metrics: list[str],
    main_text: str,
) -> None:
    matrix_path = outputs_root / "multimodal" / "cross_case_synthesis"
    matrix_path = matrix_path / "cross_case_claim_evidence_matrix.csv"
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
    }
    missing = sorted(required - set(matrix.columns))
    if missing:
        findings.append(Finding("ERROR", "Claim-evidence matrix", f"Missing columns: {missing}"))
        return

    findings.append(Finding("PASS", "Claim-evidence matrix", f"Found {matrix_path}"))
    metrics.append(
        "- Claim-evidence statuses: "
        + ", ".join(
            f"{status}={count}"
            for status, count in matrix["support_status"]
            .fillna("unknown")
            .value_counts()
            .sort_index()
            .items()
        )
    )
    unsupported = matrix[
        matrix["support_status"].fillna("") == "not_supported_current_snapshot"
    ]
    if unsupported.empty:
        findings.append(
            Finding("PASS", "Claim-evidence matrix", "No unsupported tracked claims.")
        )
    else:
        labels = ", ".join(unsupported["claim_id"].astype(str))
        findings.append(
            Finding(
                "WARN",
                "Claim-evidence matrix",
                f"Unsupported claims remain explicitly blocked: {labels}.",
            )
        )

    text = main_text.lower()
    if "claim-evidence matrix" in text or "claim scope" in text:
        findings.append(
            Finding("PASS", "Claim-evidence matrix", "Manuscript cites claim-scope matrix.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Claim-evidence matrix",
                "Manuscript does not cite the claim-evidence matrix.",
            )
        )
    check_claim_language_gates(matrix, main_text, findings, metrics)


def check_claim_language_gates(
    matrix: pd.DataFrame,
    main_text: str,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    """Reject assertive manuscript claims that the evidence matrix does not support."""
    unsupported_claims = set(
        matrix.loc[
            matrix["support_status"].fillna("") == "not_supported_current_snapshot",
            "claim_id",
        ].astype(str)
    )
    active_rules = [
        claim_id
        for claim_id in UNSUPPORTED_CLAIM_LANGUAGE_RULES
        if claim_id in unsupported_claims
    ]
    metrics.append(f"- Unsupported claim-language gates active: {len(active_rules)}")
    if not active_rules:
        findings.append(
            Finding(
                "PASS",
                "Claim language gates",
                "No unsupported claim families require language gates.",
            )
        )
        return

    violations = find_unsupported_claim_language(main_text, active_rules)
    if not violations:
        findings.append(
            Finding(
                "PASS",
                "Claim language gates",
                "No assertive unsupported claim language found in main.tex.",
            )
        )
        return

    for violation in violations:
        findings.append(
            Finding(
                "BLOCKER",
                "Claim language gates",
                (
                    f"{violation['label']} appears assertive despite unsupported "
                    f"claim status: {violation['excerpt']}"
                ),
            )
        )


def find_unsupported_claim_language(
    main_text: str,
    active_claim_ids: list[str],
) -> list[dict[str, str]]:
    plain_text = strip_latex(main_text).lower()
    sentences = split_sentences(plain_text)
    violations = []
    for claim_id in active_claim_ids:
        rule = UNSUPPORTED_CLAIM_LANGUAGE_RULES[claim_id]
        patterns = [re.compile(pattern, flags=re.I | re.S) for pattern in rule["patterns"]]
        for sentence in sentences:
            if any(pattern.search(sentence) for pattern in patterns):
                if sentence_has_scope_guard(sentence):
                    continue
                violations.append(
                    {
                        "claim_id": claim_id,
                        "label": str(rule["label"]),
                        "excerpt": truncate_sentence(sentence),
                    }
                )
    return violations


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if sentence.strip()
    ]


def sentence_has_scope_guard(sentence: str) -> bool:
    return any(term in sentence for term in CLAIM_SCOPE_GUARD_TERMS)


def truncate_sentence(sentence: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", sentence).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def check_figure_evidence_wording(main_text: str, findings: list[Finding]) -> None:
    text = main_text.lower()
    if "moving-block" in text and "table~\\ref{tab:temporal}" in text:
        findings.append(
            Finding("PASS", "Figure evidence wording", "Optical figure points to autocorrelation-aware intervals.")
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Figure evidence wording",
                "Optical figure does not point to the moving-block uncertainty evidence.",
            )
        )

    context_terms = ["segmentation baseline", "cross-validated temperature rmse", "temporal standard deviation"]
    if all(term in text for term in context_terms):
        findings.append(
            Finding(
                "PASS",
                "Figure evidence wording",
                "Baseline and optical-thermal figures define their evidence and variability.",
            )
        )
    else:
        findings.append(
            Finding(
                "WARN",
                "Figure evidence wording",
                "Baseline or optical-thermal figure wording is incomplete.",
            )
        )


def add_headline_number_checks(
    data: pd.DataFrame,
    main_text: str,
    findings: list[Finding],
    metrics: list[str],
) -> None:
    baseline = data[data["case_label"] == "15gs_20C"]
    checks = {
        "baseline vapor minimum": f"{baseline['vapor_area_fraction_mean'].min():.3f}",
        "baseline vapor maximum": f"{baseline['vapor_area_fraction_mean'].max():.3f}",
        "baseline heat-flux minimum": f"{baseline['heat_flux_mean_w_cm2'].min():.2f}",
        "baseline heat-flux maximum": f"{baseline['heat_flux_mean_w_cm2'].max():.2f}",
        "5gs maximum vapor fraction": (
            f"{data[data['case_label'] == '5gs_22C']['vapor_area_fraction_mean'].max():.3f}"
        ),
        "25gs maximum heat flux": (
            f"{data[data['case_label'] == '25gs_20C']['heat_flux_mean_w_cm2'].max():.2f}"
        ),
    }
    for label, value in checks.items():
        metrics.append(f"- {label}: {value}")
        if value in main_text:
            findings.append(Finding("PASS", "Headline result sync", f"{label} appears as {value}."))
        else:
            findings.append(
                Finding("WARN", "Headline result sync", f"{label} value {value} not found.")
            )


def extract_environment(text: str, name: str) -> str:
    match = re.search(rf"\\begin\{{{name}\}}(.*?)\\end\{{{name}\}}", text, flags=re.S)
    return match.group(1) if match else ""


def strip_latex(text: str) -> str:
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[$^_{}~]", " ", text)
    return re.sub(r"\s+", " ", text)


def build_report(findings: list[Finding], metrics: list[str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counts = {
        level: sum(1 for finding in findings if finding.level == level)
        for level in levels(findings)
    }
    lines = [
        "# ATE Submission Package Audit",
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
    lines.append("")
    return "\n".join(lines)


def truthy_series(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])


def levels(findings: list[Finding]) -> list[str]:
    preferred = ["ERROR", "BLOCKER", "WARN", "PASS"]
    present = {finding.level for finding in findings}
    return [level for level in preferred if level in present]


if __name__ == "__main__":
    main()
