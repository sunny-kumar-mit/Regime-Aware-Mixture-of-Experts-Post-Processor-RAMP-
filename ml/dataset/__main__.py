"""
RAMP Training Dataset CLI
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Usage:
  python -m ml.dataset build --help
  python -m ml.dataset validate --help
  python -m ml.dataset stats --help
  python -m ml.dataset split --help
  python -m ml.dataset leakage-check --help
  python -m ml.dataset inspect --help
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from ml.dataset.builder import DatasetBuilder
from ml.dataset.leakage_guard import LeakageGuard


DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "processed" / "training" / "ramp_dataset_v0.3.0"


def cmd_build(args: argparse.Namespace) -> int:
    """Build dataset pipeline."""
    out_dir = Path(args.output_dir)
    print(f"[*] Building RAMP training dataset (version: {args.version}, mode: {args.mode})...")
    print(f"[*] Target directory: {out_dir}")

    builder = DatasetBuilder(
        dataset_id=f"ramp_dataset_v{args.version}",
        version=args.version,
        data_mode=args.mode,
    )

    try:
        results = builder.generate_synthetic_dataset(num_days=args.days, output_dir=out_dir)
        version = results["version"]
        split = results["split_manifest"]
        leakage = results["leakage_report"]

        print(f"[OK] Dataset build SUCCESSFUL!")
        print(f"     Dataset ID:       {version.dataset_id}")
        print(f"     Version:          {version.version}")
        print(f"     Mode:             {version.data_mode}")
        print(f"     Total Samples:    {version.row_count}")
        print(f"     Features (X):     {version.feature_count}")
        print(f"     Targets (Y):      {version.target_count}")
        print(f"     Train Rows:       {split.train_rows}")
        print(f"     Validation Rows:  {split.val_rows}")
        print(f"     Test Rows:        {split.test_rows}")
        print(f"     Leakage Status:   {leakage.status}")
        print(f"     Artifacts saved:  {out_dir}")
        return 0
    except Exception as e:
        print(f"[FAIL] Error building dataset: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate dataset files and schema integrity."""
    d_dir = Path(args.dataset_dir)
    if not d_dir.exists():
        print(f"[FAIL] Dataset directory not found: {d_dir}", file=sys.stderr)
        return 1

    req_files = [
        "dataset_version.json",
        "split_manifest.json",
        "preprocessing_manifest.json",
        "leakage_report.json",
        "dataset_statistics.json",
        "feature_registry.json",
        "DATASET_CARD.md",
    ]

    missing = [f for f in req_files if not (d_dir / f).exists()]
    if missing:
        print(f"[FAIL] Missing required dataset artifacts: {missing}", file=sys.stderr)
        return 1

    print(f"[OK] All required dataset artifacts present in {d_dir}.")
    with open(d_dir / "dataset_version.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    print(f"     Validated: {meta.get('dataset_id')} (Mode: {meta.get('data_mode')})")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Display split statistics."""
    d_dir = Path(args.dataset_dir)
    stats_file = d_dir / "dataset_statistics.json"
    if not stats_file.exists():
        print(f"[FAIL] Statistics file not found: {stats_file}", file=sys.stderr)
        return 1

    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)

    print(f"============================================================")
    print(f"RAMP DATASET SPLIT STATISTICS: {d_dir.name}")
    print(f"============================================================")
    for sname, sdata in stats.items():
        print(f"\n[{sname}] Rows: {sdata.get('row_count')}, Cells: {sdata.get('grid_cells')}")
        print(f"  Rainfall Mean:    {sdata.get('rainfall_mean')} mm")
        print(f"  Rainfall Median:  {sdata.get('rainfall_median')} mm")
        print(f"  Rainfall Max:     {sdata.get('rainfall_max')} mm")
        print(f"  Rainfall P90/P99: {sdata.get('rainfall_p90')} / {sdata.get('rainfall_p99')} mm")
        events = sdata.get("event_counts", {})
        print(f"  Rainy Days (>0.1mm):   {events.get('rainfall_occurrence', 0)}")
        print(f"  Heavy (>=64.5mm):      {events.get('heavy_rainfall', 0)}")
        print(f"  Very Heavy (>=115.6):  {events.get('very_heavy_rainfall', 0)}")
        print(f"  Extreme (>=204.5):     {events.get('extremely_heavy_rainfall', 0)}")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    """Inspect temporal split boundaries."""
    d_dir = Path(args.dataset_dir)
    split_file = d_dir / "split_manifest.json"
    if not split_file.exists():
        print(f"[FAIL] Split manifest not found: {split_file}", file=sys.stderr)
        return 1

    with open(split_file, "r", encoding="utf-8") as f:
        split = json.load(f)

    print(f"[*] Split Type: {split.get('split_type')}")
    print(f"[*] Purge Gap:  {split.get('purge_gap_hours')} hours")
    print(f"    TRAIN:      {split.get('train_rows')} rows | {split.get('train_range')}")
    print(f"    VALIDATION: {split.get('val_rows')} rows | {split.get('val_range')}")
    print(f"    TEST:       {split.get('test_rows')} rows | {split.get('test_range')}")
    return 0


def cmd_leakage_check(args: argparse.Namespace) -> int:
    """Run leakage checks on generated dataset."""
    d_dir = Path(args.dataset_dir)
    leak_file = d_dir / "leakage_report.json"
    if not leak_file.exists():
        print(f"[FAIL] Leakage report not found: {leak_file}", file=sys.stderr)
        return 1

    with open(leak_file, "r", encoding="utf-8") as f:
        rep = json.load(f)

    print(f"============================================================")
    print(f"RAMP LEAKAGE AUDIT REPORT: {rep.get('status')}")
    print(f"============================================================")
    print(f"Checks Audited: {rep.get('checks_run')}")
    for p in rep.get("passed_checks", []):
        print(f"  [PASS] {p}")
    if rep.get("violations"):
        for v in rep.get("violations", []):
            print(f"  [FAIL] {v}")
        return 1
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Display comprehensive dataset summary."""
    cmd_validate(args)
    cmd_split(args)
    cmd_stats(args)
    cmd_leakage_check(args)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.dataset",
        description="RAMP Dataset Builder & Validation CLI — SIH26080",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Build and serialize training dataset")
    p_build.add_argument("--output-dir", default=str(DEFAULT_DATASET_DIR), help="Output directory")
    p_build.add_argument("--days", type=int, default=20, help="Days of data to synthesize")
    p_build.add_argument("--version", default="0.3.0", help="Dataset version (e.g. 0.3.0)")
    p_build.add_argument("--mode", default="SYNTHETIC_DEMO", choices=["SYNTHETIC_DEMO", "REAL"], help="Data mode")
    p_build.set_defaults(func=cmd_build)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate dataset artifact integrity")
    p_val.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR), help="Dataset directory")
    p_val.set_defaults(func=cmd_validate)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show split statistics")
    p_stats.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR), help="Dataset directory")
    p_stats.set_defaults(func=cmd_stats)

    # split
    p_split = subparsers.add_parser("split", help="Show temporal split manifest")
    p_split.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR), help="Dataset directory")
    p_split.set_defaults(func=cmd_split)

    # leakage-check
    p_leak = subparsers.add_parser("leakage-check", help="Audit dataset for data leakage")
    p_leak.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR), help="Dataset directory")
    p_leak.set_defaults(func=cmd_leakage_check)

    # inspect
    p_insp = subparsers.add_parser("inspect", help="Full dataset inspection")
    p_insp.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR), help="Dataset directory")
    p_insp.set_defaults(func=cmd_inspect)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
