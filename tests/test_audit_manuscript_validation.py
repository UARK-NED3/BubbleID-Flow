from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_audit_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "audit_manuscript_validation.py"
    )
    spec = importlib.util.spec_from_file_location("audit_manuscript_validation", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_model_manifest_prevents_false_local_artifact_blocker(tmp_path):
    module = load_audit_module()
    manifest = tmp_path / "model_artifact_manifest.csv"
    manifest.write_text(
        "\n".join(
            [
                "artifact,availability_status,location_or_url,sha256_or_version,validation_role",
                (
                    "model_final.pth,public_archive_documented,"
                    "https://osf.io/download/example/,"
                    "10613DE030B35637BECB4FDA524F8D829E9B77B25E90AB9A670992E8A9B4B166,"
                    "inference weights"
                ),
                "metrics.json,not_archived,local pending,not_available,training trace",
                (
                    "eval/coco_instances_results.json,not_archived,local pending,"
                    "not_available,held-out metrics"
                ),
                (
                    "manual_validation_panel,pending,not_yet_generated,"
                    "not_available,manual validation"
                ),
            ]
        ),
        encoding="utf-8",
    )
    findings = []
    metrics = []

    module.check_model_artifacts(tmp_path / "missing_model_dir", manifest, findings, metrics)

    by_item = {(finding.level, finding.item) for finding in findings}
    assert ("PASS", "Model artifact manifest") in by_item
    assert ("WARN", "Local model artifacts") in by_item
    assert ("WARN", "Model validation metrics") in by_item
    assert ("WARN", "Manual segmentation validation") in by_item
    assert not any(finding.level == "BLOCKER" for finding in findings)


def test_missing_model_manifest_keeps_model_artifact_blocker(tmp_path):
    module = load_audit_module()
    findings = []
    metrics = []

    module.check_model_artifacts(
        tmp_path / "missing_model_dir",
        tmp_path / "missing_manifest.csv",
        findings,
        metrics,
    )

    assert any(
        finding.level == "BLOCKER" and finding.item == "Model validation artifacts"
        for finding in findings
    )


def test_segmentation_validation_plan_reports_pending_targets(tmp_path):
    module = load_audit_module()
    plan = tmp_path / "cross_case_segmentation_validation_plan.csv"
    plan.write_text(
        "\n".join(
            [
                (
                    "case_label,state_label,validation_role,image_frames,"
                    "vapor_area_fraction_relative_ci95_half_width,sampling_warning,"
                    "minimum_manual_masks,validation_status,claim_gate_until_complete"
                ),
                (
                    "15gs_20C,25,onset_or_low_vapor,6,0.12,short_sample,8,"
                    "planned_not_complete,Do not report individual bubble count"
                ),
            ]
        ),
        encoding="utf-8",
    )
    findings = []
    metrics = []
    tables = []

    module.check_segmentation_validation_plan(plan, findings, metrics, tables)

    assert any(
        finding.level == "PASS" and finding.item == "Segmentation validation plan"
        for finding in findings
    )
    assert any(
        finding.level == "WARN" and finding.item == "Manual segmentation validation"
        for finding in findings
    )
    assert any("Segmentation validation targets" in metric for metric in metrics)
    assert any("Segmentation validation plan" in table for table in tables)


def test_active_threshold_sensitivity_reports_missing_sweep(tmp_path):
    module = load_audit_module()
    sensitivity = tmp_path / "cross_case_active_threshold_sensitivity.csv"
    sensitivity.write_text(
        "\n".join(
            [
                (
                    "case_label,state_label,baseline_active_column_threshold,"
                    "active_threshold_sensitivity_status,active_thresholds_evaluated,"
                    "active_length_max_abs_delta_from_baseline,"
                    "threshold_sensitivity_limit,next_verification_needed"
                ),
                (
                    "15gs_20C,40,0.05,missing_threshold_sweep,,,"
                    "per-frame active-length threshold sweep missing,"
                    "Rerun per-case image analysis with --active-column-sensitivity-thresholds."
                ),
            ]
        ),
        encoding="utf-8",
    )
    findings = []
    metrics = []
    tables = []

    module.check_active_threshold_sensitivity(sensitivity, findings, metrics, tables)

    assert any(
        finding.level == "PASS" and finding.item == "Active threshold sensitivity"
        for finding in findings
    )
    assert any(
        finding.level == "WARN" and finding.item == "Active threshold sensitivity"
        for finding in findings
    )
    assert any("Active-length threshold sensitivity statuses" in metric for metric in metrics)
