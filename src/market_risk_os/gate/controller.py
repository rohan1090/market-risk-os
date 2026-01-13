"""Behavior gate controller with policy mapping."""

from datetime import datetime, timedelta, timezone
from typing import List

from ..core import (
    BehaviorGate,
    GateID,
    RiskState,
    RiskStateEnum,
    StateID,
    ensure_utc,
)
from ..core.validation import ensure_01
from .policy import get_policy


class BehaviorGateController:
    """Controller for creating behavior gates based on risk state."""
    
    def build_gate(
        self,
        risk_state: RiskState,
        now: datetime,
    ) -> BehaviorGate:
        """
        Build a behavior gate from a risk state.
        
        Args:
            risk_state: Current risk state
            now: Current UTC datetime
            
        Returns:
            BehaviorGate model instance
        """
        # Normalize timestamp to UTC
        now_utc = ensure_utc(now)
        
        # Get policy for dominant state
        policy = get_policy(risk_state.dominant_state)
        allowed_behaviors = policy["allowed"]
        forbidden_behaviors = policy["forbidden"]
        
        # Calculate aggressiveness limit: (1 - instability) * confidence
        base = 1.0 - risk_state.instability_score
        aggressiveness_limit = ensure_01(
            "aggressiveness_limit", base * risk_state.confidence
        )
        
        # Calculate gate confidence: min(state.confidence, 1 - ambiguity)
        gate_confidence = ensure_01(
            "gate_confidence",
            min(risk_state.confidence, 1.0 - risk_state.ambiguity),
        )
        
        # Calculate enforced_until based on valid_horizons
        enforced_until = self._calculate_enforced_until(risk_state.valid_horizons, now_utc)
        
        # Generate deterministic gate_id from state_id
        gate_id = GateID(f"gate_{risk_state.state_id}")
        
        # Generate explanation
        explanation = self._generate_explanation(
            risk_state.dominant_state,
            risk_state.instability_score,
            risk_state.ambiguity,
            gate_confidence,
        )
        
        return BehaviorGate(
            gate_id=gate_id,
            risk_state_id=risk_state.state_id,
            allowed_behaviors=allowed_behaviors,
            forbidden_behaviors=forbidden_behaviors,
            aggressiveness_limit=aggressiveness_limit,
            confidence=gate_confidence,
            enforced_until=enforced_until,
            explanation=explanation,
        )
    
    def _calculate_enforced_until(
        self,
        valid_horizons: List[str],
        now: datetime,
    ) -> datetime:
        """
        Calculate enforced_until timestamp based on valid horizons.
        
        Rules:
        - "intraday" present => now + 6 hours, truncated to hour
        - "short_term" present => now + 1 day
        - else => now + 7 days
        
        Args:
            valid_horizons: List of valid time horizons
            now: Current UTC datetime
            
        Returns:
            UTC datetime for enforcement end
        """
        horizons_lower = [h.lower() for h in valid_horizons]
        
        if "intraday" in horizons_lower:
            # End of trading session: now + 6 hours, truncated to hour
            enforced = now + timedelta(hours=6)
            # Truncate to hour
            enforced = enforced.replace(minute=0, second=0, microsecond=0)
        elif "short_term" in horizons_lower:
            # Short term: now + 1 day
            enforced = now + timedelta(days=1)
        else:
            # Default: now + 7 days
            enforced = now + timedelta(days=7)
        
        return ensure_utc(enforced)
    
    def _generate_explanation(
        self,
        dominant_state: RiskStateEnum,
        instability_score: float,
        ambiguity: float,
        confidence: float,
    ) -> str:
        """
        Generate non-prescriptive explanation for the gate.
        
        Args:
            dominant_state: Dominant risk state
            instability_score: Instability score
            ambiguity: Ambiguity score
            confidence: Gate confidence
            
        Returns:
            Explanation string (non-prescriptive, no "trade"/"buy"/"sell")
        """
        return (
            f"Behavior constraints for {dominant_state.value} state: "
            f"instability {instability_score:.2f}, ambiguity {ambiguity:.2f}, "
            f"confidence {confidence:.2f}. Behaviors are constrained (not instructed)."
        )
    
    # Backward compatibility: create_gate with gate_id parameter
    def create_gate(
        self,
        risk_state: RiskState,
        gate_id: GateID,
    ) -> BehaviorGate:
        """
        Create a behavior gate (backward compatibility wrapper).
        
        Args:
            risk_state: Current risk state
            gate_id: Unique identifier for this gate (ignored, generated from state_id)
            
        Returns:
            BehaviorGate model instance
        """
        from ..core import utc_now
        
        return self.build_gate(risk_state, utc_now())
