from __future__ import annotations

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a first multimodal thermal/acoustic/image summary for one test case."
    )
    parser.add_argument("--case-label", required=True, help="Case label such as 15gs_20C.")
    parser.add_argument("--image-root", required=True, help="Root containing image state folders.")
    parser.add_argument("--thermal-workbook", required=True, help="Reduced thermal workbook.")
    parser.add_argument("--thermal-input-workbook", required=True, help="Workbook containing voltage.")
    parser.add_argument("--ae-hit-file", required=True, help="EasyAE HIT text file.")
    parser.add_argument("--weights", required=True, help="Detectron2 Mask R-CNN weights.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--roi", default="0,485,1024,70")
    parser.add_argument("--frames-per-state", type=int, default=12)
    parser.add_argument("--bins", type=int, default=64)
    parser.add_argument("--score-threshold", type=float, default=0.30)
    parser.add_argument("--voltage-tolerance", type=float, default=0.75)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir = output_dir / "representative_overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    states = discover_states(Path(args.image_root))
    predictor = DefaultPredictor(_build_cfg(args.weights, args.score_threshold, args.device))
    image_summary, frame_metrics = summarize_image_states(
        states=states,
        predictor=predictor,
        roi=parse_roi(args.roi),
        frames_per_state=args.frames_per_state,
        overlay_dir=overlay_dir,
    )
    thermal_summary = summarize_thermal_states(
        states=states,
        thermal_workbook=Path(args.thermal_workbook),
        thermal_input_workbook=Path(args.thermal_input_workbook),
        voltage_tolerance=args.voltage_tolerance,
    )
    ae_summary = summarize_ae_by_thermal_windows(
        hit_file=Path(args.ae_hit_file),
        thermal_windows=thermal_summary[
            ["state_label", "time_start_s", "time_end_s"]
        ].dropna(),
    )

    summary = (
        image_summary.merge(thermal_summary, on=["state_label", "state_voltage"], how="outer")
        .merge(ae_summary, on="state_label", how="left")
        .sort_values("state_voltage", na_position="last")
    )

    summary_path = output_dir / f"{args.case_label}_multimodal_state_summary.csv"
    frame_metrics_path = output_dir / f"{args.case_label}_image_frame_metrics.csv"
    figure_path = output_dir / f"{args.case_label}_integrated_baseline_panel.png"
    image_summary_path = output_dir / f"{args.case_label}_image_state_summary.csv"

    summary.to_csv(summary_path, index=False)
    frame_metrics.to_csv(frame_metrics_path, index=False)
    image_summary.to_csv(image_summary_path, index=False)
    plot_integrated_panel(
        case_label=args.case_label,
        summary=summary,
        figure_path=figure_path,
        thermal_workbook=Path(args.thermal_workbook),
        overlay_dir=overlay_dir,
    )

    print(f"Wrote {summary_path}")
    print(f"Wrote {frame_metrics_path}")
    print(f"Wrote {figure_path}")


def discover_states(image_root: Path) -> list[dict]:
    states = []
    for path in sorted([p for p in image_root.iterdir() if p.is_dir()], key=lambda p: parse_state_voltage(p.name)):
        voltage = parse_state_voltage(path.name)
        if voltage is None:
            continue
        states.append({"state_label": path.name, "state_voltage": voltage, "path": path})
    return states


def parse_state_voltage(label: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", label)
    return float(match.group(0)) if match else None


def sample_evenly(paths: list[Path], count: int) -> list[Path]:
    if count <= 0 or len(paths) <= count:
        return paths
    indices = np.linspace(0, len(paths) - 1, count, dtype=int)
    return [paths[int(index)] for index in indices]


def summarize_image_states(
    states: list[dict],
    predictor: DefaultPredictor,
    roi: tuple[int, int, int, int],
    frames_per_state: int,
    overlay_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    frame_rows = []
    for state in states:
        image_paths = sample_evenly(iter_images(state["path"]), frames_per_state)
        representative_index = len(image_paths) // 2 if image_paths else -1
        for frame_index, image_path in enumerate(image_paths):
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            cropped = crop_array(image, roi)
            combined = predict_combined_mask(predictor, cropped)
            metrics = mask_metrics(combined)
            frame_rows.append(
                {
                    "state_label": state["state_label"],
                    "state_voltage": state["state_voltage"],
                    "frame_name": image_path.name,
                    **metrics,
                }
            )
            if frame_index == representative_index:
                overlay_path = overlay_dir / f"{safe_name(state['state_label'])}_{image_path.stem}_overlay.png"
                cv2.imwrite(str(overlay_path), overlay_combined_mask(cropped, combined))

    frame_metrics = pd.DataFrame(frame_rows)
    grouped = frame_metrics.groupby(["state_label", "state_voltage"], as_index=False)
    summary = grouped.agg(
        image_frames=("frame_name", "count"),
        vapor_area_fraction_mean=("vapor_area_fraction", "mean"),
        vapor_area_fraction_std=("vapor_area_fraction", "std"),
        active_length_fraction_mean=("active_length_fraction", "mean"),
        vapor_front_x_px_mean=("vapor_front_x_px", "mean"),
    )
    return summary, frame_metrics


def predict_combined_mask(predictor: DefaultPredictor, image: np.ndarray) -> np.ndarray:
    outputs = predictor(image)
    instances = outputs["instances"].to("cpu")
    masks = instances.pred_masks.numpy() if instances.has("pred_masks") else np.empty((0, *image.shape[:2]))
    return np.any(masks, axis=0).astype(np.uint8) * 255 if len(masks) else np.zeros(image.shape[:2], dtype=np.uint8)


def mask_metrics(mask: np.ndarray) -> dict:
    mask_bool = mask > 0
    column_fraction = mask_bool.mean(axis=0)
    active_columns = np.flatnonzero(column_fraction > 0.05)
    vapor_front = float(active_columns.max()) if len(active_columns) else np.nan
    return {
        "vapor_area_fraction": float(mask_bool.mean()),
        "active_length_fraction": float(len(active_columns) / mask.shape[1]),
        "vapor_front_x_px": vapor_front,
    }


def summarize_thermal_states(
    states: list[dict],
    thermal_workbook: Path,
    thermal_input_workbook: Path,
    voltage_tolerance: float,
) -> pd.DataFrame:
    thermal = pd.read_excel(thermal_workbook)
    thermal_input = pd.read_excel(thermal_input_workbook)
    combined = thermal.copy()

    voltage_col = find_column(thermal_input, ["Voltage"])
    time_col = find_column(combined, ["Time [s]"])
    power_col = find_column(combined, ["Power"])
    heat_flux_col = find_column(combined, ["Heat Flux"])
    inlet_subcool_col = find_column(combined, ["Inlet Subcooling"])
    pin_col = find_column(combined, ["Inlet Pressure"])
    pout_col = find_column(combined, ["Outlet Pressure"])
    htc_cols = [col for col in combined.columns if "Heat Transfer Coefficient" in str(col)]
    quality_cols = [col for col in combined.columns if str(col).startswith("Quality at x")]

    combined["_abs_voltage"] = thermal_input[voltage_col].abs().to_numpy()
    rows = []
    for state in states:
        target = state["state_voltage"]
        selected = combined[(combined["_abs_voltage"] - target).abs() <= voltage_tolerance]
        if selected.empty:
            rows.append(
                {
                    "state_label": state["state_label"],
                    "state_voltage": target,
                    "thermal_rows": 0,
                }
            )
            continue
        heat_flux = selected[heat_flux_col]
        if "W/m²" in heat_flux_col or "W/m2" in heat_flux_col:
            heat_flux_w_cm2 = heat_flux / 10_000.0
        else:
            heat_flux_w_cm2 = heat_flux
        rows.append(
            {
                "state_label": state["state_label"],
                "state_voltage": target,
                "thermal_rows": len(selected),
                "time_start_s": float(selected[time_col].min()),
                "time_end_s": float(selected[time_col].max()),
                "voltage_mean_v": float(selected["_abs_voltage"].mean()),
                "power_mean_w": float(selected[power_col].mean()),
                "heat_flux_mean_w_cm2": float(heat_flux_w_cm2.mean()),
                "inlet_subcooling_mean_c": float(selected[inlet_subcool_col].mean()),
                "pressure_drop_mean_kpa": float((selected[pin_col] - selected[pout_col]).mean()),
                "htc_mean_w_m2k": float(selected[htc_cols].mean(axis=1).mean()) if htc_cols else np.nan,
                "quality_x7_mean": float(selected[quality_cols[-1]].mean()) if quality_cols else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_ae_by_thermal_windows(hit_file: Path, thermal_windows: pd.DataFrame) -> pd.DataFrame:
    hits = read_hit_file(hit_file)
    time_col = "SSSSSSSS.mmmuuun"
    rows = []
    for row in thermal_windows.itertuples(index=False):
        duration = max(float(row.time_end_s - row.time_start_s), 1e-9)
        selected = hits[(hits[time_col] >= row.time_start_s) & (hits[time_col] <= row.time_end_s)]
        ch1 = selected[selected["CH"] == 1]
        ch2 = selected[selected["CH"] == 2]
        rows.append(
            {
                "state_label": row.state_label,
                "ae_hits": len(selected),
                "ae_hit_rate_hz": float(len(selected) / duration),
                "ae_abs_energy_rate": float(selected["ABS-ENERGY"].sum() / duration) if len(selected) else 0.0,
                "ae_amp_mean_db": float(selected["AMP"].mean()) if len(selected) else np.nan,
                "ae_ch1_hit_rate_hz": float(len(ch1) / duration),
                "ae_ch2_hit_rate_hz": float(len(ch2) / duration),
            }
        )
    return pd.DataFrame(rows)


def read_hit_file(hit_file: Path) -> pd.DataFrame:
    with hit_file.open("r", encoding="latin1") as handle:
        lines = handle.readlines()
    header_idx = next(
        index for index, line in enumerate(lines) if line.strip().startswith("ID") and "SSSS" in line
    )
    columns = lines[header_idx].split()
    sig_idx = columns.index("SIG")
    columns = columns[:sig_idx] + ["SIG-STRENGTH"] + columns[sig_idx + 2 :]
    return pd.read_csv(
        hit_file,
        sep=r"\s+",
        names=columns,
        skiprows=header_idx + 1,
        engine="python",
    )


def find_column(data: pd.DataFrame, fragments: list[str]) -> str:
    for column in data.columns:
        text = str(column)
        if all(fragment in text for fragment in fragments):
            return column
    raise KeyError(f"Could not find column containing {fragments}")


def plot_integrated_panel(
    case_label: str,
    summary: pd.DataFrame,
    figure_path: Path,
    thermal_workbook: Path,
    overlay_dir: Path,
) -> None:
    thermal = pd.read_excel(thermal_workbook)
    time_col = find_column(thermal, ["Time [s]"])
    heat_flux_col = find_column(thermal, ["Heat Flux"])
    heat_flux = thermal[heat_flux_col]
    if "W/m²" in heat_flux_col or "W/m2" in heat_flux_col:
        heat_flux = heat_flux / 10_000.0

    fig = plt.figure(figsize=(13, 8), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    ax0.plot(thermal[time_col], heat_flux, color="#333333", linewidth=1.5)
    ax0.set_title(f"{case_label}: thermal forcing")
    ax0.set_xlabel("Test-relative time (s)")
    ax0.set_ylabel("Heat flux (W/cm$^2$)")
    ax0.grid(True, alpha=0.3)

    ax1.errorbar(
        summary["state_voltage"],
        summary["vapor_area_fraction_mean"],
        yerr=summary["vapor_area_fraction_std"].fillna(0),
        marker="o",
        color="#1664a2",
        linewidth=1.8,
        capsize=3,
    )
    ax1.set_title("Image-derived vapor coverage")
    ax1.set_xlabel("Applied voltage state (V)")
    ax1.set_ylabel("Projected vapor area fraction")
    ax1.grid(True, alpha=0.3)

    ax2.plot(
        summary["state_voltage"],
        summary["htc_mean_w_m2k"],
        marker="s",
        color="#8c2d04",
        linewidth=1.8,
        label="Mean HTC",
    )
    ax2b = ax2.twinx()
    ax2b.plot(
        summary["state_voltage"],
        summary["heat_flux_mean_w_cm2"],
        marker="^",
        color="#2ca25f",
        linewidth=1.8,
        label="Heat flux",
    )
    ax2.set_title("Thermal state summary")
    ax2.set_xlabel("Applied voltage state (V)")
    ax2.set_ylabel("Mean HTC (W/m$^2$ K)")
    ax2b.set_ylabel("Heat flux (W/cm$^2$)")
    ax2.grid(True, alpha=0.3)

    ax3.plot(
        summary["state_voltage"],
        summary["ae_hit_rate_hz"],
        marker="o",
        color="#6a51a3",
        linewidth=1.8,
        label="AE hit rate",
    )
    ax3b = ax3.twinx()
    ax3b.plot(
        summary["state_voltage"],
        summary["ae_abs_energy_rate"],
        marker="D",
        color="#d95f0e",
        linewidth=1.8,
        label="AE abs. energy rate",
    )
    ax3.set_title("AE activity, provisional time alignment")
    ax3.set_xlabel("Applied voltage state (V)")
    ax3.set_ylabel("Hit rate (Hz)")
    ax3b.set_ylabel("Abs. energy rate")
    ax3.grid(True, alpha=0.3)

    fig.suptitle(
        "First integrated BubbleID-Flow multimodal panel: image, thermal, and acoustic metrics",
        fontsize=14,
    )
    fig.savefig(figure_path, dpi=220)
    plt.close(fig)

    contact_sheet_path = figure_path.with_name(f"{case_label}_representative_overlay_sheet.png")
    make_overlay_sheet(overlay_dir, contact_sheet_path)


def make_overlay_sheet(overlay_dir: Path, output_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    paths = sorted(overlay_dir.glob("*.png"))
    if not paths:
        return
    cell_w, cell_h = 360, 50
    cols = 3
    rows = int(np.ceil(len(paths) / cols))
    label_h = 20
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
    for index, path in enumerate(paths):
        row, col = divmod(index, cols)
        x = col * cell_w
        y = row * (cell_h + label_h)
        draw.text((x + 4, y + 3), path.name.split("_192.")[0], fill=(0, 0, 0), font=font)
        image = Image.open(path).convert("RGB").resize((cell_w, cell_h))
        sheet.paste(image, (x, y + label_h))
    sheet.save(output_path)


def overlay_combined_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    overlay = image.copy()
    red = np.zeros_like(image)
    red[:, :, 2] = 255
    mask_bool = mask > 0
    overlay[mask_bool] = cv2.addWeighted(image, 0.55, red, 0.45, 0)[mask_bool]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 255, 0), 1)
    return overlay


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _build_cfg(weights: str, score_threshold: float, device: str):
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
    return cfg


if __name__ == "__main__":
    main()
