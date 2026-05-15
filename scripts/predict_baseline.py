from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from bubbleid_flow.baseline import BaselineSegmentationConfig, segment_dark_bubbles
from bubbleid_flow.paths import iter_images
from bubbleid_flow.preprocess import parse_roi
from bubbleid_flow.progress import progress


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline bubble segmentation on images.")
    parser.add_argument("input_root", help="Image folder")
    parser.add_argument("output_root", help="Output folder")
    parser.add_argument("--roi", default=None, help="Optional ROI formatted as x,y,width,height")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of frames")
    parser.add_argument("--blackhat-kernel", type=int, default=17)
    parser.add_argument("--min-area-px", type=int, default=12)
    parser.add_argument("--close-kernel", type=int, default=3)
    parser.add_argument("--dilate-iterations", type=int, default=1)
    args = parser.parse_args()

    roi = parse_roi(args.roi) if args.roi else None
    config = BaselineSegmentationConfig(
        roi=roi,
        blackhat_kernel=args.blackhat_kernel,
        min_area_px=args.min_area_px,
        close_kernel=args.close_kernel,
        dilate_iterations=args.dilate_iterations,
    )

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    image_paths = iter_images(input_root)
    if args.limit is not None:
        image_paths = image_paths[: args.limit]

    for image_path in progress(image_paths, desc="Segmenting images"):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        mask, overlay = segment_dark_bubbles(image, config)
        relative = image_path.relative_to(input_root)
        mask_path = output_root / "masks" / relative.with_suffix(".png")
        overlay_path = output_root / "overlays" / relative.with_suffix(".png")
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(mask_path), mask)
        cv2.imwrite(str(overlay_path), overlay)


if __name__ == "__main__":
    main()
