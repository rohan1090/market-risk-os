"""Pytest fixtures for interaction and state estimation tests."""

from datetime import datetime, timezone
from typing import List

import pytest

from market_risk_os.core import (
    Directionality,
    Pressure,
    PressureID,
    PressureType,
    RiskState,
    RiskStateEnum,
    StateID,
)


# Fixed timestamp for deterministic tests
fixed_now_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def pressures_reinforcing_short():
    """Two pressures with same horizon, compatible directionality, mags >= 0.55."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_0"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.65,
            acceleration=0.3,
            confidence=0.8,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("volatility_SPX_1"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.70,
            acceleration=0.2,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 2",
        ),
    ]


@pytest.fixture
def pressures_conflicting_short():
    """Two pressures with same horizon, opposing directionality, mags >= 0.55."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_0"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.65,
            acceleration=0.3,
            confidence=0.8,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("liquidity_SPX_0"),
            pressure_type=PressureType.LIQUIDITY,
            source_assets=["SPX"],
            directionality=Directionality.NEGATIVE,
            magnitude=0.70,
            acceleration=-0.2,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 2",
        ),
    ]


@pytest.fixture
def pressures_mixed_set():
    """Contains both reinforcing + conflicting candidates + one different-horizon pressure."""
    return [
        # Reinforcing pair (same horizon, compatible directionality, high mags)
        Pressure(
            pressure_id=PressureID("volatility_SPX_0"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.65,
            acceleration=0.3,
            confidence=0.8,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("volatility_SPX_1"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.70,
            acceleration=0.2,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 2",
        ),
        # Conflicting pair (same horizon, opposing directionality, high mags)
        Pressure(
            pressure_id=PressureID("liquidity_SPX_0"),
            pressure_type=PressureType.LIQUIDITY,
            source_assets=["SPX"],
            directionality=Directionality.NEGATIVE,
            magnitude=0.68,
            acceleration=-0.2,
            confidence=0.72,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 3",
        ),
        # Different horizon (should not interact with short_term)
        Pressure(
            pressure_id=PressureID("correlation_SPX_0"),
            pressure_type=PressureType.CORRELATION,
            source_assets=["SPX"],
            directionality=Directionality.NEUTRAL,
            magnitude=0.60,
            acceleration=0.1,
            confidence=0.7,
            detected_at=fixed_now_utc,
            time_horizon="medium_term",
            explanation="Test pressure 4",
        ),
    ]


@pytest.fixture
def pressures_below_threshold():
    """Pressures with mags < 0.55 => should produce no interactions."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_0"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.40,
            acceleration=0.2,
            confidence=0.8,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("liquidity_SPX_0"),
            pressure_type=PressureType.LIQUIDITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.50,
            acceleration=0.1,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Test pressure 2",
        ),
    ]



@pytest.fixture
def pressures_stable_low():
    """Pressures with low magnitudes (<0.30), reasonable confidence."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_stable"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.25,
            acceleration=0.1,
            confidence=0.7,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Stable pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("liquidity_SPX_stable"),
            pressure_type=PressureType.LIQUIDITY,
            source_assets=["SPX"],
            directionality=Directionality.NEUTRAL,
            magnitude=0.20,
            acceleration=0.0,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Stable pressure 2",
        ),
    ]


@pytest.fixture
def pressures_latent_mid():
    """Pressures with mid magnitudes (~0.60), reasonable confidence."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_latent"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.60,
            acceleration=0.3,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Latent pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("correlation_SPX_latent"),
            pressure_type=PressureType.CORRELATION,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.65,
            acceleration=0.2,
            confidence=0.70,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Latent pressure 2",
        ),
    ]


@pytest.fixture
def pressures_stress_high():
    """Pressures with high magnitudes (~0.90), reasonable confidence."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_stress"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.90,
            acceleration=0.5,
            confidence=0.80,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Stress pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("concentration_SPX_stress"),
            pressure_type=PressureType.CONCENTRATION,
            source_assets=["SPX"],
            directionality=Directionality.NEGATIVE,
            magnitude=0.85,
            acceleration=-0.4,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Stress pressure 2",
        ),
    ]


@pytest.fixture
def pressures_direction_up():
    """Strong upward bias pressures, low ambiguity expected."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_up"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.70,
            acceleration=0.3,
            confidence=0.85,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Upward pressure 1",
        ),
        Pressure(
            pressure_id=PressureID("momentum_SPX_up"),
            pressure_type=PressureType.MOMENTUM,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.75,
            acceleration=0.4,
            confidence=0.80,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Upward pressure 2",
        ),
    ]


@pytest.fixture
def pressures_direction_up_low_confidence():
    """Strong upward bias pressures with low confidence -> should yield None directional bias."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_up_low_conf"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.70,
            acceleration=0.3,
            confidence=0.40,  # Low confidence
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Upward pressure 1 (low confidence)",
        ),
        Pressure(
            pressure_id=PressureID("momentum_SPX_up_low_conf"),
            pressure_type=PressureType.MOMENTUM,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.75,
            acceleration=0.4,
            confidence=0.35,  # Low confidence
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Upward pressure 2 (low confidence)",
        ),
    ]


@pytest.fixture
def pressures_direction_conflict():
    """Balanced upward/downward pressures -> should yield 'none' when ambiguity high."""
    return [
        Pressure(
            pressure_id=PressureID("volatility_SPX_up_conflict"),
            pressure_type=PressureType.VOLATILITY,
            source_assets=["SPX"],
            directionality=Directionality.POSITIVE,
            magnitude=0.65,
            acceleration=0.3,
            confidence=0.75,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Upward conflict pressure",
        ),
        Pressure(
            pressure_id=PressureID("liquidity_SPX_down_conflict"),
            pressure_type=PressureType.LIQUIDITY,
            source_assets=["SPX"],
            directionality=Directionality.NEGATIVE,
            magnitude=0.68,
            acceleration=-0.3,
            confidence=0.72,
            detected_at=fixed_now_utc,
            time_horizon="short_term",
            explanation="Downward conflict pressure",
        ),
    ]


def create_previous_state(
    dominant_state: RiskStateEnum,
    timestamp: datetime = None,
) -> RiskState:
    """
    Helper to create a previous_state object with chosen dominant_state.
    
    Args:
        dominant_state: Dominant state enum value
        timestamp: Optional timestamp (defaults to fixed_now_utc)
    
    Returns:
        RiskState object with specified dominant_state
    """
    if timestamp is None:
        timestamp = fixed_now_utc
    
    return RiskState(
        state_id=StateID(f"previous_state_{dominant_state.value}"),
        dominant_state=dominant_state,
        contributing_pressures=[],
        interactions=[],
        instability_score=0.5,  # Default value, not used in hysteresis logic
        directional_bias=None,
        confidence=0.7,
        ambiguity=0.3,
        valid_horizons=["short_term"],
        detected_at=timestamp,
        explanation=f"Previous state: {dominant_state.value}",
    )


def make_risk_state(
    dominant_state: RiskStateEnum,
    instability: float = 0.5,
    ambiguity: float = 0.3,
    confidence: float = 0.7,
    valid_horizons: List[str] = None,
    timestamp: datetime = None,
) -> RiskState:
    """
    Helper to build a RiskState object with specified parameters.
    
    Args:
        dominant_state: Dominant state enum value
        instability: Instability score (default 0.5)
        ambiguity: Ambiguity score (default 0.3)
        confidence: Confidence score (default 0.7)
        valid_horizons: List of valid horizons (default ["short_term"])
        timestamp: Optional timestamp (defaults to fixed_now_utc)
    
    Returns:
        RiskState object with specified parameters
    """
    if timestamp is None:
        timestamp = fixed_now_utc
    if valid_horizons is None:
        valid_horizons = ["short_term"]
    
    return RiskState(
        state_id=StateID(f"state_test_{dominant_state.value}_{int(timestamp.timestamp())}"),
        dominant_state=dominant_state,
        contributing_pressures=[],
        interactions=[],
        instability_score=instability,
        directional_bias=None,
        confidence=confidence,
        ambiguity=ambiguity,
        valid_horizons=valid_horizons,
        detected_at=timestamp,
        explanation=f"Test state: {dominant_state.value}",
    )
