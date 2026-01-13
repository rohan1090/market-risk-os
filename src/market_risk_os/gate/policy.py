"""Policy mapping for behavior gates."""

from typing import Dict, List

from ..core import BehaviorType, RiskStateEnum


def get_policy(dominant_state: RiskStateEnum) -> Dict[str, List[BehaviorType]]:
    """
    Get behavior policy for a given risk state.
    
    Args:
        dominant_state: Dominant risk state
        
    Returns:
        Dictionary with 'allowed' and 'forbidden' behavior lists (sorted)
    """
    policies = {
        RiskStateEnum.STABLE: {
            "allowed": [
                BehaviorType.TREND_FOLLOWING,
                BehaviorType.MEAN_REVERSION,
                BehaviorType.CARRY,
                BehaviorType.LIQUIDITY_PROVIDING,
                BehaviorType.VOLATILITY_EXPANSION,
                BehaviorType.CONVEX_STRUCTURES,
            ],
            "forbidden": [],
        },
        RiskStateEnum.ELEVATED: {
            "allowed": [
                BehaviorType.MEAN_REVERSION,
                BehaviorType.LIQUIDITY_PROVIDING,
                BehaviorType.HEDGING_ONLY,
                BehaviorType.VOLATILITY_EXPANSION,
            ],
            "forbidden": [
                BehaviorType.TREND_FOLLOWING,
                BehaviorType.CARRY,
            ],
        },
        RiskStateEnum.UNSTABLE: {
            "allowed": [
                BehaviorType.HEDGING_ONLY,
                BehaviorType.VOLATILITY_EXPANSION,
                BehaviorType.CONVEX_STRUCTURES,
                BehaviorType.REDUCE_EXPOSURE,
            ],
            "forbidden": [
                BehaviorType.TREND_FOLLOWING,
                BehaviorType.MEAN_REVERSION,
                BehaviorType.CARRY,
                BehaviorType.LIQUIDITY_PROVIDING,
            ],
        },
        RiskStateEnum.CRITICAL: {
            "allowed": [
                BehaviorType.HEDGING_ONLY,
                BehaviorType.REDUCE_EXPOSURE,
            ],
            "forbidden": [
                BehaviorType.TREND_FOLLOWING,
                BehaviorType.MEAN_REVERSION,
                BehaviorType.CARRY,
                BehaviorType.LIQUIDITY_PROVIDING,
                BehaviorType.VOLATILITY_EXPANSION,
                BehaviorType.CONVEX_STRUCTURES,
            ],
        },
    }
    
    policy = policies.get(dominant_state, policies[RiskStateEnum.STABLE])
    
    # Return sorted lists for determinism
    return {
        "allowed": sorted(policy["allowed"], key=lambda x: x.value),
        "forbidden": sorted(policy["forbidden"], key=lambda x: x.value),
    }

