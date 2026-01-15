"""Deterministic bar fixtures for testing."""

import math
import random
from datetime import datetime, timedelta, timezone

from market_risk_os.io.providers import Bar


def generate_bars_spx_like(
    start_date: datetime = None,
    num_bars: int = 120,
) -> list[Bar]:
    """
    Generate deterministic SPX-like bars with a volatility regime shift.
    
    First 80 days: low volatility (std ~0.01)
    Last 40 days: higher volatility (std ~0.03)
    
    Args:
        start_date: Start date (defaults to 120 days ago)
        num_bars: Number of bars to generate (default 120)
    
    Returns:
        List of Bar objects sorted by timestamp (ascending)
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=num_bars)
    
    start_date = start_date.replace(tzinfo=timezone.utc)
    
    # Use fixed seed for determinism
    rng = random.Random(42)
    
    bars = []
    base_price = 4500.0
    
    for i in range(num_bars):
        ts = start_date + timedelta(days=i)
        
        # Determine volatility regime
        if i < 80:
            # Low volatility regime
            daily_vol = 0.01
        else:
            # High volatility regime
            daily_vol = 0.03
        
        # Generate price movement
        # Use random walk with drift
        drift = 0.0001  # Small upward drift
        shock = rng.gauss(0.0, daily_vol)
        
        if i == 0:
            open_price = base_price
        else:
            open_price = bars[-1].close
        
        # Compute high/low/close from open
        price_change = open_price * (drift + shock)
        close_price = open_price + price_change
        
        # High and low are within reasonable range of open/close
        high_price = max(open_price, close_price) * (1.0 + abs(rng.gauss(0.0, daily_vol * 0.5)))
        low_price = min(open_price, close_price) * (1.0 - abs(rng.gauss(0.0, daily_vol * 0.5)))
        
        # Ensure high >= max(open, close) and low <= min(open, close)
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Volume (arbitrary but deterministic)
        volume = 1000000 + int(rng.uniform(-100000, 100000))
        
        bar = Bar(
            ts=ts,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=float(volume),
        )
        
        bars.append(bar)
    
    return bars


def get_bars_spx_like() -> list[Bar]:
    """
    Get a fixed set of SPX-like bars for testing.
    
    Returns:
        List of 120 Bar objects with volatility regime shift
    """
    return generate_bars_spx_like()


