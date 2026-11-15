import numpy as np
import pytest

from bubbleid_flow.vapor_fraction import projected_mask_metrics, streamwise_area_fraction_profile


def test_streamwise_area_fraction_profile_counts_nonzero_pixels():
    mask = np.zeros((2, 4), dtype=np.uint8)
    mask[:, 0] = 255
    mask[0, 2] = 255

    profile = streamwise_area_fraction_profile(mask, bins=2)

    assert profile["bubble_area_px"].tolist() == [2, 1]
    assert profile["total_area_px"].tolist() == [4, 4]
    assert profile["projected_vapor_area_fraction"].tolist() == [0.5, 0.25]


def test_projected_mask_metrics_uses_documented_active_column_threshold():
    mask = np.zeros((4, 5), dtype=np.uint8)
    mask[:, 0] = 255
    mask[0, 2] = 255
    mask[0:2, 4] = 255

    metrics = projected_mask_metrics(mask, active_column_threshold=0.30)

    assert metrics["vapor_area_fraction"] == pytest.approx(7 / 20)
    assert metrics["active_length_fraction"] == pytest.approx(2 / 5)
    assert metrics["vapor_front_x_px"] == 4.0


def test_projected_mask_metrics_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="2D"):
        projected_mask_metrics(np.zeros((2, 2, 1), dtype=np.uint8))

    with pytest.raises(ValueError, match="between 0 and 1"):
        projected_mask_metrics(np.zeros((2, 2), dtype=np.uint8), active_column_threshold=1.5)
