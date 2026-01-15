"""
Schwab OAuth bootstrap helpers (manual, one-time).

Security / invariants:
- No network calls except inside exchange_code_for_token().
- No environment variable reads in this module.
- Never print/log access tokens or refresh tokens.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode


# NOTE: These are Schwab OAuth endpoints. Keep OAuth + HTTP logic isolated here.
_AUTHORIZE_URL = "https://api.schwabapi.com/v1/oauth/authorize"
_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


def generate_pkce_verifier() -> str:
    """
    Generate a high-entropy PKCE code_verifier (URL-safe).
    """
    # 86 chars or longer; token_urlsafe(64) yields ~86 chars.
    return secrets.token_urlsafe(64)


def pkce_challenge_s256(verifier: str) -> str:
    """
    Compute PKCE S256 code_challenge from verifier.
    """
    if not verifier:
        raise ValueError("verifier is required for PKCE challenge")
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_authorize_url(
    client_id: str,
    redirect_uri: str,
    scopes: List[str],
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: str = "S256",
) -> Tuple[str, str]:
    """
    Build the Schwab authorization URL the user should open manually.

    Args:
        client_id: Schwab application client id
        redirect_uri: registered redirect URI
        scopes: list of scopes (space-separated per OAuth spec)
    """
    if not client_id or not redirect_uri:
        raise ValueError("client_id and redirect_uri are required")

    scope_str = " ".join([s.strip() for s in scopes if s and s.strip()])
    if not scope_str:
        raise ValueError("at least one scope is required")

    if state is None:
        state = secrets.token_urlsafe(16)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope_str,
        "state": state,
    }

    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = code_challenge_method

    query = urlencode(params)
    return f"{_AUTHORIZE_URL}?{query}", state


def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    code_verifier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Exchange an authorization code for an access token + refresh token.

    Network calls happen ONLY here.
    """
    if not client_id or not client_secret or not redirect_uri or not code:
        raise ValueError("client_id, client_secret, redirect_uri, and code are required")

    try:
        import requests  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "requests is required to run Schwab OAuth bootstrap. Install 'requests'."
        ) from e

    # Schwab token exchange is form-encoded.
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if code_verifier:
        data["code_verifier"] = code_verifier

    try:
        resp = requests.post(_TOKEN_URL, data=data, timeout=30)
    except Exception as e:
        raise RuntimeError("Failed to reach Schwab token endpoint.") from e

    if resp.status_code != 200:
        # Do NOT print response body (may contain tokens or sensitive details).
        raise RuntimeError(f"Token exchange failed with HTTP {resp.status_code}.")

    try:
        token = resp.json()
    except Exception as e:
        raise RuntimeError("Token exchange response was not valid JSON.") from e

    if not isinstance(token, dict):
        raise RuntimeError("Token exchange response must be a JSON object.")

    return token


def load_token(token_path: str) -> Optional[Dict[str, Any]]:
    """Load token JSON from disk. Returns None if missing."""
    try:
        with open(token_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        raise ValueError("Token file exists but is not valid JSON.") from e

    if not isinstance(obj, dict):
        raise ValueError("Token file must contain a JSON object.")
    return obj


def save_token(token_path: str, token: Dict[str, Any]) -> None:
    """
    Save token JSON to disk, adding created_at (epoch seconds, UTC).

    Also adds expires_at when expires_in is present (created_at + expires_in).
    """
    if not isinstance(token, dict):
        raise ValueError("token must be a dict")

    created_at = int(time.time())
    out = dict(token)
    out["created_at"] = created_at

    expires_in = out.get("expires_in")
    if isinstance(expires_in, (int, float)):
        try:
            out["expires_at"] = int(created_at + float(expires_in))
        except Exception:
            # keep deterministic: omit expires_at if malformed
            pass

    with open(token_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")


def redact_token_for_print(token: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive token fields for printing.

    Removes access_token/refresh_token/id_token if present.
    """
    if not isinstance(token, dict):
        return {}

    redacted = dict(token)
    for k in ["access_token", "refresh_token", "id_token"]:
        if k in redacted:
            redacted[k] = "<redacted>"
    return redacted


def _approx_expiry_str(token: Dict[str, Any]) -> Optional[str]:
    """Best-effort helper to compute an approximate expiry time string."""
    expires_at = token.get("expires_at")
    if isinstance(expires_at, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(expires_at), tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            return None
    return None


