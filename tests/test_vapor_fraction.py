import numpy as np

from bubbleid_flow.vapor_fraction import streamwise_area_fraction_profile


def test_streamwise_area_fraction_profile_counts_nonzero_pixels():
    mask = np.zeros((2, 4), dtype=np.uint8)
    mask[:, 0] = 255
    mask[0, 2] = 255

    profile = streamwise_area_fraction_profile(mask, bins=2)

    assert profile["bubble_area_px"].tolist() == [2, 1]
    assert profile["total_area_px"].tolist() == [4, 4]
    assert profile["projected_vapor_area_fraction"].tolist() == [0.5, 0.25]
