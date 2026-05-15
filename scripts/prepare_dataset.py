from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from bubbleid_flow.paths import iter_images
from bubbleid_flow.preprocess import crop_image, parse_roi
from bubbleid_flow.progress import progress


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop source images into a clean working dataset.")
    parser.add_argument("input_root", help="Raw image folder")
    parser.add_argument("output_root", help="Output folder for cropped images")
    parser.add_argument("--roi", required=True, help="Crop ROI formatted as x,y,width,height")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of frames")
    parser.add_argument("--extension", default=".png", help="Output image extension, e.g. .png or .jpg")
    args = parser.parse_args()

    roi = parse_roi(args.roi)
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    image_paths = iter_images(input_root)
    if args.limit is not None:
        image_paths = image_paths[: args.limit]

    for image_path in progress(image_paths, desc="Cropping images"):
        relative = image_path.relative_to(input_root).with_suffix(args.extension)
        output_path = output_root / relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped = crop_image(image_path, roi)
        if not cv2.imwrite(str(output_path), cropped):
            raise RuntimeError(f"Could not write image: {output_path}")


if __name__ == "__main__":
    main()
