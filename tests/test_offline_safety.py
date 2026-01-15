"""Offline safety guard tests."""

import sys


def test_market_risk_os_import_does_not_load_yahoo():
    import market_risk_os  # noqa: F401

    assert "market_risk_os.io.providers.yahoo" not in sys.modules


