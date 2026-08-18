from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pycocotools.coco import COCO

from bubbleid_flow.baseline import BaselineSegmentationConfig, segment_dark_bubbles
from bubbleid_flow.learned import PixelGaussianModel, fit_pixel_gaussian, predict_mask
from scripts.analyze_segmentation_robustness import frame_sequence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Mask R-CNN coverage with simple and learned pixel baselines."
    )
    parser.add_argument("--train-json", required=True)
    parser.add_argument("--val-json", required=True)
    parser.add_argument("--mask-rcnn-metrics", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=31)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fit_records, calibration_records = sequence_grouped_calibration_split(Path(args.train_json))
    fit_images, fit_masks = load_records(Path(args.train_json), fit_records)
    calibration_images, calibration_masks = load_records(Path(args.train_json), calibration_records)

    base_model = fit_pixel_gaussian(
        fit_images,
        fit_masks,
        threshold=0.5,
        min_area_px=20,
        seed=args.seed,
    )
    thresholds = np.linspace(0.10, 0.90, 17)
    calibration_rows = []
    for threshold in thresholds:
        model = replace(base_model, threshold=float(threshold))
        metrics = evaluate_arrays(calibration_images, calibration_masks, model=model)
        calibration_rows.append({"threshold": threshold, **summarize(metrics)})
    calibration = pd.DataFrame(calibration_rows)
    selected_threshold = float(
        calibration.sort_values(
            ["mean_absolute_area_fraction_error", "mean_union_mask_iou"],
            ascending=[True, False],
        ).iloc[0]["threshold"]
    )
    model = replace(base_model, threshold=selected_threshold)
    model.save(output_dir / "pixel_gaussian_baseline.json")
    calibration.to_csv(output_dir / "pixel_gaussian_calibration_sweep.csv", index=False)

    val_images, val_masks, val_names = load_coco(Path(args.val_json))
    learned = evaluate_arrays(val_images, val_masks, model=model, names=val_names)
    simple = evaluate_simple(val_images, val_masks, val_names)
    learned["method"] = "Pixel Gaussian"
    simple["method"] = "Otsu morphology"

    mask_rcnn = pd.read_csv(args.mask_rcnn_metrics).copy()
    mask_rcnn = mask_rcnn.rename(
        columns={
            "file_name": "image_name",
            "ground_truth_vapor_area_fraction": "ground_truth_area_fraction",
            "predicted_vapor_area_fraction": "predicted_area_fraction",
        }
    )
    mask_rcnn["method"] = "Mask R-CNN"
    required = [
        "method",
        "image_name",
        "ground_truth_area_fraction",
        "predicted_area_fraction",
        "signed_area_fraction_error",
        "absolute_area_fraction_error",
        "union_mask_iou",
        "union_mask_dice",
    ]
    by_image = pd.concat([simple[required], learned[required], mask_rcnn[required]], ignore_index=True)
    by_image.to_csv(output_dir / "segmentation_baselines_by_image.csv", index=False)

    summary_rows = []
    for method, group in by_image.groupby("method", sort=False):
        summary_rows.append({"method": method, **summarize(group)})
    summary = pd.DataFrame(summary_rows)
    summary["training_images"] = summary["method"].map(
        {"Otsu morphology": 0, "Pixel Gaussian": len(fit_records), "Mask R-CNN": 104}
    )
    summary["calibration_images"] = summary["method"].map(
        {"Otsu morphology": 0, "Pixel Gaussian": len(calibration_records), "Mask R-CNN": 0}
    )
    summary["holdout_images"] = len(val_images)
    summary.to_csv(output_dir / "segmentation_baseline_summary.csv", index=False)
    make_figure(summary, by_image, output_dir)

    manifest = {
        "split": "same-sequence internal holdout",
        "fit_images": len(fit_records),
        "calibration_images": len(calibration_records),
        "holdout_images": len(val_images),
        "calibration_grouping": "every fifth sorted source-sequence index from training only",
        "selected_pixel_gaussian_threshold": selected_threshold,
        "selection_metric": "minimum calibration projected-area MAE, IoU tie-break",
    }
    (output_dir / "segmentation_baseline_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(summary.to_string(index=False))


def sequence_grouped_calibration_split(train_json: Path) -> tuple[list[dict], list[dict]]:
    records = json.loads(train_json.read_text(encoding="utf-8"))["images"]
    sequences = sorted({frame_sequence(record["file_name"]) for record in records})
    calibration_sequences = set(sequences[4::5])
    calibration = [
        record for record in records if frame_sequence(record["file_name"]) in calibration_sequences
    ]
    fit = [record for record in records if record not in calibration]
    if not fit or not calibration:
        raise ValueError("Training records could not be divided into fit and calibration subsets")
    return fit, calibration


def load_records(coco_json: Path, records: list[dict]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    coco = COCO(str(coco_json))
    images = []
    masks = []
    for record in records:
        image = cv2.imread(record["file_name"], cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"Could not read {record['file_name']}")
        images.append(image.astype(np.float32) / 255.0)
        masks.append(union_mask(coco, int(record["id"])))
    return images, masks


def load_coco(coco_json: Path) -> tuple[list[np.ndarray], list[np.ndarray], list[str]]:
    coco = COCO(str(coco_json))
    records = coco.loadImgs(sorted(coco.getImgIds()))
    images, masks = load_records(coco_json, records)
    return images, masks, [Path(record["file_name"]).name for record in records]


def union_mask(coco: COCO, image_id: int) -> np.ndarray:
    record = coco.loadImgs([image_id])[0]
    mask = np.zeros((record["height"], record["width"]), dtype=bool)
    for annotation in coco.loadAnns(coco.getAnnIds(imgIds=[image_id])):
        mask |= coco.annToMask(annotation).astype(bool)
    return mask


def evaluate_arrays(
    images: list[np.ndarray],
    targets: list[np.ndarray],
    *,
    model: PixelGaussianModel,
    names: list[str] | None = None,
) -> pd.DataFrame:
    predictions = [predict_mask(image, model) for image in images]
    return score_predictions(predictions, targets, names)


def evaluate_simple(
    images: list[np.ndarray], targets: list[np.ndarray], names: list[str]
) -> pd.DataFrame:
    config = BaselineSegmentationConfig()
    predictions = []
    for image in images:
        bgr = cv2.cvtColor(np.round(image * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        mask, _ = segment_dark_bubbles(bgr, config)
        predictions.append(mask > 0)
    return score_predictions(predictions, targets, names)


def score_predictions(
    predictions: list[np.ndarray],
    targets: list[np.ndarray],
    names: list[str] | None,
) -> pd.DataFrame:
    rows = []
    for index, (prediction, target) in enumerate(zip(predictions, targets, strict=True)):
        prediction = prediction.astype(bool)
        target = target.astype(bool)
        intersection = int(np.count_nonzero(prediction & target))
        union = int(np.count_nonzero(prediction | target))
        pred_area = int(np.count_nonzero(prediction))
        target_area = int(np.count_nonzero(target))
        denominator = pred_area + target_area
        pred_fraction = pred_area / target.size
        target_fraction = target_area / target.size
        error = pred_fraction - target_fraction
        rows.append(
            {
                "image_name": names[index] if names else str(index),
                "ground_truth_area_fraction": target_fraction,
                "predicted_area_fraction": pred_fraction,
                "signed_area_fraction_error": error,
                "absolute_area_fraction_error": abs(error),
                "union_mask_iou": intersection / union if union else 1.0,
                "union_mask_dice": 2 * intersection / denominator if denominator else 1.0,
            }
        )
    return pd.DataFrame(rows)


def summarize(frame: pd.DataFrame) -> dict[str, float | int]:
    return {
        "images": int(len(frame)),
        "mean_union_mask_iou": float(frame["union_mask_iou"].mean()),
        "mean_union_mask_dice": float(frame["union_mask_dice"].mean()),
        "mean_absolute_area_fraction_error": float(
            frame["absolute_area_fraction_error"].mean()
        ),
        "mean_signed_area_fraction_error": float(frame["signed_area_fraction_error"].mean()),
    }


def make_figure(summary: pd.DataFrame, by_image: pd.DataFrame, output_dir: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 10,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
            "axes.edgecolor": "black",
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
            "mathtext.bf": "Arial:bold",
            "savefig.dpi": 300,
        }
    )
    colors = {"Otsu morphology": "#999999", "Pixel Gaussian": "#009E73", "Mask R-CNN": "#0072B2"}
    order = ["Otsu morphology", "Pixel Gaussian", "Mask R-CNN"]
    ordered = summary.set_index("method").loc[order]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55), constrained_layout=True)
    axes[0].bar(order, ordered["mean_union_mask_iou"], color=[colors[item] for item in order])
    axes[0].set(ylabel="Mean union-mask IoU", ylim=(0, 1))
    axes[1].bar(order, ordered["mean_union_mask_dice"], color=[colors[item] for item in order])
    axes[1].set(ylabel="Mean union-mask Dice", ylim=(0, 1))
    axes[2].bar(
        order,
        ordered["mean_absolute_area_fraction_error"],
        color=[colors[item] for item in order],
    )
    axes[2].set(ylabel="Projected-area-fraction MAE", ylim=(0, None))
    for label, axis in zip("abc", axes, strict=True):
        axis.text(0.0, 1.04, f"({label})", transform=axis.transAxes, va="bottom", clip_on=False)
        axis.tick_params(axis="x", labelrotation=25)
        axis.tick_params(direction="in", top=True, right=True)
        axis.grid(False)
        for spine in axis.spines.values():
            spine.set_visible(True)
            spine.set_color("black")
        for tick in axis.get_xticklabels():
            tick.set_horizontalalignment("right")
    for suffix in ("pdf", "png"):
        fig.savefig(output_dir / f"Figure_segmentation_baselines.{suffix}", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
