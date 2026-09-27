"""
RAMP Model Training Command-Line Interface (CLI)
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part AE: CLI Interface supporting:
  python -m ml.training inspect
  python -m ml.training validate
  python -m ml.training train
  python -m ml.training evaluate
  python -m ml.training calibrate
  python -m ml.training register
  python -m ml.training status
  python -m ml.training pipeline
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from ml.training.dataset_gate import DatasetGate, RealTrainingEligibilityGate
from ml.training.pipeline import TrainingPipeline
from ml.training.registry import ModelRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ml.training.cli")


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect dataset, manifests, and training environment."""
    ds_dir = args.dataset_version or "ml/datasets/real/ramp_dataset_real_v1.0.0"
    if not ds_dir.startswith("ml/datasets"):
        ds_dir = f"ml/datasets/real/{ds_dir}"

    pipeline = TrainingPipeline(dataset_dir=ds_dir)
    info = pipeline.inspect_environment()
    print("\n================ RAMP TRAINING ENVIRONMENT INSPECTION ================")
    print(json.dumps(info, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate dataset gate, manifests, checksums, and eligibility."""
    ds_dir = args.dataset_version or "ml/datasets/real/ramp_dataset_real_v1.0.0"
    if not ds_dir.startswith("ml/datasets"):
        ds_dir = f"ml/datasets/real/{ds_dir}"

    res = DatasetGate.validate(ds_dir)
    elig = RealTrainingEligibilityGate.evaluate(ds_dir)
    print("\n================ DATASET VALIDATION REPORT ================")
    print(f"Dataset: {ds_dir}")
    print(f"Integrity Valid: {res['valid']}")
    print(f"Real Data Available: {elig['real_data_available']}")
    print(f"Real Training Deferred: {elig['real_training_deferred']}")
    print(f"Effective Mode: {elig['effective_mode']}")
    print(f"Message: {elig['message']}")
    return 0 if res["valid"] else 1


def cmd_status(args: argparse.Namespace) -> int:
    """Display current model registry status and active models."""
    reg = ModelRegistry()
    models = reg.list_models()
    active = reg.get_active_models()

    print("\n================ MODEL REGISTRY STATUS ================")
    print(f"Total Registered Models: {len(models)}")
    print("Active Models by Type:")
    for mtype, mid in active.items():
        print(f"  {mtype}: {mid}")
    print("\nAll Registered Models:")
    for m in models:
        print(
            f"  - {m['model_id']} | Type: {m['model_type']} | "
            f"Status: {m['lifecycle_status']} | Mode: {m['data_mode']}"
        )
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Execute complete end-to-end model training, verification, and registration."""
    ds_dir = args.dataset_version or "ml/datasets/real/ramp_dataset_real_v1.0.0"
    if not ds_dir.startswith("ml/datasets"):
        ds_dir = f"ml/datasets/real/{ds_dir}"

    seed = int(args.seed) if args.seed else 42
    cal_method = args.calibration or "isotonic"

    print(f"\n================ STARTING RAMP MODEL TRAINING PIPELINE ================")
    print(f"Dataset Version: {ds_dir}")
    print(f"Seed: {seed} | Calibration: {cal_method}")

    pipeline = TrainingPipeline(dataset_dir=ds_dir, random_seed=seed)
    result = pipeline.run_pipeline(calibration_method=cal_method, allow_overwrite=True)

    print("\n================ PIPELINE EXECUTION SUMMARY ================")
    print(f"Status: {result.get('status')}")
    print(f"Pipeline Status: {result.get('pipeline_status')}")
    print(f"Real Production Training: {result.get('real_production_training')}")
    print(f"Data Mode: {result.get('data_mode')}")
    print(f"Duration: {result.get('training_duration_seconds')} seconds")
    print(f"Models Registered: {result.get('models_registered')}")

    if "model_comparison" in result:
        print("\nObjective Model Comparison:")
        for row in result["model_comparison"]:
            print(
                f"  {row['model']:<20} | MAE: {row['mae']:<6} | RMSE: {row['rmse']:<6} | "
                f"POD: {row['pod_0p1mm']:<5} | FAR: {row['far_0p1mm']:<5} | CSI: {row['csi_0p1mm']:<5}"
            )

    return 0 if result.get("status") == "PIPELINE_COMPLETE" else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.training",
        description="RAMP Model Retraining, Calibration & Model Registry CLI (Phase 13)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inspect
    p_insp = subparsers.add_parser("inspect", help="Inspect training environment and dataset")
    p_insp.add_argument("--dataset-version", type=str, default=None)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate dataset gate and real-data eligibility")
    p_val.add_argument("--dataset-version", type=str, default=None)

    # status
    p_stat = subparsers.add_parser("status", help="Display model registry status")

    # pipeline
    p_pipe = subparsers.add_parser("pipeline", help="Run complete model training pipeline")
    p_pipe.add_argument("--dataset-version", type=str, default=None)
    p_pipe.add_argument("--seed", type=int, default=42)
    p_pipe.add_argument("--calibration", type=str, default="isotonic", choices=["isotonic", "platt", "none"])
    p_pipe.add_argument("--mode", type=str, default=None)

    # train (alias to pipeline)
    p_tr = subparsers.add_parser("train", help="Train models")
    p_tr.add_argument("--dataset-version", type=str, default=None)
    p_tr.add_argument("--seed", type=int, default=42)
    p_tr.add_argument("--model", type=str, default="all")

    # evaluate
    p_ev = subparsers.add_parser("evaluate", help="Evaluate models")
    p_ev.add_argument("--dataset-version", type=str, default=None)
    p_ev.add_argument("--model", type=str, default="all")

    # calibrate
    p_cal = subparsers.add_parser("calibrate", help="Calibrate models")
    p_cal.add_argument("--calibration", type=str, default="isotonic")

    # register
    p_reg = subparsers.add_parser("register", help="Register a model")
    p_reg.add_argument("--model-id", type=str, required=False)

    args = parser.parse_args()

    if args.command == "inspect":
        return cmd_inspect(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command in ("pipeline", "train", "evaluate", "calibrate", "register"):
        # All route cleanly into pipeline / inspection execution
        return cmd_pipeline(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
