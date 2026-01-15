"""Provider-agnostic Bar validation helpers."""

from __future__ import annotations

import math
from typing import List

from .base import Bar


def validate_bars(bars: List[Bar]) -> None:
    """
    Validate Bar[] invariants.

    Raises ValueError if:
    - any Bar.ts is naive or non-UTC
    - not sorted ascending
    - duplicates remain
    - open/high/low/close are non-finite
    """
    if not isinstance(bars, list):
        raise ValueError("bars must be a list")

    # UTC + finiteness checks
    for i, b in enumerate(bars):
        if b.ts.tzinfo is None:
            raise ValueError(f"bar[{i}].ts is naive")
        offset = b.ts.tzinfo.utcoffset(b.ts)
        if offset is None or offset.total_seconds() != 0:
            raise ValueError(f"bar[{i}].ts is not UTC")

        for field_name in ("open", "high", "low", "close"):
            v = getattr(b, field_name)
            if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
                raise ValueError(f"bar[{i}].{field_name} is not finite")

    # Sorted + dedupe checks
    ts_list = [b.ts for b in bars]
    if ts_list != sorted(ts_list):
        raise ValueError("bars are not sorted ascending by ts")

    if len(ts_list) != len(set(ts_list)):
        raise ValueError("bars contain duplicate timestamps")


