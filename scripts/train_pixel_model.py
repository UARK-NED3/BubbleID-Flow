from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from bubbleid_flow.io import read_gray, read_rgb_uint8, save_gray_mask, save_rgb
from bubbleid_flow.labelme import find_labelme_jsons, read_labelme_record
from bubbleid_flow.learned import (
    fit_pixel_gaussian,
    iou_score,
    overlay_mask,
    predict_mask,
)
from bubbleid_flow.preprocess import parse_roi


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a lightweight pixel model from Labelme masks.")
    parser.add_argument("--annotation-root", action="append", required=True)
    parser.add_argument("--model-out", required=True)
    parser.add_argument("--report-out", required=True)
    parser.add_argument("--examples-out", required=True)
    parser.add_argument("--roi", default=None, help="Optional ROI formatted as x,y,width,height")
    parser.add_argument("--holdout-every", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--min-area-px", type=int, default=20)
    args = parser.parse_args()

    roi = parse_roi(args.roi) if args.roi else None
    json_paths = find_labelme_jsons(args.annotation_root)
    if not json_paths:
        raise RuntimeError("No Labelme JSON files found")

    records = [read_labelme_record(path) for path in json_paths]
    usable = [record for record in records if record.image_path.exists()]
    if len(usable) != len(records):
        print(f"Warning: skipped {len(records) - len(usable)} annotations with missing images")

    train_records = [record for i, record in enumerate(usable) if i % args.holdout_every != 0]
    val_records = [record for i, record in enumerate(usable) if i % args.holdout_every == 0]
    if not val_records:
        val_records = train_records[-1:]
        train_records = train_records[:-1]

    train_images = [read_gray(record.image_path) for record in train_records]
    train_masks = [record.mask for record in train_records]
    model = fit_pixel_gaussian(
        train_images,
        train_masks,
        roi=roi,
        threshold=args.threshold,
        min_area_px=args.min_area_px,
    )
    model.save(args.model_out)

    report_path = Path(args.report_out)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    examples_dir = Path(args.examples_out)
    examples_dir.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["split", "json_path", "image_path", "iou"])
        writer.writeheader()
        for split, split_records in [("train", train_records), ("val", val_records)]:
            for record in split_records:
                gray = read_gray(record.image_path)
                pred = predict_mask(gray, model)
                _, target = _crop_pair(gray, record.mask, roi)
                writer.writerow(
                    {
                        "split": split,
                        "json_path": record.json_path,
                        "image_path": record.image_path,
                        "iou": iou_score(pred, target),
                    }
                )

    for record in val_records[:8]:
        gray = read_gray(record.image_path)
        rgb = read_rgb_uint8(record.image_path)
        pred = predict_mask(gray, model)
        rgb_roi, target = _crop_pair(rgb, record.mask, roi)
        save_rgb(examples_dir / f"{record.image_path.stem}_prediction.png", overlay_mask(rgb_roi, pred))
        save_rgb(examples_dir / f"{record.image_path.stem}_ground_truth.png", overlay_mask(rgb_roi, target))
        save_gray_mask(examples_dir / f"{record.image_path.stem}_mask.png", pred)

    print(f"Trained on {len(train_records)} images; validated on {len(val_records)} images")
    print(f"Saved model to {args.model_out}")
    print(f"Saved report to {args.report_out}")


def _crop_pair(
    image: np.ndarray, mask: np.ndarray, roi: tuple[int, int, int, int] | None
) -> tuple[np.ndarray, np.ndarray]:
    if roi is None:
        return image, mask
    x, y, width, height = roi
    return image[y : y + height, x : x + width], mask[y : y + height, x : x + width]


if __name__ == "__main__":
    main()
