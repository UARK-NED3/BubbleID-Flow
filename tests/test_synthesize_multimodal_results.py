from __future__ import annotations

import importlib.util
import math
from pathlib import Path


def load_synthesis_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "synthesize_multimodal_results.py"
    )
    spec = importlib.util.spec_from_file_location("synthesize_multimodal_results", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_load_summaries_annotates_legacy_active_column_threshold(tmp_path):
    module = load_synthesis_module()
    summary = tmp_path / "15gs_20C_multimodal_state_summary.csv"
    summary.write_text(
        "\n".join(
            [
                "state_label,state_voltage,image_frames,thermal_rows,heat_flux_mean_w_cm2,"
                "htc_mean_w_m2k,ae_abs_energy_rate,vapor_area_fraction_mean,"
                "active_length_fraction_mean",
                "45,45,8,12,24.3,7300,100.0,0.21,0.62",
            ]
        ),
        encoding="utf-8",
    )

    data = module.load_summaries([summary], active_column_threshold=0.05)

    assert data["active_column_threshold"].tolist() == [0.05]
    assert data["active_column_threshold_source"].tolist() == ["synthesis_argument"]
    assert data["multimodal_complete"].tolist() == [True]


def test_load_summaries_flags_ae_window_overlap_and_caution_states(tmp_path):
    module = load_synthesis_module()
    summary = tmp_path / "15gs_20C_multimodal_state_summary.csv"
    summary.write_text(
        "\n".join(
            [
                "state_label,state_voltage,image_frames,thermal_rows,time_start_s,time_end_s,"
                "heat_flux_mean_w_cm2,htc_mean_w_m2k,ae_abs_energy_rate,"
                "vapor_area_fraction_mean,active_length_fraction_mean",
                "25V,25,8,12,0,10,8.0,3000,10.0,0.10,0.40",
                "30V,30,8,12,9,20,10.0,3500,20.0,0.20,0.50",
                "35V,35,8,12,50,190,12.0,4000,30.0,0.30,0.60",
            ]
        ),
        encoding="utf-8",
    )

    data = module.load_summaries([summary], active_column_threshold=0.05)
    by_state = data.set_index("state_label")

    assert by_state.loc["30V", "ae_window_quality"] == "blocked"
    assert by_state.loc["30V", "ae_window_overlaps_previous_state"] == "25V"
    assert by_state.loc["30V", "ae_interpretation_weight"] == 0.0
    assert by_state.loc["35V", "ae_window_quality"] == "caution"
    assert "long_window_gt_120s" in by_state.loc["35V", "ae_window_quality_reason"]


def test_build_trend_summary_reports_quality_gated_rank_agreement():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 4,
            "state_label": ["25", "30", "35", "40"],
            "state_voltage": [25, 30, 35, 40],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 14.0],
            "vapor_area_fraction_mean": [0.10, 0.20, 0.30, 0.40],
            "active_length_fraction_mean": [0.35, 0.45, 0.55, 0.65],
            "ae_abs_energy_rate": [1.0, 4.0, 3.0, 2.0],
            "ae_window_quality": ["pass", "blocked", "caution", "caution"],
        }
    )

    trend = module.build_trend_summary(data)
    row = trend.iloc[0]

    assert row["states"] == 4
    assert row["ae_pass_states"] == 1
    assert row["ae_caution_states"] == 2
    assert row["ae_blocked_states"] == 1
    assert row["ae_nonblocked_states"] == 3
    assert math.isclose(row["spearman_heat_flux_vapor_area"], 1.0)
    assert math.isclose(row["spearman_heat_flux_active_length"], 1.0)
    assert math.isclose(row["spearman_vapor_area_ae_all_states"], 0.2)
    assert math.isclose(row["spearman_vapor_area_ae_nonblocked"], 0.5)
    assert row["max_vapor_state"] == "40"


def test_build_trend_sensitivity_identifies_influential_ae_state():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 5,
            "state_label": ["25", "30", "35", "40", "55 CHF"],
            "state_voltage": [25, 30, 35, 40, 55],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 14.0, 18.0],
            "vapor_area_fraction_mean": [0.10, 0.20, 0.30, 0.40, 0.50],
            "active_length_fraction_mean": [0.25, 0.35, 0.45, 0.55, 0.65],
            "ae_abs_energy_rate": [1.0, 2.0, 3.0, 4.0, 0.2],
            "ae_window_quality": ["caution"] * 5,
        }
    )

    sensitivity = module.build_trend_sensitivity(data)
    ae_row = sensitivity[
        sensitivity["relationship"] == "vapor_area_vs_ae_nonblocked"
    ].iloc[0]

    assert ae_row["states_used"] == 5
    assert ae_row["most_influential_removed_state"] == "55 CHF"
    assert ae_row["spearman_without_most_influential_state"] > ae_row["baseline_spearman"]
    assert ae_row["max_abs_delta"] > 0.5


def test_build_sampling_uncertainty_flags_wide_short_sample():
    module = load_synthesis_module()
    summary = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"],
            "state_label": ["40"],
            "state_voltage": [40.0],
            "heat_flux_mean_w_cm2": [18.0],
            "multimodal_complete": [True],
        }
    )
    frame_metrics = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 4,
            "state_label": ["40"] * 4,
            "vapor_area_fraction": [0.02, 0.08, 0.12, 0.18],
            "active_length_fraction": [0.20, 0.25, 0.35, 0.40],
        }
    )

    uncertainty = module.build_sampling_uncertainty(summary, frame_metrics)
    row = uncertainty.iloc[0]

    assert row["image_frames_from_metrics"] == 4
    assert row["vapor_area_fraction_n"] == 4
    assert row["vapor_area_fraction_ci95_half_width"] > 0
    assert row["vapor_area_fraction_relative_ci95_half_width"] > 0.25
    assert "short_sample" in row["sampling_warning"]
    assert "wide_vapor_ci" in row["sampling_warning"]


def test_attach_sampling_uncertainty_columns_updates_analysis_rows():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"],
            "state_label": ["40"],
            "vapor_area_fraction_ci95_half_width": [99.0],
        }
    )
    sampling = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"],
            "state_label": ["40"],
            "image_frames_from_metrics": [8],
            "vapor_area_fraction_ci95_half_width": [0.018],
            "vapor_area_fraction_relative_ci95_half_width": [0.296],
            "sampling_warning": ["wide_vapor_ci"],
        }
    )

    merged = module.attach_sampling_uncertainty_columns(data, sampling)
    row = merged.iloc[0]

    assert row["image_frames_from_metrics"] == 8
    assert row["vapor_area_fraction_ci95_half_width"] == 0.018
    assert row["vapor_area_fraction_relative_ci95_half_width"] == 0.296
    assert row["sampling_warning"] == "wide_vapor_ci"
    assert "vapor_area_fraction_ci95_half_width_x" not in merged.columns


def test_build_active_threshold_sensitivity_uses_frame_threshold_sweep():
    module = load_synthesis_module()
    summary = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"],
            "state_label": ["40"],
            "state_voltage": [40.0],
            "multimodal_complete": [True],
            "active_column_threshold": [0.05],
            "active_length_fraction_mean": [0.40],
        }
    )
    frame_metrics = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C", "15gs_20C"],
            "state_label": ["40", "40"],
            "active_length_fraction_thr_0p025": [0.50, 0.54],
            "active_length_fraction_thr_0p05": [0.40, 0.42],
            "active_length_fraction_thr_0p075": [0.30, 0.32],
        }
    )

    sensitivity = module.build_active_threshold_sensitivity(summary, frame_metrics)
    row = sensitivity.iloc[0]

    assert row["active_threshold_sensitivity_status"] == "checked"
    assert row["active_thresholds_evaluated"] == "0.025;0.05;0.075"
    assert math.isclose(row["active_length_baseline_mean"], 0.41)
    assert row["active_length_max_abs_delta_from_baseline"] > 0.09
    assert row["most_sensitive_threshold"] in {0.025, 0.075}


def test_build_active_threshold_sensitivity_gates_legacy_frame_metrics():
    module = load_synthesis_module()
    summary = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"],
            "state_label": ["40"],
            "state_voltage": [40.0],
            "multimodal_complete": [True],
            "active_column_threshold": [0.05],
            "active_length_fraction_mean": [0.40],
        }
    )
    frame_metrics = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"],
            "state_label": ["40"],
            "active_length_fraction": [0.40],
        }
    )

    sensitivity = module.build_active_threshold_sensitivity(summary, frame_metrics)
    row = sensitivity.iloc[0]

    assert row["active_threshold_sensitivity_status"] == "missing_threshold_sweep"
    assert "Rerun per-case image analysis" in row["next_verification_needed"]


def test_state_map_scaled_values_masks_blocked_ae_energy():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 3,
            "state_label": ["25", "30", "35"],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0],
            "vapor_area_fraction_mean": [0.10, 0.20, 0.30],
            "active_length_fraction_mean": [0.20, 0.40, 0.60],
            "ae_abs_energy_rate": [10.0, 20.0, 30.0],
            "htc_mean_w_m2k": [3000.0, 4000.0, 5000.0],
            "ae_window_quality": ["caution", "blocked", "caution"],
            "ae_interpretation_weight": [0.5, 0.0, 0.5],
        }
    )

    _, metric_labels, scaled = module.state_map_scaled_values(data)
    ae_index = metric_labels.index("AE energy\nscreening")
    weight_index = metric_labels.index("AE quality\nweight")

    assert module.np.isnan(scaled[1, ae_index])
    assert scaled[0, ae_index] == 0.0
    assert scaled[2, ae_index] == 1.0
    assert scaled[1, weight_index] == 0.0
    assert scaled[0, weight_index] == 0.5
    assert scaled[2, weight_index] == 0.5


def test_build_thermal_response_checks_marks_state_level_context_supported():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 4,
            "state_label": ["25", "30", "35", "40"],
            "state_voltage": [25.0, 30.0, 35.0, 40.0],
            "heat_flux_mean_w_cm2": [8.0, 12.0, 16.0, 20.0],
            "htc_mean_w_m2k": [3000.0, 4200.0, 5000.0, 6100.0],
            "pressure_drop_mean_kpa": [1.2, 1.1, 1.0, 0.9],
            "quality_x7_mean": [-0.25, -0.23, -0.21, -0.19],
            "thermal_rows": [100, 100, 100, 100],
            "thermal_window_span_s": [10.0, 11.0, 10.0, 9.0],
        }
    )

    checks = module.build_thermal_response_checks(data)
    row = checks.iloc[0]

    assert row["thermal_context_status"] == "state_level_supported"
    assert row["heat_flux_drop_count_vs_voltage"] == 0
    assert math.isclose(row["spearman_voltage_heat_flux"], 1.0)
    assert math.isclose(row["spearman_heat_flux_htc"], 1.0)
    assert "thermocouple_uncertainty" in row["limiting_factors"]


def test_build_ae_evidence_tiers_classifies_blocked_and_legacy_snapshots():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["5gs_22C"] * 4 + ["25gs_20C"] * 4,
            "state_label": ["25", "30", "35", "40", "30", "35", "40", "45"],
            "state_voltage": [25, 30, 35, 40, 30, 35, 40, 45],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 14.0, 9.0, 11.0, 13.0, 15.0],
            "vapor_area_fraction_mean": [0.10, 0.20, 0.30, 0.40, 0.10, 0.20, 0.30, 0.40],
            "active_length_fraction_mean": [0.25, 0.35, 0.45, 0.55, 0.20, 0.30, 0.40, 0.50],
            "ae_abs_energy_rate": [1.0, 2.0, 3.0, 4.0, 1.0, 2.0, 3.0, 4.0],
            "ae_window_quality": [
                "caution",
                "blocked",
                "caution",
                "caution",
                "caution",
                "caution",
                "caution",
                "caution",
            ],
        }
    )
    trend = module.build_trend_summary(data)
    sensitivity = module.build_trend_sensitivity(data)

    tiers = module.build_ae_evidence_tiers(data, trend, sensitivity)
    by_case = tiers.set_index("case_label")

    assert by_case.loc["5gs_22C", "ae_evidence_tier"] == "blocked_mixed_window_snapshot"
    assert "overlap_blocked_windows" in by_case.loc["5gs_22C", "limiting_factors"]
    assert by_case.loc["25gs_20C", "ae_evidence_tier"] == "exploratory_legacy_window_snapshot"
    assert "no_pass_quality_windows" in by_case.loc["25gs_20C", "limiting_factors"]
    assert not bool(by_case.loc["25gs_20C", "trigger_synchronization_verified"])


def test_build_ae_readiness_matrix_blocks_quantitative_ae_without_pass_windows():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["5gs_22C"] * 4 + ["25gs_20C"] * 5,
            "state_label": ["25", "30", "35", "40", "30", "35", "40", "45", "50"],
            "ae_window_quality": [
                "caution",
                "blocked",
                "caution",
                "caution",
                "caution",
                "caution",
                "caution",
                "caution",
                "caution",
            ],
            "ae_window_quality_reason": [
                "legacy_no_contiguous_window_metadata",
                "overlaps_previous_state;legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
            ],
        }
    )
    tiers = module.pd.DataFrame(
        {
            "case_label": ["5gs_22C", "25gs_20C"],
            "ae_evidence_tier": [
                "blocked_mixed_window_snapshot",
                "exploratory_legacy_window_snapshot",
            ],
            "limiting_factors": [
                "overlap_blocked_windows",
                "no_pass_quality_windows",
            ],
        }
    )

    readiness = module.build_ae_readiness_matrix(data, tiers)
    by_case = readiness.set_index("case_label")

    assert by_case.loc["5gs_22C", "ae_readiness_status"] == "blocked_for_quantitative_use"
    assert by_case.loc["25gs_20C", "ae_readiness_status"] == "legacy_screening_only"
    assert not bool(by_case.loc["5gs_22C", "quantitative_ae_ready"])
    assert not bool(by_case.loc["25gs_20C", "quantitative_ae_ready"])
    assert "overlap_blocked_windows" in by_case.loc["5gs_22C", "blocking_criteria"]
    assert "missing_contiguous_window_metadata" in by_case.loc[
        "25gs_20C", "blocking_criteria"
    ]


def test_ae_verification_status_can_open_quantitative_readiness_gate(tmp_path):
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 6,
            "state_label": ["25", "30", "35", "40", "45", "50"],
            "state_voltage": [25, 30, 35, 40, 45, 50],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 14.0, 16.0, 18.0],
            "vapor_area_fraction_mean": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
            "active_length_fraction_mean": [0.20, 0.25, 0.30, 0.35, 0.40, 0.45],
            "ae_abs_energy_rate": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "ae_window_quality": ["pass"] * 6,
            "ae_window_quality_reason": ["none"] * 6,
            "thermal_window_selection": ["largest_contiguous_block"] * 6,
        }
    )
    verification_path = tmp_path / "ae_verification.csv"
    verification_path.write_text(
        "\n".join(
            [
                "case_label,trigger_synchronization_verified,sensor_coupling_verified",
                "15gs_20C,true,true",
            ]
        ),
        encoding="utf-8",
    )

    verification = module.build_ae_verification_status(data, verification_path)
    trend = module.build_trend_summary(data)
    sensitivity = module.build_trend_sensitivity(data)
    tiers = module.build_ae_evidence_tiers(
        data,
        trend,
        sensitivity,
        verification_status=verification,
    )
    readiness = module.build_ae_readiness_matrix(
        data,
        tiers,
        verification_status=verification,
    )
    row = readiness.iloc[0]

    assert bool(row["quantitative_ae_ready"])
    assert row["ae_readiness_status"] == "quantitative_ready"
    assert row["blocking_criteria"] == "none"
    assert bool(tiers.iloc[0]["trigger_synchronization_verified"])
    assert bool(tiers.iloc[0]["sensor_coupling_verified"])


def test_build_ae_remediation_plan_prioritizes_overlap_and_sensitive_cases():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 5,
            "state_label": ["25", "30", "35", "50", "55 CHF"],
            "state_voltage": [25, 30, 35, 50, 55],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 16.0, 18.0],
            "vapor_area_fraction_mean": [0.10, 0.20, 0.30, 0.40, 0.50],
            "active_length_fraction_mean": [0.20, 0.30, 0.40, 0.50, 0.60],
            "ae_abs_energy_rate": [1.0, 2.0, 3.0, 4.0, 0.2],
            "ae_window_quality": ["caution", "caution", "blocked", "caution", "caution"],
            "ae_window_quality_reason": [
                "legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
                "overlaps_previous_state;legacy_no_contiguous_window_metadata",
                "long_window_gt_120s;legacy_no_contiguous_window_metadata",
                "legacy_no_contiguous_window_metadata",
            ],
        }
    )
    trend = module.build_trend_summary(data)
    sensitivity = module.build_trend_sensitivity(data)
    tiers = module.build_ae_evidence_tiers(data, trend, sensitivity)
    readiness = module.build_ae_readiness_matrix(data, tiers)
    verification = module.build_ae_verification_status(data)

    plan = module.build_ae_remediation_plan(data, sensitivity, readiness, verification)
    row = plan.iloc[0]

    assert row["remediation_priority"] == 1
    assert row["blocked_state_labels"] == "35"
    assert row["long_window_state_labels"] == "50"
    assert row["most_influential_ae_state"] == "55 CHF"
    assert "contiguous-window selection" in row["primary_rerun_action"]
    assert "influential state 55 CHF" in row["verification_actions"]


def test_build_segmentation_validation_plan_selects_manual_mask_targets():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 5,
            "state_label": ["25", "30", "35", "40", "55 CHF"],
            "state_voltage": [25, 30, 35, 40, 55],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 14.0, 18.0],
            "vapor_area_fraction_mean": [0.05, 0.10, 0.16, 0.12, 0.31],
            "active_length_fraction_mean": [0.10, 0.20, 0.30, 0.35, 0.70],
            "image_frames": [6, 8, 8, 8, 6],
        }
    )
    sampling = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 5,
            "state_label": ["25", "30", "35", "40", "55 CHF"],
            "vapor_area_fraction_relative_ci95_half_width": [0.10, 0.12, 0.45, 0.20, 0.18],
            "sampling_warning": ["short_sample", "none", "wide_vapor_ci", "none", "short_sample"],
        }
    )

    plan = module.build_segmentation_validation_plan(data, sampling)
    by_state = plan.set_index("state_label")

    assert {"25", "35", "55 CHF"} <= set(by_state.index)
    assert "onset_or_low_vapor" in by_state.loc["25", "validation_role"]
    assert "developed_mid_sweep" in by_state.loc["35", "validation_role"]
    assert "highest_sampling_uncertainty" in by_state.loc["35", "validation_role"]
    assert "high_vapor_or_chf_adjacent" in by_state.loc["55 CHF", "validation_role"]
    assert by_state.loc["25", "validation_status"] == "planned_not_complete"
    assert "individual bubble count" in by_state.loc["25", "claim_gate_until_complete"]
    assert "add raw-sequence frames" in by_state.loc["25", "recommended_annotation_action"]


def test_build_claim_evidence_matrix_blocks_unsupported_claims():
    module = load_synthesis_module()
    data = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"] * 5,
            "state_label": ["25", "30", "35", "40", "55 CHF"],
            "state_voltage": [25, 30, 35, 40, 55],
            "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 14.0, 18.0],
            "vapor_area_fraction_mean": [0.10, 0.20, 0.30, 0.40, 0.50],
            "active_length_fraction_mean": [0.25, 0.35, 0.45, 0.55, 0.65],
            "ae_abs_energy_rate": [1.0, 2.0, 3.0, 4.0, 0.2],
            "ae_window_quality": ["caution"] * 5,
        }
    )
    trend = module.build_trend_summary(data)
    sensitivity = module.build_trend_sensitivity(data)
    sampling = module.pd.DataFrame(
        {
            "case_label": ["15gs_20C"],
            "state_label": ["40"],
            "vapor_area_fraction_relative_ci95_half_width": [0.30],
            "sampling_warning": ["wide_vapor_ci"],
        }
    )
    thermal = module.build_thermal_response_checks(
        module.pd.DataFrame(
            {
                "case_label": ["15gs_20C"] * 5,
                "state_label": ["25", "30", "35", "40", "55 CHF"],
                "state_voltage": [25, 30, 35, 40, 55],
                "heat_flux_mean_w_cm2": [8.0, 10.0, 12.0, 14.0, 18.0],
                "htc_mean_w_m2k": [3000.0, 3500.0, 4200.0, 4800.0, 5200.0],
                "pressure_drop_mean_kpa": [1.2, 1.1, 1.0, 0.9, 0.8],
                "quality_x7_mean": [-0.25, -0.24, -0.23, -0.22, -0.21],
                "thermal_rows": [100, 100, 100, 100, 100],
                "thermal_window_span_s": [10.0, 10.0, 10.0, 10.0, 10.0],
            }
        )
    )
    ae_tiers = module.build_ae_evidence_tiers(data, trend, sensitivity)
    ae_readiness = module.build_ae_readiness_matrix(data, ae_tiers)
    segmentation_plan = module.build_segmentation_validation_plan(data, sampling)

    matrix = module.build_claim_evidence_matrix(
        data,
        trend,
        sensitivity,
        sampling,
        thermal,
        segmentation_plan,
        ae_tiers,
        ae_readiness,
    )
    by_claim = matrix.set_index("claim_id")

    assert by_claim.loc["optical_heat_flux_trend", "support_status"] == (
        "supported_with_limits"
    )
    assert by_claim.loc["state_level_thermal_response", "support_status"] == (
        "supported_with_limits"
    )
    assert by_claim.loc["ae_screening_comparison", "support_status"] == "screening_only"
    assert "cross_case_ae_readiness_matrix.csv" in by_claim.loc[
        "ae_screening_comparison", "evidence_artifacts"
    ]
    assert by_claim.loc["ae_regime_classifier_or_lead_lag", "support_status"] == (
        "not_supported_current_snapshot"
    )
    assert "Do not make" in by_claim.loc["ae_regime_classifier_or_lead_lag", "allowed_scope"]
    assert by_claim.loc["bubble_instance_statistics", "support_status"] == (
        "not_supported_current_snapshot"
    )
    assert "cross_case_segmentation_validation_plan.csv" in by_claim.loc[
        "bubble_instance_statistics", "evidence_artifacts"
    ]
