"""Base interface for market data providers."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Protocol

from ...core.time import ensure_utc


@dataclass
class Bar:
    """OHLCV bar data with UTC timestamp."""
    
    ts: datetime  # Timezone-aware UTC timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0  # Optional, defaults to 0.0
    
    def __post_init__(self):
        """Ensure timestamp is UTC-aware."""
        self.ts = ensure_utc(self.ts)


class MarketDataProvider(Protocol):
    """
    Protocol for market data providers.
    
    All providers must implement get_bars() to return historical price bars.
    """
    
    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D",
    ) -> List[Bar]:
        """
        Get historical price bars for a symbol.
        
        Args:
            symbol: Asset symbol (e.g., "SPX")
            start: Start datetime (timezone-aware UTC)
            end: End datetime (timezone-aware UTC)
            timeframe: Bar timeframe (e.g., "1D", "1H", "1M")
        
        Returns:
            List of Bar objects, sorted by timestamp (ascending)
        """
        ...


