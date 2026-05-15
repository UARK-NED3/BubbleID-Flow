from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from bubbleid_flow.paths import iter_images


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample frames for manual bubble annotation.")
    parser.add_argument("input_root", help="Prepared or raw image folder")
    parser.add_argument("output_root", help="Folder for sampled annotation frames")
    parser.add_argument("--count", type=int, default=100, help="Number of frames to sample")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    image_paths = iter_images(input_root)
    if not image_paths:
        raise RuntimeError(f"No images found under {input_root}")

    random.seed(args.seed)
    selected = sorted(random.sample(image_paths, min(args.count, len(image_paths))))
    for image_path in selected:
        relative = image_path.relative_to(input_root)
        output_path = output_root / relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, output_path)

    print(f"Copied {len(selected)} frames to {output_root}")


if __name__ == "__main__":
    main()
