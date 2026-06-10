from __future__ import annotations

import argparse
from pathlib import Path

from bubbleid_flow.io import read_gray, read_rgb_uint8, save_gray_mask, save_rgb
from bubbleid_flow.learned import PixelGaussianModel, overlay_mask, predict_mask
from bubbleid_flow.paths import iter_images
from bubbleid_flow.progress import progress


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a trained lightweight pixel model on image folders.")
    parser.add_argument("input_root")
    parser.add_argument("output_root")
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    model = PixelGaussianModel.load(args.model)
    image_paths = iter_images(input_root)
    if args.limit is not None:
        image_paths = image_paths[: args.limit]

    for image_path in progress(image_paths, desc="Predicting masks"):
        gray = read_gray(image_path)
        rgb = read_rgb_uint8(image_path)
        pred = predict_mask(gray, model)

        if model.roi is None:
            rgb_roi = rgb
        else:
            x, y, width, height = model.roi
            rgb_roi = rgb[y : y + height, x : x + width]

        relative = image_path.relative_to(input_root).with_suffix(".png")
        save_gray_mask(output_root / "masks" / relative, pred)
        save_rgb(output_root / "overlays" / relative, overlay_mask(rgb_roi, pred))


if __name__ == "__main__":
    main()
