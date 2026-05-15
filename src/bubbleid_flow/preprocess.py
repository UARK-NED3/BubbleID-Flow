from pathlib import Path

import cv2


def crop_image(image_path: str | Path, roi: tuple[int, int, int, int]):
    """Read an image and crop to (x, y, width, height)."""
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    x, y, width, height = roi
    return image[y : y + height, x : x + width]
