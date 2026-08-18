from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.analyze_segmentation_robustness import (
    bootstrap_intervals,
    coverage_regimes,
    frame_sequence,
)


def test_frame_sequence_groups_filename_variants() -> None:
    assert frame_sequence("camera_C001H001S0001000090e.png") == 1000090
    assert frame_sequence("camera_C001H001S0001000090(2).png") == 1000090


def test_bootstrap_intervals_are_deterministic() -> None:
    frame = pd.DataFrame(
        {
            "union_mask_iou": [0.2, 0.4, 0.8],
            "union_mask_dice": [0.3, 0.5, 0.9],
            "absolute_area_fraction_error": [0.01, 0.02, 0.03],
            "signed_area_fraction_error": [-0.01, 0.0, 0.03],
        }
    )
    first = bootstrap_intervals(frame, samples=1000, seed=17)
    second = bootstrap_intervals(frame, samples=1000, seed=17)
    assert first == second
    assert np.isclose(first["mean_union_mask_iou"]["estimate"], 0.4666666667)


def test_coverage_regimes_match_the_manuscript_boundaries() -> None:
    groups = coverage_regimes(pd.Series([0.0, 0.05, 0.050001, 0.15, 0.150001]))
    assert list(groups.astype(str)) == [
        "low (<=0.05)",
        "low (<=0.05)",
        "intermediate (0.05-0.15)",
        "intermediate (0.05-0.15)",
        "high (>0.15)",
    ]
