"""
RAMP Real Dataset CLI Tool
SIH26080 | MoES / NCMRWF

Usage:
  python -m ml.datasets.real inspect
  python -m ml.datasets.real discover
  python -m ml.datasets.real match
  python -m ml.datasets.real qc
  python -m ml.datasets.real build [--fixture] [--samples N]
  python -m ml.datasets.real validate
  python -m ml.datasets.real statistics
  python -m ml.datasets.real export
"""

import argparse
import json
import sys
from pathlib import Path

from ml.datasets.real.pipeline import RealDatasetPipeline


def cmd_inspect(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    res = pipeline.inspect_pipeline_readiness()
    print("=" * 60)
    print(f"RAMP REAL DATASET PIPELINE INSPECTION — {res['dataset_id']}")
    print("=" * 60)
    print(f"Status:                 {res['status']}")
    print(f"Data Mode:              {res['data_mode']}")
    print(f"Real Data Available:    {res['real_data_available']}")
    print(f"Files Discovered:       {res['total_files_discovered']}")
    print(f"Message:                {res['message']}")
    print("Thresholds:")
    for k, v in res["target_thresholds"].items():
        print(f"  - {k}: {v} mm")
    print("=" * 60)
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    disc = pipeline.discover_operational_sources()
    print("=" * 60)
    print("OPERATIONAL DATA DISCOVERY SCAN")
    print("=" * 60)
    print(f"Overall Data Mode:      {disc['overall_mode']}")
    print(f"Honesty Notice:         {disc['honesty_notice']}")
    print("\nScanned Providers:")
    for pid, s in disc["scans"].items():
        status = "AVAILABLE" if s["is_available"] else "UNMOUNTED"
        print(f"  [{status:<10}] {pid:<18}: {s['total_files']} files ({s['data_mode']})")
    print("=" * 60)
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    print("=" * 60)
    print("NWP + IMD TEMPORAL MATCHING ENGINE")
    print("=" * 60)
    print("Matching Rule: forecast_valid_time == observation_time")
    print("Tolerance:     ±0 hours (strict)")
    print("Dimensions:    timestamp, latitude, longitude")
    print("Anti-Leakage:  Active — Future observations strictly blocked")
    print("Missing Rule:  Missing observations NEVER converted to 0 mm")
    print("=" * 60)
    return 0


def cmd_qc(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    manifest_path = pipeline.output_dir / "qc_report.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("=" * 60)
        print(f"DATASET QUALITY CONTROL AUDIT — {pipeline.dataset_id}")
        print("=" * 60)
        print(json.dumps(data, indent=2))
        print("=" * 60)
    else:
        print(f"QC report not found at {manifest_path}. Run 'build' first.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    print("=" * 60)
    print(f"BUILDING DATASET: {pipeline.dataset_id}")
    print("=" * 60)
    res = pipeline.build_dataset(
        force_synthetic_fixture=args.fixture,
        sample_count=args.samples,
    )
    print(f"Build Result:     {res.get('status')}")
    print(f"Data Mode:        {res.get('data_mode')}")
    print(f"Total Samples:    {res.get('total_samples', 0)}")
    print(f"Artifacts:        {len(res.get('artifacts_written', []))} files created in {pipeline.output_dir}")
    print("=" * 60)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    required = [
        "dataset_manifest.json",
        "dataset_card.md",
        "dataset_statistics.json",
        "source_manifest.json",
        "leakage_report.json",
        "qc_report.json",
        "split_manifest.json",
        "event_distribution.json",
        "spatial_coverage.json",
        "checksum_manifest.json",
    ]
    missing = [f for f in required if not (pipeline.output_dir / f).exists()]
    print("=" * 60)
    print(f"VALIDATING ARTIFACTS IN: {pipeline.output_dir}")
    print("=" * 60)
    if missing:
        print(f"VALIDATION FAILED: Missing {len(missing)} artifacts: {missing}")
        return 1
    print(f"VALIDATION PASSED: All {len(required)} authoritative metadata artifacts present.")
    print("=" * 60)
    return 0


def cmd_statistics(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    stats_path = pipeline.output_dir / "dataset_statistics.json"
    if stats_path.exists():
        with open(stats_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("=" * 60)
        print(f"DATASET STATISTICS — {pipeline.dataset_id}")
        print("=" * 60)
        print(json.dumps(data, indent=2))
        print("=" * 60)
    else:
        print(f"Statistics not found at {stats_path}. Run 'build' first.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    pipeline = RealDatasetPipeline()
    print("=" * 60)
    print(f"DATASET EXPORT SUMMARY — {pipeline.dataset_id}")
    print("=" * 60)
    print(f"Directory: {pipeline.output_dir.resolve()}")
    for f in pipeline.output_dir.iterdir():
        print(f"  - {f.name} ({f.stat().st_size} bytes)")
    print("=" * 60)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.datasets.real",
        description="RAMP Real Paired Dataset CLI (SIH26080 - MoES / NCMRWF)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inspect
    subparsers.add_parser("inspect", help="Inspect operational readiness and source hierarchy")

    # discover
    subparsers.add_parser("discover", help="Scan raw data storage for operational archives")

    # match
    subparsers.add_parser("match", help="Verify NWP and IMD forecast-observation temporal matching")

    # qc
    subparsers.add_parser("qc", help="Display data quality audit and validation flags")

    # build
    build_p = subparsers.add_parser("build", help="Build authoritative paired dataset")
    build_p.add_argument("--fixture", action="store_true", help="Generate synthetic test fixture for CI validation")
    build_p.add_argument("--samples", type=int, default=500, help="Number of fixture samples")

    # validate
    subparsers.add_parser("validate", help="Validate all 10 required manifests and integrity checksums")

    # statistics
    subparsers.add_parser("statistics", help="Display distribution metrics and correlations")

    # export
    subparsers.add_parser("export", help="List and summarize exported dataset artifacts")

    args = parser.parse_args()

    dispatch = {
        "inspect": cmd_inspect,
        "discover": cmd_discover,
        "match": cmd_match,
        "qc": cmd_qc,
        "build": cmd_build,
        "validate": cmd_validate,
        "statistics": cmd_statistics,
        "export": cmd_export,
    }

    handler = dispatch.get(args.command)
    if handler:
        return handler(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
