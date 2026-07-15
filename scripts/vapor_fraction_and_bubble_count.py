from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor

from bubbleid_flow.preprocess import crop_array, parse_roi


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pure data script: Count Bubbles, Clusters, and calculate Total Vapor Fraction into exact custom format."
    )
    parser.add_argument("image_dir", help="Path to the directory containing images.")
    parser.add_argument("output_dir", help="Path to the output directory.")
    parser.add_argument("--weights", required=True, help="Path to model weights (.pth file).")
    parser.add_argument("--roi", required=True, help="Crop as x,y,width,height.")
    parser.add_argument("--score-threshold", type=float, default=0.3, help="Confidence threshold.")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu", help="Device to run inference on.")
    parser.add_argument("--cluster-size-threshold", type=int, default=350, help="Area threshold in pixels to distinguish cluster from single bubble.")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(list(image_dir.glob("*.bmp")))
    if not image_paths:
        raise ValueError(f"No .bmp images found in directory: {image_dir}")

    predictor = DefaultPredictor(_build_cfg(args.weights, args.score_threshold, args.device))
    
    quantity_data = []

    for idx, image_path in enumerate(image_paths):
        print(f"[{idx+1}/{len(image_paths)}] Processing data for {image_path.name}...")
        
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            print(f"Warning: Could not read image {image_path}. Skipping.")
            continue

        roi = parse_roi(args.roi)
        cropped = crop_array(image, roi)
        
        outputs = predictor(cropped)
        instances = outputs["instances"].to("cpu")
        
        # Combine all instance masks into a single binary mask to remove overlapping predictions
        masks = instances.pred_masks.numpy() if instances.has("pred_masks") else np.empty((0, *cropped.shape[:2]))
        combined_mask = np.any(masks, axis=0).astype(np.uint8) * 255 if len(masks) else np.zeros(cropped.shape[:2], dtype=np.uint8)
        
        # Calculate pixel sizes and overall vapor fraction across the entire bounding region
        total_pixel = combined_mask.size
        vapor_pixel = np.count_nonzero(combined_mask)
        vapor_fraction = vapor_pixel / total_pixel if total_pixel > 0 else 0.0

        #Analyze connected regions to separate single bubbles from multi-bubble clusters
        num_labels, labels_im, stats, centroids = cv2.connectedComponentsWithStats(combined_mask)
        
        bubble = 0
        bubble_cluster = 0
        component_details = []

        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area >= args.cluster_size_threshold:
                bubble_cluster += 1
                obj_type = "cluster"
            else:
                bubble += 1
                obj_type = "bubble"
            component_details.append((label, obj_type))

        stem = image_path.stem
        overlay_path = output_dir / f"{stem}_colored_overlay.png"
        overlay_image = _draw_red_purple_components(cropped, labels_im, component_details, centroids)
        cv2.imwrite(str(overlay_path), overlay_image)

        quantity_data.append({
            "frame": image_path.name,
            "bubble": bubble,
            "bubble_cluster": bubble_cluster,
            "total_bubble": bubble + bubble_cluster,
            "vapor_pixel": vapor_pixel,
            "total_pixel": total_pixel,
            "vapor_fraction": round(vapor_fraction, 4)
        })

    # Compile dataset metrics into the final aggregated CSV spreadsheet
    summary_df = pd.DataFrame(quantity_data)
    summary_csv_path = output_dir / "bubble_data_analysis.csv"
    summary_df.to_csv(summary_csv_path, index=False)
    
    print("\n--- Data Processing Complete ---")
    print(f"Saved analytics summary file to: {summary_csv_path}")


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
    cfg.TEST.DETECTIONS_PER_IMAGE = 1500
    cfg.MODEL.ROI_HEADS.NMS_THRESH_TEST = 0.4  # Strict filter threshold to eliminate duplicate detections
    return cfg


def _draw_red_purple_components(image: np.ndarray, labels_im: np.ndarray, component_details: list, centroids: np.ndarray) -> np.ndarray:
    overlay = image.copy().astype(np.float32)
    
    for label, obj_type in component_details:
        comp_mask = labels_im == label
        
        if obj_type == "bubble":
            # Direct pixel blending matrix calculation for pure Red tinting: (0, 0, 255)
            overlay[comp_mask, 0] = overlay[comp_mask, 0] * 0.65  # Blue Channel
            overlay[comp_mask, 1] = overlay[comp_mask, 1] * 0.65  # Green Channel
            overlay[comp_mask, 2] = overlay[comp_mask, 2] * 0.65 + 255 * 0.35  # Red Channel
        else:
            # Direct pixel blending matrix calculation for pure Purple tinting: (255, 0, 128)
            overlay[comp_mask, 0] = overlay[comp_mask, 0] * 0.60 + 255 * 0.40  # Blue Channel
            overlay[comp_mask, 1] = overlay[comp_mask, 1] * 0.60  # Green Channel
            overlay[comp_mask, 2] = overlay[comp_mask, 2] * 0.60 + 128 * 0.40  # Red Channel

    # Convert image mapping data format back to standard integer properties
    overlay = np.clip(overlay, 0, 255).astype(np.uint8)

    # Place alphanumeric ID text stamps right above calculated object centroids
    for label, obj_type in component_details:
        cX = int(centroids[label, 0])
        cY = int(centroids[label, 1])
        
        if not (np.isnan(cX) or np.isnan(cY)):
            text = f"B{label}" if obj_type == "bubble" else f"C{label}"
            cv2.putText(
                overlay, text, (cX - 10, cY + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA
            )
            
    return overlay


if __name__ == "__main__":
    main()
