from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_ACTIVE_COLUMN_THRESHOLD = 0.05


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


def projected_mask_metrics(
    mask: np.ndarray,
    active_column_threshold: float = DEFAULT_ACTIVE_COLUMN_THRESHOLD,
) -> dict[str, float]:
    """Summarize a projected vapor mask into manuscript-scale metrics."""
    if mask.ndim != 2:
        raise ValueError("mask must be a 2D array")
    if not 0 <= active_column_threshold <= 1:
        raise ValueError("active_column_threshold must be between 0 and 1")

    mask_bool = mask > 0
    column_fraction = mask_bool.mean(axis=0)
    active_columns = np.flatnonzero(column_fraction > active_column_threshold)
    vapor_front = float(active_columns.max()) if len(active_columns) else np.nan
    return {
        "vapor_area_fraction": float(mask_bool.mean()),
        "active_length_fraction": float(len(active_columns) / mask.shape[1]),
        "vapor_front_x_px": vapor_front,
    }


def active_length_threshold_sweep(
    mask: np.ndarray,
    thresholds: list[float] | tuple[float, ...],
) -> dict[str, float | str]:
    """Compute active vapor length over a small threshold sweep.

    The sweep preserves enough information to audit whether the active-length
    trend is a property of the masks or an artifact of one column-occupancy
    cutoff.
    """
    if mask.ndim != 2:
        raise ValueError("mask must be a 2D array")
    if not thresholds:
        return {}

    mask_bool = mask > 0
    column_fraction = mask_bool.mean(axis=0)
    values = []
    metrics: dict[str, float | str] = {}
    for threshold in thresholds:
        if not 0 <= threshold <= 1:
            raise ValueError("active-column sensitivity thresholds must be between 0 and 1")
        active_columns = np.flatnonzero(column_fraction > threshold)
        value = float(len(active_columns) / mask.shape[1])
        values.append(value)
        metrics[f"active_length_fraction_thr_{threshold_label(threshold)}"] = value

    metrics["active_length_thresholds_evaluated"] = ";".join(
        f"{threshold:.6g}" for threshold in thresholds
    )
    metrics["active_length_threshold_sensitivity_range"] = (
        float(max(values) - min(values)) if values else np.nan
    )
    return metrics


def threshold_label(threshold: float) -> str:
    """Return a stable numeric threshold label for CSV column names."""
    label = f"{threshold:.6g}".replace("-", "m").replace(".", "p")
    return label
