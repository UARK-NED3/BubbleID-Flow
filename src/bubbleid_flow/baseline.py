from dataclasses import dataclass

import cv2
import numpy as np

from bubbleid_flow.preprocess import crop_array


@dataclass(frozen=True)
class BaselineSegmentationConfig:
    """Configuration for a simple dark-feature bubble segmentation baseline."""

    roi: tuple[int, int, int, int] | None = None
    blackhat_kernel: int = 17
    min_area_px: int = 12
    close_kernel: int = 3
    dilate_iterations: int = 1


def segment_dark_bubbles(
    image: np.ndarray, config: BaselineSegmentationConfig
) -> tuple[np.ndarray, np.ndarray]:
    """Segment dark bubble outlines from a bright flow-channel background.

    This is a baseline for inspection and annotation triage. It is not intended
    to replace a fine-tuned instance segmentation model.
    """
    working = crop_array(image, config.roi) if config.roi is not None else image.copy()
    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    kernel_size = _odd_kernel(config.blackhat_kernel)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    enhanced = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)

    _, mask = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    close_size = _odd_kernel(config.close_kernel)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
    if config.dilate_iterations > 0:
        mask = cv2.dilate(mask, close_kernel, iterations=config.dilate_iterations)

    mask = remove_small_components(mask, config.min_area_px)
    overlay = draw_overlay(working, mask)
    return mask, overlay


def remove_small_components(mask: np.ndarray, min_area_px: int) -> np.ndarray:
    """Remove connected components smaller than the requested pixel area."""
    if min_area_px <= 0:
        return mask

    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    clean = np.zeros_like(mask)
    for label in range(1, stats.shape[0]):
        if stats[label, cv2.CC_STAT_AREA] >= min_area_px:
            clean[labels == label] = 255
    return clean


def draw_overlay(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Draw a red transparent mask overlay on a BGR image."""
    color = np.zeros_like(image)
    color[:, :, 2] = mask
    return cv2.addWeighted(image, 0.78, color, 0.22, 0)


def _odd_kernel(value: int) -> int:
    value = max(1, int(value))
    return value if value % 2 == 1 else value + 1
