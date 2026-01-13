"""Base interaction evaluator with graph-based evaluation."""

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from ..core import (
    Directionality,
    InteractionID,
    InteractionType,
    Pressure,
    PressureInteraction,
    PressureID,
)


class InteractionGraph:
    """Graph structure for tracking pressure interactions."""
    
    def __init__(self):
        """Initialize an empty interaction graph."""
        self._edges: Dict[PressureID, Set[PressureID]] = defaultdict(set)
        self._interactions: Dict[Tuple[PressureID, PressureID], InteractionID] = {}
    
    def add_interaction(
        self,
        pressure1: PressureID,
        pressure2: PressureID,
        interaction_id: InteractionID,
    ) -> None:
        """
        Add an interaction between two pressures.
        
        Args:
            pressure1: First pressure ID
            pressure2: Second pressure ID
            interaction_id: Interaction identifier
        """
        # Add bidirectional edges
        self._edges[pressure1].add(pressure2)
        self._edges[pressure2].add(pressure1)
        
        # Store interaction ID (using sorted tuple for consistency)
        key = tuple(sorted([pressure1, pressure2]))
        self._interactions[key] = interaction_id
    
    def get_neighbors(self, pressure_id: PressureID) -> Set[PressureID]:
        """
        Get neighboring pressures for a given pressure.
        
        Args:
            pressure_id: Pressure identifier
        
        Returns:
            Set of neighboring pressure IDs
        """
        return self._edges.get(pressure_id, set())
    
    def has_interaction(self, pressure1: PressureID, pressure2: PressureID) -> bool:
        """
        Check if two pressures have an interaction.
        
        Args:
            pressure1: First pressure ID
            pressure2: Second pressure ID
        
        Returns:
            True if interaction exists
        """
        key = tuple(sorted([pressure1, pressure2]))
        return key in self._interactions
    
    def get_interaction_id(
        self,
        pressure1: PressureID,
        pressure2: PressureID,
    ) -> Optional[InteractionID]:
        """
        Get interaction ID for two pressures.
        
        Args:
            pressure1: First pressure ID
            pressure2: Second pressure ID
        
        Returns:
            Interaction ID if exists, None otherwise
        """
        key = tuple(sorted([pressure1, pressure2]))
        return self._interactions.get(key)


class BaseInteractionEvaluator:
    """Base class for evaluating pressure interactions."""
    
    def __init__(self):
        """Initialize the interaction evaluator."""
        self.graph = InteractionGraph()
    
    def evaluate_interactions(
        self,
        pressures: List[Pressure],
    ) -> List[PressureInteraction]:
        """
        Evaluate interactions between pressures.
        
        Args:
            pressures: List of detected pressures
        
        Returns:
            List of pressure interactions
        """
        interactions = []
        
        # Evaluate all pairs of pressures
        for i, pressure1 in enumerate(pressures):
            for pressure2 in pressures[i + 1:]:
                interaction = self._evaluate_pair(pressure1, pressure2)
                if interaction:
                    interactions.append(interaction)
                    # Add to graph
                    self.graph.add_interaction(
                        pressure1.pressure_id,
                        pressure2.pressure_id,
                        interaction.interaction_id,
                    )
        
        return interactions
    
    def _evaluate_pair(
        self,
        pressure1: Pressure,
        pressure2: Pressure,
    ) -> Optional[PressureInteraction]:
        """
        Evaluate interaction between two pressures using basic rules.
        
        Args:
            pressure1: First pressure
            pressure2: Second pressure
        
        Returns:
            PressureInteraction if interaction detected, None otherwise
        """
        # Basic rule: pressures interact if they have similar directionality
        # or if their magnitudes are both high
        
        # Check if pressures should interact
        should_interact = self._should_interact(pressure1, pressure2)
        
        if not should_interact:
            return None
        
        # Determine interaction type
        interaction_type = self._determine_interaction_type(pressure1, pressure2)
        
        # Calculate instability contribution
        instability_contribution = self._calculate_instability(
            pressure1,
            pressure2,
        )
        
        # Calculate confidence
        confidence = min(pressure1.confidence, pressure2.confidence)
        
        # Generate interaction ID
        interaction_id = InteractionID(
            f"int_{pressure1.pressure_id}_{pressure2.pressure_id}"
        )
        
        return PressureInteraction(
            interaction_id=interaction_id,
            pressures_involved=[pressure1.pressure_id, pressure2.pressure_id],
            interaction_type=interaction_type,
            instability_contribution=instability_contribution,
            confidence=confidence,
            explanation=(
                f"Interaction between {pressure1.pressure_type.value} and "
                f"{pressure2.pressure_type.value} pressures"
            ),
        )
    
    def _should_interact(self, pressure1: Pressure, pressure2: Pressure) -> bool:
        """
        Determine if two pressures should interact.
        
        Args:
            pressure1: First pressure
            pressure2: Second pressure
        
        Returns:
            True if pressures should interact
        """
        # Basic rule: interact if both have high magnitude
        if pressure1.magnitude > 0.5 and pressure2.magnitude > 0.5:
            return True
        
        # Or if they have matching directionality
        if pressure1.directionality == pressure2.directionality:
            return True
        
        return False
    
    def _determine_interaction_type(
        self,
        pressure1: Pressure,
        pressure2: Pressure,
    ) -> InteractionType:
        """
        Determine the type of interaction.
        
        Args:
            pressure1: First pressure
            pressure2: Second pressure
        
        Returns:
            Interaction type
        """
        # Basic rules for interaction type
        if pressure1.directionality == pressure2.directionality:
            if pressure1.directionality in [
                Directionality.POSITIVE,
                Directionality.NEGATIVE,
            ]:
                return InteractionType.REINFORCEMENT
            return InteractionType.RESONANCE
        
        if pressure1.acceleration * pressure2.acceleration > 0:
            return InteractionType.AMPLIFICATION
        
        return InteractionType.COUNTERACTION
    
    def _calculate_instability(
        self,
        pressure1: Pressure,
        pressure2: Pressure,
    ) -> float:
        """
        Calculate instability contribution from interaction.
        
        Args:
            pressure1: First pressure
            pressure2: Second pressure
        
        Returns:
            Instability contribution in [0, 1]
        """
        # Simple formula: average magnitude weighted by acceleration
        avg_magnitude = (pressure1.magnitude + pressure2.magnitude) / 2.0
        avg_acceleration = abs((pressure1.acceleration + pressure2.acceleration) / 2.0)
        
        instability = avg_magnitude * (0.5 + avg_acceleration * 0.5)
        return min(1.0, instability)

