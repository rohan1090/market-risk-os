"""Convexity pressure detector."""

from ..core import (
    Directionality,
    Pressure,
    PressureID,
    PressureType,
    utc_now,
)
from .base import BasePressureDetector


class ConvexityDetector(BasePressureDetector):
    """Detector for convexity-based pressure."""
    
    @property
    def pressure_type(self) -> PressureType:
        """Return convexity pressure type."""
        return PressureType.CONCENTRATION  # Using concentration as proxy for convexity
    
    def detect(
        self,
        symbol: str,
        pressure_id: PressureID,
    ) -> Pressure:
        """
        Detect convexity pressure.
        
        Args:
            symbol: Asset symbol
            pressure_id: Unique identifier for this pressure
        
        Returns:
            Pressure model instance
        """
        # Placeholder implementation
        features = self.feature_store.extract_features(symbol, ["convexity", "volatility"])
        convexity = features.get("convexity", 0.05)
        volatility = features.get("volatility", 0.15)
        
        # Simple logic: higher convexity = higher magnitude
        magnitude = min(1.0, convexity * 10.0)  # Scale to [0, 1]
        acceleration = volatility * 2.0 - 0.3  # Use volatility as acceleration proxy
        acceleration = max(-1.0, min(1.0, acceleration))  # Clamp to [-1, 1]
        
        # Convexity is typically neutral in directionality
        directionality = Directionality.NEUTRAL
        
        confidence = 0.6  # Placeholder confidence
        
        return Pressure(
            pressure_id=pressure_id,
            pressure_type=self.pressure_type,
            source_assets=[symbol],
            directionality=directionality,
            magnitude=magnitude,
            acceleration=acceleration,
            confidence=confidence,
            detected_at=utc_now(),
            time_horizon="medium_term",
            explanation=f"Convexity pressure detected for {symbol} with magnitude {magnitude:.2f}",
        )

