"""
Canonical detector template.

All pressure detectors should follow this pattern for consistency and safety.
"""

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...core import (
    Directionality,
    Pressure,
    PressureID,
    PressureType,
    ensure_utc,
)
from ...core.validation import ensure_01, ensure_m11
from ...features.transforms import (
    acceleration_from_magnitudes,
    confidence_from_quality,
    squash01_from_z,
)
from ..base import BasePressureDetector


@dataclass
class DetectorConfig:
    """Configuration for a pressure detector."""
    
    name: str
    pressure_type: PressureType
    time_horizon: str
    # Add detector-specific config fields here


class TemplateDetector(BasePressureDetector):
    """
    Base implementation for pressure detectors with safety guarantees.
    
    Subclasses should:
    1. Set class attributes: name, pressure_type, time_horizon
    2. Implement compute_raw() to return raw magnitude and directionality
    3. Optionally implement explain() for custom explanations
    
    This base class handles:
    - UTC timestamp enforcement
    - Bounded output validation
    - Confidence computation
    - Acceleration calculation
    """
    
    def __init__(self, config: Optional[DetectorConfig] = None):
        """
        Initialize detector.
        
        Args:
            config: Optional configuration (can override class attributes)
        """
        self._name: Optional[str] = None
        self._pressure_type: Optional[PressureType] = None
        self._time_horizon: Optional[str] = None
        if config:
            self._name = config.name
            self._pressure_type = config.pressure_type
            self._time_horizon = config.time_horizon
    
    @property
    def name(self) -> str:
        """Return the name of this detector."""
        if self._name is not None:
            return self._name
        if hasattr(self.__class__, 'name'):
            return self.__class__.name
        raise ValueError(
            f"{self.__class__.__name__} must define 'name' as a class attribute "
            "or provide it via DetectorConfig"
        )
    
    @property
    def pressure_type(self) -> PressureType:
        """Return the type of pressure this detector identifies."""
        if self._pressure_type is not None:
            return self._pressure_type
        if hasattr(self.__class__, 'pressure_type'):
            return self.__class__.pressure_type
        raise ValueError(
            f"{self.__class__.__name__} must define 'pressure_type' as a class attribute "
            "or provide it via DetectorConfig"
        )
    
    @property
    def time_horizon(self) -> str:
        """Return the time horizon this detector operates on."""
        if self._time_horizon is not None:
            return self._time_horizon
        if hasattr(self.__class__, 'time_horizon'):
            return self.__class__.time_horizon
        raise ValueError(
            f"{self.__class__.__name__} must define 'time_horizon' as a class attribute "
            "or provide it via DetectorConfig"
        )
    
    def detect(
        self,
        symbol: str,
        features: Dict[str, Any],
        now: datetime,
    ) -> List[Pressure]:
        """
        Detect pressure with safety guarantees.
        
        This method ensures:
        - UTC timestamps
        - Bounded outputs (magnitude, acceleration, confidence in valid ranges)
        - Finite values (no NaN/inf)
        
        Args:
            symbol: Asset symbol
            features: Feature dictionary
            now: Current UTC datetime (will be normalized to UTC)
        
        Returns:
            List of Pressure objects (typically one, but may be multiple)
        """
        # Normalize timestamp to UTC
        now_utc = ensure_utc(now)
        
        # Compute raw values from subclass
        raw_results = self.compute_raw(symbol, features, now_utc)
        
        if not raw_results:
            return []
        
        pressures = []
        prev_magnitude: Optional[float] = None
        
        for i, raw in enumerate(raw_results):
            # Extract raw values
            raw_magnitude = raw.get("magnitude", 0.0)
            raw_directionality = raw.get("directionality", Directionality.NEUTRAL)
            raw_acceleration = raw.get("acceleration", None)
            raw_confidence = raw.get("confidence", None)
            
            # Quality metrics for confidence
            missing_ratio = raw.get("missing_ratio", 0.0)
            staleness_seconds = raw.get("staleness_seconds", 0.0)
            stability = raw.get("stability", 1.0)
            
            # Compute magnitude (squash to [0, 1])
            if isinstance(raw_magnitude, (int, float)):
                # If raw_magnitude is a z-score, squash it
                if raw.get("is_zscore", False):
                    magnitude = squash01_from_z(raw_magnitude)
                else:
                    # Already in magnitude space, just clamp
                    magnitude = ensure_01("magnitude", raw_magnitude)
            else:
                magnitude = 0.0
            
            # Compute acceleration
            if raw_acceleration is not None:
                acceleration = ensure_m11("acceleration", raw_acceleration)
            else:
                # Compute from magnitude change
                if prev_magnitude is not None:
                    acceleration = acceleration_from_magnitudes(
                        magnitude,
                        prev_magnitude,
                        max_step=raw.get("max_step", 1.0),
                    )
                else:
                    acceleration = 0.0
            
            # Compute confidence
            if raw_confidence is not None:
                confidence = ensure_01("confidence", raw_confidence)
            else:
                confidence = confidence_from_quality(
                    missing_ratio=missing_ratio,
                    staleness_seconds=staleness_seconds,
                    stability=stability,
                )
            
            # Generate pressure ID
            pressure_id = PressureID(f"{self.pressure_type.value}_{symbol}_{i}")
            
            # Generate explanation
            explanation = self.explain(symbol, raw, magnitude, acceleration, confidence)
            
            # Create Pressure object
            pressure = Pressure(
                pressure_id=pressure_id,
                pressure_type=self.pressure_type,
                source_assets=[symbol],
                directionality=raw_directionality,
                magnitude=magnitude,
                acceleration=acceleration,
                confidence=confidence,
                detected_at=now_utc,
                time_horizon=self.time_horizon,
                explanation=explanation,
            )
            
            pressures.append(pressure)
            prev_magnitude = magnitude
        
        return pressures
    
    @abstractmethod
    def compute_raw(
        self,
        symbol: str,
        features: Dict[str, Any],
        now: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Compute raw pressure values.
        
        Subclasses must implement this method.
        
        Args:
            symbol: Asset symbol
            features: Feature dictionary
            now: Current UTC datetime
        
        Returns:
            List of dictionaries with keys:
            - magnitude: float (raw magnitude or z-score)
            - directionality: Directionality enum
            - acceleration: Optional[float] (if None, computed from magnitude change)
            - confidence: Optional[float] (if None, computed from quality metrics)
            - missing_ratio: float (0..1, default 0.0)
            - staleness_seconds: float (≥0, default 0.0)
            - stability: float (0..1, default 1.0)
            - is_zscore: bool (if True, magnitude is treated as z-score)
            - max_step: float (for acceleration computation, default 1.0)
        """
        pass
    
    def explain(
        self,
        symbol: str,
        raw: Dict[str, Any],
        magnitude: float,
        acceleration: float,
        confidence: float,
    ) -> str:
        """
        Generate explanation for detected pressure.
        
        Subclasses can override for custom explanations.
        
        Args:
            symbol: Asset symbol
            raw: Raw computation results
            magnitude: Final magnitude value
            acceleration: Final acceleration value
            confidence: Final confidence value
        
        Returns:
            Explanation string
        """
        return (
            f"{self.pressure_type.value} pressure for {symbol}: "
            f"magnitude={magnitude:.2f}, acceleration={acceleration:.2f}, "
            f"confidence={confidence:.2f}"
        )

