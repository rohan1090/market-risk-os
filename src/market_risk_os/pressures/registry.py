"""Detector registry for governance and discovery."""

from typing import List

from .base import BasePressureDetector


class DetectorRegistry:
    """Lightweight registry for pressure detectors."""
    
    def __init__(self):
        """Initialize empty registry."""
        self._detectors: List[BasePressureDetector] = []
    
    def register_detector(self, detector: BasePressureDetector) -> None:
        """
        Register a detector.
        
        Args:
            detector: Detector instance to register
        """
        if not isinstance(detector, BasePressureDetector):
            raise TypeError(
                f"Detector must be instance of BasePressureDetector, got {type(detector)}"
            )
        
        # Avoid duplicates (by name)
        if any(d.name == detector.name for d in self._detectors):
            return  # Already registered
        
        self._detectors.append(detector)
    
    def get_detectors(self) -> List[BasePressureDetector]:
        """
        Get all registered detectors.
        
        Returns:
            List of registered detectors
        """
        return self._detectors.copy()
    
    def clear_registry_for_tests(self) -> None:
        """Clear registry (for testing only)."""
        self._detectors.clear()
    
    def register_default_detectors(self) -> None:
        """
        Register default detectors.
        
        This function is idempotent - can be called multiple times safely.
        """
        # Import here to avoid circular dependencies
        from .synthetic import SyntheticDetector
        
        # Clear existing if any
        self.clear_registry_for_tests()
        
        # Register synthetic detector (always available)
        synthetic = SyntheticDetector()
        self.register_detector(synthetic)
        
        # Register volatility regime shift detector
        from .detectors.volatility_regime_shift import VolatilityRegimeShiftDetector
        vol_regime = VolatilityRegimeShiftDetector()
        self.register_detector(vol_regime)


# Global registry instance
_registry = DetectorRegistry()


def register_detector(detector: BasePressureDetector) -> None:
    """Register a detector in the global registry."""
    _registry.register_detector(detector)


def get_detectors() -> List[BasePressureDetector]:
    """Get all registered detectors."""
    return _registry.get_detectors()


def clear_registry_for_tests() -> None:
    """Clear registry (for testing only)."""
    _registry.clear_registry_for_tests()


def register_default_detectors() -> None:
    """Register default detectors (idempotent)."""
    _registry.register_default_detectors()

