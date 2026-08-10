from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def parse_roi(roi_str: str) -> list[int]:
    """pass x,y,width,height for croping"""
    return [int(x) for x in roi_str.split(",")]


def polygon_to_mask(img_shape: tuple[int, int], points: list) -> np.ndarray:
    """Labelme JSON-polygon to generate bubble mask using OpenCV"""
    mask = np.zeros(img_shape, dtype=np.uint8)
    pts = np.array(points, dtype=np.int32)
    
    if len(pts) >= 3:
        cv2.fillPoly(mask, [pts], 255)
            
    return mask > 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate labeled Bubble Count and Vapor Fraction from Polygon annotations.")
    parser.add_argument("data_dir", help="Path to folder containing .bmp and .json files side by side.")
    parser.add_argument("--roi", required=True, help="Crop as x,y,width,height for analysis area.")
    parser.add_argument("--output-dir", default="outputs/gt_analysis", help="Directory to save the final CSV report.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_paths = sorted(list(data_dir.glob("*.json")))
    if not json_paths:
        raise ValueError(f"No .json files found in directory: {data_dir}")

    # ROI pixels area calculation (w * h)
    x, y, w, h = parse_roi(args.roi)
    roi_total_pixels = w * h
    
    csv_rows = []

    print(f"\n--- Starting Vapor Fraction & Bubble Count Analysis on {len(json_paths)} Frames ---")
    print(f"Analysis ROI Area: {w}x{h} = {roi_total_pixels} pixels\n" + "-"*60)

    for idx, json_path in enumerate(json_paths):
        image_path = data_dir / f"{json_path.stem}.bmp"
        if not image_path.exists():
            print(f"Warning: Image file {image_path.name} not found. Skipping.")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            label_data = json.load(f)
            
        img_shape = (label_data["imageHeight"], label_data["imageWidth"])
        
        bubble_count_in_roi = 0
        merged_bubble_mask_full = np.zeros(img_shape, dtype=np.uint8)
        
        # (2 class to one single class automatically)
        for shape in label_data["shapes"]:
            points = shape["points"]
            
            # Generate only polygon mask
            single_obj_mask = polygon_to_mask(img_shape, points)
            
            # Check the position of object is in ROI or not
            cropped_single_obj = single_obj_mask[y:y+h, x:x+w]
            
            if np.sum(cropped_single_obj) > 0:
                bubble_count_in_roi += 1
                merged_bubble_mask_full[single_obj_mask] = 255
                
        # Crop roi
        cropped_bubble_mask = merged_bubble_mask_full[y:y+h, x:x+w]
        
        #  Vapor pixel Area calculation
        vapor_pixel_area = np.sum(cropped_bubble_mask > 0)
        
        # Vapor Fraction: (bubble area / ROI area)
        vapor_fraction = (vapor_pixel_area / roi_total_pixels) if roi_total_pixels > 0 else 0.0
        
        # print the quantity to terminal
        print(f"[{idx+1}/{len(json_paths)}] Frame: {image_path.name}")
        print(f"  Total Bubbles in ROI : {bubble_count_in_roi}")
        print(f"  Vapor Pixel Area     : {vapor_pixel_area} px")
        print(f"  Vapor Fraction       : {round(vapor_fraction, 4)}")
        print("-" * 60)
        
        # Creating CSV-file 
        csv_rows.append({
            "frame": image_path.name,
            "total_bubble": bubble_count_in_roi,
            "vapor pixel area (px)": vapor_pixel_area,
            "vapor_fraction": round(vapor_fraction, 4)
        })

    if csv_rows:
        df = pd.DataFrame(csv_rows)
        csv_output_path = output_dir / "ground_truth.csv"
        df.to_csv(csv_output_path, index=False)
        print(f"\n[SUCCESS] Analysis complete! All individual frame metrics saved to: {csv_output_path}\n")


if __name__ == "__main__":
    main()
