# Pressure Detectors

This module implements the pressure detection layer for market risk analysis.

## Overview

Pressure detectors identify various types of market pressures (volatility, liquidity, correlation, etc.) and produce `Pressure` objects with bounded, validated outputs.

## Architecture

### Base Interface

All detectors implement `BasePressureDetector` which requires:

- `name: str` - Unique detector name
- `pressure_type: PressureType` - Type of pressure detected
- `time_horizon: str` - Time horizon (e.g., "short_term", "medium_term")
- `detect(symbol: str, features: dict, now: datetime) -> list[Pressure]` - Detection method

### Detector Template

The canonical detector template is in `templates/detector_template.py`. This provides:

- Automatic UTC timestamp enforcement
- Bounded output validation (magnitude, acceleration, confidence)
- Confidence computation from quality metrics
- Acceleration computation from magnitude changes

## Creating a New Detector

### Step 1: Use the Template

Create a new detector class inheriting from `TemplateDetector`:

```python
from market_risk_os.pressures.templates.detector_template import TemplateDetector
from market_risk_os.core import PressureType, Directionality

class MyDetector(TemplateDetector):
    name = "my_detector"
    pressure_type = PressureType.VOLATILITY  # Choose appropriate type
    time_horizon = "short_term"
    
    def compute_raw(self, symbol: str, features: dict, now: datetime):
        # Implement your detection logic here
        # Return list of dicts with raw values
        return [{
            "magnitude": 0.5,  # Raw magnitude or z-score
            "directionality": Directionality.NEUTRAL,
            "missing_ratio": 0.0,
            "staleness_seconds": 0.0,
            "stability": 0.8,
            "is_zscore": False,  # True if magnitude is a z-score
        }]
    
    def explain(self, symbol, raw, magnitude, acceleration, confidence):
        # Optional: custom explanation
        return f"Custom explanation for {symbol}"
```

### Step 2: Register the Detector

Add your detector to `registry.py` in `register_default_detectors()`:

```python
def register_default_detectors(self) -> None:
    # ... existing registrations ...
    
    from .my_detector import MyDetector
    self.register_detector(MyDetector())
```

### Step 3: Test

The invariant tests in `tests/test_pressure_invariants.py` will automatically validate your detector. Ensure:

- All outputs are bounded (magnitude ∈ [0,1], acceleration ∈ [-1,1], confidence ∈ [0,1])
- All values are finite (no NaN/inf)
- Timestamps are timezone-aware UTC
- JSON serialization works

## Math Utilities

Use functions from `features/transforms.py`:

- `squash01_from_z(z)` - Convert z-score to [0,1]
- `acceleration_from_magnitudes(curr, prev)` - Compute acceleration
- `confidence_from_quality(...)` - Compute confidence from quality metrics
- `rolling_mean()`, `rolling_std()`, `zscore()`, `sigmoid()`, `ema()`, `clamp()`

## Validation

Always use validation helpers from `core/validation.py`:

- `ensure_01(name, x)` - Ensure value in [0,1]
- `ensure_m11(name, x)` - Ensure value in [-1,1]
- `require_finite(name, x)` - Ensure value is finite

The template automatically applies these, but use them directly if needed.

## Constraints

- **No trading language**: Do not use buy/sell, forecast, or trading terminology
- **Deterministic**: No randomness in computations
- **Bounded outputs**: All outputs must satisfy invariants
- **UTC timestamps**: All timestamps must be timezone-aware UTC
- **JSON serializable**: All Pressure objects must serialize to JSON

## Registry

The detector registry (`registry.py`) provides:

- `register_detector(detector)` - Register a detector
- `get_detectors()` - Get all registered detectors
- `register_default_detectors()` - Register default detectors (idempotent)
- `clear_registry_for_tests()` - Clear registry (testing only)

The orchestrator uses the registry to discover and run detectors automatically.

