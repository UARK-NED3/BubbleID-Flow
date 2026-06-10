from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import ColorMode, Visualizer

from bubbleid_flow.paths import iter_images
from bubbleid_flow.preprocess import crop_array, parse_roi
from bubbleid_flow.progress import progress


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict bubble instance masks with a trained Mask R-CNN.")
    parser.add_argument("input_root")
    parser.add_argument("output_root")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--score-threshold", type=float, default=0.5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--roi", default=None, help="Optional crop as x,y,width,height before prediction.")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    predictor = DefaultPredictor(_build_cfg(args.weights, args.score_threshold, args.device))
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    roi = parse_roi(args.roi) if args.roi else None
    image_paths = iter_images(input_root)
    if args.limit is not None:
        image_paths = image_paths[: args.limit]

    for image_path in progress(image_paths, desc="Predicting Mask R-CNN bubbles"):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        if roi is not None:
            image = crop_array(image, roi)
        outputs = predictor(image)
        instances = outputs["instances"].to("cpu")
        masks = instances.pred_masks.numpy() if instances.has("pred_masks") else np.empty((0, *image.shape[:2]))
        combined = np.any(masks, axis=0).astype(np.uint8) * 255 if len(masks) else np.zeros(image.shape[:2], dtype=np.uint8)

        relative = image_path.relative_to(input_root).with_suffix(".png")
        mask_path = output_root / "masks" / relative
        overlay_path = output_root / "overlays" / relative
        instances_path = output_root / "instances" / relative
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        instances_path.parent.mkdir(parents=True, exist_ok=True)

        cv2.imwrite(str(mask_path), combined)
        overlay = _overlay_combined_mask(image, combined)
        cv2.imwrite(str(overlay_path), overlay)
        visualizer = Visualizer(image[:, :, ::-1], scale=1.0, instance_mode=ColorMode.IMAGE_BW)
        rendered = visualizer.draw_instance_predictions(instances).get_image()[:, :, ::-1]
        cv2.imwrite(str(instances_path), rendered)


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


if __name__ == "__main__":
    main()
