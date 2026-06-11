from __future__ import annotations

import numpy as np
import pandas as pd


def streamwise_area_fraction_profile(
    mask: np.ndarray,
    bins: int,
    pixel_size_mm: float | None = None,
) -> pd.DataFrame:
    """Compute projected vapor area fraction in streamwise x-bins.

    The input mask is interpreted as a 2D projected bubble mask. Nonzero pixels
    are counted as vapor/bubble area.
    """
    if mask.ndim != 2:
        raise ValueError("mask must be a 2D array")
    if bins <= 0:
        raise ValueError("bins must be positive")

    height, width = mask.shape
    edges = np.linspace(0, width, bins + 1, dtype=int)
    rows = []
    mask_bool = mask > 0
    for index, (x0, x1) in enumerate(zip(edges[:-1], edges[1:])):
        if x1 <= x0:
            continue
        bin_mask = mask_bool[:, x0:x1]
        total_area_px = bin_mask.size
        bubble_area_px = int(bin_mask.sum())
        x_center_px = 0.5 * (x0 + x1 - 1)
        row = {
            "bin_index": index,
            "x_start_px": int(x0),
            "x_end_px": int(x1),
            "x_center_px": x_center_px,
            "total_area_px": int(total_area_px),
            "bubble_area_px": bubble_area_px,
            "projected_vapor_area_fraction": bubble_area_px / total_area_px,
        }
        if pixel_size_mm is not None:
            row["x_center_mm"] = x_center_px * pixel_size_mm
        rows.append(row)

    return pd.DataFrame(rows)
