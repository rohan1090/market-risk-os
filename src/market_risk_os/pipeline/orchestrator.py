"""Orchestrator pipeline for market risk analysis."""

from typing import List, Optional

from ..core import (
    BehaviorGate,
    GateID,
    InteractionID,
    Pressure,
    RiskState,
    utc_now,
)
from ..features import FeatureStore
from ..gate import BehaviorGateController
from ..interactions import BaseInteractionEvaluator
from ..pressures import get_detectors, register_default_detectors
from ..state import RiskStateEstimator


class PipelineOrchestrator:
    """Orchestrates the complete market risk analysis pipeline."""
    
    def __init__(
        self,
        feature_store: Optional[FeatureStore] = None,
        interaction_evaluator: Optional[BaseInteractionEvaluator] = None,
        state_estimator: Optional[RiskStateEstimator] = None,
        gate_controller: Optional[BehaviorGateController] = None,
    ):
        """
        Initialize the pipeline orchestrator.
        
        Args:
            feature_store: Feature store instance (creates default if None)
            interaction_evaluator: Interaction evaluator (creates default if None)
            state_estimator: Risk state estimator (creates default if None)
            gate_controller: Behavior gate controller (creates default if None)
        """
        self.feature_store = feature_store or FeatureStore()
        self.interaction_evaluator = (
            interaction_evaluator or BaseInteractionEvaluator()
        )
        self.state_estimator = state_estimator or RiskStateEstimator()
        self.gate_controller = gate_controller or BehaviorGateController()
        
        # Ensure default detectors are registered
        register_default_detectors()
    
    def run(self, symbol: str) -> dict:
        """
        Run the complete pipeline for a given symbol.
        
        Args:
            symbol: Asset symbol to analyze
        
        Returns:
            Dictionary containing:
            - pressures: List of detected pressures
            - interactions: List of pressure interactions
            - risk_state: Estimated risk state
            - behavior_gate: Created behavior gate
        """
        # Generate one UTC timestamp per run
        now = utc_now()
        
        # Ensure default detectors are registered
        register_default_detectors()
        
        # Step 1: Feature extraction
        features = self.feature_store.extract_features(symbol)
        
        # Step 2: Pressure detection (using registry)
        pressures = self._detect_pressures(symbol, features, now)
        
        # Step 3: Interaction evaluation
        interactions = self.interaction_evaluator.evaluate_interactions(pressures)
        
        # Step 4: Risk state estimation
        risk_state = self.state_estimator.estimate(
            symbol,
            pressures,
            interactions,
            now,
        )
        
        # Step 5: Behavior gate creation
        gate_id = GateID(f"gate_{symbol}_{self._generate_timestamp(now)}")
        behavior_gate = self.gate_controller.create_gate(risk_state, gate_id)
        
        return {
            "symbol": symbol,
            "features": features,
            "pressures": pressures,
            "interactions": interactions,
            "risk_state": risk_state,
            "behavior_gate": behavior_gate,
        }
    
    def _detect_pressures(
        self,
        symbol: str,
        features: dict,
        now,
    ) -> List[Pressure]:
        """
        Run all registered pressure detectors for a symbol.
        
        Args:
            symbol: Asset symbol
            features: Extracted features dictionary
            now: Current UTC datetime
        
        Returns:
            List of detected pressures
        """
        pressures = []
        detectors = get_detectors()
        
        for detector in detectors:
            try:
                detector_pressures = detector.detect(symbol, features, now)
                pressures.extend(detector_pressures)
            except Exception as e:
                # Log error but continue with other detectors
                print(f"Warning: Pressure detector {detector.name} failed: {e}")
        
        return pressures
    
    def _generate_timestamp(self, now=None) -> str:
        """
        Generate a simple timestamp string for IDs.
        
        Args:
            now: Optional datetime (uses current time if None)
        """
        from datetime import datetime
        
        if now is None:
            now = datetime.now()
        
        return now.strftime("%Y%m%d%H%M%S")

