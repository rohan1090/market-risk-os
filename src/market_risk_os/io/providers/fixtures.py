"""Fixture data provider (offline, deterministic)."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from ...core.time import ensure_utc
from .base import Bar, MarketDataProvider
from .validation import validate_bars


class FixtureDataProvider(MarketDataProvider):
    """
    Deterministic provider that reads bars from a local fixture file.

    The fixture file is read only when get_bars() is called.
    """

    def __init__(self, fixture_path: Union[str, Path]):
        self.fixture_path = Path(fixture_path)

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D",
    ) -> List[Bar]:
        """
        Load bars from fixture file and return filtered bars.

        Fixture formats supported:
        - list of dicts: [{"ts": "...", "open":..., "high":..., "low":..., "close":..., "volume":...}, ...]
        - dict mapping symbol -> list of dicts

        Filtering: inclusive start, exclusive end.
        """
        if timeframe != "1D":
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Only '1D' is supported.")

        payload = self._load_fixture()
        rows = self._select_rows(payload, symbol)

        start_utc = ensure_utc(start)
        end_utc = ensure_utc(end)

        bars: List[Bar] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ts = self._parse_ts(row.get("ts") or row.get("datetime") or row.get("timestamp"))
            if ts is None:
                continue

            if not (start_utc <= ts < end_utc):
                continue

            o = self._finite_float(row.get("open"))
            h = self._finite_float(row.get("high"))
            l = self._finite_float(row.get("low"))
            c = self._finite_float(row.get("close"))
            if o is None or h is None or l is None or c is None:
                continue

            v = self._finite_float(row.get("volume"))
            if v is None:
                v = 0.0

            bars.append(Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v))

        # Ensure ascending order before validation
        bars.sort(key=lambda b: b.ts)
        validate_bars(bars)
        return bars

    def _load_fixture(self) -> Any:
        try:
            with self.fixture_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as e:
            raise ValueError(f"Fixture file not found: {self.fixture_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Fixture file is not valid JSON: {self.fixture_path}") from e

    @staticmethod
    def _select_rows(payload: Any, symbol: str) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if symbol in payload and isinstance(payload[symbol], list):
                return payload[symbol]
            # Fallback: first list value in dict
            for v in payload.values():
                if isinstance(v, list):
                    return v
        raise ValueError("Unsupported fixture format; expected list or dict mapping symbol->list.")

    @staticmethod
    def _parse_ts(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                return None
            v = float(value)
            seconds = v / 1000.0 if v > 1e11 else v
            try:
                return ensure_utc(datetime.fromtimestamp(seconds))
            except Exception:
                return None
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return ensure_utc(datetime.fromisoformat(s))
            except Exception:
                return None
        return None

    @staticmethod
    def _finite_float(x: Any) -> Optional[float]:
        if x is None:
            return None
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(v):
            return None
        return v


