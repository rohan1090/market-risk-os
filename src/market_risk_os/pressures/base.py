"""Base interface for pressure detectors."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

from ..core import Pressure, PressureID, PressureType


class BasePressureDetector(ABC):
    """
    Base interface for all pressure detectors.
    
    Each detector must expose:
    - name: str
    - pressure_type: PressureType enum
    - time_horizon: str
    - detect(symbol: str, features: dict, now: datetime) -> list[Pressure]
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this detector."""
        pass
    
    @property
    @abstractmethod
    def pressure_type(self) -> PressureType:
        """Return the type of pressure this detector identifies."""
        pass
    
    @property
    @abstractmethod
    def time_horizon(self) -> str:
        """Return the time horizon this detector operates on."""
        pass
    
    @abstractmethod
    def detect(
        self,
        symbol: str,
        features: Dict[str, any],
        now: datetime,
    ) -> List[Pressure]:
        """
        Detect pressures for a given symbol.
        
        Args:
            symbol: Asset symbol
            features: Dictionary of extracted features
            now: Current UTC datetime (timezone-aware)
        
        Returns:
            List of Pressure objects (may be empty)
        """
        pass
