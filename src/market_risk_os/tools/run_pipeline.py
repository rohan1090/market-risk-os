"""
Manual pipeline runner (integration-only).

Provider selection is explicit and safe:
- Default is fixtures (offline).
- Yahoo and Schwab providers are only imported when selected.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from ..pipeline import PipelineOrchestrator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Market Risk OS pipeline.")
    parser.add_argument("--symbol", default="SPX", help="Asset symbol to analyze")
    parser.add_argument(
        "--provider",
        choices=["fixtures", "yahoo", "schwab", "none"],
        default=os.getenv("PROVIDER", "fixtures"),
        help="Data provider to use (default: fixtures)",
    )
    parser.add_argument(
        "--fixture-path",
        default=os.getenv("FIXTURE_PATH", "tests/fixtures/bars_spx_like.json"),
        help="Path to fixtures JSON (used when provider=fixtures)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    provider = None
    if args.provider == "fixtures":
        from ..io.providers.fixtures import FixtureDataProvider

        provider = FixtureDataProvider(Path(args.fixture_path))
    elif args.provider == "yahoo":
        from ..io.providers.yahoo import YahooDataProvider

        provider = YahooDataProvider()
    elif args.provider == "schwab":
        from ..io.providers.schwab import SchwabDataProvider

        provider = SchwabDataProvider()
    elif args.provider == "none":
        provider = None

    orchestrator = PipelineOrchestrator(provider=provider)
    result = orchestrator.run(args.symbol)

    pressures = result.get("pressures", [])
    interactions = result.get("interactions", [])
    risk_state = result.get("risk_state")
    behavior_gate = result.get("behavior_gate")

    print(f"symbol: {result.get('symbol')}")
    print(f"pressures: {len(pressures)}")
    print(f"interactions: {len(interactions)}")
    if risk_state is not None:
        print(f"risk_state: {risk_state.dominant_state}")
    if behavior_gate is not None:
        print(f"behavior_gate: {behavior_gate.gate_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


