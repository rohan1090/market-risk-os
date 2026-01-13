"""Smoke test for pipeline orchestrator.

This test verifies:
- Pipeline runs end-to-end without errors
- Returns valid objects with all required fields
- Output shape is stable
- Handles non-standard symbols gracefully
"""

import pytest
from market_risk_os.pipeline import PipelineOrchestrator


class TestPipelineSmoke:
    """Smoke tests for the pipeline orchestrator."""
    
    def test_pipeline_runs_end_to_end(self):
        """Test that pipeline runs end-to-end without errors."""
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run("SPX")
        
        # Should not raise any exceptions
        assert result is not None
    
    def test_pipeline_returns_all_required_keys(self):
        """Test that pipeline returns dictionary with all required keys."""
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run("SPX")
        
        # Verify all required keys are present (subset check allows additional keys)
        required_keys = {
            "symbol",
            "features",
            "pressures",
            "interactions",
            "risk_state",
            "behavior_gate",
        }
        assert required_keys.issubset(result.keys()), \
            f"Missing keys: {required_keys - set(result.keys())}"
    
    def test_pipeline_returns_valid_objects(self):
        """Test that all returned objects are valid Pydantic models."""
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run("SPX")
        
        # Verify symbol is a string
        assert isinstance(result["symbol"], str)
        assert result["symbol"] == "SPX"
        
        # Verify features is a dictionary
        assert isinstance(result["features"], dict)
        
        # Verify pressures is a list
        assert isinstance(result["pressures"], list)
        # Each pressure should be a valid Pressure model (Pydantic will validate)
        for pressure in result["pressures"]:
            # Accessing required fields will raise if missing
            _ = pressure.pressure_id
            _ = pressure.pressure_type
            _ = pressure.directionality
            _ = pressure.magnitude
            _ = pressure.acceleration
            _ = pressure.confidence
            _ = pressure.detected_at
            # Validate ranges
            assert 0.0 <= pressure.magnitude <= 1.0
            assert -1.0 <= pressure.acceleration <= 1.0
            assert 0.0 <= pressure.confidence <= 1.0
        
        # Verify interactions is a list
        assert isinstance(result["interactions"], list)
        # Each interaction should be a valid PressureInteraction model
        for interaction in result["interactions"]:
            _ = interaction.interaction_id
            _ = interaction.pressures_involved
            _ = interaction.interaction_type
            _ = interaction.instability_contribution
            _ = interaction.confidence
            # Validate constraints
            assert len(interaction.pressures_involved) >= 2
            assert 0.0 <= interaction.instability_contribution <= 1.0
            assert 0.0 <= interaction.confidence <= 1.0
        
        # Verify risk_state is a valid RiskState model
        risk_state = result["risk_state"]
        _ = risk_state.state_id
        _ = risk_state.dominant_state
        _ = risk_state.contributing_pressures
        _ = risk_state.interactions
        _ = risk_state.instability_score
        _ = risk_state.confidence
        _ = risk_state.ambiguity
        _ = risk_state.valid_horizons
        _ = risk_state.detected_at
        # Validate ranges
        assert 0.0 <= risk_state.instability_score <= 1.0
        assert 0.0 <= risk_state.confidence <= 1.0
        assert 0.0 <= risk_state.ambiguity <= 1.0
        
        # Verify behavior_gate is a valid BehaviorGate model
        behavior_gate = result["behavior_gate"]
        _ = behavior_gate.gate_id
        _ = behavior_gate.risk_state_id
        _ = behavior_gate.allowed_behaviors
        _ = behavior_gate.forbidden_behaviors
        _ = behavior_gate.aggressiveness_limit
        _ = behavior_gate.confidence
        _ = behavior_gate.enforced_until
        # Validate ranges
        assert 0.0 <= behavior_gate.aggressiveness_limit <= 1.0
        assert 0.0 <= behavior_gate.confidence <= 1.0
        # Validate no overlap between allowed and forbidden
        overlap = set(behavior_gate.allowed_behaviors) & set(behavior_gate.forbidden_behaviors)
        assert len(overlap) == 0, f"Overlapping behaviors: {overlap}"
    
    def test_pipeline_output_shape_is_stable(self):
        """Test that pipeline output shape is stable across runs."""
        orchestrator = PipelineOrchestrator()
        
        # Run twice with same input
        result1 = orchestrator.run("SPX")
        result2 = orchestrator.run("SPX")
        
        # Check that both results have at least the required keys
        required_keys = {
            "symbol",
            "features",
            "pressures",
            "interactions",
            "risk_state",
            "behavior_gate",
        }
        assert required_keys.issubset(result1.keys())
        assert required_keys.issubset(result2.keys())
        
        # Check types are stable
        assert isinstance(result1["pressures"], list)
        assert isinstance(result2["pressures"], list)
        assert isinstance(result1["interactions"], list)
        assert isinstance(result2["interactions"], list)
        assert result1["risk_state"] is not None
        assert result2["risk_state"] is not None
        assert result1["behavior_gate"] is not None
        assert result2["behavior_gate"] is not None
        
        # Number of pressures should be stable (same detectors)
        assert len(result1["pressures"]) == len(result2["pressures"])
        
        # If interactions list is non-empty, verify each element has required attributes
        if result1["interactions"] and result2["interactions"]:
            for interaction in result1["interactions"]:
                _ = interaction.interaction_id
                _ = interaction.pressures_involved
                _ = interaction.interaction_type
                _ = interaction.instability_contribution
                _ = interaction.confidence
            for interaction in result2["interactions"]:
                _ = interaction.interaction_id
                _ = interaction.pressures_involved
                _ = interaction.interaction_type
                _ = interaction.instability_contribution
                _ = interaction.confidence
    
    def test_pipeline_handles_nonstandard_symbol(self):
        """Test that pipeline handles non-standard symbols robustly."""
        # This test validates robustness to unusual symbols
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run("TEST_SYMBOL")
        
        # All objects should be valid regardless of symbol
        assert isinstance(result["pressures"], list)
        assert isinstance(result["interactions"], list)
        assert result["risk_state"] is not None
        assert result["behavior_gate"] is not None
        
        # Risk state should still be valid
        risk_state = result["risk_state"]
        assert 0.0 <= risk_state.instability_score <= 1.0
        assert 0.0 <= risk_state.confidence <= 1.0
        assert 0.0 <= risk_state.ambiguity <= 1.0
    
    def test_pipeline_objects_serialize_to_json(self):
        """Test that all objects can be serialized to JSON (validates completeness)."""
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run("SPX")
        
        # All Pydantic models should serialize without errors
        for pressure in result["pressures"]:
            json_str = pressure.model_dump_json()
            assert isinstance(json_str, str)
            assert len(json_str) > 0
        
        for interaction in result["interactions"]:
            json_str = interaction.model_dump_json()
            assert isinstance(json_str, str)
            assert len(json_str) > 0
        
        risk_state_json = result["risk_state"].model_dump_json()
        assert isinstance(risk_state_json, str)
        assert len(risk_state_json) > 0
        
        gate_json = result["behavior_gate"].model_dump_json()
        assert isinstance(gate_json, str)
        assert len(gate_json) > 0
    
    def test_pipeline_returns_valid_features(self):
        """Test that features dictionary is valid."""
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run("SPX")
        
        features = result["features"]
        assert isinstance(features, dict)
        # Features should not be None (even if empty)
        assert features is not None

