"""Invariant tests for behavior gates."""

from datetime import timedelta

from market_risk_os.core import RiskStateEnum
from market_risk_os.gate import BehaviorGateController
from tests.conftest import fixed_now_utc, make_risk_state


class TestGateExistsForEachState:
    """Test that gates can be built for each risk state."""
    
    def test_gate_exists_for_each_state(self):
        """Test that a gate can be built for each RiskStateEnum state."""
        controller = BehaviorGateController()
        
        for state in [RiskStateEnum.STABLE, RiskStateEnum.ELEVATED, RiskStateEnum.UNSTABLE, RiskStateEnum.CRITICAL]:
            risk_state = make_risk_state(
                dominant_state=state,
                instability=0.5,
                ambiguity=0.3,
                confidence=0.7,
                valid_horizons=["short_term"],
            )
            
            gate = controller.build_gate(risk_state, fixed_now_utc)
            
            assert gate is not None
            assert gate.risk_state_id == risk_state.state_id
            
            # Assert boundedness
            assert 0.0 <= gate.aggressiveness_limit <= 1.0
            assert 0.0 <= gate.confidence <= 1.0
            
            # Assert behavior lists are lists
            assert isinstance(gate.allowed_behaviors, list)
            assert isinstance(gate.forbidden_behaviors, list)
            
            # Assert at least one allowed behavior (policy guarantees this for all states)
            assert len(gate.allowed_behaviors) > 0


class TestNoOverlapAllowedForbidden:
    """Test that allowed and forbidden behaviors don't overlap."""
    
    def test_no_overlap_allowed_forbidden(self):
        """Test that allowed and forbidden behaviors have no overlap."""
        controller = BehaviorGateController()
        
        for state in [RiskStateEnum.STABLE, RiskStateEnum.ELEVATED, RiskStateEnum.UNSTABLE, RiskStateEnum.CRITICAL]:
            risk_state = make_risk_state(
                dominant_state=state,
                instability=0.5,
                ambiguity=0.3,
                confidence=0.7,
                valid_horizons=["short_term"],
            )
            
            gate = controller.build_gate(risk_state, fixed_now_utc)
            
            overlap = set(gate.allowed_behaviors) & set(gate.forbidden_behaviors)
            assert overlap == set(), f"State {state} has overlapping behaviors: {overlap}"


class TestListsSortedAndDeterministic:
    """Test that behavior lists are sorted and deterministic."""
    
    def test_lists_sorted_and_deterministic(self):
        """Test that behavior lists are sorted and identical for same inputs."""
        controller = BehaviorGateController()
        
        risk_state = make_risk_state(
            dominant_state=RiskStateEnum.UNSTABLE,
            instability=0.6,
            ambiguity=0.4,
            confidence=0.8,
            valid_horizons=["short_term"],
        )
        
        gate1 = controller.build_gate(risk_state, fixed_now_utc)
        gate2 = controller.build_gate(risk_state, fixed_now_utc)
        
        # Assert lists are identical
        assert gate1.allowed_behaviors == gate2.allowed_behaviors
        assert gate1.forbidden_behaviors == gate2.forbidden_behaviors
        
        # Assert gate_id is deterministic and has correct prefix
        assert gate1.gate_id == gate2.gate_id
        assert str(gate1.gate_id).startswith("gate_")
        assert gate1.risk_state_id == risk_state.state_id
        
        # Assert lists are sorted (robust to Enum or string behaviors)
        assert gate1.allowed_behaviors == sorted(gate1.allowed_behaviors, key=str)
        assert gate1.forbidden_behaviors == sorted(gate1.forbidden_behaviors, key=str)
        assert gate2.allowed_behaviors == sorted(gate2.allowed_behaviors, key=str)
        assert gate2.forbidden_behaviors == sorted(gate2.forbidden_behaviors, key=str)


class TestAggressivenessLimitBoundedAndMonotonic:
    """Test that aggressiveness limit is bounded and monotonic."""
    
    def test_aggressiveness_limit_bounded_and_monotonic(self):
        """Test that aggressiveness limit is in [0,1] and decreases with instability."""
        controller = BehaviorGateController()
        
        # Low instability
        low_risk_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.2,
            ambiguity=0.2,
            confidence=0.9,
            valid_horizons=["short_term"],
        )
        
        # High instability
        high_risk_state = make_risk_state(
            dominant_state=RiskStateEnum.UNSTABLE,
            instability=0.8,
            ambiguity=0.2,
            confidence=0.9,
            valid_horizons=["short_term"],
        )
        
        gate_low = controller.build_gate(low_risk_state, fixed_now_utc)
        gate_high = controller.build_gate(high_risk_state, fixed_now_utc)
        
        # Assert bounds
        assert 0.0 <= gate_low.aggressiveness_limit <= 1.0
        assert 0.0 <= gate_high.aggressiveness_limit <= 1.0
        
        # Assert monotonicity: low instability => higher aggressiveness
        assert gate_low.aggressiveness_limit > gate_high.aggressiveness_limit, \
            f"Low instability ({low_risk_state.instability_score}) should have higher aggressiveness than high ({high_risk_state.instability_score})"


class TestAggressivenessRespectsConfidence:
    """Test that aggressiveness limit respects confidence."""
    
    def test_aggressiveness_respects_confidence(self):
        """Test that higher confidence yields higher aggressiveness limit."""
        controller = BehaviorGateController()
        
        # Same instability, different confidence
        high_conf_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.5,
            ambiguity=0.2,
            confidence=0.9,
            valid_horizons=["short_term"],
        )
        
        low_conf_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.5,
            ambiguity=0.2,
            confidence=0.4,
            valid_horizons=["short_term"],
        )
        
        gate_high_conf = controller.build_gate(high_conf_state, fixed_now_utc)
        gate_low_conf = controller.build_gate(low_conf_state, fixed_now_utc)
        
        # Higher confidence should yield higher aggressiveness
        assert gate_high_conf.aggressiveness_limit > gate_low_conf.aggressiveness_limit, \
            f"Higher confidence ({high_conf_state.confidence}) should yield higher aggressiveness than lower ({low_conf_state.confidence})"


class TestGateConfidenceDegradesWithAmbiguity:
    """Test that gate confidence degrades with ambiguity."""
    
    def test_gate_confidence_degrades_with_ambiguity(self):
        """Test that higher ambiguity yields lower gate confidence."""
        controller = BehaviorGateController()
        
        # Same confidence, different ambiguity
        low_amb_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.5,
            ambiguity=0.1,
            confidence=0.8,
            valid_horizons=["short_term"],
        )
        
        high_amb_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.5,
            ambiguity=0.6,
            confidence=0.8,
            valid_horizons=["short_term"],
        )
        
        gate_low_amb = controller.build_gate(low_amb_state, fixed_now_utc)
        gate_high_amb = controller.build_gate(high_amb_state, fixed_now_utc)
        
        # Lower ambiguity should yield higher gate confidence
        assert gate_low_amb.confidence > gate_high_amb.confidence, \
            f"Lower ambiguity ({low_amb_state.ambiguity}) should yield higher gate confidence than higher ({high_amb_state.ambiguity})"


class TestEnforcedUntilIsUtcAndInFuture:
    """Test that enforced_until is UTC and in the future."""
    
    def test_enforced_until_is_utc_and_in_future(self):
        """Test that enforced_until is timezone-aware UTC and after now."""
        controller = BehaviorGateController()
        
        risk_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.3,
            ambiguity=0.2,
            confidence=0.8,
            valid_horizons=["short_term"],
        )
        
        gate = controller.build_gate(risk_state, fixed_now_utc)
        
        # Assert timezone-aware UTC
        assert gate.enforced_until.tzinfo is not None
        assert gate.enforced_until.tzinfo.utcoffset(gate.enforced_until).total_seconds() == 0
        
        # Assert in future
        assert gate.enforced_until > fixed_now_utc, \
            f"enforced_until ({gate.enforced_until}) should be after now ({fixed_now_utc})"
    
    def test_enforced_until_horizons(self):
        """Test that enforced_until respects valid horizons."""
        controller = BehaviorGateController()
        now = fixed_now_utc
        
        # Test intraday horizon
        intraday_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.3,
            ambiguity=0.2,
            confidence=0.8,
            valid_horizons=["intraday"],
        )
        gate_intraday = controller.build_gate(intraday_state, now)
        # Should be within 1 day (intraday => 6 hours, truncated to hour)
        assert gate_intraday.enforced_until <= now + timedelta(days=1)
        assert gate_intraday.enforced_until > now
        
        # Test short_term horizon
        short_term_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.3,
            ambiguity=0.2,
            confidence=0.8,
            valid_horizons=["short_term"],
        )
        gate_short = controller.build_gate(short_term_state, now)
        # Should be between 12 and 36 hours (short_term => 1 day)
        assert now + timedelta(hours=12) <= gate_short.enforced_until <= now + timedelta(hours=36)
        
        # Test medium_term (default case)
        medium_term_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.3,
            ambiguity=0.2,
            confidence=0.8,
            valid_horizons=["medium_term"],
        )
        gate_medium = controller.build_gate(medium_term_state, now)
        # Should be between 5 and 9 days (default => 7 days)
        assert now + timedelta(days=5) <= gate_medium.enforced_until <= now + timedelta(days=9)


class TestSerialization:
    """Test that gates can be serialized."""
    
    def test_serialization(self):
        """Test that gate can be serialized to JSON."""
        controller = BehaviorGateController()
        
        risk_state = make_risk_state(
            dominant_state=RiskStateEnum.ELEVATED,
            instability=0.5,
            ambiguity=0.3,
            confidence=0.7,
            valid_horizons=["short_term"],
        )
        
        gate = controller.build_gate(risk_state, fixed_now_utc)
        
        # Serialize to JSON
        json_str = gate.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # Verify it contains expected fields
        assert "gate_id" in json_str
        assert "allowed_behaviors" in json_str
        assert "forbidden_behaviors" in json_str


class TestCriticalMoreRestrictiveThanStable:
    """Test that CRITICAL state is at least as restrictive as STABLE."""
    
    def test_critical_more_restrictive_than_stable(self):
        """Test that CRITICAL gate has fewer allowed and more forbidden behaviors than STABLE."""
        controller = BehaviorGateController()
        
        # Build gates with identical parameters
        stable_state = make_risk_state(
            dominant_state=RiskStateEnum.STABLE,
            instability=0.5,
            ambiguity=0.3,
            confidence=0.7,
            valid_horizons=["short_term"],
        )
        
        critical_state = make_risk_state(
            dominant_state=RiskStateEnum.CRITICAL,
            instability=0.5,
            ambiguity=0.3,
            confidence=0.7,
            valid_horizons=["short_term"],
        )
        
        gate_stable = controller.build_gate(stable_state, fixed_now_utc)
        gate_critical = controller.build_gate(critical_state, fixed_now_utc)
        
        # CRITICAL should be more restrictive: fewer allowed, more forbidden
        assert len(gate_stable.allowed_behaviors) > len(gate_critical.allowed_behaviors), \
            f"STABLE should allow more behaviors ({len(gate_stable.allowed_behaviors)}) than CRITICAL ({len(gate_critical.allowed_behaviors)})"
        assert len(gate_critical.forbidden_behaviors) >= len(gate_stable.forbidden_behaviors), \
            f"CRITICAL should forbid at least as many behaviors ({len(gate_critical.forbidden_behaviors)}) as STABLE ({len(gate_stable.forbidden_behaviors)})"

