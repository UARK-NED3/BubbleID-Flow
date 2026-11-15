from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WindowSelection:
    data: pd.DataFrame
    block_index: int
    block_count: int
    gap_threshold_s: float
    reason: str


def infer_time_gap_threshold(
    data: pd.DataFrame,
    time_col: str,
    *,
    minimum_gap_s: float = 5.0,
    median_multiplier: float = 5.0,
) -> float:
    """Infer a conservative gap threshold for splitting non-contiguous state windows."""
    times = np.sort(pd.to_numeric(data[time_col], errors="coerce").dropna().to_numpy(dtype=float))
    if len(times) < 2:
        return minimum_gap_s
    diffs = np.diff(times)
    positive = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(positive) == 0:
        return minimum_gap_s
    return float(max(minimum_gap_s, np.median(positive) * median_multiplier))


def split_contiguous_windows(
    selected: pd.DataFrame,
    time_col: str,
    *,
    max_gap_s: float,
) -> list[pd.DataFrame]:
    """Split voltage-selected rows into contiguous time blocks."""
    if selected.empty:
        return []
    ordered = selected.sort_values(time_col).copy()
    times = pd.to_numeric(ordered[time_col], errors="coerce").to_numpy(dtype=float)
    if len(times) == 1:
        return [ordered]
    gaps = np.diff(times)
    block_ids = np.concatenate([[0], np.cumsum(gaps > max_gap_s)])
    return [block.copy() for _, block in ordered.groupby(block_ids, sort=True)]


def choose_operating_window(
    windows: list[pd.DataFrame],
    time_col: str,
    *,
    previous_end_s: float | None = None,
    gap_threshold_s: float = 0.0,
) -> WindowSelection:
    """Choose the largest contiguous block that does not overlap the previous state."""
    if not windows:
        raise ValueError("windows must contain at least one block")

    indexed = list(enumerate(windows))
    if previous_end_s is None:
        candidates = indexed
        reason = "largest_contiguous_block"
    else:
        candidates = [
            (index, window)
            for index, window in indexed
            if float(window[time_col].min()) > previous_end_s
        ]
        reason = "largest_nonoverlapping_contiguous_block"

    if not candidates:
        candidates = indexed
        reason = "fallback_largest_block_overlaps_previous"

    block_index, data = sorted(
        candidates,
        key=lambda item: (-len(item[1]), float(item[1][time_col].min())),
    )[0]
    return WindowSelection(
        data=data,
        block_index=block_index,
        block_count=len(windows),
        gap_threshold_s=gap_threshold_s,
        reason=reason,
    )


def max_internal_gap_s(data: pd.DataFrame, time_col: str) -> float:
    times = np.sort(pd.to_numeric(data[time_col], errors="coerce").dropna().to_numpy(dtype=float))
    if len(times) < 2:
        return 0.0
    return float(np.diff(times).max())
