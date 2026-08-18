from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from zipfile import ZipFile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from PIL import Image, ImageDraw, ImageFont

from bubbleid_flow.preprocess import crop_array, parse_roi
from bubbleid_flow.vapor_fraction import streamwise_area_fraction_profile

try:
    import cv2
except ImportError:  # pragma: no cover - exercised only in lightweight environments.
    cv2 = None

try:
    import torch
except ImportError:  # pragma: no cover - exercised only in lightweight environments.
    torch = None


DEFAULT_DATA_ROOT = (
    r"C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday"
)
DEFAULT_MODEL_DIR = (
    r"C:\Users\hanhu\Box\NED3_Share\0_BubbleID\BubbleID-Flow"
    r"\detectron2_flow_mrcnn_roi485_70"
)
DEFAULT_VISIT_DECK = (
    r"C:\Users\hanhu\Box\NED3_Share\0_NSF_CASIS_FBCE_Project"
    r"\CWRU_visit_Oct_13_17_2025\CWRU_Oct_2025_Visit_Summary.pptx"
)

CASE_STYLE = {
    "5gs_22C": ("#0072B2", "o"),
    "10gs_22C": ("#009E73", "s"),
    "15gs_20C": ("#D55E00", "^"),
    "25gs_20C": ("#CC79A7", "D"),
}


def main() -> None:
    default_device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
    parser = argparse.ArgumentParser(
        description="Prepare Applied Thermal Engineering submission figures."
    )
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    parser.add_argument("--visit-deck", default=DEFAULT_VISIT_DECK)
    parser.add_argument("--outputs-root", default="outputs/ate_submission")
    parser.add_argument("--overleaf-dir", default="overleaf_applied_thermal_engineering")
    parser.add_argument("--roi", default="0,485,1024,70")
    parser.add_argument("--score-threshold", type=float, default=0.30)
    parser.add_argument("--bins", type=int, default=64)
    parser.add_argument("--device", default=default_device)
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Regenerate figures that do not require OpenCV, Torch, or Detectron2.",
    )
    args = parser.parse_args()

    outputs_root = Path(args.outputs_root)
    figure_root = outputs_root / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    overleaf_dir = Path(args.overleaf_dir)
    overleaf_dir.mkdir(parents=True, exist_ok=True)

    set_style()
    media_dir = outputs_root / "ppt_media"
    extract_ppt_media(Path(args.visit_deck), media_dir)

    data_root = Path(args.data_root)
    model_weights = Path(args.model_dir) / "model_final.pth"
    repo_outputs = Path("outputs") / "multimodal"
    combined = load_cross_case_analysis(repo_outputs / "cross_case_synthesis")
    baseline = pd.read_csv(
        repo_outputs / "15gs_20C_baseline" / "15gs_20C_multimodal_state_summary.csv"
    )

    generated = []
    generated += figure_1_facility(media_dir, figure_root)
    fig2_assets = None
    if not args.summary_only:
        raw_image = (
            data_root
            / "Test17_Flow_Loop_and_Imaging"
            / "Images"
            / "15gs_20C"
            / "50"
            / "192.168.0.10_C001H001S0001000062.bmp"
        )
        fig2_assets = create_vision_assets(
            image_path=raw_image,
            weights=model_weights,
            roi=parse_roi(args.roi),
            bins=args.bins,
            threshold=args.score_threshold,
            device=args.device,
            output_dir=outputs_root / "vision_workflow_assets",
        )
        generated += figure_2_vision_workflow(fig2_assets, figure_root)
    generated += figure_3_baseline(baseline, figure_root)
    generated += figure_4_representative_overlays(
        repo_outputs / "15gs_20C_baseline" / "representative_overlays",
        figure_root,
    )
    generated += figure_5_cross_case(combined, figure_root)
    generated += figure_6_state_map(combined, figure_root)
    try:
        generated += figure_7_synchronization_audit(
            data_root=data_root,
            summary=baseline,
            figure_root=figure_root,
        )
    except (FileNotFoundError, PermissionError) as exc:
        if not args.summary_only:
            raise
        print(f"Skipped Figure_7_synchronization_audit: {exc}")
    if fig2_assets is not None:
        generated += graphical_abstract(fig2_assets, combined, figure_root)

    for path in generated:
        if path.suffix.lower() == ".pdf":
            target = overleaf_dir / path.name
            target.write_bytes(path.read_bytes())

    write_manifest(generated, outputs_root / "figure_manifest.txt")
    print(f"Wrote figures to {figure_root}")
    print(f"Copied flat figure files to {overleaf_dir}")


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
            "figure.dpi": 150,
            "savefig.dpi": 500,
            "axes.grid": True,
            "grid.color": "#d9d9d9",
            "grid.linewidth": 0.6,
            "grid.alpha": 0.7,
            "axes.edgecolor": "black",
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
            "mathtext.bf": "Arial:bold",
        }
    )


def extract_ppt_media(deck: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(deck) as archive:
            for name in archive.namelist():
                if name.startswith("ppt/media/") and name.lower().endswith(
                    (".png", ".jpg", ".jpeg")
                ):
                    (out_dir / Path(name).name).write_bytes(archive.read(name))
    except (FileNotFoundError, PermissionError):
        existing = list(out_dir.glob("image*.*"))
        if existing:
            return
        raise


def save_both(fig: plt.Figure, output_base: Path, dpi: int = 500) -> list[Path]:
    pdf = output_base.with_suffix(".pdf")
    png = output_base.with_suffix(".png")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return [pdf, png]


def panel_label(ax, label: str) -> None:
    ax.text(
        0.0,
        1.03,
        f"({label})",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        clip_on=False,
    )


def read_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def load_cross_case_analysis(synthesis_dir: Path) -> pd.DataFrame:
    analysis_path = synthesis_dir / "combined_multimodal_analysis_states.csv"
    if analysis_path.exists():
        data = pd.read_csv(analysis_path)
    else:
        data = pd.read_csv(synthesis_dir / "combined_multimodal_state_summary.csv")
        if "multimodal_complete" in data.columns:
            data = data[data["multimodal_complete"]].copy()
    sampling_path = synthesis_dir / "cross_case_sampling_uncertainty.csv"
    if sampling_path.exists():
        data = attach_sampling_uncertainty_columns(data, pd.read_csv(sampling_path))
    return data


def attach_sampling_uncertainty_columns(
    data: pd.DataFrame,
    sampling_uncertainty: pd.DataFrame,
) -> pd.DataFrame:
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
    return data.drop(columns=existing, errors="ignore").merge(
        sampling_uncertainty[available],
        on=keys,
        how="left",
    )


def vapor_uncertainty_for_plot(group: pd.DataFrame) -> pd.Series | None:
    if "vapor_area_fraction_ci95_half_width" in group.columns:
        ci = pd.to_numeric(group["vapor_area_fraction_ci95_half_width"], errors="coerce")
        if ci.notna().any():
            return ci.fillna(0.0)
    if "vapor_area_fraction_std" in group.columns:
        std = pd.to_numeric(group["vapor_area_fraction_std"], errors="coerce")
        if std.notna().any():
            return std.fillna(0.0)
    return None


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


def figure_1_facility(media_dir: Path, figure_root: Path) -> list[Path]:
    setup_photo = read_rgb(media_dir / "image5.jpeg")
    test_section = read_rgb(media_dir / "image6.jpeg")

    fig = plt.figure(figsize=(7.2, 5.6), constrained_layout=True)
    gs = GridSpec(2, 2, figure=fig, height_ratios=[1.0, 0.92], width_ratios=[1.05, 1.0])
    ax_photo = fig.add_subplot(gs[0, 0])
    ax_loop = fig.add_subplot(gs[0, 1])
    ax_section = fig.add_subplot(gs[1, 0])
    ax_matrix = fig.add_subplot(gs[1, 1])

    ax_photo.imshow(setup_photo)
    ax_photo.set_axis_off()
    ax_photo.set_title("Flow-loop and imaging setup")
    panel_label(ax_photo, "a")

    ax_section.imshow(test_section)
    ax_section.set_axis_off()
    ax_section.set_title("Heated test section and surface sensors")
    panel_label(ax_section, "c")

    ax_loop.set_axis_off()
    ax_loop.set_title("Available measurement streams")
    components = [
        (0.08, 0.62, "Pump"),
        (0.28, 0.62, "Preheater"),
        (0.50, 0.62, "Test\nsection"),
        (0.73, 0.62, "Condenser\nchiller"),
        (0.50, 0.26, "DAQ +\nthermal"),
        (0.20, 0.26, "AE archive"),
        (0.78, 0.26, "High-speed\nimages"),
    ]
    for x, y, text in components:
        ax_loop.add_patch(
            plt.Rectangle((x - 0.08, y - 0.07), 0.16, 0.14, fc="#f5f5f5", ec="#333333", lw=0.9)
        )
        ax_loop.text(x, y, text, ha="center", va="center", fontsize=8)
    arrows = [
        ((0.16, 0.62), (0.20, 0.62)),
        ((0.36, 0.62), (0.42, 0.62)),
        ((0.58, 0.62), (0.65, 0.62)),
        ((0.50, 0.55), (0.50, 0.36)),
        ((0.43, 0.27), (0.28, 0.27)),
        ((0.57, 0.27), (0.70, 0.27)),
    ]
    for xy0, xy1 in arrows:
        ax_loop.annotate("", xy=xy1, xytext=xy0, arrowprops=dict(arrowstyle="->", lw=1.2))
    ax_loop.text(0.02, 0.03, "Present analysis: high-speed imaging + traceable thermal states", fontsize=8)
    panel_label(ax_loop, "b")

    ax_matrix.set_axis_off()
    ax_matrix.set_title("Test matrix")
    rows = [
        ("5", "400", "22", "12"),
        ("10", "800", "22", "8"),
        ("15", "1200", "20", "9"),
        ("25", "2000", "20", "8"),
    ]
    columns = ["Nominal flow\n(g/s)", "Mass flux\n(kg m-2 s-1)", "Subcooling\n(degC)", "Optical\nstates"]
    table = ax_matrix.table(
        cellText=rows,
        colLabels=columns,
        loc="center",
        cellLoc="center",
        colLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.55)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#666666")
        if row == 0:
            cell.set_facecolor("#e8f2f9")
            cell.set_text_props(weight="bold")
    panel_label(ax_matrix, "d")
    return save_both(fig, figure_root / "Figure_1_facility_data_streams")


def build_predictor(weights: Path, threshold: float, device: str) -> DefaultPredictor:
    if cv2 is None or torch is None:
        raise RuntimeError("OpenCV, Torch, and Detectron2 are required for vision figures.")
    from detectron2 import model_zoo
    from detectron2.config import get_cfg
    from detectron2.engine import DefaultPredictor

    cfg = get_cfg()
    config_name = "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    cfg.merge_from_file(model_zoo.get_config_file(config_name))
    cfg.MODEL.WEIGHTS = str(weights)
    cfg.MODEL.DEVICE = device
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold
    cfg.MODEL.ANCHOR_GENERATOR.SIZES = [[8], [16], [32], [64], [128]]
    cfg.INPUT.MIN_SIZE_TEST = 640
    cfg.INPUT.MAX_SIZE_TEST = 900
    return DefaultPredictor(cfg)


def create_vision_assets(
    image_path: Path,
    weights: Path,
    roi: tuple[int, int, int, int],
    bins: int,
    threshold: float,
    device: str,
    output_dir: Path,
) -> dict[str, Path]:
    if cv2 is None:
        raise RuntimeError("OpenCV is required to create vision workflow assets.")
    output_dir.mkdir(parents=True, exist_ok=True)
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read {image_path}")
    cropped = crop_array(image, roi)
    predictor = build_predictor(weights, threshold, device)
    outputs = predictor(cropped)
    instances = outputs["instances"].to("cpu")
    if instances.has("pred_masks"):
        masks = instances.pred_masks.numpy()
    else:
        masks = np.empty((0, *cropped.shape[:2]))
    combined = (
        np.any(masks, axis=0).astype(np.uint8) * 255
        if len(masks)
        else np.zeros(cropped.shape[:2], dtype=np.uint8)
    )
    overlay = overlay_mask(cropped, combined)
    profile = streamwise_area_fraction_profile(combined, bins=bins)
    profile_path = output_dir / "representative_profile.csv"
    profile.to_csv(profile_path, index=False)
    crop_path = output_dir / "representative_roi.png"
    mask_path = output_dir / "representative_mask.png"
    overlay_path = output_dir / "representative_overlay.png"
    cv2.imwrite(str(crop_path), cropped)
    cv2.imwrite(str(mask_path), combined)
    cv2.imwrite(str(overlay_path), overlay)
    return {
        "crop": crop_path,
        "mask": mask_path,
        "overlay": overlay_path,
        "profile": profile_path,
        "image_path": image_path,
    }


def overlay_mask(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    overlay = image_bgr.copy()
    red = np.zeros_like(image_bgr)
    red[:, :, 2] = 255
    mask_bool = mask > 0
    blended = cv2.addWeighted(image_bgr, 0.55, red, 0.45, 0)
    overlay[mask_bool] = blended[mask_bool]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 255, 0), 1)
    return overlay


def figure_2_vision_workflow(assets: dict[str, Path], figure_root: Path) -> list[Path]:
    if cv2 is None:
        raise RuntimeError("OpenCV is required to render the vision workflow figure.")
    crop = cv2.cvtColor(cv2.imread(str(assets["crop"])), cv2.COLOR_BGR2RGB)
    mask = cv2.imread(str(assets["mask"]), cv2.IMREAD_GRAYSCALE)
    overlay = cv2.cvtColor(cv2.imread(str(assets["overlay"])), cv2.COLOR_BGR2RGB)
    profile = pd.read_csv(assets["profile"])

    fig = plt.figure(figsize=(7.2, 5.2), constrained_layout=True)
    gs = GridSpec(2, 2, figure=fig)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    titles = ["Raw near-wall ROI", "Predicted vapor mask", "Mask overlay", "Streamwise profile"]
    for ax, title in zip(axes, titles):
        ax.set_title(title)

    axes[0].imshow(crop)
    axes[0].set_axis_off()
    panel_label(axes[0], "a")

    axes[1].imshow(mask, cmap="gray", vmin=0, vmax=255)
    axes[1].set_axis_off()
    panel_label(axes[1], "b")

    axes[2].imshow(overlay)
    axes[2].set_axis_off()
    panel_label(axes[2], "c")

    axes[3].plot(
        profile["x_center_px"],
        profile["projected_vapor_area_fraction"],
        color="#0072B2",
        lw=1.8,
    )
    axes[3].fill_between(
        profile["x_center_px"],
        profile["projected_vapor_area_fraction"],
        color="#9ecae1",
        alpha=0.45,
    )
    axes[3].set_xlabel("Streamwise position, x (px)")
    axes[3].set_ylabel("Projected vapor\narea fraction")
    axes[3].set_ylim(0, max(0.08, profile["projected_vapor_area_fraction"].max() * 1.2))
    panel_label(axes[3], "d")
    return save_both(fig, figure_root / "Figure_2_vision_workflow")


def figure_3_baseline(summary: pd.DataFrame, figure_root: Path) -> list[Path]:
    data = summary.sort_values("state_voltage")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()

    ax0.plot(data["state_voltage"], data["heat_flux_mean_w_cm2"], "-o", color="#333333")
    ax0.set_ylabel("Heat flux (W/cm2)")
    ax0.set_xlabel("Voltage state (V)")
    ax0.set_title("Thermal forcing")

    ax1.errorbar(
        data["state_voltage"],
        data["vapor_area_fraction_mean"],
        yerr=data["vapor_area_fraction_std"].fillna(0),
        fmt="-o",
        capsize=3,
        color="#0072B2",
    )
    ax1.set_ylabel("Projected vapor area fraction")
    ax1.set_xlabel("Voltage state (V)")
    ax1.set_title("Optical vapor coverage")

    ax2.plot(
        data["state_voltage"],
        data["htc_mean_w_m2k"] / 1000.0,
        "-s",
        color="#D55E00",
    )
    ax2.set_ylabel("Mean HTC (kW/m2 K)")
    ax2.set_xlabel("Voltage state (V)")
    ax2.set_title("Thermal response")

    ax3.semilogy(
        data["state_voltage"],
        data["ae_abs_energy_rate"].clip(lower=1e-3),
        "-D",
        color="#009E73",
    )
    ax3.set_ylabel("AE abs. energy rate")
    ax3.set_xlabel("Voltage state (V)")
    ax3.set_title("AE activity, provisional alignment")

    for label, ax in zip("abcd", [ax0, ax1, ax2, ax3]):
        panel_label(ax, label)
    return save_both(fig, figure_root / "Figure_3_baseline_integrated_case")


def figure_4_representative_overlays(overlay_dir: Path, figure_root: Path) -> list[Path]:
    paths = sorted(overlay_dir.glob("*.png"), key=lambda p: parse_voltage_for_sort(p.name))
    cols = 3
    rows = math.ceil(len(paths) / cols)
    cell_w, cell_h = 1150, 190
    label_h = 48
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    for index, path in enumerate(paths):
        row, col = divmod(index, cols)
        x0 = col * cell_w
        y0 = row * (cell_h + label_h)
        label = clean_overlay_label(path.name)
        draw.text((x0 + 14, y0 + 8), label, fill=(0, 0, 0), font=font)
        im = Image.open(path).convert("RGB")
        im = im.resize((cell_w, cell_h))
        sheet.paste(im, (x0, y0 + label_h))
    png = figure_root / "Figure_4_representative_overlays.png"
    pdf = figure_root / "Figure_4_representative_overlays.pdf"
    sheet.save(png, dpi=(500, 500))
    sheet.save(pdf, "PDF", resolution=500)
    return [pdf, png]


def parse_voltage_for_sort(name: str) -> float:
    match = re.search(r"\d+(?:\.\d+)?", name)
    return float(match.group(0)) if match else 999.0


def clean_overlay_label(name: str) -> str:
    return name.split("_192.")[0].replace("_", " ")


def figure_5_cross_case(data: pd.DataFrame, figure_root: Path) -> list[Path]:
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), constrained_layout=True)
    ax0, ax1, ax2, ax3 = axes.ravel()
    for case, group in data.groupby("case_label", sort=False):
        group = group.sort_values("state_voltage")
        color, marker = CASE_STYLE.get(case, ("#333333", "o"))
        label = case.replace("_", " ")
        ax0.errorbar(
            group["heat_flux_mean_w_cm2"],
            group["vapor_area_fraction_mean"],
            yerr=vapor_uncertainty_for_plot(group),
            marker=marker,
            color=color,
            lw=1.5,
            capsize=2.0,
            label=label,
        )
        ax1.plot(
            group["heat_flux_mean_w_cm2"],
            group["active_length_fraction_mean"],
            marker=marker,
            color=color,
            lw=1.5,
        )
        ax2.plot(
            group["vapor_area_fraction_mean"],
            group["htc_mean_w_m2k"] / 1000.0,
            marker=marker,
            color=color,
            lw=1.5,
        )
        if "ae_window_quality" in group.columns:
            for quality, quality_group in group.groupby("ae_window_quality", sort=False):
                if quality == "blocked":
                    ax3.scatter(
                        quality_group["vapor_area_fraction_mean"],
                        quality_group["ae_abs_energy_rate"].clip(lower=1e-3),
                        marker="x",
                        color="#990000",
                        s=46,
                        linewidths=1.2,
                    )
                elif quality == "caution":
                    ax3.scatter(
                        quality_group["vapor_area_fraction_mean"],
                        quality_group["ae_abs_energy_rate"].clip(lower=1e-3),
                        marker=marker,
                        facecolors="none",
                        edgecolors=color,
                        s=42,
                        linewidths=1.1,
                    )
                else:
                    ax3.scatter(
                        quality_group["vapor_area_fraction_mean"],
                        quality_group["ae_abs_energy_rate"].clip(lower=1e-3),
                        marker=marker,
                        color=color,
                        s=34,
                    )
        else:
            ax3.scatter(
                group["vapor_area_fraction_mean"],
                group["ae_abs_energy_rate"].clip(lower=1e-3),
                marker=marker,
                color=color,
                s=34,
            )

    ax0.set_xlabel("Heat flux (W/cm2)")
    ax0.set_ylabel("Projected vapor area fraction")
    ax0.set_title("Vapor coverage")
    ax0.text(
        0.97,
        0.97,
        "bars: 95% CI",
        transform=ax0.transAxes,
        va="top",
        ha="right",
        fontsize=7,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999999", alpha=0.9),
    )
    ax1.set_xlabel("Heat flux (W/cm2)")
    ax1.set_ylabel("Active vapor length fraction")
    ax1.set_title("Streamwise extent")
    ax2.set_xlabel("Projected vapor area fraction")
    ax2.set_ylabel("Mean HTC (kW/m2 K)")
    ax2.set_title("Thermal response")
    ax3.set_xlabel("Projected vapor area fraction")
    ax3.set_ylabel("AE abs. energy rate")
    ax3.set_yscale("log")
    ax3.set_title("AE activity")
    if "ae_window_quality" in data.columns:
        ax3.text(
            0.03,
            0.03,
            "open: caution\nx: overlap",
            transform=ax3.transAxes,
            va="bottom",
            ha="left",
            fontsize=7,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999999", alpha=0.9),
        )
    for label, ax in zip("abcd", [ax0, ax1, ax2, ax3]):
        panel_label(ax, label)
    handles, labels = ax0.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=4,
        bbox_to_anchor=(0.5, 1.04),
        frameon=False,
    )
    return save_both(fig, figure_root / "Figure_5_cross_case_multimodal_signatures")


def figure_6_state_map(data: pd.DataFrame, figure_root: Path) -> list[Path]:
    labels, metric_labels, scaled = state_map_scaled_values(data)
    fig, ax = plt.subplots(
        figsize=(6.6, max(5.4, 0.18 * len(labels))),
        constrained_layout=True,
    )
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#eeeeee")
    im = ax.imshow(
        np.ma.masked_invalid(scaled),
        aspect="auto",
        cmap=cmap,
        vmin=0,
        vmax=1,
    )
    ax.set_xticks(range(len(metric_labels)), metric_labels, rotation=25, ha="right")
    ax.set_yticks(range(len(labels)), labels, fontsize=6.5)
    ax.set_title("Column-normalized multimodal state map")
    if "ae_window_quality" in data.columns:
        ax.text(
            0.01,
            -0.10,
            "Gray AE-energy cells are overlap-blocked; "
            "AE quality weight is 0, 0.5, or 1.",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=6.5,
        )
    cbar = fig.colorbar(im, ax=ax, fraction=0.025)
    cbar.set_label("Normalized value; AE quality is absolute")
    return save_both(fig, figure_root / "Figure_6_multimodal_state_map")


def figure_7_synchronization_audit(
    data_root: Path,
    summary: pd.DataFrame,
    figure_root: Path,
) -> list[Path]:
    hit_file = data_root / "3" / "HIT_15gs_20C.TXT"
    states = summary.dropna(subset=["time_start_s", "time_end_s"]).sort_values("time_start_s")
    hits = read_hit_file(hit_file)
    ae_time = hits["SSSSSSSS.mmmuuun"].to_numpy(dtype=float)
    start = min(float(states["time_start_s"].min()), float(np.nanmin(ae_time)))
    end = max(float(states["time_end_s"].max()), float(np.nanmax(ae_time)))
    bins = np.arange(max(0, start), end + 10, 10)
    hit_counts, edges = np.histogram(ae_time, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])

    fig, axes = plt.subplots(3, 1, figsize=(7.2, 5.6), sharex=True, constrained_layout=True)
    ax0, ax1, ax2 = axes
    state_centers = 0.5 * (states["time_start_s"].to_numpy() + states["time_end_s"].to_numpy())
    ax0.step(state_centers, states["state_voltage"], where="mid", color="#333333", lw=1.3)
    ax0.scatter(state_centers, states["state_voltage"], color="#333333", s=18)
    ax0.set_ylabel("|Voltage| state (V)")
    ax0.set_title("15 g/s operating-state matching audit")
    ax1.step(state_centers, states["heat_flux_mean_w_cm2"], where="mid", color="#D55E00", lw=1.3)
    ax1.scatter(state_centers, states["heat_flux_mean_w_cm2"], color="#D55E00", s=18)
    ax1.set_ylabel("Mean heat flux\n(W/cm2)")
    ax2.plot(centers, hit_counts / 10.0, color="#009E73", lw=1.0)
    ax2.set_ylabel("AE hit rate\n(Hz)")
    ax2.set_xlabel("Test-relative time (s)")

    for row in states.itertuples():
        for ax in axes:
            ax.axvspan(row.time_start_s, row.time_end_s, color="#9ecae1", alpha=0.18, lw=0)
        ax0.text(
            0.5 * (row.time_start_s + row.time_end_s),
            ax0.get_ylim()[1] * 0.88,
            str(row.state_label).replace(" ", "\n"),
            ha="center",
            va="top",
            fontsize=5.8,
            rotation=90,
        )
    for label, ax in zip("abc", axes):
        panel_label(ax, label)
    return save_both(fig, figure_root / "Figure_7_synchronization_audit")


def read_hit_file(hit_file: Path) -> pd.DataFrame:
    with hit_file.open("r", encoding="latin1") as handle:
        lines = handle.readlines()
    header_idx = next(
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("ID") and "SSSS" in line
    )
    columns = lines[header_idx].split()
    sig_idx = columns.index("SIG")
    columns = columns[:sig_idx] + ["SIG-STRENGTH"] + columns[sig_idx + 2 :]
    usecols = ["SSSSSSSS.mmmuuun", "CH", "ABS-ENERGY", "AMP"]
    return pd.read_csv(
        hit_file,
        sep=r"\s+",
        names=columns,
        skiprows=header_idx + 1,
        usecols=usecols,
        engine="python",
    )


def find_column(data: pd.DataFrame, fragments: list[str]) -> str:
    for column in data.columns:
        text = str(column)
        if all(fragment in text for fragment in fragments):
            return column
    raise KeyError(f"Could not find column containing {fragments}")


def graphical_abstract(
    assets: dict[str, Path],
    data: pd.DataFrame,
    figure_root: Path,
) -> list[Path]:
    if cv2 is None:
        raise RuntimeError("OpenCV is required to render the graphical abstract.")
    crop = cv2.cvtColor(cv2.imread(str(assets["crop"])), cv2.COLOR_BGR2RGB)
    overlay = cv2.cvtColor(cv2.imread(str(assets["overlay"])), cv2.COLOR_BGR2RGB)
    crop_img = Image.fromarray(crop)
    overlay_img = Image.fromarray(overlay)
    crop_img.thumbnail((245, 90))
    overlay_img.thumbnail((245, 90))

    fig = plt.figure(figsize=(13.28, 5.31), dpi=100)
    gs = GridSpec(
        2,
        5,
        figure=fig,
        width_ratios=[1.2, 0.32, 1.2, 0.32, 1.45],
        height_ratios=[1, 1],
    )
    ax0 = fig.add_subplot(gs[:, 0])
    ax1 = fig.add_subplot(gs[:, 2])
    ax2 = fig.add_subplot(gs[0, 4])
    ax3 = fig.add_subplot(gs[1, 4])
    arrow1 = fig.add_subplot(gs[:, 1])
    arrow2 = fig.add_subplot(gs[:, 3])

    for ax in [ax0, ax1, arrow1, arrow2]:
        ax.set_axis_off()
    ax0.set_title("Multimodal flow-boiling data", fontsize=18, weight="bold")
    ax0.text(0.5, 0.76, "High-speed images", ha="center", fontsize=13)
    ax0.imshow(crop_img, extent=(0.03, 0.97, 0.48, 0.68))
    ax0.text(0.5, 0.32, "Thermal workbooks + AE hit files", ha="center", fontsize=13)
    ax0.text(
        0.5,
        0.18,
        "heat flux, HTC, voltage windows, AE energy",
        ha="center",
        fontsize=10,
    )

    arrow1.annotate(
        "",
        xy=(0.85, 0.5),
        xytext=(0.15, 0.5),
        arrowprops=dict(arrowstyle="->", lw=3),
    )
    ax1.set_title("BubbleID-Flow", fontsize=18, weight="bold")
    ax1.imshow(overlay_img, extent=(0.03, 0.97, 0.56, 0.77))
    ax1.text(0.5, 0.42, "Mask R-CNN segmentation", ha="center", fontsize=13)
    ax1.text(0.5, 0.28, "projected vapor area", ha="center", fontsize=11)
    ax1.text(0.5, 0.17, "active vapor length", ha="center", fontsize=11)

    arrow2.annotate(
        "",
        xy=(0.85, 0.5),
        xytext=(0.15, 0.5),
        arrowprops=dict(arrowstyle="->", lw=3),
    )

    for case, group in data.groupby("case_label", sort=False):
        color, marker = CASE_STYLE.get(case, ("#333333", "o"))
        group = group.sort_values("state_voltage")
        ax2.plot(
            group["heat_flux_mean_w_cm2"],
            group["vapor_area_fraction_mean"],
            marker=marker,
            lw=1.5,
            color=color,
        )
        ax3.scatter(
            group["vapor_area_fraction_mean"],
            group["ae_abs_energy_rate"].clip(lower=1e-3),
            marker=marker,
            s=30,
            color=color,
            label=case,
        )
    ax2.set_title("Thermal forcing -> vapor coverage", fontsize=14)
    ax2.set_xlabel("Heat flux (W/cm2)")
    ax2.set_ylabel("Vapor area")
    ax3.set_title("Vapor activity + AE signatures", fontsize=14)
    ax3.set_xlabel("Vapor area")
    ax3.set_ylabel("AE energy rate")
    ax3.set_yscale("log")
    ax3.legend(ncol=2, frameon=False, fontsize=8)
    fig.suptitle(
        "Optical, thermal, and acoustic signatures are fused by operating state",
        fontsize=20,
        y=0.98,
    )
    pdf = figure_root / "Graphical_Abstract.pdf"
    png = figure_root / "Graphical_Abstract.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return [pdf, png]


def write_manifest(paths: list[Path], output: Path) -> None:
    lines = ["ATE submission figure manifest", ""]
    all_paths = {path.resolve(): path for path in paths if path.exists()}
    figure_dir = output.parent / "figures"
    if figure_dir.exists():
        for pattern in ("Figure_*.*", "Graphical_Abstract.*"):
            for path in figure_dir.glob(pattern):
                all_paths[path.resolve()] = path
    for path in sorted(all_paths.values(), key=lambda item: item.name):
        if path.exists():
            lines.append(f"{path.name}\t{path.stat().st_size} bytes")
    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
