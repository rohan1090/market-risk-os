"""Invariant tests for volatility regime shift detector."""

from datetime import datetime, timezone

import pytest

from market_risk_os.core import Directionality, PressureType
from market_risk_os.features import FeatureStore
from market_risk_os.pressures.detectors.volatility_regime_shift import (
    VolatilityRegimeShiftDetector,
)
from tests.fixtures.bars_spx_like import get_bars_spx_like


class TestVolatilityRegimeShiftDetector:
    """Test volatility regime shift detector invariants."""
    
    def test_detector_has_correct_properties(self):
        """Test detector has correct name, type, and horizon."""
        detector = VolatilityRegimeShiftDetector()
        
        assert detector.name == "volatility_regime_shift"
        assert detector.pressure_type == PressureType.VOLATILITY
        assert detector.time_horizon == "short_term"
    
    def test_detector_returns_empty_or_single_pressure(self):
        """Test detector returns either empty list or single pressure."""
        detector = VolatilityRegimeShiftDetector()
        feature_store = FeatureStore()
        
        # Get bars and compute vol features
        bars = get_bars_spx_like()
        vol_features = feature_store.compute_vol_features(bars)
        
        # Test with valid features
        now = datetime.now(timezone.utc)
        pressures = detector.detect("SPX", vol_features, now)
        
        # Should return either [] or [Pressure]
        assert isinstance(pressures, list)
        assert len(pressures) <= 1
        
        if pressures:
            pressure = pressures[0]
            assert pressure is not None
    
    def test_pressure_bounded_invariants(self):
        """Test all pressure values are bounded correctly."""
        detector = VolatilityRegimeShiftDetector()
        feature_store = FeatureStore()
        
        bars = get_bars_spx_like()
        vol_features = feature_store.compute_vol_features(bars)
        
        now = datetime.now(timezone.utc)
        pressures = detector.detect("SPX", vol_features, now)
        
        if pressures:
            pressure = pressures[0]
            
            # Boundedness checks
            assert 0.0 <= pressure.magnitude <= 1.0
            assert -1.0 <= pressure.acceleration <= 1.0
            assert 0.0 <= pressure.confidence <= 1.0
    
    def test_pressure_has_correct_type_and_directionality(self):
        """Test pressure has VOLATILITY type and NEUTRAL directionality."""
        detector = VolatilityRegimeShiftDetector()
        feature_store = FeatureStore()
        
        bars = get_bars_spx_like()
        vol_features = feature_store.compute_vol_features(bars)
        
        now = datetime.now(timezone.utc)
        pressures = detector.detect("SPX", vol_features, now)
        
        if pressures:
            pressure = pressures[0]
            assert pressure.pressure_type == PressureType.VOLATILITY
            assert pressure.directionality == Directionality.NEUTRAL
    
    def test_detected_at_is_utc_aware(self):
        """Test detected_at timestamp is timezone-aware UTC."""
        detector = VolatilityRegimeShiftDetector()
        feature_store = FeatureStore()
        
        bars = get_bars_spx_like()
        vol_features = feature_store.compute_vol_features(bars)
        
        now = datetime.now(timezone.utc)
        pressures = detector.detect("SPX", vol_features, now)
        
        if pressures:
            pressure = pressures[0]
            assert pressure.detected_at.tzinfo is not None
            assert pressure.detected_at.tzinfo.utcoffset(pressure.detected_at).total_seconds() == 0
    
    def test_explanation_is_non_empty(self):
        """Test pressure explanation is non-empty."""
        detector = VolatilityRegimeShiftDetector()
        feature_store = FeatureStore()
        
        bars = get_bars_spx_like()
        vol_features = feature_store.compute_vol_features(bars)
        
        now = datetime.now(timezone.utc)
        pressures = detector.detect("SPX", vol_features, now)
        
        if pressures:
            pressure = pressures[0]
            assert pressure.explanation is not None
            assert len(pressure.explanation) > 0
            # Should not contain trading instructions
            assert "trade" not in pressure.explanation.lower()
            assert "buy" not in pressure.explanation.lower()
            assert "sell" not in pressure.explanation.lower()
    
    def test_deterministic_pressure_id(self):
        """Test pressure ID is deterministic for same inputs."""
        detector = VolatilityRegimeShiftDetector()
        feature_store = FeatureStore()
        
        bars = get_bars_spx_like()
        vol_features = feature_store.compute_vol_features(bars)
        
        now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        pressures1 = detector.detect("SPX", vol_features, now)
        pressures2 = detector.detect("SPX", vol_features, now)
        
        if pressures1 and pressures2:
            assert pressures1[0].pressure_id == pressures2[0].pressure_id
            assert str(pressures1[0].pressure_id).startswith("p_volreg_")
    
    def test_deterministic_magnitude(self):
        """Test same inputs produce same magnitude."""
        detector = VolatilityRegimeShiftDetector()
        feature_store = FeatureStore()
        
        bars = get_bars_spx_like()
        vol_features = feature_store.compute_vol_features(bars)
        
        now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        pressures1 = detector.detect("SPX", vol_features, now)
        pressures2 = detector.detect("SPX", vol_features, now)
        
        if pressures1 and pressures2:
            assert pressures1[0].magnitude == pressures2[0].magnitude
    
    def test_returns_empty_for_insufficient_data(self):
        """Test detector returns empty list when data is insufficient."""
        detector = VolatilityRegimeShiftDetector()
        
        # Missing z_rv_ratio
        features1 = {}
        now = datetime.now(timezone.utc)
        pressures1 = detector.detect("SPX", features1, now)
        assert pressures1 == []
        
        # Missing returns
        features2 = {"z_rv_ratio": 1.5}
        pressures2 = detector.detect("SPX", features2, now)
        assert pressures2 == []
    
    def test_returns_empty_for_low_magnitude(self):
        """Test detector returns empty for very low magnitude (below threshold)."""
        detector = VolatilityRegimeShiftDetector()
        
        # Very negative z-score should produce low magnitude (< 0.1)
        # sigmoid(-2.5) ≈ 0.076, which is below the 0.1 threshold
        features = {
            "z_rv_ratio": -2.5,  # Very negative z-score produces magnitude < 0.1
            "returns": [0.001] * 100,
            "rv_20": 0.15,
            "rv_60": 0.15,
            "rv_ratio": 1.0,
            "missingness": 0.0,
            "staleness_seconds": 0.0,
            "stability": 1.0,
        }
        
        now = datetime.now(timezone.utc)
        pressures = detector.detect("SPX", features, now)
        
        # Should return empty due to magnitude threshold
        assert pressures == []

