"""
RAMP Baseline CLI Interface
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF

Usage:
  python -m ml.baselines train      - Train all 4 baselines & export models
  python -m ml.baselines evaluate   - Evaluate baselines on test split
  python -m ml.baselines benchmark  - Run full multi-model benchmark suite
  python -m ml.baselines verify     - Run categorical & continuous verification
  python -m ml.baselines inspect    - Inspect baseline model cards & metadata
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ml.baselines.model_registry import BaselineModelRegistry
from ml.baselines.train import train_and_benchmark_baselines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ml.baselines",
        description="RAMP Phase 5: Baseline Rainfall Post-Processing & Benchmarking CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # train
    train_parser = subparsers.add_parser("train", help="Train all 4 baseline systems strictly on TRAIN data")
    train_parser.add_argument("--dataset-dir", type=str, default="data/processed/training/ramp_dataset_v0.3.0", help="Path to staged dataset partitions")
    train_parser.add_argument("--output-dir", type=str, default="data/models/baselines", help="Output directory for model artifacts")

    # evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate trained baselines on test partition")
    eval_parser.add_argument("--dataset-dir", type=str, default="data/processed/training/ramp_dataset_v0.3.0", help="Dataset directory")
    eval_parser.add_argument("--models-dir", type=str, default="data/models/baselines", help="Models directory")

    # benchmark
    bm_parser = subparsers.add_parser("benchmark", help="Execute complete benchmark comparison and export JSON artifacts")
    bm_parser.add_argument("--models-dir", type=str, default="data/models/baselines", help="Models directory")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Inspect WMO/IMD verification metrics (RMSE, CSI, POD, FAR, ETS)")
    verify_parser.add_argument("--models-dir", type=str, default="data/models/baselines", help="Models directory")

    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Display metadata and model card for registered baseline models")
    inspect_parser.add_argument("--models-dir", type=str, default="data/models/baselines", help="Models directory")
    inspect_parser.add_argument("--model-id", type=str, default="global_lgbm_v1", help="Specific model ID to inspect")

    return parser


def main() -> None:
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "train":
        print(f"Starting baseline training pipeline from: {args.dataset_dir}")
        train_and_benchmark_baselines(dataset_dir=args.dataset_dir, output_dir=args.output_dir)

    elif args.command in ["evaluate", "benchmark"]:
        print(f"Running baseline benchmark...")
        train_and_benchmark_baselines(dataset_dir=getattr(args, "dataset_dir", "data/processed/training/ramp_dataset_v0.3.0"))

    elif args.command == "verify":
        bm_file = Path(args.models_dir) / "baseline_benchmark.json"
        if not bm_file.exists():
            print(f"Benchmark file not found at {bm_file}. Running benchmark first...")
            train_and_benchmark_baselines()
        with open(bm_file, "r", encoding="utf-8") as f:
            bm_data = json.load(f)
        print("\n--- BASELINE BENCHMARK MATRIX (TEST PARTITION) ---")
        for row in bm_data.get("benchmark_matrix", []):
            print(f"Model: {row['model']:<20} | RMSE: {row['rmse']:<6.2f} mm | MAE: {row['mae']:<6.2f} mm | CSI(64.5mm): {row['heavy_rain_csi_64_5']}")

    elif args.command == "inspect":
        registry = BaselineModelRegistry(models_dir=args.models_dir)
        models = registry.list_models()
        print(f"Registered Baseline Models ({len(models)} found):")
        for m in models:
            print(f"  - {m.model_id} ({m.model_type}) | Version: {m.version} | DataMode: {m.data_mode}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
