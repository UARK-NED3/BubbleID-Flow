from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def read_gray(path: str | Path) -> np.ndarray:
    """Read an image as float grayscale in [0, 1]."""
    image = Image.open(path).convert("L")
    return np.asarray(image, dtype=np.float32) / 255.0


def read_rgb_uint8(path: str | Path) -> np.ndarray:
    """Read an image as uint8 RGB."""
    image = Image.open(path).convert("RGB")
    return np.asarray(image, dtype=np.uint8)


def save_gray_mask(path: str | Path, mask: np.ndarray) -> None:
    """Save a boolean or [0, 1] mask as an 8-bit grayscale PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = (mask.astype(np.uint8) * 255) if mask.dtype == bool else np.clip(mask * 255, 0, 255).astype(np.uint8)
    Image.fromarray(out, mode="L").save(path)


def save_rgb(path: str | Path, image: np.ndarray) -> None:
    """Save an RGB uint8 image."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image.astype(np.uint8), mode="RGB").save(path)
