"""Synthetic detector for testing and fallback."""

from datetime import datetime
from typing import Any, Dict, List

from ..core import Directionality, PressureType
from .templates.detector_template import TemplateDetector


class SyntheticDetector(TemplateDetector):
    """
    Synthetic detector that produces valid Pressure objects.
    
    Used for testing and as a fallback when no real detectors are available.
    """
    
    name = "synthetic"
    pressure_type = PressureType.VOLATILITY
    time_horizon = "short_term"
    
    def compute_raw(
        self,
        symbol: str,
        features: Dict[str, Any],
        now: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Compute synthetic pressure values.
        
        Args:
            symbol: Asset symbol
            features: Feature dictionary (unused)
            now: Current datetime (unused)
        
        Returns:
            List with one synthetic pressure result
        """
        # Produce a synthetic but valid pressure
        # Magnitude based on a simple hash of symbol (deterministic)
        symbol_hash = hash(symbol) % 1000
        raw_magnitude = (symbol_hash / 1000.0) * 0.5 + 0.25  # Range [0.25, 0.75]
        
        return [
            {
                "magnitude": raw_magnitude,
                "directionality": Directionality.NEUTRAL,
                "acceleration": None,  # Will be computed
                "confidence": None,  # Will be computed
                "missing_ratio": 0.0,
                "staleness_seconds": 0.0,
                "stability": 0.8,
                "is_zscore": False,
                "max_step": 1.0,
            }
        ]
    
    def explain(
        self,
        symbol: str,
        raw: Dict[str, Any],
        magnitude: float,
        acceleration: float,
        confidence: float,
    ) -> str:
        """Generate explanation for synthetic pressure."""
        return (
            f"Synthetic {self.pressure_type.value} pressure for {symbol}: "
            f"magnitude={magnitude:.2f} (for testing/fallback)"
        )

