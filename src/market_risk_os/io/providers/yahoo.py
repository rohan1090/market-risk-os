"""
Yahoo provider is for manual development only; not guaranteed stable; never used in unit tests.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...core.time import ensure_utc
from .base import Bar, MarketDataProvider
from .validation import validate_bars


class YahooDataProvider(MarketDataProvider):
    """
    Runtime-only Yahoo provider for manual development.

    No network calls happen at import time; requests is imported inside get_bars().
    """

    _CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D",
    ) -> List[Bar]:
        if timeframe != "1D":
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Only '1D' is supported.")

        start_utc = ensure_utc(start)
        end_utc = ensure_utc(end)

        interval = "1d"
        period1 = int(start_utc.timestamp())
        period2 = int(end_utc.timestamp())

        url = self._CHART_URL.format(symbol=symbol)
        params = {
            "interval": interval,
            "period1": period1,
            "period2": period2,
            "events": "div,splits",
        }

        try:
            import requests  # type: ignore
        except Exception as e:
            raise RuntimeError("requests is required to use YahooDataProvider.") from e

        try:
            resp = requests.get(url, params=params, timeout=30)
        except Exception as e:
            raise RuntimeError("Yahoo chart request failed.") from e

        if resp.status_code != 200:
            raise RuntimeError(f"Yahoo chart request failed with status {resp.status_code}.")

        try:
            payload = resp.json()
        except Exception as e:
            raise ValueError("Yahoo chart response was not valid JSON.") from e

        bars = self._parse_chart_payload(payload)
        validate_bars(bars)
        return bars

    @staticmethod
    def _parse_chart_payload(payload: Dict[str, Any]) -> List[Bar]:
        try:
            result = payload["chart"]["result"][0]
        except Exception as e:
            raise ValueError("Yahoo chart payload missing expected fields.") from e

        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators", {}).get("quote", [])
        quote = indicators[0] if indicators else {}

        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        bars: List[Bar] = []
        for i, ts in enumerate(timestamps):
            dt = YahooDataProvider._ts_to_utc(ts)
            if dt is None:
                continue

            o = YahooDataProvider._finite_float(opens[i] if i < len(opens) else None)
            h = YahooDataProvider._finite_float(highs[i] if i < len(highs) else None)
            l = YahooDataProvider._finite_float(lows[i] if i < len(lows) else None)
            c = YahooDataProvider._finite_float(closes[i] if i < len(closes) else None)
            if o is None or h is None or l is None or c is None:
                continue

            v = YahooDataProvider._finite_float(volumes[i] if i < len(volumes) else None)
            if v is None:
                v = 0.0

            bars.append(Bar(ts=dt, open=o, high=h, low=l, close=c, volume=v))

        bars.sort(key=lambda b: b.ts)
        return bars

    @staticmethod
    def _ts_to_utc(value: Any) -> Optional[datetime]:
        try:
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                return None
            return ensure_utc(datetime.fromtimestamp(float(value), tz=timezone.utc))
        except Exception:
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


