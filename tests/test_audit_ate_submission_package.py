from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_audit_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "audit_ate_submission_package.py"
    )
    spec = importlib.util.spec_from_file_location("audit_ate_submission_package", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def unsupported_matrix(module, claim_ids):
    return module.pd.DataFrame(
        {
            "claim_id": claim_ids,
            "support_status": ["not_supported_current_snapshot"] * len(claim_ids),
        }
    )


def test_claim_language_gate_allows_explicit_limitation_language():
    module = load_audit_module()
    findings = []
    metrics = []
    matrix = unsupported_matrix(module, ["ae_regime_classifier_or_lead_lag"])
    main_text = (
        "This audit figure explains why the manuscript does not claim acoustic "
        "lead-lag behavior. AE correlations remain screening diagnostics."
    )

    module.check_claim_language_gates(matrix, main_text, findings, metrics)

    assert not any(finding.level == "BLOCKER" for finding in findings)
    assert any(
        finding.level == "PASS" and finding.item == "Claim language gates"
        for finding in findings
    )


def test_claim_language_gate_blocks_assertive_ae_classifier_language():
    module = load_audit_module()
    findings = []
    metrics = []
    matrix = unsupported_matrix(module, ["ae_regime_classifier_or_lead_lag"])
    main_text = "AE features classify boiling regime and provide lead-lag timing across states."

    module.check_claim_language_gates(matrix, main_text, findings, metrics)

    assert any(finding.level == "BLOCKER" for finding in findings)
    assert any("AE classifier/timing language" in finding.detail for finding in findings)


def test_claim_language_gate_blocks_assertive_bubble_instance_language():
    module = load_audit_module()
    findings = []
    metrics = []
    matrix = unsupported_matrix(module, ["bubble_instance_statistics"])
    main_text = "The detected masks quantify individual bubble counts and bubble sizes."

    module.check_claim_language_gates(matrix, main_text, findings, metrics)

    assert any(finding.level == "BLOCKER" for finding in findings)
    assert any("bubble instance-statistic language" in finding.detail for finding in findings)


def test_claim_language_gate_blocks_assertive_local_registration_language():
    module = load_audit_module()
    findings = []
    metrics = []
    matrix = unsupported_matrix(module, ["local_optical_thermal_coupling"])
    main_text = "The camera ROI is registered to thermocouple locations for local HTC coupling."

    module.check_claim_language_gates(matrix, main_text, findings, metrics)

    assert any(finding.level == "BLOCKER" for finding in findings)
    assert any("local optical-thermal coupling language" in finding.detail for finding in findings)


def test_segmentation_validation_plan_checker_requires_manuscript_citation(tmp_path):
    module = load_audit_module()
    plan_dir = tmp_path / "multimodal" / "cross_case_synthesis"
    plan_dir.mkdir(parents=True)
    (plan_dir / "cross_case_segmentation_validation_plan.csv").write_text(
        "\n".join(
            [
                (
                    "case_label,state_label,validation_role,minimum_manual_masks,"
                    "validation_status,claim_gate_until_complete"
                ),
                (
                    "15gs_20C,25,onset_or_low_vapor,8,planned_not_complete,"
                    "Do not report individual bubble count"
                ),
            ]
        ),
        encoding="utf-8",
    )
    findings = []
    metrics = []
    main_text = (
        "The generated cross\\_case\\_segmentation\\_validation\\_plan.csv "
        "keeps instance-level claims gated."
    )

    module.check_segmentation_validation_plan(tmp_path, findings, metrics, main_text)

    assert any(
        finding.level == "PASS" and finding.item == "Segmentation validation plan"
        for finding in findings
    )
    assert any(
        finding.level == "WARN" and finding.item == "Manual segmentation validation"
        for finding in findings
    )
    assert any("Segmentation validation targets" in metric for metric in metrics)


def test_active_threshold_sensitivity_checker_requires_manuscript_citation(tmp_path):
    module = load_audit_module()
    synthesis_dir = tmp_path / "multimodal" / "cross_case_synthesis"
    synthesis_dir.mkdir(parents=True)
    (synthesis_dir / "cross_case_active_threshold_sensitivity.csv").write_text(
        "\n".join(
            [
                (
                    "case_label,state_label,baseline_active_column_threshold,"
                    "active_threshold_sensitivity_status,active_thresholds_evaluated,"
                    "active_length_max_abs_delta_from_baseline,threshold_sensitivity_limit"
                ),
                "15gs_20C,40,0.05,missing_threshold_sweep,,,missing",
            ]
        ),
        encoding="utf-8",
    )
    findings = []
    metrics = []
    main_text = (
        "The generated cross\\_case\\_active\\_threshold\\_sensitivity.csv "
        "keeps active-length threshold robustness gated."
    )

    module.check_active_threshold_sensitivity(tmp_path, findings, metrics, main_text)

    assert any(
        finding.level == "PASS" and finding.item == "Active threshold sensitivity"
        for finding in findings
    )
    assert any(
        finding.level == "WARN" and finding.item == "Active threshold sensitivity"
        for finding in findings
    )
    assert any("Active-length threshold sensitivity statuses" in metric for metric in metrics)


def test_evidence_artifact_versioning_passes_when_artifacts_are_visible(tmp_path):
    module = load_audit_module()
    for artifact in module.VERSIONED_EVIDENCE_ARTIFACTS:
        path = tmp_path / artifact
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    findings = []
    metrics = []

    module.check_versioned_evidence_artifacts(
        tmp_path,
        findings,
        metrics,
        git_ignore_checker=lambda path: False,
    )

    assert any(
        finding.level == "PASS" and finding.item == "Evidence artifact versioning"
        for finding in findings
    )
    assert not any(finding.level == "BLOCKER" for finding in findings)
    assert any("visible to git" in metric for metric in metrics)


def test_evidence_artifact_versioning_blocks_ignored_artifacts(tmp_path):
    module = load_audit_module()
    for artifact in module.VERSIONED_EVIDENCE_ARTIFACTS:
        path = tmp_path / artifact
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    findings = []
    metrics = []

    module.check_versioned_evidence_artifacts(
        tmp_path,
        findings,
        metrics,
        git_ignore_checker=lambda path: path.name == "thermal_state_audit.csv",
    )

    assert any(
        finding.level == "BLOCKER"
        and finding.item == "Evidence artifact versioning"
        and "thermal_state_audit.csv" in finding.detail
        for finding in findings
    )
