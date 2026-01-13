"""Invariant tests for interaction generation and scoring."""

import pytest

from market_risk_os.core import InteractionID, InteractionType, PressureID
from market_risk_os.interactions.graph import (
    build_interactions,
    compute_ambiguity,
    compute_instability,
)
from market_risk_os.state.scoring import score_ambiguity, score_instability


class TestInteractionObjects:
    """Test that interaction objects are valid and serializable."""
    
    def test_interaction_objects_valid_and_serializable(self, pressures_mixed_set):
        """Test that all interaction objects are valid and can be serialized to JSON."""
        interactions = build_interactions(pressures_mixed_set)
        
        # Verify specific expected interactions exist based on fixture pressure_ids
        # Reinforcing interaction expected between volatility_SPX_0 and volatility_SPX_1
        expected_reinforcing_pair = sorted([
            PressureID("volatility_SPX_0"),
            PressureID("volatility_SPX_1"),
        ])
        assert any(
            i.pressures_involved == expected_reinforcing_pair
            and i.interaction_type == InteractionType.REINFORCEMENT
            for i in interactions
        ), f"Expected reinforcing interaction between {expected_reinforcing_pair}"
        
        # Conflicting interaction expected between volatility_SPX_0 and liquidity_SPX_0
        expected_conflicting_pair = sorted([
            PressureID("volatility_SPX_0"),
            PressureID("liquidity_SPX_0"),
        ])
        assert any(
            i.pressures_involved == expected_conflicting_pair
            and i.interaction_type == InteractionType.COUNTERACTION
            for i in interactions
        ), f"Expected conflicting interaction between {expected_conflicting_pair}"
        
        for interaction in interactions:
            # Verify pressures_involved has exactly 2 elements
            assert len(interaction.pressures_involved) == 2, \
                f"Interaction should involve exactly 2 pressures, got {len(interaction.pressures_involved)}"
            
            # Verify pressures_involved is sorted
            assert interaction.pressures_involved == sorted(interaction.pressures_involved), \
                "pressures_involved should be sorted"
            
            # Verify interaction_id has deterministic prefix
            assert interaction.interaction_id.startswith("ix_"), \
                f"interaction_id should start with 'ix_', got {interaction.interaction_id}"
            
            # Verify bounded values
            assert 0.0 <= interaction.instability_contribution <= 1.0, \
                f"instability_contribution must be in [0, 1], got {interaction.instability_contribution}"
            assert 0.0 <= interaction.confidence <= 1.0, \
                f"confidence must be in [0, 1], got {interaction.confidence}"
            
            # Verify serialization to JSON
            json_str = interaction.model_dump_json()
            assert isinstance(json_str, str), \
                "model_dump_json() should return a string"
            assert len(json_str) > 0, \
                "JSON string should not be empty"


class TestReinforcingInteractions:
    """Test reinforcing interaction creation."""
    
    def test_reinforcing_interaction_created(self, pressures_reinforcing_short):
        """Test that reinforcing interactions are created for compatible pressures."""
        interactions = build_interactions(pressures_reinforcing_short)
        
        # Should have at least one interaction
        assert len(interactions) > 0, \
            "Reinforcing pressures should produce at least one interaction"
        
        # At least one should be reinforcing
        reinforcing_interactions = [
            i for i in interactions
            if i.interaction_type == InteractionType.REINFORCEMENT
        ]
        assert len(reinforcing_interactions) > 0, \
            "Should have at least one reinforcing interaction"
        
        # Verify the interaction is valid
        for interaction in reinforcing_interactions:
            assert interaction.interaction_type == InteractionType.REINFORCEMENT
            assert len(interaction.pressures_involved) == 2


class TestConflictingInteractions:
    """Test conflicting interaction creation and ambiguity."""
    
    def test_conflicting_interaction_created_and_ambiguity_positive(
        self,
        pressures_conflicting_short,
    ):
        """Test that conflicting interactions are created and ambiguity is positive."""
        interactions = build_interactions(pressures_conflicting_short)
        
        # Should have at least one interaction
        assert len(interactions) > 0, \
            "Conflicting pressures should produce at least one interaction"
        
        # At least one should be conflicting
        conflicting_interactions = [
            i for i in interactions
            if i.interaction_type == InteractionType.COUNTERACTION
        ]
        assert len(conflicting_interactions) > 0, \
            "Should have at least one conflicting interaction"
        
        # Compute ambiguity
        ambiguity = compute_ambiguity(interactions)
        
        # Ambiguity should be positive (in (0, 1])
        assert ambiguity > 0.0, \
            f"Ambiguity should be positive when conflicting interactions exist, got {ambiguity}"
        assert ambiguity <= 1.0, \
            f"Ambiguity should be <= 1.0, got {ambiguity}"
        
        # Verify ambiguity scoring function
        ambiguity_score = score_ambiguity(interactions)
        assert ambiguity_score == ambiguity, \
            "score_ambiguity should match compute_ambiguity"


class TestEmptyListScoring:
    """Test that empty list scoring returns zero."""
    
    def test_empty_list_scoring(self):
        """Test that empty interaction lists produce zero scores."""
        # Instability should be 0.0 for empty list
        instability = compute_instability([])
        assert instability == 0.0, \
            f"Instability should be 0.0 for empty list, got {instability}"
        
        # Ambiguity should be 0.0 for empty list
        ambiguity = compute_ambiguity([])
        assert ambiguity == 0.0, \
            f"Ambiguity should be 0.0 for empty list, got {ambiguity}"


class TestThresholdFiltering:
    """Test that magnitude threshold blocks noise."""
    
    def test_threshold_blocks_noise(self, pressures_below_threshold):
        """Test that pressures below threshold produce no interactions."""
        interactions = build_interactions(pressures_below_threshold)
        
        # Should produce no interactions (both magnitudes < 0.55)
        assert interactions == [], \
            f"Pressures below threshold should produce no interactions, got {len(interactions)}"
        
        # Instability should be 0.0
        instability = compute_instability(interactions)
        assert instability == 0.0, \
            f"Instability should be 0.0 when no interactions, got {instability}"
        
        # Ambiguity should be 0.0
        ambiguity = compute_ambiguity(interactions)
        assert ambiguity == 0.0, \
            f"Ambiguity should be 0.0 when no interactions, got {ambiguity}"


class TestInstabilityMonotonicity:
    """Test instability monotonicity properties."""
    
    def test_instability_monotonicity_manual(self):
        """Test that instability is monotonic: inst([]) <= inst([w1]) <= inst([w1,w2]) <= 1."""
        from market_risk_os.core import PressureInteraction
        
        # Create two synthetic interactions with known weights
        interaction1 = PressureInteraction(
            interaction_id=InteractionID("ix_reinforcement_p1_p2"),
            pressures_involved=[PressureID("p1"), PressureID("p2")],
            interaction_type=InteractionType.REINFORCEMENT,
            instability_contribution=0.6,
            confidence=0.8,
            explanation="Test interaction 1",
        )
        
        interaction2 = PressureInteraction(
            interaction_id=InteractionID("ix_counteraction_p2_p3"),
            pressures_involved=[PressureID("p2"), PressureID("p3")],
            interaction_type=InteractionType.COUNTERACTION,
            instability_contribution=0.7,
            confidence=0.7,
            explanation="Test interaction 2",
        )
        
        # Compute instability for empty list
        inst_empty = compute_instability([])
        assert inst_empty == 0.0, \
            f"Instability of empty list should be 0.0, got {inst_empty}"
        
        # Compute instability for single interaction
        inst_single = compute_instability([interaction1])
        
        # Compute instability for both interactions
        inst_both = compute_instability([interaction1, interaction2])
        
        # Verify monotonicity with explicit bounds: 0 < inst_single <= inst_both <= 1
        assert inst_single > 0.0, \
            f"Single interaction instability should be > 0, got {inst_single}"
        assert inst_single <= 1.0, \
            f"Single interaction instability should be <= 1.0, got {inst_single}"
        assert inst_single <= inst_both, \
            f"Instability should increase with more interactions: {inst_single} <= {inst_both}"
        assert inst_both <= 1.0, \
            f"Instability should be <= 1.0, got {inst_both}"


class TestDeterminism:
    """Test that interaction generation is deterministic."""
    
    def test_determinism(self, pressures_mixed_set):
        """Test that interaction generation is deterministic."""
        # Generate interactions twice
        interactions1 = build_interactions(pressures_mixed_set)
        interactions2 = build_interactions(pressures_mixed_set)
        
        # Should have the same number of interactions
        assert len(interactions1) == len(interactions2), \
            f"Should produce same number of interactions: {len(interactions1)} vs {len(interactions2)}"
        
        # Build signature tuples: (interaction_type, tuple(pressures_involved))
        signatures1 = sorted([
            (i.interaction_type, tuple(i.pressures_involved))
            for i in interactions1
        ])
        signatures2 = sorted([
            (i.interaction_type, tuple(i.pressures_involved))
            for i in interactions2
        ])
        
        # Compare signatures (stable contract: type + pressures_involved)
        assert signatures1 == signatures2, \
            f"Interaction signatures should match: {signatures1} vs {signatures2}"

