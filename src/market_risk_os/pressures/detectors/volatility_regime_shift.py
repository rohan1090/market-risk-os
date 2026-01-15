"""Volatility regime shift detector."""

from datetime import datetime
from typing import Any, Dict, List

from ...core import Directionality, Pressure, PressureID, PressureType, ensure_utc
from ...core.validation import ensure_01, ensure_m11
from ...features.transforms import (
    acceleration_from_magnitudes,
    confidence_from_quality,
    squash01_from_z,
)
from ..base import BasePressureDetector


class VolatilityRegimeShiftDetector(BasePressureDetector):
    """
    Detector for volatility regime shifts.
    
    Detects when short-term realized volatility (20-day) significantly
    deviates from longer-term realized volatility (60-day).
    """
    
    @property
    def name(self) -> str:
        """Return the name of this detector."""
        return "volatility_regime_shift"
    
    @property
    def pressure_type(self) -> PressureType:
        """Return the type of pressure this detector identifies."""
        return PressureType.VOLATILITY
    
    @property
    def time_horizon(self) -> str:
        """Return the time horizon this detector operates on."""
        return "short_term"
    
    def detect(
        self,
        symbol: str,
        features: Dict[str, Any],
        now: datetime,
    ) -> List[Pressure]:
        """
        Detect volatility regime shift pressure.
        
        Args:
            symbol: Asset symbol
            features: Feature dictionary (must contain z_rv_ratio and vol features)
            now: Current UTC datetime
        
        Returns:
            List of Pressure objects (empty or single pressure)
        """
        now_utc = ensure_utc(now)
        
        # Extract z_rv_ratio from features
        z_rv_ratio = features.get("z_rv_ratio", 0.0)
        
        # Check if we have sufficient data
        if not isinstance(z_rv_ratio, (int, float)) or not features.get("returns"):
            return []
        
        # Extract quality metrics
        missingness = features.get("missingness", 0.0)
        staleness_seconds = features.get("staleness_seconds", 0.0)
        stability = features.get("stability", 1.0)
        
        # Compute magnitude from z-score
        magnitude = squash01_from_z(z_rv_ratio, k=1.0)
        magnitude = ensure_01("magnitude", magnitude)
        
        # Compute acceleration (no previous magnitude available, so 0.0)
        # In a real system, you'd track previous magnitude in state
        acceleration = 0.0
        acceleration = ensure_m11("acceleration", acceleration)
        
        # Compute confidence from quality metrics
        confidence = confidence_from_quality(
            missing_ratio=missingness,
            staleness_seconds=staleness_seconds,
            stability=stability,
        )
        confidence = ensure_01("confidence", confidence)
        
        # Only emit pressure if magnitude is significant (threshold)
        # This prevents noise from very small z-scores
        if magnitude < 0.1:
            return []
        
        # Generate deterministic pressure ID
        date_str = now_utc.strftime("%Y%m%d")
        pressure_id = PressureID(f"p_volreg_{symbol.lower()}_{date_str}")
        
        # Generate explanation
        rv_20 = features.get("rv_20", 0.0)
        rv_60 = features.get("rv_60", 0.0)
        rv_ratio = features.get("rv_ratio", 0.0)
        explanation = (
            f"Volatility regime shift detected: 20-day RV={rv_20:.4f}, "
            f"60-day RV={rv_60:.4f}, ratio={rv_ratio:.4f}, "
            f"z-score={z_rv_ratio:.2f}. Measured short-term vs long-term volatility."
        )
        
        # Create pressure
        pressure = Pressure(
            pressure_id=pressure_id,
            pressure_type=self.pressure_type,
            source_assets=[symbol],
            directionality=Directionality.NEUTRAL,
            magnitude=magnitude,
            acceleration=acceleration,
            confidence=confidence,
            detected_at=now_utc,
            time_horizon=self.time_horizon,
            explanation=explanation,
        )
        
        return [pressure]

