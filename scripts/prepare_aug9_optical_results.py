from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor

from bubbleid_flow.paths import iter_images
from bubbleid_flow.preprocess import crop_array, parse_roi
from bubbleid_flow.time_series import circular_moving_block_bootstrap_mean_interval
from bubbleid_flow.vapor_fraction import projected_mask_metrics


CASE_STYLE = {
    "5gs_22C": ("#0072B2", "o", "5 g/s, 22 degC"),
    "10gs_22C": ("#009E73", "s", "10 g/s, 22 degC"),
    "15gs_20C": ("#D55E00", "^", "15 g/s, 20 degC"),
    "25gs_20C": ("#CC79A7", "D", "25 g/s, 20 degC"),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate Aug. 9 BubbleID-Flow optical results and manuscript figures."
    )
    parser.add_argument("--values-workbook", required=True)
    parser.add_argument(
        "--source-workbook",
        default=None,
        help="Optional original XLSX path when --values-workbook is a CSV export.",
    )
    parser.add_argument("--combined-summary", required=True)
    parser.add_argument("--image-root", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--roi", default="0,485,1024,70")
    parser.add_argument("--score-threshold", type=float, default=0.30)
    parser.add_argument("--detections-per-image", type=int, default=300)
    parser.add_argument("--temporal-voltage", type=float, default=45.0)
    parser.add_argument("--frame-rate-hz", type=float, default=3000.0)
    parser.add_argument(
        "--max-temporal-frames",
        type=int,
        default=None,
        help="Optional deterministic cap; default processes every frame in the selected state.",
    )
    parser.add_argument(
        "--reuse-existing-temporal",
        action="store_true",
        help="Reuse the output CSV and representative assets instead of rerunning inference.",
    )
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    if args.detections_per_image <= 0:
        raise ValueError("detections-per-image must be positive")
    if args.frame_rate_hz <= 0:
        raise ValueError("frame-rate-hz must be positive")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "representative_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    optical = read_vapor_fraction_workbook(Path(args.values_workbook))
    if args.source_workbook:
        optical["optical_source"] = Path(args.source_workbook).name
    multimodal = pd.read_csv(args.combined_summary)
    merged = merge_optical_and_multimodal(optical, multimodal)
    merged.to_csv(output_dir / "aug9_state_vapor_fraction.csv", index=False)
    trend_summary = summarize_state_trends(merged)
    trend_summary.to_csv(output_dir / "aug9_case_trend_summary.csv", index=False)

    temporal_path = output_dir / "aug9_temporal_vapor_fraction_45V.csv"
    if args.reuse_existing_temporal:
        temporal = pd.read_csv(temporal_path)
        representative = existing_representative_assets(assets_dir)
    else:
        predictor = DefaultPredictor(
            build_cfg(
                weights=args.weights,
                score_threshold=args.score_threshold,
                detections_per_image=args.detections_per_image,
                device=args.device,
            )
        )
        temporal, representative = run_temporal_analysis(
            image_root=Path(args.image_root),
            predictor=predictor,
            roi=parse_roi(args.roi),
            temporal_voltage=args.temporal_voltage,
            frame_rate_hz=args.frame_rate_hz,
            max_frames=args.max_temporal_frames,
            assets_dir=assets_dir,
        )
        temporal.to_csv(temporal_path, index=False)
    temporal_summary = summarize_temporal(temporal, optical, args.temporal_voltage)
    temporal_summary.to_csv(output_dir / "aug9_temporal_summary_45V.csv", index=False)

    set_style()
    generated = []
    generated += figure_model_outputs(representative, output_dir)
    generated += figure_optical_results(optical, merged, temporal, temporal_summary, output_dir)
    generated += figure_multimodal_context(merged, output_dir)
    generated += figure_graphical_abstract(representative, merged, temporal_summary, output_dir)

    manifest = {
        "weights": str(Path(args.weights).resolve()),
        "weights_sha256": sha256(Path(args.weights)),
        "values_workbook": str(Path(args.values_workbook).resolve()),
        "values_workbook_sha256": sha256(Path(args.values_workbook)),
        "combined_summary": str(Path(args.combined_summary).resolve()),
        "combined_summary_sha256": sha256(Path(args.combined_summary)),
        "roi": args.roi,
        "score_threshold": args.score_threshold,
        "detections_per_image": args.detections_per_image,
        "frame_rate_hz": args.frame_rate_hz,
        "temporal_voltage": args.temporal_voltage,
        "temporal_frames": {
            case: int(count) for case, count in temporal.groupby("case_label").size().items()
        },
        "generated": [str(path.resolve()) for path in generated],
    }
    if args.source_workbook:
        manifest["source_workbook"] = str(Path(args.source_workbook).resolve())
        manifest["source_workbook_sha256"] = sha256(Path(args.source_workbook))
    (output_dir / "aug9_analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(temporal_summary.to_string(index=False))
    print(f"Wrote Aug. 9 optical analysis to {output_dir}")


def read_vapor_fraction_workbook(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        raw = pd.read_csv(path, header=None)
    else:
        raw = pd.read_excel(path, header=None)
    marker_rows = raw.index[raw.iloc[:, 0].astype(str).str.strip().str.lower() == "vf"].tolist()
    if len(marker_rows) != 1:
        raise ValueError("Expected exactly one 'vf' section in the values workbook")
    header_row = marker_rows[0]
    voltages = pd.to_numeric(raw.iloc[header_row, 1:], errors="coerce")
    rows = []
    for row_index in range(header_row + 1, len(raw)):
        case = str(raw.iloc[row_index, 0]).strip()
        if case.lower() in {"total_bc", "bubble", "bubble_cluster", "nan", ""}:
            break
        values = pd.to_numeric(raw.iloc[row_index, 1:], errors="coerce")
        for voltage, vapor_fraction in zip(voltages, values):
            if pd.notna(voltage) and pd.notna(vapor_fraction):
                rows.append(
                    {
                        "case_label": case,
                        "state_voltage": float(voltage),
                        "vapor_area_fraction_aug9": float(vapor_fraction),
                        "optical_source": path.name,
                    }
                )
    result = pd.DataFrame(rows).sort_values(["case_label", "state_voltage"])
    expected_cases = set(CASE_STYLE)
    if set(result["case_label"]) != expected_cases:
        raise ValueError(
            f"Unexpected cases in values workbook: {sorted(set(result['case_label']))}"
        )
    return result


def merge_optical_and_multimodal(optical: pd.DataFrame, multimodal: pd.DataFrame) -> pd.DataFrame:
    required = {
        "case_label",
        "state_label",
        "state_voltage",
        "heat_flux_mean_w_cm2",
        "htc_mean_w_m2k",
        "ae_abs_energy_rate",
    }
    missing = required - set(multimodal.columns)
    if missing:
        raise ValueError(f"Combined summary is missing columns: {sorted(missing)}")
    merged = multimodal.merge(optical, on=["case_label", "state_voltage"], how="inner")
    if len(merged) != len(optical):
        raise ValueError(
            f"Matched {len(merged)} of {len(optical)} Aug. 9 optical states to the multimodal summary"
        )
    return merged.sort_values(["case_label", "state_voltage"])


def summarize_state_trends(merged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for case, group in merged.groupby("case_label", sort=False):
        group = group.sort_values("state_voltage")
        heat_flux_group = group.dropna(
            subset=["heat_flux_mean_w_cm2", "vapor_area_fraction_aug9"]
        )
        peak = group.loc[group["vapor_area_fraction_aug9"].idxmax()]
        endpoint = group.iloc[-1]
        peak_value = float(peak["vapor_area_fraction_aug9"])
        endpoint_value = float(endpoint["vapor_area_fraction_aug9"])
        rows.append(
            {
                "case_label": case,
                "states": int(len(group)),
                "vapor_area_fraction_min": float(group["vapor_area_fraction_aug9"].min()),
                "vapor_area_fraction_max": peak_value,
                "peak_voltage_v": float(peak["state_voltage"]),
                "endpoint_voltage_v": float(endpoint["state_voltage"]),
                "endpoint_vapor_area_fraction": endpoint_value,
                "endpoint_change_from_peak": endpoint_value - peak_value,
                "endpoint_relative_change_from_peak": (
                    (endpoint_value - peak_value) / peak_value if peak_value else float("nan")
                ),
                "spearman_voltage_vs_vapor_area": spearman_rank_correlation(
                    group["state_voltage"], group["vapor_area_fraction_aug9"]
                ),
                "spearman_heat_flux_vs_vapor_area": spearman_rank_correlation(
                    heat_flux_group["heat_flux_mean_w_cm2"],
                    heat_flux_group["vapor_area_fraction_aug9"],
                ),
            }
        )
    return pd.DataFrame(rows)


def spearman_rank_correlation(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 2:
        return float("nan")
    x_rank = x.rank(method="average").to_numpy(dtype=float)
    y_rank = y.rank(method="average").to_numpy(dtype=float)
    return float(np.corrcoef(x_rank, y_rank)[0, 1])


def build_cfg(*, weights: str, score_threshold: float, detections_per_image: int, device: str):
    cfg = get_cfg()
    cfg.merge_from_file(
        model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )
    cfg.MODEL.WEIGHTS = weights
    cfg.MODEL.DEVICE = device
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_threshold
    cfg.MODEL.ANCHOR_GENERATOR.SIZES = [[8], [16], [32], [64], [128]]
    cfg.INPUT.MIN_SIZE_TEST = 640
    cfg.INPUT.MAX_SIZE_TEST = 900
    cfg.TEST.DETECTIONS_PER_IMAGE = detections_per_image
    return cfg


def run_temporal_analysis(
    *,
    image_root: Path,
    predictor: DefaultPredictor,
    roi: tuple[int, int, int, int],
    temporal_voltage: float,
    frame_rate_hz: float,
    max_frames: int | None,
    assets_dir: Path,
) -> tuple[pd.DataFrame, dict[str, dict[str, Path]]]:
    rows = []
    representative: dict[str, dict[str, Path]] = {}
    for case in CASE_STYLE:
        state_dir = find_state_directory(image_root / case, temporal_voltage)
        paths = iter_images(state_dir)
        if max_frames is not None and len(paths) > max_frames:
            indices = np.linspace(0, len(paths) - 1, max_frames, dtype=int)
            paths = [paths[int(index)] for index in indices]
        representative_index = len(paths) // 2
        for frame_index, image_path in enumerate(paths):
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            cropped = crop_array(image, roi)
            outputs = predictor(cropped)
            instances = outputs["instances"].to("cpu")
            masks = (
                instances.pred_masks.numpy()
                if instances.has("pred_masks")
                else np.empty((0, *cropped.shape[:2]), dtype=bool)
            )
            combined = np.any(masks, axis=0).astype(np.uint8) * 255 if len(masks) else np.zeros(
                cropped.shape[:2], dtype=np.uint8
            )
            metrics = projected_mask_metrics(combined)
            rows.append(
                {
                    "case_label": case,
                    "state_label": state_dir.name,
                    "state_voltage": temporal_voltage,
                    "frame_index": frame_index,
                    "time_ms": 1000.0 * frame_index / frame_rate_hz,
                    "frame_name": image_path.name,
                    "vapor_area_fraction": metrics["vapor_area_fraction"],
                    "predicted_instances": int(len(instances)),
                }
            )
            if frame_index == representative_index:
                raw_path = assets_dir / f"{case}_45V_roi.png"
                mask_path = assets_dir / f"{case}_45V_mask.png"
                overlay_path = assets_dir / f"{case}_45V_overlay.png"
                cv2.imwrite(str(raw_path), cropped)
                cv2.imwrite(str(mask_path), combined)
                cv2.imwrite(str(overlay_path), overlay_mask(cropped, combined))
                representative[case] = {
                    "raw": raw_path,
                    "mask": mask_path,
                    "overlay": overlay_path,
                }
    return pd.DataFrame(rows), representative


def find_state_directory(case_dir: Path, voltage: float) -> Path:
    matches = []
    for path in case_dir.iterdir():
        if not path.is_dir():
            continue
        match = re.search(r"\d+(?:\.\d+)?", path.name)
        if match and math.isclose(float(match.group(0)), voltage, abs_tol=1e-9):
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(f"Expected one {voltage:g} V state under {case_dir}; found {matches}")
    return matches[0]


def existing_representative_assets(assets_dir: Path) -> dict[str, dict[str, Path]]:
    result = {}
    for case in CASE_STYLE:
        assets = {
            "raw": assets_dir / f"{case}_45V_roi.png",
            "mask": assets_dir / f"{case}_45V_mask.png",
            "overlay": assets_dir / f"{case}_45V_overlay.png",
        }
        missing = [str(path) for path in assets.values() if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing representative assets for {case}: {missing}")
        result[case] = assets
    return result


def summarize_temporal(
    temporal: pd.DataFrame,
    optical: pd.DataFrame,
    temporal_voltage: float,
) -> pd.DataFrame:
    rows = []
    workbook = optical[np.isclose(optical["state_voltage"], temporal_voltage)].set_index(
        "case_label"
    )
    for case, group in temporal.groupby("case_label", sort=False):
        values = group["vapor_area_fraction"].to_numpy(dtype=float)
        n = len(values)
        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1)) if n > 1 else float("nan")
        critical = t975_approx(n - 1) if n > 1 else float("nan")
        iid_ci = critical * std / math.sqrt(n) if n > 1 else float("nan")
        block_interval = circular_moving_block_bootstrap_mean_interval(
            values,
            samples=5000,
            seed=20260813 + len(rows),
        )
        ci = (float(block_interval["upper"]) - float(block_interval["lower"])) / 2
        workbook_value = float(workbook.loc[case, "vapor_area_fraction_aug9"])
        rows.append(
            {
                "case_label": case,
                "state_voltage": temporal_voltage,
                "frames": n,
                "mean_vapor_area_fraction": mean,
                "std_vapor_area_fraction": std,
                "ci95_half_width": ci,
                "ci95_lower": block_interval["lower"],
                "ci95_upper": block_interval["upper"],
                "iid_student_t_ci95_half_width": iid_ci,
                "lag1_autocorrelation": float(pd.Series(values).autocorr(lag=1)),
                "tau_int_frames": block_interval["tau_int_frames"],
                "effective_sample_size": block_interval["effective_sample_size"],
                "bootstrap_block_length_frames": block_interval["block_length"],
                "uncertainty_method": "circular moving-block bootstrap, 5000 resamples",
                "workbook_vapor_area_fraction": workbook_value,
                "mean_minus_workbook": mean - workbook_value,
                "max_predicted_instances": int(group["predicted_instances"].max()),
            }
        )
    return pd.DataFrame(rows)


def t975_approx(degrees_of_freedom: int) -> float:
    if degrees_of_freedom <= 0:
        return float("nan")
    z = 1.959963984540054
    nu = float(degrees_of_freedom)
    return z + (z**3 + z) / (4 * nu) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * nu**2)


def overlay_mask(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    overlay = image_bgr.copy()
    red = np.zeros_like(image_bgr)
    red[:, :, 2] = 255
    mask_bool = mask > 0
    blended = cv2.addWeighted(image_bgr, 0.55, red, 0.45, 0)
    overlay[mask_bool] = blended[mask_bool]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 120, 0), 1)
    return overlay


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
            "axes.edgecolor": "black",
            "axes.grid": False,
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
            "mathtext.bf": "Arial:bold",
            "savefig.dpi": 500,
        }
    )


def save_both(fig: plt.Figure, base: Path) -> list[Path]:
    pdf = base.with_suffix(".pdf")
    png = base.with_suffix(".png")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=500, bbox_inches="tight")
    plt.close(fig)
    return [pdf, png]


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        0.0,
        1.03,
        f"({label})",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        clip_on=False,
    )


def figure_model_outputs(
    representative: dict[str, dict[str, Path]], output_dir: Path
) -> list[Path]:
    fig, axes = plt.subplots(4, 2, figsize=(7.2, 2.65), constrained_layout=True)
    for row, case in enumerate(CASE_STYLE):
        _, _, label = CASE_STYLE[case]
        raw = cv2.cvtColor(cv2.imread(str(representative[case]["raw"])), cv2.COLOR_BGR2RGB)
        overlay = cv2.cvtColor(
            cv2.imread(str(representative[case]["overlay"])), cv2.COLOR_BGR2RGB
        )
        axes[row, 0].imshow(raw)
        axes[row, 1].imshow(overlay)
        axes[row, 0].text(
            -0.015,
            0.5,
            label,
            transform=axes[row, 0].transAxes,
            ha="right",
            va="center",
            fontsize=8,
        )
        for ax in axes[row]:
            ax.set_axis_off()
    axes[0, 0].set_title("Raw 45 V ROI")
    axes[0, 1].set_title("Fine-tuned Mask R-CNN overlay")
    panel_label(axes[0, 0], "a")
    panel_label(axes[0, 1], "b")
    return save_both(fig, output_dir / "Figure_4_aug9_model_outputs")


def figure_optical_results(
    optical: pd.DataFrame,
    merged: pd.DataFrame,
    temporal: pd.DataFrame,
    temporal_summary: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()
    for case in CASE_STYLE:
        color, marker, label = CASE_STYLE[case]
        group = optical[optical["case_label"] == case].sort_values("state_voltage")
        ax0.plot(
            group["state_voltage"],
            group["vapor_area_fraction_aug9"],
            marker=marker,
            color=color,
            lw=1.4,
            linestyle="--",
            label=label,
        )
        joined = merged[merged["case_label"] == case].sort_values("heat_flux_mean_w_cm2")
        ax1.plot(
            joined["heat_flux_mean_w_cm2"],
            joined["vapor_area_fraction_aug9"],
            marker=marker,
            color=color,
            lw=1.4,
            linestyle="--",
        )
        trace = temporal[temporal["case_label"] == case]
        ax2.plot(
            trace["time_ms"],
            trace["vapor_area_fraction"],
            color=color,
            lw=1.1,
            linestyle="--",
            label=label,
        )
        row = temporal_summary[temporal_summary["case_label"] == case].iloc[0]
        ax3.scatter(
            row["workbook_vapor_area_fraction"],
            row["mean_vapor_area_fraction"],
            marker=marker,
            color=color,
            s=38,
            label=label,
        )

    ax0.set_xlabel("Applied voltage (V)")
    ax0.set_ylabel("Projected vapor coverage")
    ax1.set_xlabel("Heat flux (W/cm2)")
    ax1.set_ylabel("Projected vapor coverage")
    ax2.set_xlabel("Time from first recorded frame (ms)")
    ax2.set_ylabel("Projected vapor coverage")
    lower = min(
        temporal_summary["workbook_vapor_area_fraction"].min(),
        temporal_summary["mean_vapor_area_fraction"].min(),
    )
    upper = max(
        temporal_summary["workbook_vapor_area_fraction"].max(),
        temporal_summary["mean_vapor_area_fraction"].max(),
    )
    pad = max(0.005, 0.12 * (upper - lower))
    ax3.plot([lower - pad, upper + pad], [lower - pad, upper + pad], "--", color="#555555")
    ax3.set_xlim(lower - pad, upper + pad)
    ax3.set_ylim(lower - pad, upper + pad)
    ax3.set_xlabel("Workbook state summary")
    ax3.set_ylabel("Recomputed sequence mean")
    mae = float(np.mean(np.abs(temporal_summary["mean_minus_workbook"])))
    for label, ax in zip("abcd", axes.ravel(), strict=True):
        panel_label(ax, label)
        ax.set_box_aspect(0.72)
        ax.tick_params(direction="in", top=True, right=True)
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color("black")
    handles, labels = ax0.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.01))
    return save_both(fig, output_dir / "Figure_5_aug9_optical_results")


def figure_multimodal_context(merged: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.65), constrained_layout=True)
    ax0, ax1, ax2 = axes
    for case in CASE_STYLE:
        color, marker, label = CASE_STYLE[case]
        group = merged[merged["case_label"] == case].sort_values("state_voltage")
        ax0.plot(
            group["heat_flux_mean_w_cm2"],
            group["vapor_area_fraction_aug9"],
            marker=marker,
            color=color,
            lw=1.3,
            linestyle="--",
            label=label,
        )
        ax1.plot(
            group["vapor_area_fraction_aug9"],
            group["htc_mean_w_m2k"] / 1000.0,
            marker=marker,
            color=color,
            lw=1.3,
            linestyle="--",
        )
        for row in group.itertuples():
            quality = getattr(row, "ae_window_quality", "unknown")
            if not np.isfinite(row.ae_abs_energy_rate):
                continue
            kwargs = {
                "x": row.vapor_area_fraction_aug9,
                "y": max(float(row.ae_abs_energy_rate), 1e-3),
                "color": color,
                "s": 30,
            }
            if quality == "blocked":
                ax2.scatter(marker="x", linewidths=1.1, **kwargs)
            elif quality == "caution":
                ax2.scatter(marker=marker, facecolors="none", edgecolors=color, s=30, x=kwargs["x"], y=kwargs["y"])
            else:
                ax2.scatter(marker=marker, **kwargs)
    ax0.set_xlabel("Heat flux (W/cm2)")
    ax0.set_ylabel("Projected vapor coverage")
    ax0.set_title("Optical response")
    ax1.set_xlabel("Projected vapor coverage")
    ax1.set_ylabel("Mean HTC (kW/m2 K)")
    ax1.set_title("Thermal response")
    ax2.set_xlabel("Projected vapor coverage")
    ax2.set_ylabel("AE abs. energy rate")
    ax2.set_yscale("log")
    ax2.set_title("AE screening")
    ax2.text(
        0.03,
        0.03,
        "open: caution\nx: overlap",
        transform=ax2.transAxes,
        va="bottom",
        ha="left",
        fontsize=7,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999999", alpha=0.9),
    )
    for label, ax in zip("abc", axes):
        panel_label(ax, label)
    handles, labels = ax0.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.08))
    return save_both(fig, output_dir / "Figure_6_aug9_multimodal_context")


def figure_graphical_abstract(
    representative: dict[str, dict[str, Path]],
    merged: pd.DataFrame,
    temporal_summary: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    fig = plt.figure(figsize=(8.6, 4.0), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.15, 1.0], height_ratios=[1, 1])
    ax_raw = fig.add_subplot(grid[0, 0])
    ax_overlay = fig.add_subplot(grid[1, 0])
    ax_plot = fig.add_subplot(grid[:, 1])

    representative_case = "15gs_20C"
    raw = cv2.cvtColor(
        cv2.imread(str(representative[representative_case]["raw"])), cv2.COLOR_BGR2RGB
    )
    overlay = cv2.cvtColor(
        cv2.imread(str(representative[representative_case]["overlay"])), cv2.COLOR_BGR2RGB
    )
    ax_raw.imshow(raw)
    ax_overlay.imshow(overlay)
    for ax in (ax_raw, ax_overlay):
        ax.set_axis_off()
    ax_raw.set_title("3000-fps near-wall ROI", pad=5)
    ax_overlay.set_title("Fine-tuned one-class Mask R-CNN", pad=5)

    for case, (color, marker, label) in CASE_STYLE.items():
        group = merged[merged["case_label"] == case].dropna(
            subset=["heat_flux_mean_w_cm2", "vapor_area_fraction_aug9"]
        )
        group = group.sort_values("heat_flux_mean_w_cm2")
        ax_plot.plot(
            group["heat_flux_mean_w_cm2"],
            group["vapor_area_fraction_aug9"],
            marker=marker,
            color=color,
            lw=1.5,
            linestyle="--",
            label=label,
        )
    ax_plot.set_xlabel("Heat flux (W/cm2)")
    ax_plot.set_ylabel("Projected vapor coverage")
    ax_plot.set_title("Within-case response to thermal forcing")
    ax_plot.legend(frameon=False, fontsize=7, loc="upper left")
    mae = float(np.mean(np.abs(temporal_summary["mean_minus_workbook"])))
    neff_min = float(temporal_summary["effective_sample_size"].min())
    neff_max = float(temporal_summary["effective_sample_size"].max())
    fig.text(
        0.30,
        0.50,
        "130 annotated images\n"
        "Same-sequence holdout: IoU = 0.652, coverage MAE = 0.0051\n"
        f"45 V sequences: MAE = {mae:.5f}, effective n = {neff_min:.1f}-{neff_max:.1f}",
        ha="center",
        va="center",
        fontsize=7.5,
    )
    fig.suptitle(
        "BubbleID-Flow: auditable projected vapor coverage from boiling images",
        fontsize=12,
        weight="bold",
    )
    return save_both(fig, output_dir / "Graphical_Abstract")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


if __name__ == "__main__":
    main()
