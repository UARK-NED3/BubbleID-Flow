from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from detectron2 import model_zoo
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, build_detection_test_loader
from detectron2.data.datasets import register_coco_instances
from detectron2.engine import DefaultPredictor
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.modeling import build_model
from pycocotools.coco import COCO


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate BubbleID-Flow Mask R-CNN weights on a COCO-format holdout set."
    )
    parser.add_argument("--val-json", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--image-root", default="")
    parser.add_argument("--score-threshold", type=float, default=0.05)
    parser.add_argument(
        "--coverage-score-threshold",
        type=float,
        default=0.30,
        help="Operational score threshold used for combined-mask coverage metrics.",
    )
    parser.add_argument("--detections-per-image", type=int, default=300)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    if args.detections_per_image <= 0:
        raise ValueError("detections-per-image must be positive")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_name = "bubbleid_flow_eval"
    register_coco_instances(dataset_name, {}, args.val_json, args.image_root)
    MetadataCatalog.get(dataset_name).thing_classes = ["bubble"]

    cfg = build_cfg(
        weights=args.weights,
        score_threshold=args.score_threshold,
        detections_per_image=args.detections_per_image,
        device=args.device,
    )
    model = build_model(cfg)
    DetectionCheckpointer(model).load(args.weights)
    evaluator = COCOEvaluator(
        dataset_name,
        tasks=("bbox", "segm"),
        distributed=False,
        output_dir=str(output_dir),
    )
    loader = build_detection_test_loader(cfg, dataset_name)
    results = inference_on_dataset(model, loader, evaluator)

    coverage_cfg = build_cfg(
        weights=args.weights,
        score_threshold=args.coverage_score_threshold,
        detections_per_image=args.detections_per_image,
        device=args.device,
    )
    coverage_rows, coverage_summary = evaluate_union_coverage(
        coco_json=Path(args.val_json),
        predictor=DefaultPredictor(coverage_cfg),
    )
    coverage_rows.to_csv(output_dir / "coverage_metrics_by_image.csv", index=False)
    results["coverage"] = coverage_summary

    result_path = output_dir / "coco_evaluation_results.json"
    result_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "evaluation_config.yaml").write_text(cfg.dump(), encoding="utf-8")
    print(json.dumps(results, indent=2, sort_keys=True))
    print(f"Wrote {result_path}")


def build_cfg(
    *,
    weights: str,
    score_threshold: float,
    detections_per_image: int,
    device: str,
):
    cfg = get_cfg()
    cfg.merge_from_file(
        model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )
    cfg.DATASETS.TEST = ("bubbleid_flow_eval",)
    cfg.DATALOADER.NUM_WORKERS = 0
    cfg.MODEL.WEIGHTS = weights
    cfg.MODEL.DEVICE = device
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_threshold
    cfg.MODEL.ANCHOR_GENERATOR.SIZES = [[8], [16], [32], [64], [128]]
    cfg.INPUT.MIN_SIZE_TEST = 640
    cfg.INPUT.MAX_SIZE_TEST = 900
    cfg.TEST.DETECTIONS_PER_IMAGE = detections_per_image
    return cfg


def evaluate_union_coverage(
    *,
    coco_json: Path,
    predictor: DefaultPredictor,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    coco = COCO(str(coco_json))
    rows = []
    for image_id in sorted(coco.getImgIds()):
        record = coco.loadImgs([image_id])[0]
        image_path = Path(record["file_name"])
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        ground_truth = np.zeros(image.shape[:2], dtype=bool)
        for annotation in coco.loadAnns(coco.getAnnIds(imgIds=[image_id])):
            ground_truth |= coco.annToMask(annotation).astype(bool)

        instances = predictor(image)["instances"].to("cpu")
        masks = (
            instances.pred_masks.numpy()
            if instances.has("pred_masks")
            else np.empty((0, *image.shape[:2]), dtype=bool)
        )
        predicted = np.any(masks, axis=0) if len(masks) else np.zeros(image.shape[:2], dtype=bool)
        intersection = int(np.count_nonzero(ground_truth & predicted))
        union = int(np.count_nonzero(ground_truth | predicted))
        ground_truth_area = int(np.count_nonzero(ground_truth))
        predicted_area = int(np.count_nonzero(predicted))
        pixel_count = ground_truth.size
        iou = intersection / union if union else 1.0
        denominator = ground_truth_area + predicted_area
        dice = 2 * intersection / denominator if denominator else 1.0
        ground_truth_fraction = ground_truth_area / pixel_count
        predicted_fraction = predicted_area / pixel_count
        rows.append(
            {
                "image_id": image_id,
                "file_name": image_path.name,
                "ground_truth_vapor_area_fraction": ground_truth_fraction,
                "predicted_vapor_area_fraction": predicted_fraction,
                "signed_area_fraction_error": predicted_fraction - ground_truth_fraction,
                "absolute_area_fraction_error": abs(predicted_fraction - ground_truth_fraction),
                "union_mask_iou": iou,
                "union_mask_dice": dice,
                "predicted_instances": int(len(instances)),
            }
        )

    frame = pd.DataFrame(rows)
    summary: dict[str, float | int] = {
        "images": int(len(frame)),
        "mean_union_mask_iou": float(frame["union_mask_iou"].mean()),
        "median_union_mask_iou": float(frame["union_mask_iou"].median()),
        "mean_union_mask_dice": float(frame["union_mask_dice"].mean()),
        "mean_absolute_area_fraction_error": float(
            frame["absolute_area_fraction_error"].mean()
        ),
        "mean_signed_area_fraction_error": float(frame["signed_area_fraction_error"].mean()),
        "max_absolute_area_fraction_error": float(frame["absolute_area_fraction_error"].max()),
        "max_predicted_instances": int(frame["predicted_instances"].max()),
    }
    return frame, summary


if __name__ == "__main__":
    main()
