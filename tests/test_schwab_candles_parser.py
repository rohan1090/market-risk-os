"""Invariant tests for Schwab candles -> Bar[] parser (offline, deterministic)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from market_risk_os.io.providers.base import Bar
from market_risk_os.io.providers.schwab_parser import parse_schwab_candles, validate_bars


def _fixture_payload() -> dict:
    path = Path(__file__).parent / "fixtures" / "schwab_candles_sample.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class TestSchwabCandlesParser:
    def test_parse_returns_bars_sorted_utc(self):
        payload = _fixture_payload()
        bars = parse_schwab_candles(payload)

        assert isinstance(bars, list)
        assert len(bars) > 0

        # All timestamps tz-aware UTC
        for b in bars:
            assert b.ts.tzinfo is not None
            assert b.ts.tzinfo.utcoffset(b.ts).total_seconds() == 0

        # Sorted ascending + no dupes + finite prices
        validate_bars(bars)

    def test_parse_dedupes_timestamps(self):
        payload = _fixture_payload()
        base = payload["candles"][0].copy()
        dup = payload["candles"][0].copy()
        dup["open"] = base["open"] + 123.0  # would differ if second were kept

        payload2 = {**payload, "candles": [base, dup] + payload["candles"][1:]}
        bars = parse_schwab_candles(payload2)

        # Must drop duplicate deterministically (keep first)
        assert len(bars) == len(parse_schwab_candles(payload))
        assert bars[0].open == float(base["open"])
        validate_bars(bars)

    def test_parse_skips_invalid_candles_deterministically(self):
        valid1 = {"datetime": 1700000000000, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10}
        invalid_nan = {"datetime": 1700086400000, "open": float("nan"), "high": 2.0, "low": 0.5, "close": 1.5}
        invalid_none = {"datetime": 1700172800000, "open": 1.0, "high": None, "low": 0.5, "close": 1.5}
        valid2 = {"datetime": 1700259200000, "open": 1.5, "high": 2.5, "low": 1.0, "close": 2.0}

        payload = {"symbol": "SPX", "candles": [valid1, invalid_nan, invalid_none, valid2]}
        bars = parse_schwab_candles(payload)

        assert len(bars) == 2
        assert bars[0].close == 1.5
        assert bars[1].close == 2.0
        validate_bars(bars)

    def test_validate_bars_raises_on_naive_or_unsorted(self):
        # Naive dt: Bar(ts=...) auto-normalizes to UTC, so we pass a Bar-like object
        # to ensure validate_bars catches naive timestamps.
        b1 = SimpleNamespace(
            ts=datetime(2024, 1, 1, 0, 0, 0),  # naive
            open=1.0,
            high=2.0,
            low=0.5,
            close=1.5,
        )
        with pytest.raises(ValueError):
            validate_bars([b1])

        # Unsorted
        b2 = Bar(ts=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc), open=1.0, high=2.0, low=0.5, close=1.5)
        b3 = Bar(ts=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), open=1.0, high=2.0, low=0.5, close=1.5)
        with pytest.raises(ValueError):
            validate_bars([b2, b3])


