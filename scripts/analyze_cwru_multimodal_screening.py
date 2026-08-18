"""Create an evidence-bounded optical--acoustic--thermal CWRU screening result.

This bridge intentionally uses the 10 g/s Test 17 case only. Its optical and
thermal state summaries are available, the EasyAE event/continuous exports
cover the thermal run, and the WFS archive spans the run. The separate
acquisition systems have timestamp registration but no verified common
hardware trigger, so every output is exploratory state-level co-variation,
not a time-resolved coupling or source-localization result.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


THERMAL_START = "2025-10-17T11:41:47.605"
AE_START = "2025-10-17T11:42:13.000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aelab-root", required=True, type=Path)
    parser.add_argument("--hit", required=True, type=Path)
    parser.add_argument("--time", required=True, type=Path)
    parser.add_argument("--wfs", required=True, type=Path)
    parser.add_argument("--thermal-summary", required=True, type=Path)
    parser.add_argument("--optical-summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-wfs-records", type=int, default=512)
    return parser.parse_args()


def registration_offset_s() -> float:
    return (datetime.fromisoformat(AE_START) - datetime.fromisoformat(THERMAL_START)).total_seconds()


def build_windows(thermal: pd.DataFrame) -> pd.DataFrame:
    selected = thermal[
        (thermal["case_label"] == "10gs_22C")
        & thermal["time_start_s"].notna()
        & thermal["time_end_s"].notna()
    ][["state_label", "state_voltage", "time_start_s", "time_end_s"]].copy()
    offset_s = registration_offset_s()
    selected["ae_start_s"] = selected["time_start_s"] - offset_s
    selected["ae_end_s"] = selected["time_end_s"] - offset_s
    selected["registration_status"] = "timestamp_registered_not_trigger_verified"
    selected["thermal_start_iso"] = THERMAL_START
    selected["ae_start_iso"] = AE_START
    return selected.sort_values("state_voltage").reset_index(drop=True)


def merge_modalities(
    windows: pd.DataFrame,
    thermal: pd.DataFrame,
    optical: pd.DataFrame,
    ae: pd.DataFrame,
) -> pd.DataFrame:
    thermal_columns = [
        "case_label", "state_label", "state_voltage", "heat_flux_mean_w_cm2",
        "wall_temperature_mean_c",
    ]
    thermal_case = thermal.loc[thermal["case_label"] == "10gs_22C", thermal_columns]
    optical_case = optical.loc[optical["case_label"] == "10gs_22C"]
    base = windows.merge(
        thermal_case, on=["state_label", "state_voltage"], how="left", validate="one_to_one"
    ).merge(
        optical_case[["case_label", "state_label", "state_voltage", "vapor_area_fraction_aug9"]],
        on=["case_label", "state_label", "state_voltage"], how="left", validate="one_to_one"
    )
    wide = ae.pivot(index="state_label", columns="channel")
    wide.columns = [f"{metric}_ch{channel}" for metric, channel in wide.columns]
    return base.merge(wide.reset_index(), on="state_label", how="left", validate="one_to_one")


def make_figure(summary: pd.DataFrame, output_dir: Path) -> None:
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
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.3), constrained_layout=True)
    x = summary["heat_flux_mean_w_cm2"]
    axes[0, 0].plot(x, summary["vapor_area_fraction_aug9"], "o--", color="#0072B2", linewidth=1.25)
    axes[0, 0].set(xlabel="Electrical heat flux (W cm-2)", ylabel="Projected vapor coverage")
    for channel, color in ((1, "#009E73"), (2, "#D55E00")):
        axes[0, 1].plot(x, summary[f"asl_mean_dbae_ch{channel}"], "o--", color=color, label=f"AE channel {channel}")
        axes[1, 0].plot(x, summary[f"hit_rate_hz_ch{channel}"], "o--", color=color, label=f"AE channel {channel}")
        axes[1, 1].plot(x, summary[f"hit_amplitude_median_dbae_ch{channel}"], "o--", color=color, label=f"AE channel {channel}")
    axes[0, 1].set(xlabel="Electrical heat flux (W cm-2)", ylabel="Continuous ASL (dBAE)")
    axes[1, 0].set(xlabel="Electrical heat flux (W cm-2)", ylabel="Event hit rate (s-1)")
    axes[1, 1].set(xlabel="Electrical heat flux (W cm-2)", ylabel="Median hit amplitude (dBAE)")
    for label, axis in zip("abcd", axes.ravel(), strict=True):
        axis.text(0.0, 1.03, f"({label})", transform=axis.transAxes, va="bottom", clip_on=False)
        axis.tick_params(direction="in", top=True, right=True)
        axis.grid(False)
        for spine in axis.spines.values():
            spine.set_visible(True)
            spine.set_color("black")
    axes[0, 1].legend(frameon=False, fontsize=7)
    fig.savefig(output_dir / "Figure_S1_timestamp_registered_multimodal_screening.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "Figure_S1_timestamp_registered_multimodal_screening.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    analysis_dir = args.aelab_root / "flow-boiling-ae" / "analysis"
    sys.path.insert(0, str(analysis_dir))
    from cwru_test17 import (  # Imported after user-configured AELab location is known.
        read_hit_export,
        read_time_export,
        read_wfs_prefix,
        summarize_prefix_spectra,
        summarize_state_windows,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    thermal = pd.read_csv(args.thermal_summary)
    optical = pd.read_csv(args.optical_summary)
    windows = build_windows(thermal)
    hit = read_hit_export(args.hit)
    continuous = read_time_export(args.time)
    ae = summarize_state_windows(hit, continuous, windows)
    prefix = read_wfs_prefix(args.wfs, max_records=args.max_wfs_records)
    spectra = summarize_prefix_spectra(prefix)
    summary = merge_modalities(windows, thermal, optical, ae)

    windows.to_csv(args.output_dir / "10gs_timestamp_registered_windows.csv", index=False)
    ae.to_csv(args.output_dir / "10gs_ae_state_summary.csv", index=False)
    spectra.to_csv(args.output_dir / "10gs_wfs_prefix_spectra.csv", index=False)
    summary.to_csv(args.output_dir / "10gs_timestamp_registered_multimodal_summary.csv", index=False)
    manifest = {
        "case": "10gs_22C",
        "thermal_start_iso": THERMAL_START,
        "ae_start_iso": AE_START,
        "ae_minus_thermal_start_s": registration_offset_s(),
        "registration_status": "timestamp_registered_not_trigger_verified",
        "allowed_interpretation": "exploratory state-level co-variation during the imposed voltage ramp",
        "prohibited_interpretations": [
            "sub-second optical-acoustic synchronization",
            "causal coupling",
            "acoustic source localization",
            "calibrated acoustic energy",
            "cross-case or experiment-level generalization",
        ],
        "wfs_prefix_records": args.max_wfs_records,
        "wfs_note": "bounded prefix is a decoding/spectral provenance check, not a state-matched waveform result",
        "sensor_note": "archive notes report approximate sensor locations and inadequate mounting as a concern",
    }
    (args.output_dir / "multimodal_screening_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    make_figure(summary, args.output_dir)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
