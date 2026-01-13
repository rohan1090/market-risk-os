"""Pure interaction generation rules."""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..core import Directionality

from ..core import (
    InteractionID,
    InteractionType,
    Pressure,
    PressureInteraction,
    PressureID,
    ensure_01,
)


# Minimum magnitude threshold for interactions (strict)
MIN_MAG = 0.55


def generate_interactions(pressures: List[Pressure]) -> List[PressureInteraction]:
    """
    Generate interactions between pressures using deterministic rules.
    
    Rules:
    - Only consider pairs with the same time_horizon (strict)
    - Both magnitudes must be >= MIN_MAG (strict)
    - reinforcing: compatible directionality (both NEUTRAL, both POSITIVE, or both NEGATIVE)
    - conflicting: opposing directionality (POSITIVE vs NEGATIVE)
    - Otherwise: no interaction
    
    Args:
        pressures: List of pressures (will be sorted by pressure_id for determinism)
    
    Returns:
        List of PressureInteraction objects
    """
    if len(pressures) < 2:
        return []
    
    # Sort pressures by pressure_id for deterministic ordering
    sorted_pressures = sorted(pressures, key=lambda p: p.pressure_id)
    
    interactions = []
    
    # Consider all unique pairs (i < j)
    for i in range(len(sorted_pressures)):
        for j in range(i + 1, len(sorted_pressures)):
            p1 = sorted_pressures[i]
            p2 = sorted_pressures[j]
            
            interaction = _evaluate_pair(p1, p2)
            if interaction:
                interactions.append(interaction)
    
    return interactions


def _evaluate_pair(p1: Pressure, p2: Pressure) -> PressureInteraction | None:
    """
    Evaluate interaction between two pressures.
    
    Args:
        p1: First pressure
        p2: Second pressure
    
    Returns:
        PressureInteraction if interaction exists, None otherwise
    """
    # Strict: same time_horizon required
    if p1.time_horizon != p2.time_horizon:
        return None
    
    # Strict: both magnitudes must be >= MIN_MAG
    if p1.magnitude < MIN_MAG or p2.magnitude < MIN_MAG:
        return None
    
    # Determine interaction type based on directionality
    interaction_type = _classify_interaction_type(p1.directionality, p2.directionality)
    
    if interaction_type is None:
        # No interaction (e.g., MIXED directionality)
        return None
    
    # Calculate instability contribution: geometric mean of magnitudes
    instability_contribution = ensure_01("instability", (p1.magnitude * p2.magnitude) ** 0.5)
    
    # Calculate confidence: average of confidences
    confidence = ensure_01("confidence", (p1.confidence + p2.confidence) / 2.0)
    
    # Generate deterministic interaction ID (pressure IDs sorted)
    pressure_ids = sorted([p1.pressure_id, p2.pressure_id])
    interaction_id_str = f"ix_{interaction_type.value}_{pressure_ids[0]}_{pressure_ids[1]}"
    interaction_id = InteractionID(interaction_id_str)
    
    # Generate explanation (component-referential, non-prescriptive)
    explanation = (
        f"Interaction between {p1.pressure_type.value} and {p2.pressure_type.value} "
        f"pressures: {interaction_type.value}"
    )
    
    return PressureInteraction(
        interaction_id=interaction_id,
        pressures_involved=pressure_ids,
        interaction_type=interaction_type,
        instability_contribution=instability_contribution,
        confidence=confidence,
        explanation=explanation,
    )


def _classify_interaction_type(
    dir1: "Directionality",
    dir2: "Directionality",
) -> InteractionType | None:
    """
    Classify interaction type based on directionality compatibility.
    
    Args:
        dir1: First pressure directionality
        dir2: Second pressure directionality
    
    Returns:
        InteractionType (REINFORCEMENT or COUNTERACTION) or None if no interaction
    """
    # Import here to avoid circular imports
    from ..core import Directionality, InteractionType
    
    # Reinforcing: compatible directionality (same value)
    if dir1 == dir2:
        if dir1 in (Directionality.POSITIVE, Directionality.NEGATIVE, Directionality.NEUTRAL):
            return InteractionType.REINFORCEMENT
    
    # Conflicting: opposing directionality
    if (dir1 == Directionality.POSITIVE and dir2 == Directionality.NEGATIVE) or (
        dir1 == Directionality.NEGATIVE and dir2 == Directionality.POSITIVE
    ):
        return InteractionType.COUNTERACTION
    
    # Otherwise: no interaction (e.g., MIXED with anything)
    return None

