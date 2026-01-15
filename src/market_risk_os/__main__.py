"""CLI entrypoint for market_risk_os."""

import argparse
import json
import sys

from .pipeline import PipelineOrchestrator


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Market Risk OS - Risk analysis pipeline"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Asset symbol to analyze (e.g., SPX)",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "pretty"],
        default="pretty",
        help="Output format (default: pretty)",
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = PipelineOrchestrator()
    
    # Run pipeline
    try:
        result = orchestrator.run(args.symbol)
        
        # Format output
        if args.output == "json":
            # Output as JSON
            output = {
                "symbol": result["symbol"],
                "pressures": [p.model_dump() for p in result["pressures"]],
                "interactions": [i.model_dump() for i in result["interactions"]],
                "risk_state": result["risk_state"].model_dump(),
                "behavior_gate": result["behavior_gate"].model_dump(),
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            # Pretty output
            print(f"\n{'='*60}")
            print(f"Market Risk Analysis: {result['symbol']}")
            print(f"{'='*60}\n")
            
            print(f"Pressures Detected: {len(result['pressures'])}")
            for pressure in result["pressures"]:
                print(f"  - {pressure.pressure_type.value}: "
                      f"magnitude={pressure.magnitude:.2f}, "
                      f"confidence={pressure.confidence:.2f}")
            
            print(f"\nInteractions: {len(result['interactions'])}")
            for interaction in result["interactions"]:
                print(f"  - {interaction.interaction_type.value}: "
                      f"instability={interaction.instability_contribution:.2f}")
            
            risk_state = result["risk_state"]
            print(f"\nRisk State: {risk_state.dominant_state.value}")
            print(f"  Instability Score: {risk_state.instability_score:.2f}")
            print(f"  Confidence: {risk_state.confidence:.2f}")
            print(f"  Ambiguity: {risk_state.ambiguity:.2f}")
            
            gate = result["behavior_gate"]
            print(f"\nBehavior Gate:")
            print(f"  Allowed Behaviors: {len(gate.allowed_behaviors)}")
            print(f"  Forbidden Behaviors: {len(gate.forbidden_behaviors)}")
            print(f"  Aggressiveness Limit: {gate.aggressiveness_limit:.2f}")
            print(f"{'='*60}\n")
        
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


