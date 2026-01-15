"""
Live Schwab provider. Intended for runtime integration only.
Unit tests must remain offline and must not import this module.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...core.time import ensure_utc
from .base import Bar, MarketDataProvider
from .schwab_parser import parse_schwab_candles, validate_bars


class SchwabDataProvider(MarketDataProvider):
    """
    Live Schwab provider. Intended for runtime integration only.

    Unit tests must remain offline and must not import this module.
    """

    # NOTE: Keep this constant; do not read env vars at import time.
    _PRICE_HISTORY_URL = "https://api.schwabapi.com/marketdata/v1/pricehistory"

    def _load_token(self, token_path: str) -> Dict[str, Any]:
        """
        Load OAuth token JSON from disk.

        No refresh logic here. If token missing/expired, callers must fail loudly.
        """
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                token = json.load(f)
        except FileNotFoundError as e:
            raise RuntimeError(
                "Schwab token file not found. Manual OAuth is required. "
                "Create a token JSON file and set SCHWAB_TOKEN_PATH to its location."
            ) from e
        except json.JSONDecodeError as e:
            raise RuntimeError("Schwab token file is not valid JSON.") from e

        if not isinstance(token, dict):
            raise RuntimeError("Schwab token file must contain a JSON object.")
        return token

    def _is_token_expired(self, token: Dict[str, Any], now_utc: datetime) -> bool:
        """
        Determine whether a token is expired.

        Supported shapes:
        - {"access_token": "...", "expires_at": <epoch seconds>}
        - {"access_token": "...", "expires_in": <seconds>, "obtained_at": <epoch seconds>}
        """
        if not isinstance(token, dict):
            return True

        expires_at = token.get("expires_at")
        if isinstance(expires_at, (int, float)):
            try:
                exp = float(expires_at)
            except Exception:
                return True
            # Consider expired if within 30 seconds of expiry
            return now_utc.timestamp() >= (exp - 30.0)

        expires_in = token.get("expires_in")
        obtained_at = token.get("obtained_at") or token.get("created_at") or token.get("issued_at")
        if isinstance(expires_in, (int, float)) and isinstance(obtained_at, (int, float)):
            try:
                exp = float(obtained_at) + float(expires_in)
            except Exception:
                return True
            return now_utc.timestamp() >= (exp - 30.0)

        # If we can't reason about expiry, treat as expired (safe default)
        return True

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D",
    ) -> List[Bar]:
        """
        Fetch historical candles from Schwab and convert to Bar[] using the existing parser.

        Responsibilities:
        - Read credentials ONLY inside this method:
          SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET, SCHWAB_REDIRECT_URI, SCHWAB_TOKEN_PATH
        - Load OAuth token from SCHWAB_TOKEN_PATH
        - If token missing/expired: raise RuntimeError with manual OAuth instructions
        - Call Schwab price history endpoint
        - parse_schwab_candles(payload) + validate_bars(bars)
        - Return validated Bar[]
        """
        # Guardrails: env vars read only here (not at import time)
        client_id = os.getenv("SCHWAB_CLIENT_ID")
        client_secret = os.getenv("SCHWAB_CLIENT_SECRET")
        redirect_uri = os.getenv("SCHWAB_REDIRECT_URI")
        token_path = os.getenv("SCHWAB_TOKEN_PATH", ".schwab_token.json")

        if not client_id or not client_secret or not redirect_uri:
            raise RuntimeError(
                "Missing Schwab credentials. Set SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET, "
                "and SCHWAB_REDIRECT_URI environment variables."
            )

        now_utc = ensure_utc(datetime.now(timezone.utc))
        token = self._load_token(token_path)

        access_token = token.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise RuntimeError(
                "Schwab token missing access_token. Manual OAuth is required to create a valid token file."
            )

        if self._is_token_expired(token, now_utc):
            raise RuntimeError(
                "Schwab token is missing expiry metadata or is expired. Manual OAuth is required; "
                "no automatic refresh is implemented."
            )

        # Normalize input timestamps to UTC
        start_utc = ensure_utc(start)
        end_utc = ensure_utc(end)

        # Minimal timeframe support (extend in integration as needed)
        if timeframe != "1D":
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Only '1D' is supported.")

        # Schwab expects epoch milliseconds
        start_ms = int(start_utc.timestamp() * 1000)
        end_ms = int(end_utc.timestamp() * 1000)

        params = {
            "symbol": symbol,
            "startDate": start_ms,
            "endDate": end_ms,
            "frequencyType": "daily",
            "frequency": 1,
            "needExtendedHoursData": "false",
        }

        headers = {
            # Do NOT log this token or headers.
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            import requests  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "requests is required for SchwabDataProvider at runtime. Install 'requests' to use this provider."
            ) from e

        try:
            resp = requests.get(self._PRICE_HISTORY_URL, params=params, headers=headers, timeout=30)
        except Exception as e:
            # Do not include headers/tokens in exception messages.
            raise RuntimeError("Failed to call Schwab price history endpoint.") from e

        if resp.status_code == 401:
            raise RuntimeError("Schwab API unauthorized (401). Token may be invalid or expired.")
        if resp.status_code != 200:
            raise RuntimeError(f"Schwab API request failed with status {resp.status_code}.")

        try:
            payload = resp.json()
        except Exception as e:
            raise ValueError("Schwab API response was not valid JSON.") from e

        try:
            bars = parse_schwab_candles(payload)
            validate_bars(bars)
        except Exception as e:
            # Do not dump payload; keep errors audit-safe.
            raise ValueError("Failed to parse Schwab candles payload into Bar objects.") from e

        return bars


