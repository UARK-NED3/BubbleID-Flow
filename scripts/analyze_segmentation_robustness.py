from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pycocotools import mask as mask_utils
from pycocotools.coco import COCO


FRAME_PATTERN = re.compile(r"S(?P<sequence>\d+)", re.IGNORECASE)
COVERAGE_REGIME_BINS = [-np.inf, 0.05, 0.15, np.inf]
COVERAGE_REGIME_LABELS = ["low (<=0.05)", "intermediate (0.05-0.15)", "high (>0.15)"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit BubbleID-Flow holdout robustness from archived COCO predictions."
    )
    parser.add_argument("--train-json", required=True)
    parser.add_argument("--val-json", required=True)
    parser.add_argument("--predictions-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260812)
    parser.add_argument(
        "--score-thresholds", default="0.05,0.10,0.20,0.30,0.40,0.50,0.70"
    )
    parser.add_argument("--detection-caps", default="50,100,200,300")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    thresholds = [float(value) for value in args.score_thresholds.split(",")]
    caps = [int(value) for value in args.detection_caps.split(",")]
    if not thresholds or not caps or min(caps) <= 0:
        raise ValueError("At least one score threshold and positive detection cap are required")

    coco = COCO(args.val_json)
    predictions = json.loads(Path(args.predictions_json).read_text(encoding="utf-8"))
    predictions_by_image: dict[int, list[dict]] = defaultdict(list)
    for prediction in predictions:
        predictions_by_image[int(prediction["image_id"])].append(prediction)
    for image_predictions in predictions_by_image.values():
        image_predictions.sort(key=lambda item: float(item["score"]), reverse=True)

    rows_by_setting = []
    selected_rows = None
    for threshold in thresholds:
        for cap in caps:
            rows = evaluate_setting(coco, predictions_by_image, threshold, cap)
            summary = summarize_metrics(rows)
            summary.update(
                {
                    "score_threshold": threshold,
                    "detection_cap": cap,
                    "images_at_cap": int((rows["predicted_instances"] == cap).sum()),
                }
            )
            rows_by_setting.append(summary)
            if np.isclose(threshold, 0.30) and cap == 300:
                selected_rows = rows

    if selected_rows is None:
        raise ValueError("The required manuscript operating point (threshold 0.30, cap 300) is missing")

    sensitivity = pd.DataFrame(rows_by_setting).sort_values(
        ["detection_cap", "score_threshold"]
    )
    sensitivity.to_csv(output_dir / "segmentation_operating_point_sensitivity.csv", index=False)

    split_audit, split_summary = audit_split_similarity(args.train_json, args.val_json)
    selected_rows = selected_rows.merge(split_audit, on=["image_id", "file_name"], how="left")
    selected_rows.to_csv(output_dir / "segmentation_metrics_by_image.csv", index=False)

    image_groups = build_coverage_group_manifest(coco, selected_rows)
    image_groups.to_csv(output_dir / "segmentation_evaluation_image_groups.csv", index=False)

    regime = summarize_by_regime(selected_rows)
    regime.to_csv(output_dir / "segmentation_metrics_by_coverage_regime.csv", index=False)
    bootstrap = bootstrap_intervals(
        selected_rows, samples=args.bootstrap_samples, seed=args.seed
    )
    operating_point = summarize_metrics(selected_rows)
    robustness_summary = {
        "operating_point": {
            "score_threshold": 0.30,
            "detection_cap": 300,
            **operating_point,
        },
        "bootstrap": {
            "samples": args.bootstrap_samples,
            "seed": args.seed,
            "confidence_level": 0.95,
            "interval_method": "image-level percentile bootstrap",
            "metrics": bootstrap,
        },
        "split_audit": split_summary,
        "interpretation": {
            "supported": "internal same-sequence reconstruction of projected vapor area",
            "not_supported": "experiment-held-out generalization or individual-bubble statistics",
        },
    }
    (output_dir / "segmentation_robustness_summary.json").write_text(
        json.dumps(robustness_summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    make_figure(selected_rows, sensitivity, regime, output_dir)
    print(json.dumps(robustness_summary, indent=2, sort_keys=True))


def evaluate_setting(
    coco: COCO,
    predictions_by_image: dict[int, list[dict]],
    threshold: float,
    cap: int,
) -> pd.DataFrame:
    rows = []
    for image_id in sorted(coco.getImgIds()):
        record = coco.loadImgs([image_id])[0]
        height, width = int(record["height"]), int(record["width"])
        ground_truth = np.zeros((height, width), dtype=bool)
        for annotation in coco.loadAnns(coco.getAnnIds(imgIds=[image_id])):
            ground_truth |= coco.annToMask(annotation).astype(bool)

        retained = [
            item
            for item in predictions_by_image.get(image_id, [])
            if float(item["score"]) >= threshold
        ][:cap]
        predicted = np.zeros((height, width), dtype=bool)
        for item in retained:
            predicted |= mask_utils.decode(item["segmentation"]).astype(bool)

        intersection = int(np.count_nonzero(ground_truth & predicted))
        union = int(np.count_nonzero(ground_truth | predicted))
        ground_truth_area = int(np.count_nonzero(ground_truth))
        predicted_area = int(np.count_nonzero(predicted))
        pixel_count = ground_truth.size
        denominator = ground_truth_area + predicted_area
        rows.append(
            {
                "image_id": image_id,
                "file_name": Path(record["file_name"]).name,
                "ground_truth_vapor_area_fraction": ground_truth_area / pixel_count,
                "predicted_vapor_area_fraction": predicted_area / pixel_count,
                "signed_area_fraction_error": (predicted_area - ground_truth_area)
                / pixel_count,
                "absolute_area_fraction_error": abs(predicted_area - ground_truth_area)
                / pixel_count,
                "union_mask_iou": intersection / union if union else 1.0,
                "union_mask_dice": 2 * intersection / denominator if denominator else 1.0,
                "predicted_instances": len(retained),
            }
        )
    return pd.DataFrame(rows)


def summarize_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    return {
        "images": int(len(frame)),
        "mean_union_mask_iou": float(frame["union_mask_iou"].mean()),
        "median_union_mask_iou": float(frame["union_mask_iou"].median()),
        "mean_union_mask_dice": float(frame["union_mask_dice"].mean()),
        "mean_absolute_area_fraction_error": float(
            frame["absolute_area_fraction_error"].mean()
        ),
        "mean_signed_area_fraction_error": float(
            frame["signed_area_fraction_error"].mean()
        ),
        "max_absolute_area_fraction_error": float(
            frame["absolute_area_fraction_error"].max()
        ),
        "max_predicted_instances": int(frame["predicted_instances"].max()),
    }


def bootstrap_intervals(
    frame: pd.DataFrame, *, samples: int, seed: int
) -> dict[str, dict[str, float]]:
    if samples <= 0:
        raise ValueError("bootstrap-samples must be positive")
    metric_columns = {
        "mean_union_mask_iou": "union_mask_iou",
        "mean_union_mask_dice": "union_mask_dice",
        "mean_absolute_area_fraction_error": "absolute_area_fraction_error",
        "mean_signed_area_fraction_error": "signed_area_fraction_error",
    }
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(frame), size=(samples, len(frame)))
    output = {}
    for name, column in metric_columns.items():
        values = frame[column].to_numpy(dtype=float)
        samples_mean = values[indices].mean(axis=1)
        low, high = np.quantile(samples_mean, [0.025, 0.975])
        output[name] = {
            "estimate": float(values.mean()),
            "ci95_low": float(low),
            "ci95_high": float(high),
        }
    return output


def summarize_by_regime(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.assign(
        coverage_regime=coverage_regimes(frame["ground_truth_vapor_area_fraction"])
    ).groupby("coverage_regime", observed=True)
    rows = []
    for regime, group in grouped:
        rows.append({"coverage_regime": str(regime), **summarize_metrics(group)})
    return pd.DataFrame(rows)


def coverage_regimes(values: pd.Series) -> pd.Categorical:
    return pd.cut(
        values,
        bins=COVERAGE_REGIME_BINS,
        labels=COVERAGE_REGIME_LABELS,
    )


def build_coverage_group_manifest(coco: COCO, frame: pd.DataFrame) -> pd.DataFrame:
    """Attach original COCO paths and manual-coverage groups to Fig. 5 inputs."""
    records = pd.DataFrame(
        {
            "image_id": [image_id for image_id in sorted(coco.getImgIds())],
            "coco_image_path": [
                (
                    Path(Path(coco.loadImgs([image_id])[0]["file_name"]).parent.name)
                    / Path(coco.loadImgs([image_id])[0]["file_name"]).name
                ).as_posix()
                for image_id in sorted(coco.getImgIds())
            ],
        }
    )
    columns = [
        "image_id",
        "file_name",
        "ground_truth_vapor_area_fraction",
        "predicted_vapor_area_fraction",
        "union_mask_iou",
        "union_mask_dice",
        "absolute_area_fraction_error",
        "predicted_instances",
        "source_sequence_index",
        "same_nominal_frame_in_training",
        "nearest_training_frame_distance",
        "most_similar_training_file",
    ]
    manifest = frame[columns].merge(records, on="image_id", how="left", validate="one_to_one")
    manifest.insert(
        2,
        "coverage_regime",
        coverage_regimes(manifest["ground_truth_vapor_area_fraction"]),
    )
    return manifest.sort_values(
        ["coverage_regime", "ground_truth_vapor_area_fraction", "file_name"],
        kind="stable",
    ).reset_index(drop=True)


def audit_split_similarity(train_json: str, val_json: str) -> tuple[pd.DataFrame, dict]:
    train_records = json.loads(Path(train_json).read_text(encoding="utf-8"))["images"]
    val_records = json.loads(Path(val_json).read_text(encoding="utf-8"))["images"]
    train_images = [(record, load_gray(record["file_name"])) for record in train_records]
    train_sequence = [frame_sequence(record["file_name"]) for record, _ in train_images]
    rows = []
    for record in val_records:
        val_image = load_gray(record["file_name"])
        val_sequence = frame_sequence(record["file_name"])
        best = None
        for (train_record, train_image), sequence in zip(train_images, train_sequence):
            correlation, normalized_mae = image_similarity(val_image, train_image)
            candidate = (correlation, -normalized_mae, train_record, sequence, normalized_mae)
            if best is None or candidate[:2] > best[:2]:
                best = candidate
        assert best is not None
        correlation, _, nearest_record, nearest_sequence, normalized_mae = best
        same_nominal = any(sequence == val_sequence for sequence in train_sequence)
        min_distance = min(abs(sequence - val_sequence) for sequence in train_sequence)
        rows.append(
            {
                "image_id": int(record["id"]),
                "file_name": Path(record["file_name"]).name,
                "source_sequence_index": val_sequence,
                "same_nominal_frame_in_training": bool(same_nominal),
                "nearest_training_frame_distance": int(min_distance),
                "most_similar_training_file": Path(nearest_record["file_name"]).name,
                "nearest_training_image_correlation": float(correlation),
                "nearest_training_normalized_mae": float(normalized_mae),
            }
        )
    frame = pd.DataFrame(rows)
    summary = {
        "train_images": len(train_records),
        "holdout_images": len(val_records),
        "distinct_camera_prefixes": 1,
        "holdout_with_same_nominal_frame_in_training": int(
            frame["same_nominal_frame_in_training"].sum()
        ),
        "holdout_with_training_frame_within_one_index": int(
            (frame["nearest_training_frame_distance"] <= 1).sum()
        ),
        "median_nearest_training_frame_distance": float(
            frame["nearest_training_frame_distance"].median()
        ),
        "median_nearest_training_image_correlation": float(
            frame["nearest_training_image_correlation"].median()
        ),
        "split_classification": "same-sequence internal holdout",
    }
    return frame, summary


def frame_sequence(path: str) -> int:
    match = FRAME_PATTERN.search(Path(path).stem)
    if not match:
        raise ValueError(f"Could not parse source sequence from {path}")
    return int(match.group("sequence"))


def load_gray(path: str) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Could not read image {path}")
    return cv2.resize(image, (256, 32), interpolation=cv2.INTER_AREA).astype(np.float32)


def image_similarity(first: np.ndarray, second: np.ndarray) -> tuple[float, float]:
    first_flat = first.ravel()
    second_flat = second.ravel()
    if np.std(first_flat) == 0 or np.std(second_flat) == 0:
        correlation = float(first_flat.mean() == second_flat.mean())
    else:
        correlation = float(np.corrcoef(first_flat, second_flat)[0, 1])
    normalized_mae = float(np.mean(np.abs(first - second)) / 255.0)
    return correlation, normalized_mae


def make_figure(
    frame: pd.DataFrame,
    sensitivity: pd.DataFrame,
    regime: pd.DataFrame,
    output_dir: Path,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 10,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.linewidth": 0.8,
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
            "mathtext.bf": "Arial:bold",
            "savefig.dpi": 300,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), constrained_layout=True)
    blue, orange, green = "#0072B2", "#D55E00", "#009E73"

    ax = axes[0, 0]
    x = frame["ground_truth_vapor_area_fraction"]
    y = frame["predicted_vapor_area_fraction"]
    limit = max(float(x.max()), float(y.max())) * 1.08
    ax.scatter(x, y, color=blue, edgecolor="white", linewidth=0.5, s=28)
    ax.plot([0, limit], [0, limit], color="black", linewidth=1, linestyle="--")
    ax.set(xlabel="Manual projected vapor coverage", ylabel="Predicted projected vapor coverage", xlim=(0, limit), ylim=(0, limit))

    ax = axes[0, 1]
    ax.scatter(x, frame["union_mask_iou"], color=green, edgecolor="white", linewidth=0.5, s=28)
    ax.set(xlabel="Manual projected vapor coverage", ylabel="Union-mask IoU", ylim=(0, 1))

    cap300 = sensitivity[sensitivity["detection_cap"] == 300]
    ax = axes[1, 0]
    ax.plot(cap300["score_threshold"], cap300["mean_union_mask_iou"], marker="o", color=blue, linestyle="--", label="Mean IoU")
    ax.plot(cap300["score_threshold"], cap300["mean_union_mask_dice"], marker="s", color=green, linestyle="--", label="Mean Dice")
    ax.axvline(0.30, color="black", linestyle="--", linewidth=0.9)
    ax.set(xlabel="Score threshold", ylabel="Overlap metric", ylim=(0, 1))
    ax.legend(frameon=False, loc="lower right")

    ax = axes[1, 1]
    ax.plot(cap300["score_threshold"], cap300["mean_absolute_area_fraction_error"], marker="o", color=orange, linestyle="--", label="MAE")
    ax.plot(cap300["score_threshold"], np.abs(cap300["mean_signed_area_fraction_error"]), marker="s", color=blue, linestyle="--", label="Absolute bias")
    ax.axvline(0.30, color="black", linestyle="--", linewidth=0.9)
    ax.set(xlabel="Score threshold", ylabel="Projected-area-fraction error", ylim=(0, None))
    ax.legend(
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.28),
        ncol=2,
    )

    for label, ax in zip("abcd", axes.ravel()):
        ax.text(0.0, 1.04, f"({label})", transform=ax.transAxes, va="bottom", clip_on=False)
        ax.tick_params(direction="in", top=True, right=True)
        ax.grid(False)

    for suffix in ("pdf", "png"):
        fig.savefig(output_dir / f"Figure_5_segmentation_robustness.{suffix}", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
