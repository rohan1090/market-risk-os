"""Invariant tests for risk state estimation with hysteresis."""

from datetime import datetime, timezone

import pytest

from market_risk_os.core import Directionality, PressureID, RiskStateEnum
from market_risk_os.interactions.graph import build_interactions
from market_risk_os.state.estimator import (
    LATENT_TO_STABLE,
    LATENT_TO_STRESS,
    STABLE_TO_LATENT,
    STRESS_TO_LATENT,
    TREND_ENTER,
    TREND_EXIT,
    RiskStateEstimator,
)
from tests.conftest import create_previous_state, fixed_now_utc


class TestMinimalState:
    """Test that estimator returns valid state even with empty inputs."""
    
    def test_estimator_returns_valid_risk_state_minimal(self):
        """Test that estimator returns valid RiskState with empty inputs."""
        estimator = RiskStateEstimator()
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=[],
            interactions=[],
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # Verify it's a valid RiskState
        assert risk_state is not None
        assert risk_state.instability_score == 0.0
        assert risk_state.ambiguity == 0.0
        assert 0.0 <= risk_state.confidence <= 1.0
        assert risk_state.dominant_state == RiskStateEnum.STABLE
        
        # Verify serialization
        json_str = risk_state.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # Verify timestamp is timezone-aware UTC
        assert risk_state.detected_at.tzinfo is not None
        assert risk_state.detected_at.tzinfo.utcoffset(risk_state.detected_at).total_seconds() == 0


class TestStateSelectionNoPrevious:
    """Test state selection without previous state (entry thresholds)."""
    
    def test_stable_low_pressures(self, pressures_stable_low):
        """Test that low magnitude pressures yield STABLE or ELEVATED."""
        estimator = RiskStateEstimator()
        interactions = build_interactions(pressures_stable_low)
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures_stable_low,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # Verify instability score is bounded
        assert 0.0 <= risk_state.instability_score <= 1.0
        
        # Deterministic threshold mapping: if instability < TREND_ENTER => STABLE
        if risk_state.instability_score < TREND_ENTER:
            assert risk_state.dominant_state == RiskStateEnum.STABLE
        # If instability >= TREND_ENTER and < STABLE_TO_LATENT => ELEVATED
        elif TREND_ENTER <= risk_state.instability_score < STABLE_TO_LATENT:
            assert risk_state.dominant_state == RiskStateEnum.ELEVATED
        # Should not exceed STABLE_TO_LATENT with low pressures
        assert risk_state.instability_score < STABLE_TO_LATENT
    
    def test_latent_mid_pressures_with_interactions(self, pressures_latent_mid):
        """Test that mid magnitude pressures with interactions yield appropriate state."""
        estimator = RiskStateEstimator()
        interactions = build_interactions(pressures_latent_mid)
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures_latent_mid,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # Verify instability score is bounded
        assert 0.0 <= risk_state.instability_score <= 1.0
        
        # Deterministic threshold mapping (entry thresholds, no previous state)
        if risk_state.instability_score >= LATENT_TO_STRESS:
            assert risk_state.dominant_state == RiskStateEnum.CRITICAL
        elif risk_state.instability_score >= STABLE_TO_LATENT:
            assert risk_state.dominant_state == RiskStateEnum.UNSTABLE
        elif risk_state.instability_score >= TREND_ENTER:
            assert risk_state.dominant_state == RiskStateEnum.ELEVATED
        else:
            assert risk_state.dominant_state == RiskStateEnum.STABLE
    
    def test_stress_high_pressures_with_interactions(self, pressures_stress_high):
        """Test that high magnitude pressures yield high instability state."""
        estimator = RiskStateEstimator()
        interactions = build_interactions(pressures_stress_high)
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures_stress_high,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # Verify instability score is bounded
        assert 0.0 <= risk_state.instability_score <= 1.0
        
        # With high magnitudes, instability should be high (>= STABLE_TO_LATENT)
        # Deterministic threshold mapping (entry thresholds, no previous state)
        assert risk_state.instability_score >= STABLE_TO_LATENT
        # The pressures_stress_high fixture produces instability between STABLE_TO_LATENT and LATENT_TO_STRESS
        # so the state should be UNSTABLE (not CRITICAL, which requires >= LATENT_TO_STRESS)
        assert STABLE_TO_LATENT <= risk_state.instability_score < LATENT_TO_STRESS
        assert risk_state.dominant_state == RiskStateEnum.UNSTABLE


class TestHysteresisLatentToStable:
    """Test hysteresis prevents flip-flopping from latent to stable."""
    
    def test_hysteresis_prevents_flip_flop_latent_to_stable(self):
        """Test that latent state remains even when instability in hysteresis band."""
        from market_risk_os.core import Pressure, PressureType
        
        estimator = RiskStateEstimator()
        
        # Create pressures that yield instability in the hysteresis band
        # Target: LATENT_TO_STABLE (0.45) < instability < STABLE_TO_LATENT (0.55)
        # Using mags=[0.6, 0.6] produces instability ~0.51
        pressures = [
            Pressure(
                pressure_id=PressureID("test_latent_1"),
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.60,
                acceleration=0.3,
                confidence=0.75,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Test pressure 1",
            ),
            Pressure(
                pressure_id=PressureID("test_latent_2"),
                pressure_type=PressureType.CORRELATION,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.60,
                acceleration=0.3,
                confidence=0.75,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Test pressure 2",
            ),
        ]
        interactions = build_interactions(pressures)
        
        # Create previous state as UNSTABLE (latent_instability)
        previous_state = create_previous_state(RiskStateEnum.UNSTABLE)
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=previous_state,
        )
        
        # Assert instability is in the hysteresis band (tight, within 0.05)
        assert LATENT_TO_STABLE < risk_state.instability_score < STABLE_TO_LATENT, \
            f"Instability {risk_state.instability_score:.4f} not in band ({LATENT_TO_STABLE}, {STABLE_TO_LATENT})"
        # With instability in hysteresis band and previous state UNSTABLE, should remain UNSTABLE
        assert risk_state.dominant_state == RiskStateEnum.UNSTABLE
        
        # Test transition: instability <= LATENT_TO_STABLE should transition to STABLE
        # Create pressures that yield very low instability
        low_pressures = [
            Pressure(
                pressure_id=PressureID("test_stable_1"),
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.25,  # Low magnitude (no interactions, so instability = 0.4 * 0.25 = 0.10)
                acceleration=0.1,
                confidence=0.70,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Low pressure",
            ),
        ]
        low_interactions = build_interactions(low_pressures)
        
        risk_state_transition = estimator.estimate(
            symbol="SPX",
            pressures=low_pressures,
            interactions=low_interactions,
            now=fixed_now_utc,
            previous_state=previous_state,
        )
        
        # Assert instability is <= LATENT_TO_STABLE
        assert risk_state_transition.instability_score <= LATENT_TO_STABLE, \
            f"Instability {risk_state_transition.instability_score:.4f} should be <= {LATENT_TO_STABLE}"
        # With instability <= LATENT_TO_STABLE and previous state UNSTABLE, should transition to STABLE
        assert risk_state_transition.dominant_state == RiskStateEnum.STABLE


class TestHysteresisStressDrop:
    """Test hysteresis prevents stress from dropping too quickly."""
    
    def test_hysteresis_prevents_stress_drop(self):
        """Test that stress state remains even when instability in hysteresis band."""
        from market_risk_os.core import Pressure, PressureType
        
        estimator = RiskStateEstimator()
        
        # Create previous state as CRITICAL (stress)
        previous_state = create_previous_state(RiskStateEnum.CRITICAL)
        
        # Create pressures that yield instability in the hysteresis band
        # Target: STRESS_TO_LATENT (0.70) < instability < LATENT_TO_STRESS (0.80)
        # Using mags=[0.8, 0.85] produces instability ~0.7011
        pressures = [
            Pressure(
                pressure_id=PressureID("test_stress_1"),
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.80,
                acceleration=0.4,
                confidence=0.75,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Stress pressure 1",
            ),
            Pressure(
                pressure_id=PressureID("test_stress_2"),
                pressure_type=PressureType.CONCENTRATION,
                source_assets=["SPX"],
                directionality=Directionality.NEGATIVE,
                magnitude=0.85,
                acceleration=0.4,
                confidence=0.75,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Stress pressure 2",
            ),
        ]
        interactions = build_interactions(pressures)
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=previous_state,
        )
        
        # Assert instability is in the hysteresis band (tight, within 0.05)
        assert STRESS_TO_LATENT < risk_state.instability_score < LATENT_TO_STRESS, \
            f"Instability {risk_state.instability_score:.4f} not in band ({STRESS_TO_LATENT}, {LATENT_TO_STRESS})"
        # With instability in hysteresis band and previous state CRITICAL, should remain CRITICAL
        assert risk_state.dominant_state == RiskStateEnum.CRITICAL
        
        # Test transition: instability <= STRESS_TO_LATENT should go to UNSTABLE
        # Using mags=[0.65, 0.65] produces instability ~0.5525 which is <= STRESS_TO_LATENT
        mid_pressures = [
            Pressure(
                pressure_id=PressureID("test_mid_1"),
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.65,  # Mid magnitude
                acceleration=0.3,
                confidence=0.70,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Mid pressure 1",
            ),
            Pressure(
                pressure_id=PressureID("test_mid_2"),
                pressure_type=PressureType.CORRELATION,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.65,  # Mid magnitude
                acceleration=0.3,
                confidence=0.70,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Mid pressure 2",
            ),
        ]
        mid_interactions = build_interactions(mid_pressures)
        
        risk_state_transition = estimator.estimate(
            symbol="SPX",
            pressures=mid_pressures,
            interactions=mid_interactions,
            now=fixed_now_utc,
            previous_state=previous_state,
        )
        
        # Assert instability is <= STRESS_TO_LATENT
        assert risk_state_transition.instability_score <= STRESS_TO_LATENT, \
            f"Instability {risk_state_transition.instability_score:.4f} should be <= {STRESS_TO_LATENT}"
        # With instability <= STRESS_TO_LATENT and previous state CRITICAL, should transition to UNSTABLE
        assert risk_state_transition.dominant_state == RiskStateEnum.UNSTABLE


class TestDirectionalBias:
    """Test directional bias requires low ambiguity and sufficient confidence."""
    
    def test_directional_bias_requires_low_ambiguity(self, pressures_direction_up):
        """Test that directional bias is computed when ambiguity is low."""
        estimator = RiskStateEstimator()
        interactions = []  # No interactions => ambiguity = 0
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures_direction_up,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # With low ambiguity (0.0) and high confidence, should have directional bias
        assert risk_state.ambiguity <= 0.35
        assert risk_state.confidence >= 0.50
        assert risk_state.directional_bias == Directionality.POSITIVE  # "up"
    
    def test_directional_bias_none_when_ambiguity_high(self, pressures_direction_conflict):
        """Test that directional bias is None when ambiguity is high."""
        estimator = RiskStateEstimator()
        interactions = build_interactions(pressures_direction_conflict)
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures_direction_conflict,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # With conflicting pressures and interactions, ambiguity should be high
        # Directional bias should be None when ambiguity > 0.35
        assert risk_state.ambiguity > 0.35
        assert risk_state.directional_bias is None
    
    def test_directional_bias_none_when_confidence_low(self, pressures_direction_up_low_confidence):
        """Test that directional bias is None when confidence is low."""
        estimator = RiskStateEstimator()
        interactions = []  # No interactions => ambiguity = 0
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures_direction_up_low_confidence,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # With low confidence, directional bias should be None even if ambiguity is low
        assert risk_state.confidence < 0.50
        assert risk_state.ambiguity == 0.0  # No interactions => no ambiguity
        assert risk_state.directional_bias is None


class TestContributingPressures:
    """Test that contributing pressures are deterministic top 3."""
    
    def test_contributing_pressures_is_deterministic_top3(self):
        """Test that exactly 3 pressures are returned, sorted by magnitude*confidence."""
        from market_risk_os.core import Pressure, PressureType
        
        estimator = RiskStateEstimator()
        
        # Create 5 pressures with known scores
        pressures = [
            Pressure(
                pressure_id=PressureID("p1"),  # score = 0.5 * 0.8 = 0.40
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.5,
                acceleration=0.2,
                confidence=0.8,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Pressure 1",
            ),
            Pressure(
                pressure_id=PressureID("p2"),  # score = 0.9 * 0.7 = 0.63
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.9,
                acceleration=0.3,
                confidence=0.7,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Pressure 2",
            ),
            Pressure(
                pressure_id=PressureID("p3"),  # score = 0.6 * 0.85 = 0.51
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.6,
                acceleration=0.2,
                confidence=0.85,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Pressure 3",
            ),
            Pressure(
                pressure_id=PressureID("p4"),  # score = 0.4 * 0.9 = 0.36
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.4,
                acceleration=0.1,
                confidence=0.9,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Pressure 4",
            ),
            Pressure(
                pressure_id=PressureID("p5"),  # score = 0.7 * 0.75 = 0.525
                pressure_type=PressureType.VOLATILITY,
                source_assets=["SPX"],
                directionality=Directionality.POSITIVE,
                magnitude=0.7,
                acceleration=0.3,
                confidence=0.75,
                detected_at=fixed_now_utc,
                time_horizon="short_term",
                explanation="Pressure 5",
            ),
        ]
        
        risk_state = estimator.estimate(
            symbol="SPX",
            pressures=pressures,
            interactions=[],
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # Should have exactly 3 contributing pressures
        assert len(risk_state.contributing_pressures) == 3
        
        # Top 3 should be p2 (0.63), p5 (0.525), p3 (0.51)
        expected_top3 = [PressureID("p2"), PressureID("p5"), PressureID("p3")]
        assert risk_state.contributing_pressures == expected_top3


class TestDeterminism:
    """Test that state estimation is deterministic."""
    
    def test_determinism_same_inputs_same_state(self, pressures_mixed_set):
        """Test that same inputs produce same state outputs."""
        estimator = RiskStateEstimator()
        interactions = build_interactions(pressures_mixed_set)
        
        risk_state1 = estimator.estimate(
            symbol="SPX",
            pressures=pressures_mixed_set,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        risk_state2 = estimator.estimate(
            symbol="SPX",
            pressures=pressures_mixed_set,
            interactions=interactions,
            now=fixed_now_utc,
            previous_state=None,
        )
        
        # Compare stable signatures
        assert risk_state1.dominant_state == risk_state2.dominant_state
        assert abs(risk_state1.instability_score - risk_state2.instability_score) < 1e-9
        assert abs(risk_state1.ambiguity - risk_state2.ambiguity) < 1e-9
        assert risk_state1.directional_bias == risk_state2.directional_bias
        assert risk_state1.contributing_pressures == risk_state2.contributing_pressures
        assert risk_state1.interactions == risk_state2.interactions
        
        # Serialization equality (detected_at is fixed via fixed_now_utc, so model_dump should be identical)
        dump1 = risk_state1.model_dump()
        dump2 = risk_state2.model_dump()
        assert dump1 == dump2, "Serialized states should be identical"
