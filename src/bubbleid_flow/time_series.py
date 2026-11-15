from __future__ import annotations

import math

import numpy as np


def integrated_autocorrelation_time(values: np.ndarray) -> float:
    """Estimate the integrated autocorrelation time using the initial positive sequence."""
    series = np.asarray(values, dtype=float)
    series = series[np.isfinite(series)]
    if series.size < 3:
        return 1.0

    centered = series - series.mean()
    variance = float(np.dot(centered, centered))
    if variance <= 0:
        return 1.0

    autocorrelation = np.correlate(centered, centered, mode="full")[series.size - 1 :]
    autocorrelation = autocorrelation / autocorrelation[0]
    positive = []
    for coefficient in autocorrelation[1:]:
        if not np.isfinite(coefficient) or coefficient <= 0:
            break
        positive.append(float(coefficient))

    tau = 1.0 + 2.0 * float(np.sum(positive))
    return float(np.clip(tau, 1.0, series.size))


def effective_sample_size(values: np.ndarray) -> float:
    """Return a dependence-adjusted sample size for a scalar time series."""
    series = np.asarray(values, dtype=float)
    series = series[np.isfinite(series)]
    if series.size == 0:
        return 0.0
    return float(series.size / integrated_autocorrelation_time(series))


def circular_moving_block_bootstrap_mean_interval(
    values: np.ndarray,
    *,
    samples: int = 5000,
    confidence: float = 0.95,
    block_length: int | None = None,
    seed: int = 17,
) -> dict[str, float | int]:
    """Bootstrap a mean while retaining short-range serial dependence."""
    series = np.asarray(values, dtype=float)
    series = series[np.isfinite(series)]
    if series.size == 0:
        raise ValueError("values must contain at least one finite observation")
    if samples <= 0:
        raise ValueError("samples must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie between zero and one")

    tau = integrated_autocorrelation_time(series)
    if block_length is None:
        block_length = max(1, int(math.ceil(tau)))
    block_length = int(np.clip(block_length, 1, series.size))

    rng = np.random.default_rng(seed)
    block_count = int(math.ceil(series.size / block_length))
    starts = rng.integers(0, series.size, size=(samples, block_count))
    offsets = np.arange(block_length, dtype=int)
    indices = (starts[..., None] + offsets) % series.size
    resampled = series[indices.reshape(samples, -1)[:, : series.size]]
    means = resampled.mean(axis=1)
    alpha = (1.0 - confidence) / 2.0

    return {
        "samples": int(samples),
        "block_length": int(block_length),
        "tau_int_frames": float(tau),
        "effective_sample_size": float(series.size / tau),
        "mean": float(series.mean()),
        "lower": float(np.quantile(means, alpha)),
        "upper": float(np.quantile(means, 1.0 - alpha)),
    }
