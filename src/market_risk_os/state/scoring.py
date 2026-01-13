"""Pure scoring functions for risk state computation."""

from typing import List

from ..core import Pressure, PressureInteraction, ensure_01
from ..interactions.graph import compute_ambiguity, compute_instability


def score_instability(
    pressures: List[Pressure],
    interactions: List[PressureInteraction],
) -> float:
    """
    Score instability from interactions and pressures.
    
    Blends interaction instability (60%) with pressure magnitudes (40%).
    Deterministic: same inputs => same outputs.
    
    Args:
        pressures: List of pressures
        interactions: List of pressure interactions
    
    Returns:
        Instability score in [0, 1]. Returns 0.0 if no pressures and no interactions.
    """
    # Compute interaction instability
    interaction_instability = compute_instability(interactions)
    
    # Compute pressure component (mean magnitude)
    if pressures:
        pressure_component = sum(p.magnitude for p in pressures) / len(pressures)
    else:
        pressure_component = 0.0
    pressure_component = ensure_01("pressure_component", pressure_component)
    
    # If no pressures and no interactions, return 0.0
    if not pressures and not interactions:
        return 0.0
    
    # Blend: 60% interaction instability, 40% pressure component
    instability = 0.6 * interaction_instability + 0.4 * pressure_component
    return ensure_01("instability", instability)


def score_ambiguity(interactions: List[PressureInteraction]) -> float:
    """
    Score ambiguity from interactions.
    
    Deterministic: same inputs => same outputs.
    Empty interactions => 0.0
    
    Args:
        interactions: List of pressure interactions
    
    Returns:
        Ambiguity score in [0, 1]
    """
    return compute_ambiguity(interactions)


def score_confidence(
    pressures: List[Pressure],
    interactions: List[PressureInteraction],
) -> float:
    """
    Score confidence from pressures and interactions.
    
    Weighted combination: 70% pressure confidence, 30% interaction confidence.
    Deterministic: same inputs => same outputs.
    
    Args:
        pressures: List of pressures
        interactions: List of pressure interactions
    
    Returns:
        Confidence score in [0, 1]. Missing lists treated as mean 0.0.
    """
    # Compute pressure confidence mean
    if pressures:
        pressure_conf_mean = sum(p.confidence for p in pressures) / len(pressures)
    else:
        pressure_conf_mean = 0.0
    
    # Compute interaction confidence mean
    if interactions:
        interaction_conf_mean = (
            sum(i.confidence for i in interactions) / len(interactions)
        )
    else:
        interaction_conf_mean = 0.0
    
    # Weighted combination: 70% pressure, 30% interaction
    confidence = 0.7 * pressure_conf_mean + 0.3 * interaction_conf_mean
    return ensure_01("confidence", confidence)

