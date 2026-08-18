from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from scripts.analyze_multimodal_case import discover_states, summarize_thermal_states


CHANNEL_WIDTH_M = 2.5e-3
CHANNEL_HEIGHT_M = 5.0e-3
HEATED_LENGTH_M = 0.1146
FLOW_AREA_M2 = CHANNEL_WIDTH_M * CHANNEL_HEIGHT_M
HEATED_AREA_M2 = CHANNEL_WIDTH_M * HEATED_LENGTH_M
HYDRAULIC_DIAMETER_M = 2 * CHANNEL_WIDTH_M * CHANNEL_HEIGHT_M / (
    CHANNEL_WIDTH_M + CHANNEL_HEIGHT_M
)
CASE_ORDER = ("5gs_22C", "10gs_22C", "15gs_20C", "25gs_20C")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit traceable thermal state windows and geometry-derived quantities."
    )
    parser.add_argument("--flow-loop-root", required=True)
    parser.add_argument("--image-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--voltage-tolerance", type=float, default=0.75)
    args = parser.parse_args()

    flow_root = Path(args.flow_loop_root)
    image_root = Path(args.image_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for case in CASE_ORDER:
        state_rows = summarize_thermal_states(
            states=discover_states(image_root / case),
            thermal_workbook=flow_root / case / f"{case}.xlsx",
            thermal_input_workbook=flow_root / case / f"{case}_IN_with_units.xlsx",
            voltage_tolerance=args.voltage_tolerance,
        )
        state_rows.insert(0, "case_label", case)
        frames.append(state_rows)

    summary = pd.concat(frames, ignore_index=True)
    summary["mass_flux_kg_m2_s"] = summary["mass_flow_mean_kg_s"] / FLOW_AREA_M2
    summary["mass_flux_std_kg_m2_s"] = summary["mass_flow_std_kg_s"] / FLOW_AREA_M2
    summary["heat_flux_from_power_w_cm2"] = summary["power_mean_w"] / HEATED_AREA_M2 / 1e4
    summary["heat_flux_reconstruction_delta_w_cm2"] = (
        summary["heat_flux_mean_w_cm2"] - summary["heat_flux_from_power_w_cm2"]
    )
    summary["bulk_temperature_rise_c"] = (
        summary["outlet_temperature_mean_c"] - summary["inlet_temperature_mean_c"]
    )
    summary.to_csv(output_dir / "thermal_state_audit.csv", index=False)

    manifest = {
        "channel_width_m": CHANNEL_WIDTH_M,
        "channel_height_m": CHANNEL_HEIGHT_M,
        "heated_length_m": HEATED_LENGTH_M,
        "flow_area_m2": FLOW_AREA_M2,
        "heated_area_m2": HEATED_AREA_M2,
        "hydraulic_diameter_m": HYDRAULIC_DIAMETER_M,
        "heat_flux_equation": "q_double_prime=P/(heated_length*channel_width)",
        "mass_flux_equation": "G=m_dot/(channel_width*channel_height)",
        "uncertainty_scope": (
            "reported standard deviations quantify within-window temporal variation only; "
            "instrument calibration uncertainties were not supplied"
        ),
        "excluded_from_validation": [
            "Qsp energy balance because its source notebook multiplies m_dot*cp*abs(Tout-Tin) by an undocumented 0.53",
            "friction-factor outputs because source mass velocity uses g/s without conversion to kg/s",
            "supplied HTC as a validated endpoint because thermocouple placement/corrections and sensor uncertainty are not documented",
        ],
    }
    (output_dir / "thermal_reduction_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(summary[[
        "case_label",
        "state_label",
        "mass_flux_kg_m2_s",
        "heat_flux_mean_w_cm2",
        "heat_flux_reconstruction_delta_w_cm2",
        "wall_temperature_mean_c",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
