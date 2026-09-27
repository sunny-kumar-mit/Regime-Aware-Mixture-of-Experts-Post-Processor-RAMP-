"""
RAMP Operational Forecast CLI
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Operational CLI for triggering inference, inspecting available cycles,
and exporting forecast products.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ml.inference.input_resolver import ForecastCycleResolver
from ml.inference.pipeline import OperationalInferencePipeline
from ml.inference.products import ForecastProductManager


def main():
    parser = argparse.ArgumentParser(
        description="RAMP Operational Forecast Inference & Product Orchestrator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: cycles
    subparsers.add_parser("cycles", help="List discoverable forecast cycles")

    # Command: infer
    infer_parser = subparsers.add_parser("infer", help="Execute operational forecast inference")
    infer_parser.add_argument("--cycle-id", required=True, help="Cycle identifier (e.g. DEMO_20260927_00Z)")
    infer_parser.add_argument("--lead", type=int, default=24, help="Lead time in hours (default: 24)")
    infer_parser.add_argument("--out", type=str, default=None, help="Optional output JSON path")

    # Command: status
    subparsers.add_parser("status", help="Inspect operational forecasting status desk")

    args = parser.parse_args()

    if args.command == "cycles":
        resolver = ForecastCycleResolver()
        cycles = resolver.list_available_cycles()
        print(f"Discovered {len(cycles)} forecast cycle(s):")
        for c in cycles:
            real_str = "REAL" if c.is_real else "SYNTHETIC DEMO"
            print(f"  - [{c.cycle_id}] {c.date} {c.cycle_utc} | Model: {c.model} | Mode: {real_str} | Leads: {c.available_leads}")

    elif args.command == "infer":
        pipeline = OperationalInferencePipeline()
        print(f"Executing RAMP operational inference for cycle {args.cycle_id}, lead +{args.lead}h...")
        res = pipeline.run_forecast(args.cycle_id, args.lead, user_action="CLI_RUN")
        if res["status"] != "SUCCESS":
            print(f"Inference blocked: {res}")
            sys.exit(1)

        print(f"Inference SUCCESS. Run ID: {res['forecast_run_id']}")
        nat = res["national_summary"]["national_metrics"]
        print(f"National Summary: Max RAMP Rain = {nat['max_ramp_rainfall_mm']} mm, Max Extreme Prob = {nat['max_extreme_probability']}")
        print(f"Dominant Regime: {nat['dominant_regime']}")
        print(f"Timing: Total = {res['performance']['total_time_ms']} ms")

        if args.out:
            out_p = Path(args.out)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
            print(f"Forecast output written to {out_p}")

    elif args.command == "status":
        from ramp.data_plane.discovery import DataDiscoveryService
        ds = DataDiscoveryService()
        mat = ds.get_availability_matrix()
        print(f"Operational Data Status: {mat.data_mode}")
        for p_id, p_res in mat.providers.items():
            print(f"  - {p_id.upper()}: {p_res.status} ({p_res.data_mode})")


if __name__ == "__main__":
    main()
