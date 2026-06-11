from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor

from bubbleid_flow.preprocess import crop_array, parse_roi
from bubbleid_flow.vapor_fraction import streamwise_area_fraction_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot projected vapor area fraction along the flow direction."
    )
    parser.add_argument("image_path")
    parser.add_argument("output_dir")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--roi", required=True, help="Crop as x,y,width,height.")
    parser.add_argument("--bins", type=int, default=64)
    parser.add_argument("--score-threshold", type=float, default=0.3)
    parser.add_argument("--pixel-size-mm", type=float, default=None)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    roi = parse_roi(args.roi)
    cropped = crop_array(image, roi)
    predictor = DefaultPredictor(_build_cfg(args.weights, args.score_threshold, args.device))
    outputs = predictor(cropped)
    instances = outputs["instances"].to("cpu")
    masks = instances.pred_masks.numpy() if instances.has("pred_masks") else np.empty((0, *cropped.shape[:2]))
    combined = np.any(masks, axis=0).astype(np.uint8) * 255 if len(masks) else np.zeros(cropped.shape[:2], dtype=np.uint8)

    profile = streamwise_area_fraction_profile(
        combined,
        bins=args.bins,
        pixel_size_mm=args.pixel_size_mm,
    )

    stem = image_path.stem
    crop_path = output_dir / f"{stem}_roi.png"
    mask_path = output_dir / f"{stem}_mask.png"
    overlay_path = output_dir / f"{stem}_overlay.png"
    csv_path = output_dir / f"{stem}_vapor_fraction_profile.csv"
    plot_path = output_dir / f"{stem}_vapor_fraction_profile.png"

    cv2.imwrite(str(crop_path), cropped)
    cv2.imwrite(str(mask_path), combined)
    cv2.imwrite(str(overlay_path), _overlay_combined_mask(cropped, combined))
    profile.to_csv(csv_path, index=False)
    _plot_profile(profile, plot_path, pixel_size_mm=args.pixel_size_mm)

    print(f"Wrote {csv_path}")
    print(f"Wrote {plot_path}")
    print(f"Wrote {overlay_path}")
    print(f"Mean projected vapor area fraction: {profile['projected_vapor_area_fraction'].mean():.4f}")


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


def _overlay_combined_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    overlay = image.copy()
    red = np.zeros_like(image)
    red[:, :, 2] = 255
    mask_bool = mask > 0
    overlay[mask_bool] = cv2.addWeighted(image, 0.55, red, 0.45, 0)[mask_bool]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 255, 0), 1)
    return overlay


def _plot_profile(profile, plot_path: Path, pixel_size_mm: float | None) -> None:
    x_column = "x_center_mm" if pixel_size_mm is not None else "x_center_px"
    x_label = "Streamwise position, x (mm)" if pixel_size_mm is not None else "Streamwise position, x (px)"

    fig, ax = plt.subplots(figsize=(8, 3.6), constrained_layout=True)
    ax.plot(
        profile[x_column],
        profile["projected_vapor_area_fraction"],
        color="#1664a2",
        linewidth=2.0,
    )
    ax.fill_between(
        profile[x_column],
        profile["projected_vapor_area_fraction"],
        color="#9ecae1",
        alpha=0.35,
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel("Projected vapor area fraction")
    ax.set_ylim(0, max(0.05, min(1.0, profile["projected_vapor_area_fraction"].max() * 1.2)))
    ax.grid(True, color="#d0d0d0", linewidth=0.8, alpha=0.8)
    fig.savefig(plot_path, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
