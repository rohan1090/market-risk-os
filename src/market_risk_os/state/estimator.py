"""Risk state estimator with hysteresis state machine."""

from datetime import datetime
from typing import List, Optional

from ..core import (
    Directionality,
    InteractionID,
    Pressure,
    PressureID,
    PressureInteraction,
    RiskState,
    RiskStateEnum,
    StateID,
    ensure_utc,
)
from .scoring import score_ambiguity, score_confidence, score_instability


# Hysteresis thresholds (constants)
STABLE_TO_LATENT = 0.55
LATENT_TO_STABLE = 0.45
LATENT_TO_STRESS = 0.80
STRESS_TO_LATENT = 0.70
TREND_ENTER = 0.35
TREND_EXIT = 0.30

# State mappings (requirement states to existing enum)
# "stable" -> STABLE
# "trend_supported" -> ELEVATED
# "latent_instability" -> UNSTABLE
# "stress" -> CRITICAL


class RiskStateEstimator:
    """Estimates risk state from pressures and interactions with hysteresis."""
    
    def __init__(self):
        """Initialize the risk state estimator."""
        pass
    
    def estimate(
        self,
        symbol: str,
        pressures: List[Pressure],
        interactions: List[PressureInteraction],
        now: datetime,
        previous_state: Optional[RiskState] = None,
    ) -> RiskState:
        """
        Estimate risk state from pressures and interactions with hysteresis.
        
        Args:
            symbol: Asset symbol
            pressures: List of detected pressures
            interactions: List of pressure interactions
            now: Current UTC datetime (will be normalized to UTC)
            previous_state: Optional previous risk state for hysteresis
        
        Returns:
            RiskState model instance
        """
        # Normalize timestamp to UTC
        now_utc = ensure_utc(now)
        
        # Compute scores using pure functions
        instability_score = score_instability(pressures, interactions)
        ambiguity = score_ambiguity(interactions)
        confidence = score_confidence(pressures, interactions)
        
        # Determine dominant state with hysteresis
        dominant_state = self._determine_dominant_state_with_hysteresis(
            instability_score,
            previous_state,
        )
        
        # Calculate directional bias (only if ambiguity low and confidence sufficient)
        directional_bias = self._calculate_directional_bias(
            pressures,
            ambiguity,
            confidence,
        )
        
        # Collect contributing pressures (top 3 by magnitude * confidence)
        contributing_pressures = self._select_contributing_pressures(pressures, n=3)
        
        # Collect interaction IDs (sorted)
        interaction_ids = sorted([i.interaction_id for i in interactions])
        
        # Determine valid horizons
        valid_horizons = self._determine_valid_horizons(pressures)
        
        # Generate state ID
        state_id = StateID(f"state_{symbol}_{now_utc.timestamp()}")
        
        # Generate explanation
        explanation = self._generate_explanation(
            dominant_state,
            instability_score,
            ambiguity,
            contributing_pressures,
            interaction_ids,
        )
        
        return RiskState(
            state_id=state_id,
            dominant_state=dominant_state,
            contributing_pressures=contributing_pressures,
            interactions=interaction_ids,
            instability_score=instability_score,
            directional_bias=directional_bias,
            confidence=confidence,
            ambiguity=ambiguity,
            valid_horizons=valid_horizons,
            detected_at=now_utc,
            explanation=explanation,
        )
    
    def _determine_dominant_state_with_hysteresis(
        self,
        instability_score: float,
        previous_state: Optional[RiskState],
    ) -> RiskStateEnum:
        """
        Determine dominant state using hysteresis to prevent flip-flopping.
        
        Args:
            instability_score: Calculated instability score
            previous_state: Previous risk state (None if first run)
        
        Returns:
            Dominant risk state enum
        """
        if previous_state is None:
            # No previous state: use entry thresholds
            if instability_score < TREND_ENTER:
                return RiskStateEnum.STABLE
            elif instability_score < STABLE_TO_LATENT:
                return RiskStateEnum.ELEVATED  # "trend_supported"
            elif instability_score < LATENT_TO_STRESS:
                return RiskStateEnum.UNSTABLE  # "latent_instability"
            else:
                return RiskStateEnum.CRITICAL  # "stress"
        
        # Hysteresis logic based on previous state
        prev_state = previous_state.dominant_state
        
        if prev_state == RiskStateEnum.STABLE:
            # From stable: remain stable until instability >= STABLE_TO_LATENT
            if instability_score >= STABLE_TO_LATENT:
                return RiskStateEnum.UNSTABLE  # "latent_instability"
            elif instability_score >= TREND_ENTER:
                return RiskStateEnum.ELEVATED  # "trend_supported"
            else:
                return RiskStateEnum.STABLE
        
        elif prev_state == RiskStateEnum.ELEVATED:  # "trend_supported"
            # From trend_supported: exit to stable if < TREND_EXIT, escalate if >= STABLE_TO_LATENT
            if instability_score < TREND_EXIT:
                return RiskStateEnum.STABLE
            elif instability_score >= STABLE_TO_LATENT:
                return RiskStateEnum.UNSTABLE  # "latent_instability"
            else:
                return RiskStateEnum.ELEVATED  # remain in trend_supported
        
        elif prev_state == RiskStateEnum.UNSTABLE:  # "latent_instability"
            # From latent_instability: revert only if <= LATENT_TO_STABLE, escalate if >= LATENT_TO_STRESS
            if instability_score <= LATENT_TO_STABLE:
                return RiskStateEnum.STABLE
            elif instability_score >= LATENT_TO_STRESS:
                return RiskStateEnum.CRITICAL  # "stress"
            else:
                return RiskStateEnum.UNSTABLE  # remain in latent_instability
        
        elif prev_state == RiskStateEnum.CRITICAL:  # "stress"
            # From stress: remain stress until instability <= STRESS_TO_LATENT
            if instability_score <= STRESS_TO_LATENT:
                return RiskStateEnum.UNSTABLE  # "latent_instability"
            else:
                return RiskStateEnum.CRITICAL  # remain in stress
        
        # Fallback (should not reach here, but handle gracefully)
        # Use entry thresholds if previous state is unrecognized
        if instability_score < TREND_ENTER:
            return RiskStateEnum.STABLE
        elif instability_score < STABLE_TO_LATENT:
            return RiskStateEnum.ELEVATED
        elif instability_score < LATENT_TO_STRESS:
            return RiskStateEnum.UNSTABLE
        else:
            return RiskStateEnum.CRITICAL
    
    def _calculate_directional_bias(
        self,
        pressures: List[Pressure],
        ambiguity: float,
        confidence: float,
    ) -> Optional[Directionality]:
        """
        Calculate directional bias only when ambiguity is low and confidence is sufficient.
        
        Args:
            pressures: List of pressures
            ambiguity: Calculated ambiguity score
            confidence: Calculated confidence score
        
        Returns:
            Directional bias (POSITIVE/"up", NEGATIVE/"down", or None/"none")
        """
        # Only compute bias if ambiguity <= 0.35 AND confidence >= 0.50
        if ambiguity > 0.35 or confidence < 0.50:
            return None
        
        if not pressures:
            return None
        
        # Compute weighted direction evidence
        up_weight = sum(
            p.magnitude * p.confidence
            for p in pressures
            if p.directionality == Directionality.POSITIVE
        )
        down_weight = sum(
            p.magnitude * p.confidence
            for p in pressures
            if p.directionality == Directionality.NEGATIVE
        )
        total = up_weight + down_weight
        
        # If total is tiny, return None
        eps = 1e-9
        if total < eps:
            return None
        
        # Compute bias score: (up_weight - down_weight) / total
        bias_score = (up_weight - down_weight) / (total + eps)
        
        # Determine bias based on score
        if bias_score >= 0.25:
            return Directionality.POSITIVE  # "up"
        elif bias_score <= -0.25:
            return Directionality.NEGATIVE  # "down"
        else:
            return None  # "none"
    
    def _select_contributing_pressures(
        self,
        pressures: List[Pressure],
        n: int = 3,
    ) -> List[PressureID]:
        """
        Select top N contributing pressures by (magnitude * confidence).
        
        Args:
            pressures: List of pressures
            n: Number of pressures to select (default 3)
        
        Returns:
            List of pressure IDs, sorted deterministically
        """
        if not pressures:
            return []
        
        # Compute scores: (magnitude * confidence, pressure_id) for deterministic tie-breaking
        scored = [
            (p.magnitude * p.confidence, p.pressure_id)
            for p in pressures
        ]
        
        # Sort by score (descending), then by pressure_id (ascending) for tie-breaking
        scored.sort(key=lambda x: (-x[0], x[1]))
        
        # Take top N
        top_n = scored[:n]
        
        # Return pressure IDs
        return [pressure_id for _, pressure_id in top_n]
    
    def _determine_valid_horizons(self, pressures: List[Pressure]) -> List[str]:
        """
        Determine valid time horizons from pressures.
        
        Args:
            pressures: List of pressures
        
        Returns:
            List of valid horizon strings, sorted. Defaults to ["short_term"] if empty.
        """
        horizons = set()
        for pressure in pressures:
            if pressure.time_horizon:
                horizons.add(pressure.time_horizon)
        
        # Default if none specified
        if not horizons:
            return ["short_term"]
        
        return sorted(list(horizons))
    
    def _generate_explanation(
        self,
        dominant_state: RiskStateEnum,
        instability_score: float,
        ambiguity: float,
        contributing_pressures: List[PressureID],
        interaction_ids: List[InteractionID],
    ) -> str:
        """
        Generate non-prescriptive explanation for the risk state.
        
        Args:
            dominant_state: Dominant risk state
            instability_score: Instability score
            ambiguity: Ambiguity score
            contributing_pressures: List of contributing pressure IDs
            interaction_ids: List of interaction IDs
        
        Returns:
            Explanation string (component-referential, non-prescriptive)
        """
        pressure_ref = (
            f"Contributing pressures: {', '.join(str(p) for p in contributing_pressures[:3])}"
            if contributing_pressures
            else "No contributing pressures"
        )
        interaction_ref = (
            f"Interactions: {len(interaction_ids)}"
            if interaction_ids
            else "No interactions"
        )
        
        return (
            f"Risk state: {dominant_state.value} "
            f"(instability: {instability_score:.2f}, ambiguity: {ambiguity:.2f}). "
            f"{pressure_ref}. {interaction_ref}."
        )
