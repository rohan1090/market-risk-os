# Market Risk OS

A comprehensive market risk analysis system that detects pressures, evaluates interactions, estimates risk states, and controls behavior gates.

## Overview

Market Risk OS provides a pipeline for:
1. **Feature Extraction** - Extract market features from asset data
2. **Pressure Detection** - Detect various types of market pressures (volatility, convexity, etc.)
3. **Interaction Evaluation** - Evaluate how pressures interact using graph-based analysis
4. **Risk State Estimation** - Estimate overall risk state with scoring and ambiguity calculation
5. **Behavior Gate Control** - Create behavior gates based on risk state policies

## Installation

```bash
pip install -e .
```

## Usage

### CLI Entrypoint

Run the pipeline for a specific symbol:

```bash
python -m market_risk_os.run --symbol SPX
```

#### Options

- `--symbol`: Asset symbol to analyze (required, e.g., SPX)
- `--output`: Output format - `json` or `pretty` (default: `pretty`)

#### Examples

Pretty output:
```bash
python -m market_risk_os.run --symbol SPX
```

JSON output:
```bash
python -m market_risk_os.run --symbol SPX --output json
```

### Programmatic Usage

```python
from market_risk_os.pipeline import PipelineOrchestrator

# Initialize orchestrator
orchestrator = PipelineOrchestrator()

# Run pipeline
result = orchestrator.run("SPX")

# Access results
pressures = result["pressures"]
interactions = result["interactions"]
risk_state = result["risk_state"]
behavior_gate = result["behavior_gate"]
```

### Using Schwab Provider (Optional)

To use the Schwab data provider for real market data:

1. Set environment variables (see `.env.example`):
   ```bash
   export SCHWAB_CLIENT_ID=your_client_id
   export SCHWAB_CLIENT_SECRET=your_client_secret
   export SCHWAB_REDIRECT_URI=your_redirect_uri
   export SCHWAB_TOKEN_PATH=.schwab_token.json
   ```

2. Initialize orchestrator with Schwab provider:
   ```python
   from market_risk_os.io.providers import SchwabDataProvider
   from market_risk_os.pipeline import PipelineOrchestrator
   
   provider = SchwabDataProvider()
   orchestrator = PipelineOrchestrator(provider=provider)
   result = orchestrator.run("SPX")
   ```

**Note**: The Schwab provider is currently a skeleton implementation. Full OAuth integration is required for production use. Unit tests use fake providers and do not require Schwab credentials.

## Architecture

### Components

- **FeatureStore** (`features/feature_store.py`): Stubbed feature extraction
- **Pressure Detectors** (`pressures/`): Base class and implementations (volatility, convexity)
- **Interaction Evaluator** (`interactions/base.py`): Graph-based interaction evaluation
- **Risk State Estimator** (`state/estimator.py`): Scoring and ambiguity calculation
- **Behavior Gate Controller** (`gate/controller.py`): Policy-based gate creation
- **Pipeline Orchestrator** (`pipeline/orchestrator.py`): Main pipeline coordination

## Models

All models use Pydantic v2 with strict validation:

- `Pressure`: Market pressure with magnitude, acceleration, confidence
- `PressureInteraction`: Interactions between pressures
- `RiskState`: Overall risk state with instability score and ambiguity
- `BehaviorGate`: Gate controlling allowed/forbidden behaviors

## License

[Add your license here]

