from __future__ import annotations

import pandas as pd

from bubbleid_flow.thermal_windows import (
    choose_operating_window,
    split_contiguous_windows,
)


def test_choose_operating_window_prefers_nonoverlapping_contiguous_block():
    selected = pd.DataFrame(
        {
            "time_s": [10.0, 10.5, 11.0, 100.0, 100.5, 101.0, 101.5],
            "value": [1, 2, 3, 4, 5, 6, 7],
        }
    )

    windows = split_contiguous_windows(selected, "time_s", max_gap_s=5.0)
    choice = choose_operating_window(
        windows,
        "time_s",
        previous_end_s=20.0,
        gap_threshold_s=5.0,
    )

    assert choice.reason == "largest_nonoverlapping_contiguous_block"
    assert choice.block_count == 2
    assert choice.data["time_s"].tolist() == [100.0, 100.5, 101.0, 101.5]


def test_choose_operating_window_reports_fallback_when_every_block_overlaps():
    selected = pd.DataFrame({"time_s": [10.0, 10.5, 100.0], "value": [1, 2, 3]})
    windows = split_contiguous_windows(selected, "time_s", max_gap_s=5.0)

    choice = choose_operating_window(
        windows,
        "time_s",
        previous_end_s=200.0,
        gap_threshold_s=5.0,
    )

    assert choice.reason == "fallback_largest_block_overlaps_previous"
    assert choice.data["time_s"].tolist() == [10.0, 10.5]
