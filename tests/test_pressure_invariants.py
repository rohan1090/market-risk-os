"""Invariant tests for pressure detection layer.

These tests automatically validate ALL registered detectors and ensure
that pressure math remains stable and bounded.
"""

import json
import math
from datetime import datetime, timezone

import pytest

from market_risk_os.core import Pressure, PressureID, utc_now
from market_risk_os.core.validation import ensure_01, ensure_m11, require_finite
from market_risk_os.features.transforms import (
    acceleration_from_magnitudes,
    confidence_from_quality,
    sigmoid,
    squash01_from_z,
)
from market_risk_os.pressures import (
    clear_registry_for_tests,
    get_detectors,
    register_default_detectors,
)


class TestRegistryInvariants:
    """Tests for detector registry."""
    
    def test_registry_has_detectors(self):
        """Registry must contain at least one detector."""
        clear_registry_for_tests()
        register_default_detectors()
        
        detectors = get_detectors()
        assert len(detectors) >= 1, "Registry must have at least one detector"
    
    def test_registry_idempotent(self):
        """register_default_detectors() must be idempotent."""
        clear_registry_for_tests()
        register_default_detectors()
        count1 = len(get_detectors())
        
        register_default_detectors()
        count2 = len(get_detectors())
        
        assert count1 == count2, "Registry registration should be idempotent"


class TestDetectorInvariants:
    """Tests that validate all registered detectors produce valid pressures."""
    
    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Setup registry before each test."""
        clear_registry_for_tests()
        register_default_detectors()
        yield
        # Cleanup not strictly necessary, but good practice
        clear_registry_for_tests()
    
    def test_all_detectors_produce_valid_pressures(self):
        """
        All registered detectors must produce valid Pressure objects.
        
        Validates:
        - Output is a list
        - All items are Pressure objects
        - All required fields exist
        - magnitude ∈ [0, 1]
        - acceleration ∈ [-1, 1]
        - confidence ∈ [0, 1]
        - detected_at is timezone-aware
        - model_dump_json() succeeds
        """
        detectors = get_detectors()
        assert len(detectors) > 0, "No detectors registered"
        
        # Fixed UTC datetime for determinism
        fixed_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Synthetic features for testing
        synthetic_features = {
            "price": 4500.0,
            "volatility": 0.15,
            "volume": 1000000,
            "returns": 0.02,
            "convexity": 0.05,
        }
        
        for detector in detectors:
            # Call detect() with synthetic features
            pressures = detector.detect("TEST_SYMBOL", synthetic_features, fixed_now)
            
            # Assert output is a list
            assert isinstance(pressures, list), (
                f"Detector {detector.name} must return a list, got {type(pressures)}"
            )
            
            # Each detector should produce at least one pressure (or empty list is OK)
            for i, pressure in enumerate(pressures):
                # Assert Pressure object
                assert isinstance(pressure, Pressure), (
                    f"Detector {detector.name} pressure {i} must be Pressure instance"
                )
                
                # Assert required fields exist
                assert hasattr(pressure, "pressure_id"), "Missing pressure_id"
                assert hasattr(pressure, "pressure_type"), "Missing pressure_type"
                assert hasattr(pressure, "magnitude"), "Missing magnitude"
                assert hasattr(pressure, "acceleration"), "Missing acceleration"
                assert hasattr(pressure, "confidence"), "Missing confidence"
                assert hasattr(pressure, "detected_at"), "Missing detected_at"
                
                # Assert magnitude ∈ [0, 1]
                assert 0.0 <= pressure.magnitude <= 1.0, (
                    f"Detector {detector.name} pressure {i}: "
                    f"magnitude must be in [0, 1], got {pressure.magnitude}"
                )
                
                # Assert acceleration ∈ [-1, 1]
                assert -1.0 <= pressure.acceleration <= 1.0, (
                    f"Detector {detector.name} pressure {i}: "
                    f"acceleration must be in [-1, 1], got {pressure.acceleration}"
                )
                
                # Assert confidence ∈ [0, 1]
                assert 0.0 <= pressure.confidence <= 1.0, (
                    f"Detector {detector.name} pressure {i}: "
                    f"confidence must be in [0, 1], got {pressure.confidence}"
                )
                
                # Assert detected_at is timezone-aware
                assert pressure.detected_at.tzinfo is not None, (
                    f"Detector {detector.name} pressure {i}: "
                    "detected_at must be timezone-aware"
                )
                
                # Assert model_dump_json() succeeds
                try:
                    json_str = pressure.model_dump_json()
                    # Verify it's valid JSON
                    json.loads(json_str)
                except Exception as e:
                    pytest.fail(
                        f"Detector {detector.name} pressure {i}: "
                        f"model_dump_json() failed: {e}"
                    )
                
                # Assert all values are finite
                assert math.isfinite(pressure.magnitude), (
                    f"Detector {detector.name} pressure {i}: magnitude must be finite"
                )
                assert math.isfinite(pressure.acceleration), (
                    f"Detector {detector.name} pressure {i}: acceleration must be finite"
                )
                assert math.isfinite(pressure.confidence), (
                    f"Detector {detector.name} pressure {i}: confidence must be finite"
                )


class TestMathInvariants:
    """Tests for pure math functions."""
    
    def test_sigmoid_output_always_01(self):
        """Sigmoid output must always be in [0, 1]."""
        test_cases = [
            -100.0,
            -10.0,
            -1.0,
            0.0,
            1.0,
            10.0,
            100.0,
            float("inf"),
            float("-inf"),
        ]
        
        for z in test_cases:
            result = sigmoid(z)
            assert 0.0 <= result <= 1.0, (
                f"sigmoid({z}) = {result} must be in [0, 1]"
            )
            assert math.isfinite(result), f"sigmoid({z}) must be finite"
    
    def test_squash01_from_z_output_always_01(self):
        """squash01_from_z output must always be in [0, 1]."""
        test_cases = [
            -100.0,
            -10.0,
            -1.0,
            0.0,
            1.0,
            10.0,
            100.0,
        ]
        
        for z in test_cases:
            result = squash01_from_z(z)
            assert 0.0 <= result <= 1.0, (
                f"squash01_from_z({z}) = {result} must be in [0, 1]"
            )
            assert math.isfinite(result), f"squash01_from_z({z}) must be finite"
    
    def test_acceleration_always_m11(self):
        """acceleration_from_magnitudes must always return [-1, 1]."""
        test_cases = [
            (0.0, 0.0),
            (0.5, 0.0),
            (1.0, 0.0),
            (0.0, 1.0),
            (1.0, 0.5),
            (0.1, 0.9),
            (0.9, 0.1),
        ]
        
        for curr, prev in test_cases:
            result = acceleration_from_magnitudes(curr, prev)
            assert -1.0 <= result <= 1.0, (
                f"acceleration_from_magnitudes({curr}, {prev}) = {result} "
                "must be in [-1, 1]"
            )
            assert math.isfinite(result), (
                f"acceleration_from_magnitudes({curr}, {prev}) must be finite"
            )
    
    def test_confidence_degrades_with_missingness(self):
        """Confidence should decrease as missing_ratio increases."""
        base_confidence = confidence_from_quality(
            missing_ratio=0.0,
            staleness_seconds=0.0,
            stability=1.0,
        )
        
        high_missing_confidence = confidence_from_quality(
            missing_ratio=0.9,
            staleness_seconds=0.0,
            stability=1.0,
        )
        
        assert high_missing_confidence < base_confidence, (
            "Confidence should decrease with higher missing_ratio"
        )
    
    def test_confidence_degrades_with_staleness(self):
        """Confidence should decrease as staleness increases."""
        fresh_confidence = confidence_from_quality(
            missing_ratio=0.0,
            staleness_seconds=0.0,
            stability=1.0,
        )
        
        stale_confidence = confidence_from_quality(
            missing_ratio=0.0,
            staleness_seconds=1000.0,
            stability=1.0,
        )
        
        assert stale_confidence < fresh_confidence, (
            "Confidence should decrease with higher staleness"
        )
    
    def test_confidence_increases_with_stability(self):
        """Confidence should increase as stability increases."""
        low_stability_confidence = confidence_from_quality(
            missing_ratio=0.0,
            staleness_seconds=0.0,
            stability=0.1,
        )
        
        high_stability_confidence = confidence_from_quality(
            missing_ratio=0.0,
            staleness_seconds=0.0,
            stability=1.0,
        )
        
        assert high_stability_confidence > low_stability_confidence, (
            "Confidence should increase with higher stability"
        )
    
    def test_confidence_always_01(self):
        """confidence_from_quality must always return [0, 1]."""
        test_cases = [
            (0.0, 0.0, 1.0),
            (0.5, 100.0, 0.5),
            (1.0, 10000.0, 0.0),
            (0.0, 0.0, 0.0),
        ]
        
        for missing_ratio, staleness, stability in test_cases:
            result = confidence_from_quality(
                missing_ratio=missing_ratio,
                staleness_seconds=staleness,
                stability=stability,
            )
            assert 0.0 <= result <= 1.0, (
                f"confidence_from_quality({missing_ratio}, {staleness}, {stability}) = "
                f"{result} must be in [0, 1]"
            )
            assert math.isfinite(result), "Confidence must be finite"


class TestValidationInvariants:
    """Tests for validation helpers."""
    
    def test_ensure_01_clamps_and_validates(self):
        """ensure_01 must clamp to [0, 1] and reject NaN/inf."""
        # Valid values
        assert ensure_01("test", 0.0) == 0.0
        assert ensure_01("test", 0.5) == 0.5
        assert ensure_01("test", 1.0) == 1.0
        
        # Clamping
        assert ensure_01("test", -1.0) == 0.0
        assert ensure_01("test", 2.0) == 1.0
        
        # Reject NaN/inf
        with pytest.raises(ValueError):
            ensure_01("test", float("nan"))
        
        with pytest.raises(ValueError):
            ensure_01("test", float("inf"))
    
    def test_ensure_m11_clamps_and_validates(self):
        """ensure_m11 must clamp to [-1, 1] and reject NaN/inf."""
        # Valid values
        assert ensure_m11("test", -1.0) == -1.0
        assert ensure_m11("test", 0.0) == 0.0
        assert ensure_m11("test", 1.0) == 1.0
        
        # Clamping
        assert ensure_m11("test", -2.0) == -1.0
        assert ensure_m11("test", 2.0) == 1.0
        
        # Reject NaN/inf
        with pytest.raises(ValueError):
            ensure_m11("test", float("nan"))
        
        with pytest.raises(ValueError):
            ensure_m11("test", float("inf"))
    
    def test_require_finite_rejects_nan_inf(self):
        """require_finite must reject NaN and inf."""
        # Valid values
        assert require_finite("test", 0.0) == 0.0
        assert require_finite("test", 100.0) == 100.0
        
        # Reject NaN/inf
        with pytest.raises(ValueError):
            require_finite("test", float("nan"))
        
        with pytest.raises(ValueError):
            require_finite("test", float("inf"))
        
        with pytest.raises(ValueError):
            require_finite("test", float("-inf"))


