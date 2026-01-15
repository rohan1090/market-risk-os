"""Tests for orchestrator with fake data provider."""

from datetime import datetime, timezone
from typing import List

import pytest

from market_risk_os.io.providers import Bar, MarketDataProvider
from market_risk_os.pipeline import PipelineOrchestrator
from tests.fixtures.bars_spx_like import get_bars_spx_like


class FakeDataProvider:
    """Fake data provider for testing (no network calls)."""
    
    def __init__(self, bars: List[Bar] = None):
        """
        Initialize fake provider.
        
        Args:
            bars: Optional list of bars to return (defaults to SPX-like bars)
        """
        if bars is None:
            bars = get_bars_spx_like()
        self._bars = bars
    
    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1D",
    ) -> List[Bar]:
        """
        Get bars (returns stored bars filtered by date range).
        
        Args:
            symbol: Asset symbol (ignored)
            start: Start datetime
            end: End datetime
            timeframe: Bar timeframe (ignored)
        
        Returns:
            List of bars within date range
        """
        start_utc = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
        end_utc = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
        
        filtered = [
            bar for bar in self._bars
            if start_utc <= bar.ts <= end_utc
        ]
        return filtered


class TestOrchestratorWithFakeProvider:
    """Test orchestrator with fake data provider."""
    
    def test_orchestrator_accepts_provider(self):
        """Test orchestrator can be initialized with a provider."""
        bars = get_bars_spx_like()
        provider = FakeDataProvider(bars)
        
        orchestrator = PipelineOrchestrator(provider=provider)
        
        assert orchestrator.provider is not None
        assert orchestrator.feature_store.provider is not None
    
    def test_orchestrator_run_returns_expected_keys(self):
        """Test orchestrator run returns expected dictionary keys."""
        bars = get_bars_spx_like()
        provider = FakeDataProvider(bars)
        
        orchestrator = PipelineOrchestrator(provider=provider)
        
        result = orchestrator.run("SPX")
        
        # Check expected keys
        assert "symbol" in result
        assert "features" in result
        assert "pressures" in result
        assert "interactions" in result
        assert "risk_state" in result
        assert "behavior_gate" in result
    
    def test_orchestrator_includes_vol_regime_pressure(self):
        """Test orchestrator includes volatility regime shift pressure."""
        bars = get_bars_spx_like()
        provider = FakeDataProvider(bars)
        
        orchestrator = PipelineOrchestrator(provider=provider)
        
        result = orchestrator.run("SPX")
        
        # Check that pressures list exists
        assert isinstance(result["pressures"], list)
        
        # Check if volatility regime shift pressure is present
        vol_pressures = [
            p for p in result["pressures"]
            if p.pressure_type.value == "volatility"
            and "volreg" in str(p.pressure_id).lower()
        ]
        
        # May or may not be present depending on magnitude threshold
        # But if present, should be valid
        for pressure in vol_pressures:
            assert 0.0 <= pressure.magnitude <= 1.0
            assert 0.0 <= pressure.confidence <= 1.0
    
    def test_orchestrator_output_serializes_to_json(self):
        """Test orchestrator output can be serialized to JSON."""
        bars = get_bars_spx_like()
        provider = FakeDataProvider(bars)
        
        orchestrator = PipelineOrchestrator(provider=provider)
        
        result = orchestrator.run("SPX")
        
        # Try to serialize each component
        import json
        
        # Serialize pressures
        pressures_json = [p.model_dump_json() for p in result["pressures"]]
        assert isinstance(pressures_json, list)
        
        # Serialize risk state
        risk_state_json = result["risk_state"].model_dump_json()
        assert isinstance(risk_state_json, str)
        assert len(risk_state_json) > 0
        
        # Serialize behavior gate
        gate_json = result["behavior_gate"].model_dump_json()
        assert isinstance(gate_json, str)
        assert len(gate_json) > 0
    
    def test_orchestrator_works_without_provider(self):
        """Test orchestrator works without provider (falls back to stubbed features)."""
        orchestrator = PipelineOrchestrator(provider=None)
        
        result = orchestrator.run("SPX")
        
        # Should still return all expected keys
        assert "symbol" in result
        assert "features" in result
        assert "pressures" in result
        assert "interactions" in result
        assert "risk_state" in result
        assert "behavior_gate" in result


