"""Strict enums for market risk models."""

from enum import Enum


class PressureType(str, Enum):
    """Types of market pressure."""
    
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    CORRELATION = "correlation"
    CONCENTRATION = "concentration"
    MOMENTUM = "momentum"
    REVERSAL = "reversal"


class Directionality(str, Enum):
    """Directional characteristics of pressure."""
    
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class InteractionType(str, Enum):
    """Types of pressure interactions."""
    
    AMPLIFICATION = "amplification"
    DAMPENING = "dampening"
    REINFORCEMENT = "reinforcement"
    COUNTERACTION = "counteraction"
    RESONANCE = "resonance"


class RiskState(str, Enum):
    """Dominant risk states."""
    
    STABLE = "stable"
    ELEVATED = "elevated"
    UNSTABLE = "unstable"
    CRITICAL = "critical"
    TRANSITIONING = "transitioning"


class BehaviorType(str, Enum):
    """Types of behaviors that can be allowed or forbidden."""
    
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY_EXPANSION = "volatility_expansion"
    CONVEX_STRUCTURES = "convex_structures"
    LIQUIDITY_PROVIDING = "liquidity_providing"
    CARRY = "carry"
    HEDGING_ONLY = "hedging_only"
    REDUCE_EXPOSURE = "reduce_exposure"

