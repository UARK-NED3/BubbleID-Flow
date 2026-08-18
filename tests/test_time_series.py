import numpy as np

from bubbleid_flow.time_series import (
    circular_moving_block_bootstrap_mean_interval,
    effective_sample_size,
    integrated_autocorrelation_time,
)


def test_constant_series_has_unit_autocorrelation_time() -> None:
    values = np.ones(20)
    assert integrated_autocorrelation_time(values) == 1.0
    assert effective_sample_size(values) == 20.0


def test_positive_serial_dependence_reduces_effective_sample_size() -> None:
    values = np.repeat(np.arange(10, dtype=float), 8)
    assert integrated_autocorrelation_time(values) > 1.0
    assert effective_sample_size(values) < len(values)


def test_moving_block_bootstrap_is_deterministic_and_contains_mean() -> None:
    values = np.sin(np.linspace(0, 4 * np.pi, 120)) + 0.25
    first = circular_moving_block_bootstrap_mean_interval(values, samples=1000, seed=9)
    second = circular_moving_block_bootstrap_mean_interval(values, samples=1000, seed=9)
    assert first == second
    assert first["lower"] <= first["mean"] <= first["upper"]
    assert first["block_length"] >= 1
