"""Feature store for extracting and storing market features."""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..core.time import ensure_utc, utc_now
from ..io.providers import Bar, MarketDataProvider
from .transforms import rolling_mean, rolling_std, zscore


class FeatureStore:
    """Feature store for market data extraction."""
    
    def __init__(self, provider: Optional[MarketDataProvider] = None):
        """
        Initialize the feature store.
        
        Args:
            provider: Optional market data provider. If None, uses stubbed behavior.
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.provider = provider
    
    def extract_features(
        self,
        symbol: str,
        features: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract features for a given symbol.
        
        Args:
            symbol: Asset symbol (e.g., 'SPX')
            features: Optional list of specific features to extract.
                     If None, extracts all available features.
        
        Returns:
            Dictionary of feature names to values
        """
        # Stubbed implementation - returns mock data
        if symbol not in self._cache:
            self._cache[symbol] = {
                "price": 4500.0,
                "volatility": 0.15,
                "volume": 1000000,
                "returns": 0.02,
                "convexity": 0.05,
                "correlation_matrix": {},
            }
        
        result = self._cache[symbol].copy()
        
        if features:
            result = {k: v for k, v in result.items() if k in features}
        
        return result
    
    def get_feature(self, symbol: str, feature_name: str) -> Any:
        """
        Get a specific feature for a symbol.
        
        Args:
            symbol: Asset symbol
            feature_name: Name of the feature
        
        Returns:
            Feature value
        """
        features = self.extract_features(symbol)
        return features.get(feature_name)
    
    def update_features(self, symbol: str, features: Dict[str, Any]) -> None:
        """
        Update features for a symbol.
        
        Args:
            symbol: Asset symbol
            features: Dictionary of feature updates
        """
        if symbol not in self._cache:
            self._cache[symbol] = {}
        self._cache[symbol].update(features)
    
    def get_price_bars(
        self,
        symbol: str,
        now: datetime,
        lookback_days: int = 120,
        timeframe: str = "1D",
    ) -> List[Bar]:
        """
        Get historical price bars for a symbol.
        
        Args:
            symbol: Asset symbol
            now: Current UTC datetime
            lookback_days: Number of days to look back
            timeframe: Bar timeframe (e.g., "1D", "1H")
        
        Returns:
            List of Bar objects, sorted by timestamp (ascending)
        """
        if self.provider is None:
            # Return empty list if no provider
            return []
        
        now_utc = ensure_utc(now)
        start = now_utc - timedelta(days=lookback_days)
        
        bars = self.provider.get_bars(symbol, start, now_utc, timeframe)
        # Ensure sorted by timestamp
        bars.sort(key=lambda b: b.ts)
        return bars
    
    def compute_vol_features(self, bars: List[Bar]) -> Dict[str, Any]:
        """
        Compute volatility features from price bars.
        
        Args:
            bars: List of Bar objects (sorted by timestamp)
        
        Returns:
            Dictionary containing:
            - returns: List of daily returns
            - rv_20: Annualized realized vol over last 20 returns
            - rv_60: Annualized realized vol over last 60 returns
            - rv_ratio: rv_20 / (rv_60 + eps)
            - z_rv_ratio: Z-score of rv_ratio vs rolling history
            - missingness: Ratio of missing bars
            - staleness_seconds: Age of most recent bar
            - stability: Stability metric (1.0 - coefficient of variation of returns)
        """
        if not bars:
            return {
                "returns": [],
                "rv_20": 0.0,
                "rv_60": 0.0,
                "rv_ratio": 0.0,
                "z_rv_ratio": 0.0,
                "missingness": 1.0,
                "staleness_seconds": float("inf"),
                "stability": 0.0,
            }
        
        # Compute daily returns
        returns = []
        for i in range(1, len(bars)):
            if bars[i].close > 0 and bars[i-1].close > 0:
                ret = (bars[i].close - bars[i-1].close) / bars[i-1].close
                if math.isfinite(ret):
                    returns.append(ret)
        
        if not returns:
            return {
                "returns": [],
                "rv_20": 0.0,
                "rv_60": 0.0,
                "rv_ratio": 0.0,
                "z_rv_ratio": 0.0,
                "missingness": 1.0,
                "staleness_seconds": float("inf"),
                "stability": 0.0,
            }
        
        # Compute realized volatilities (annualized)
        # Annualized RV = sqrt(252) * std(daily_returns)
        eps = 1e-12
        sqrt_252 = math.sqrt(252.0)
        
        # RV over last 20 returns
        rv_20_std = rolling_std(returns, 20, eps)
        rv_20 = sqrt_252 * rv_20_std
        
        # RV over last 60 returns
        rv_60_std = rolling_std(returns, 60, eps)
        rv_60 = sqrt_252 * rv_60_std
        
        # RV ratio
        rv_ratio = rv_20 / (rv_60 + eps) if rv_60 > eps else 0.0
        
        # Z-score of rv_ratio vs rolling history
        # Use rolling mean and std of rv_ratio over history
        # For simplicity, compute rv_ratio for each window and track history
        rv_ratio_history = []
        for i in range(60, len(returns)):
            window_20 = returns[max(0, i-20):i]
            window_60 = returns[max(0, i-60):i]
            if len(window_20) >= 2 and len(window_60) >= 2:
                rv_20_hist = sqrt_252 * rolling_std(window_20, len(window_20), eps)
                rv_60_hist = sqrt_252 * rolling_std(window_60, len(window_60), eps)
                if rv_60_hist > eps:
                    rv_ratio_hist = rv_20_hist / (rv_60_hist + eps)
                    if math.isfinite(rv_ratio_hist):
                        rv_ratio_history.append(rv_ratio_hist)
        
        if rv_ratio_history:
            rv_ratio_mean = rolling_mean(rv_ratio_history, len(rv_ratio_history))
            rv_ratio_std = rolling_std(rv_ratio_history, len(rv_ratio_history), eps)
            z_rv_ratio = zscore(rv_ratio, rv_ratio_mean, rv_ratio_std, eps)
        else:
            z_rv_ratio = 0.0
        
        # Data quality metrics
        # Missingness: assume bars are consecutive if provider returns them
        # For now, assume 0.0 if we have bars
        missingness = 0.0
        
        # Staleness: age of most recent bar
        most_recent_bar = bars[-1]
        now_utc = utc_now()
        staleness_seconds = (now_utc - most_recent_bar.ts).total_seconds()
        staleness_seconds = max(0.0, staleness_seconds)
        
        # Stability: 1.0 - coefficient of variation of returns
        if len(returns) >= 2:
            returns_mean = rolling_mean(returns, len(returns))
            returns_std = rolling_std(returns, len(returns), eps)
            if abs(returns_mean) > eps:
                cv = abs(returns_std / (returns_mean + eps))
                stability = max(0.0, min(1.0, 1.0 - cv))
            else:
                stability = 0.5  # Default if mean is near zero
        else:
            stability = 0.5
        
        return {
            "returns": returns,
            "rv_20": rv_20,
            "rv_60": rv_60,
            "rv_ratio": rv_ratio,
            "z_rv_ratio": z_rv_ratio,
            "missingness": missingness,
            "staleness_seconds": staleness_seconds,
            "stability": stability,
        }

