"""Tests for FixtureDataProvider (offline, deterministic)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from market_risk_os.io.providers.fixtures import FixtureDataProvider
from market_risk_os.io.providers.validation import validate_bars


def test_fixture_data_provider_returns_bars_deterministically():
    fixture_path = Path(__file__).parent / "fixtures" / "bars_spx_like.json"
    provider = FixtureDataProvider(fixture_path)

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    bars1 = provider.get_bars("SPX", start, end, timeframe="1D")
    bars2 = provider.get_bars("SPX", start, end, timeframe="1D")

    assert isinstance(bars1, list)
    assert len(bars1) > 0
    assert bars1 == bars2
    validate_bars(bars1)

    # Ensure all timestamps are UTC aware
    for b in bars1:
        assert b.ts.tzinfo is not None
        assert b.ts.tzinfo.utcoffset(b.ts).total_seconds() == 0


