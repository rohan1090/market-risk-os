"""Deterministic math utilities for pressure computation."""

import math
from collections.abc import Sequence
from typing import Optional


def rolling_mean(values: Sequence[float], window: int) -> float:
    """
    Compute rolling mean over the last window elements.
    
    Args:
        values: Sequence of numeric values
        window: Number of elements to average
    
    Returns:
        Mean of last window elements, or 0.0 if insufficient data
    """
    if not values or window <= 0:
        return 0.0
    
    n = min(len(values), window)
    if n == 0:
        return 0.0
    
    subset = values[-n:]
    result = sum(subset) / n
    
    # Ensure finite
    if not math.isfinite(result):
        return 0.0
    
    return result


def rolling_std(values: Sequence[float], window: int, eps: float = 1e-12) -> float:
    """
    Compute rolling standard deviation over the last window elements.
    
    Args:
        values: Sequence of numeric values
        window: Number of elements to use
        eps: Small epsilon to prevent division by zero
    
    Returns:
        Standard deviation of last window elements, or eps if insufficient data
    """
    if not values or window <= 0:
        return eps
    
    n = min(len(values), window)
    if n < 2:
        return eps
    
    subset = values[-n:]
    mean = sum(subset) / n
    
    variance = sum((x - mean) ** 2 for x in subset) / n
    result = math.sqrt(max(variance, eps))
    
    # Ensure finite
    if not math.isfinite(result):
        return eps
    
    return result


def zscore(x: float, mean: float, std: float, eps: float = 1e-12) -> float:
    """
    Compute z-score: (x - mean) / std.
    
    Args:
        x: Value to standardize
        mean: Mean value
        std: Standard deviation
        eps: Small epsilon to prevent division by zero
    
    Returns:
        Z-score, clamped to reasonable range to prevent overflow
    """
    if not math.isfinite(x) or not math.isfinite(mean) or not math.isfinite(std):
        return 0.0
    
    std_safe = max(abs(std), eps)
    result = (x - mean) / std_safe
    
    # Clamp to prevent extreme values
    result = max(-10.0, min(10.0, result))
    
    return result


def sigmoid(z: float, k: float = 1.0) -> float:
    """
    Compute sigmoid function: 1 / (1 + exp(-k*z)).
    
    Maps real numbers to (0, 1) range.
    
    Args:
        z: Input value
        k: Scaling factor (steepness)
    
    Returns:
        Sigmoid value in (0, 1)
    """
    if not math.isfinite(z) or not math.isfinite(k):
        return 0.5
    
    # Clamp z to prevent overflow
    z_clamped = max(-50.0, min(50.0, z * k))
    
    try:
        result = 1.0 / (1.0 + math.exp(-z_clamped))
    except (OverflowError, ValueError):
        # Fallback for edge cases
        if z_clamped > 0:
            return 1.0
        else:
            return 0.0
    
    # Ensure finite and in range
    if not math.isfinite(result):
        return 0.5
    
    return max(0.0, min(1.0, result))


def squash01_from_z(z: float, k: float = 1.0) -> float:
    """
    Squash z-score to [0, 1] range using sigmoid.
    
    This is a convenience wrapper around sigmoid for z-scores.
    
    Args:
        z: Z-score value
        k: Scaling factor for sigmoid
    
    Returns:
        Value in [0, 1]
    """
    return sigmoid(z, k)


def ema(values: Sequence[float], alpha: float) -> float:
    """
    Compute exponential moving average.
    
    Args:
        values: Sequence of numeric values
        alpha: Smoothing factor in [0, 1] (higher = more weight to recent)
    
    Returns:
        EMA value, or 0.0 if no values
    """
    if not values:
        return 0.0
    
    # Clamp alpha to valid range
    alpha = max(0.0, min(1.0, alpha))
    
    if alpha == 0.0:
        # Degenerate case: return first value
        return values[0] if values else 0.0
    
    if alpha == 1.0:
        # Degenerate case: return last value
        return values[-1] if values else 0.0
    
    # Standard EMA computation
    result = values[0]
    for value in values[1:]:
        if not math.isfinite(value):
            continue
        result = alpha * value + (1.0 - alpha) * result
    
    # Ensure finite
    if not math.isfinite(result):
        return 0.0
    
    return result


def clamp(x: float, lo: float, hi: float) -> float:
    """
    Clamp value to [lo, hi] range.
    
    Args:
        x: Value to clamp
        lo: Lower bound
        hi: Upper bound
    
    Returns:
        Clamped value
    """
    if not math.isfinite(x):
        # NaN or inf -> return midpoint
        return (lo + hi) / 2.0
    else:
        # Finite value -> clamp to range
        return max(lo, min(hi, x))


def acceleration_from_magnitudes(
    curr: float,
    prev: float,
    max_step: float = 1.0,
) -> float:
    """
    Compute acceleration from magnitude change.
    
    Acceleration represents the rate of change in pressure magnitude.
    
    Args:
        curr: Current magnitude value
        prev: Previous magnitude value
        max_step: Maximum expected step size for scaling
    
    Returns:
        Acceleration in [-1, 1] range
    """
    if not math.isfinite(curr) or not math.isfinite(prev):
        return 0.0
    
    if not math.isfinite(max_step) or max_step <= 0:
        max_step = 1.0
    
    # Compute change
    dm = curr - prev
    
    # Scale by max_step and clamp to [-1, 1]
    if max_step > 0:
        scaled = dm / max_step
    else:
        scaled = 0.0
    
    result = clamp(scaled, -1.0, 1.0)
    
    return result


def confidence_from_quality(
    missing_ratio: float,
    staleness_seconds: float,
    stability: float,
    staleness_halflife: float = 300.0,
) -> float:
    """
    Compute confidence score from data quality metrics.
    
    This represents measurement reliability, not prediction accuracy.
    
    Rules:
    - Higher missing_ratio → lower confidence
    - Higher staleness → lower confidence (exponential decay)
    - Higher stability → higher confidence
    
    Args:
        missing_ratio: Ratio of missing data in [0, 1]
        staleness_seconds: Age of data in seconds (≥0)
        stability: Stability metric in [0, 1]
        staleness_halflife: Half-life for staleness decay in seconds
    
    Returns:
        Confidence score in [0, 1]
    """
    # Validate inputs
    missing_ratio = clamp(missing_ratio, 0.0, 1.0)
    staleness_seconds = max(0.0, staleness_seconds)
    stability = clamp(stability, 0.0, 1.0)
    staleness_halflife = max(1.0, staleness_halflife)
    
    # Missing data penalty: linear decrease
    missing_penalty = 1.0 - missing_ratio
    
    # Staleness penalty: exponential decay
    if staleness_seconds > 0 and staleness_halflife > 0:
        staleness_decay = math.exp(-math.log(2.0) * staleness_seconds / staleness_halflife)
    else:
        staleness_decay = 1.0
    
    # Ensure finite
    if not math.isfinite(staleness_decay):
        staleness_decay = 0.0
    
    # Stability boost: linear increase
    stability_boost = stability
    
    # Combine factors (weighted average)
    # Missing and staleness are multiplicative (both must be good)
    # Stability is additive (bonus)
    base_confidence = missing_penalty * staleness_decay
    confidence = base_confidence * 0.7 + stability_boost * 0.3
    
    # Clamp to [0, 1]
    result = clamp(confidence, 0.0, 1.0)
    
    return result

