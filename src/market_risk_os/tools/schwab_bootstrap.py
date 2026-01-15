"""
Manual Schwab OAuth bootstrap CLI (integration/runtime-only).

This tool:
- Prints an authorization URL (does NOT open a browser).
- Prompts the user to paste back the redirect URL (or just the code).
- Exchanges the code for tokens and writes them to SCHWAB_TOKEN_PATH.

Security:
- Never prints access/refresh tokens.
- Never logs headers or full responses.
- Performs network calls ONLY during code exchange.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from ..io.providers.schwab_oauth import (
    build_authorize_url,
    exchange_code_for_token,
    generate_pkce_verifier,
    pkce_challenge_s256,
    save_token,
)


DEFAULT_SCOPES = [
    "openid",
]


def _read_required_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v.strip()


def _extract_code_and_state(user_input: str) -> tuple[str, str | None]:
    s = (user_input or "").strip()
    if not s:
        raise RuntimeError("No code provided.")

    # If it's a URL, parse out ?code=...
    if "://" in s:
        parsed = urlparse(s)
        qs = parse_qs(parsed.query)
        if "error" in qs:
            raise RuntimeError(f"Authorization error returned in redirect: {qs.get('error')}")
        code_vals = qs.get("code")
        if not code_vals or not code_vals[0]:
            raise RuntimeError("Could not find 'code' query parameter in the pasted URL.")
        state_vals = qs.get("state")
        state = state_vals[0].strip() if state_vals and state_vals[0] else None
        return code_vals[0].strip(), state

    # Otherwise treat it as a raw code
    return s, None


def main() -> int:
    print("=== Schwab OAuth Bootstrap (integration-only) ===")
    print("This tool is intended for runtime integration only.")
    print("Unit tests must remain offline and must not import or run this tool.")
    print("This tool performs network calls only during token exchange.")
    print()

    client_id = _read_required_env("SCHWAB_CLIENT_ID")
    client_secret = _read_required_env("SCHWAB_CLIENT_SECRET")
    redirect_uri = _read_required_env("SCHWAB_REDIRECT_URI")
    token_path = os.getenv("SCHWAB_TOKEN_PATH", ".schwab_token.json").strip()

    scopes_env = os.getenv("SCHWAB_SCOPES", "").strip()
    scopes = scopes_env.split() if scopes_env else DEFAULT_SCOPES

    verifier = generate_pkce_verifier()
    challenge = pkce_challenge_s256(verifier)
    auth_url, expected_state = build_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        code_challenge=challenge,
    )

    print("1) Open this URL in your browser and complete Schwab login/consent:")
    print(auth_url)
    print()
    print("2) After login, you will be redirected to your SCHWAB_REDIRECT_URI with '?code=...'.")
    print("3) Paste either the FULL redirect URL or just the authorization code below.")
    print()

    user_input = input("Paste the full redirect URL (preferred) or paste just the code= value: ").strip()
    code, returned_state = _extract_code_and_state(user_input)
    if returned_state is not None and returned_state != expected_state:
        raise RuntimeError("State mismatch. Aborting for safety.")
    if returned_state is None:
        print("Warning: state could not be verified (no URL provided). Proceeding without state validation.")

    print()
    print("Exchanging code for token (this performs a network call)...")

    token = exchange_code_for_token(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        code=code,
        code_verifier=verifier,
    )

    save_token(token_path, token)

    print()
    print(f"Token saved to {token_path}")
    expires_in = token.get("expires_in")
    created_at = token.get("created_at")
    if isinstance(created_at, (int, float)) and isinstance(expires_in, (int, float)):
        try:
            approx = float(created_at) + float(expires_in)
            dt = datetime.fromtimestamp(approx, tz=timezone.utc).isoformat()
            print(f"Approximate expiry (UTC): {dt}")
        except Exception:
            pass

    print()
    print("Reminder: ensure .env / .env.* and your token file are gitignored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


