from pathlib import Path

import cv2
import numpy as np


def parse_roi(value: str) -> tuple[int, int, int, int]:
    """Parse an ROI string formatted as x,y,width,height."""
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("ROI must be formatted as x,y,width,height")
    return tuple(parts)  # type: ignore[return-value]


def crop_array(image: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Crop an image array to (x, y, width, height)."""
    x, y, width, height = roi
    if width <= 0 or height <= 0:
        raise ValueError("ROI width and height must be positive")
    if x < 0 or y < 0 or x + width > image.shape[1] or y + height > image.shape[0]:
        raise ValueError(f"ROI {roi} is outside image shape {image.shape[:2]}")
    return image[y : y + height, x : x + width]


def crop_image(image_path: str | Path, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Read an image and crop to (x, y, width, height)."""
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    return crop_array(image, roi)
