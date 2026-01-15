"""Pure, deterministic parsing utilities for Schwab candle payloads.

Security / invariants:
- No network calls.
- No environment variable reads.
- No side effects besides returning Bar[] / raising ValueError from validate_bars().
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from ...core.time import ensure_utc
from .base import Bar
from .validation import validate_bars


def _parse_ts(value: Any) -> Optional[datetime]:
    """Parse Schwab candle timestamps from epoch(ms|s) or ISO-8601 strings."""
    if value is None:
        return None

    # Epoch milliseconds / seconds
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            return None
        v = float(value)
        # Heuristic: > 1e11 is almost certainly epoch-ms (e.g. 1700000000000)
        seconds = v / 1000.0 if v > 1e11 else v
        try:
            return ensure_utc(datetime.fromtimestamp(seconds))
        except (OverflowError, OSError, ValueError):
            return None

    # ISO-8601 string
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Accept trailing "Z"
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        return ensure_utc(dt)

    return None


def _finite_float(x: Any) -> Optional[float]:
    """Convert to float and ensure finite."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def parse_schwab_candles(payload: Dict[str, Any]) -> List[Bar]:
    """
    Convert Schwab candle JSON payload (dict) into list[Bar].

    Requirements:
    - Read candles from payload["candles"] (primary).
    - Each candle must include timestamp + open/high/low/close. Volume optional.
    - Timestamp may be epoch-ms, epoch-s, or ISO-8601 string.
    - Normalize timestamps to timezone-aware UTC.
    - Return bars sorted ascending by ts.
    - Drop duplicate timestamps deterministically (keep first).
    - Skip invalid candles deterministically (non-finite/missing required fields).
    - Raise ValueError only if payload is structurally unusable.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    candles = payload.get("candles")
    if not isinstance(candles, list):
        raise ValueError("payload missing 'candles' list")

    bars: List[Bar] = []
    seen_ts: set[datetime] = set()

    for candle in candles:
        if not isinstance(candle, dict):
            continue

        ts = _parse_ts(
            candle.get("datetime")
            if "datetime" in candle
            else candle.get("timestamp", candle.get("time"))
        )
        if ts is None:
            continue

        # Deduplicate deterministically: keep first candle for each ts
        if ts in seen_ts:
            continue

        o = _finite_float(candle.get("open"))
        h = _finite_float(candle.get("high"))
        l = _finite_float(candle.get("low"))
        c = _finite_float(candle.get("close"))
        if o is None or h is None or l is None or c is None:
            continue

        v = _finite_float(candle.get("volume"))
        if v is None:
            v = 0.0

        try:
            bar = Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v)
        except Exception:
            # Bar validates ts to UTC; numeric checks handled above.
            continue

        bars.append(bar)
        seen_ts.add(ts)

    bars.sort(key=lambda b: b.ts)
    return bars


