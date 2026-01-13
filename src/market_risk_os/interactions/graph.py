"""Pure graph-based aggregation functions for interactions."""

import math
from typing import List

from ..core import (
    InteractionType,
    PressureInteraction,
    ensure_01,
)
from .rules import generate_interactions


def compute_interaction_weight(interaction: PressureInteraction) -> float:
    """
    Compute interaction weight as product of instability contribution and confidence.
    
    Args:
        interaction: PressureInteraction to weight
    
    Returns:
        Weight in [0, 1]
    """
    weight = interaction.instability_contribution * interaction.confidence
    return ensure_01("weight", weight)


def compute_instability(interactions: List[PressureInteraction]) -> float:
    """
    Compute overall instability using noisy-OR aggregation.
    
    Noisy-OR is used because it models nonlinear accumulation: multiple independent
    sources of instability combine such that the probability of instability increases
    with each additional interaction, but with diminishing returns. This captures
    the intuition that more interactions increase instability, but not linearly.
    
    Formula: instability = 1 - Π(1 - weight_i)
    
    Args:
        interactions: List of pressure interactions
    
    Returns:
        Instability score in [0, 1]. Returns 0.0 if interactions list is empty.
    """
    if not interactions:
        return 0.0
    
    # Compute product of (1 - weight_i) for all interactions
    product = 1.0
    for interaction in interactions:
        weight = compute_interaction_weight(interaction)
        product *= 1.0 - weight
    
    # Noisy-OR: instability = 1 - product
    instability = 1.0 - product
    return ensure_01("instability", instability)


def compute_ambiguity(interactions: List[PressureInteraction]) -> float:
    """
    Compute ambiguity as the ratio of conflicting interaction weight to total weight.
    
    Ambiguity measures the proportion of interactions that are conflicting (opposing
    directionalities). Higher ambiguity indicates uncertainty about the overall
    direction of market pressures.
    
    Args:
        interactions: List of pressure interactions
    
    Returns:
        Ambiguity score in [0, 1]. Returns 0.0 if interactions list is empty or
        total weight is zero.
    """
    if not interactions:
        return 0.0
    
    # Compute weights for all interactions
    weights = [compute_interaction_weight(i) for i in interactions]
    total_weight = sum(weights)
    
    if total_weight == 0.0:
        return 0.0
    
    # Sum weights for conflicting interactions
    conflicting_weight = sum(
        weight
        for interaction, weight in zip(interactions, weights)
        if interaction.interaction_type == InteractionType.COUNTERACTION
    )
    
    # Ambiguity is the ratio of conflicting weight to total weight
    # Use small epsilon to avoid division by zero (already handled above, but defensive)
    eps = 1e-10
    ambiguity = conflicting_weight / (total_weight + eps)
    return ensure_01("ambiguity", ambiguity)


# Alias for generate_interactions from rules module
build_interactions = generate_interactions

