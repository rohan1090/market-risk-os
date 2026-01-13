"""Invariant enforcement helpers for pressure computation."""

import math


def require_finite(name: str, x: float) -> float:
    """
    Require that a value is finite (not NaN or inf).
    
    Args:
        name: Name of the value for error messages
        x: Value to check
    
    Returns:
        The value if finite
    
    Raises:
        ValueError: If value is not finite
    """
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite, got {x}")
    return x


def ensure_01(name: str, x: float) -> float:
    """
    Ensure value is in [0, 1] range and finite.
    
    Clamps to [0, 1] and raises error if NaN or inf.
    
    Args:
        name: Name of the value for error messages
        x: Value to validate
    
    Returns:
        Clamped value in [0, 1]
    
    Raises:
        ValueError: If value is not finite
    """
    require_finite(name, x)
    return max(0.0, min(1.0, x))


def ensure_m11(name: str, x: float) -> float:
    """
    Ensure value is in [-1, 1] range and finite.
    
    Clamps to [-1, 1] and raises error if NaN or inf.
    
    Args:
        name: Name of the value for error messages
        x: Value to validate
    
    Returns:
        Clamped value in [-1, 1]
    
    Raises:
        ValueError: If value is not finite
    """
    require_finite(name, x)
    return max(-1.0, min(1.0, x))

