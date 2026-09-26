"""
RAMP Mixture-of-Experts Command Line Interface
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Commands:
  python -m ml.ramp train       - Train all 7 specialized regime experts
  python -m ml.ramp evaluate    - Evaluate RAMP on validation or test split
  python -m ml.ramp benchmark   - Benchmark RAMP against all Phase 5 baselines
  python -m ml.ramp ablation    - Run MoE ablation study (Hard vs Soft vs Uniform vs Global)
  python -m ml.ramp verify      - Verify mathematical invariants of RAMP MoE
  python -m ml.ramp inspect     - Inspect model card, expert statuses, and feature importances
  python -m ml.ramp predict     - Predict rainfall on sample or parquet dataset
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from ml.ramp.benchmark import RAMPBenchmarkEngine
from ml.ramp.experts import RegimeExpert
from ml.ramp.gating import GateWeights, RegimeGatingEngine
from ml.ramp.inference import RAMPInferenceService
from ml.ramp.model import RAMPModel
from ml.ramp.model_registry import RAMPModelRegistry
from ml.ramp.training import RAMPTrainer
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime
from ml.regimes.inference import RegimeInferenceService
from ml.regimes.model_registry import RegimeModelRegistry


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ml.ramp",
        description="RAMP: Regime-Aware Mixture-of-Experts Monsoon Rainfall Post-Processor CLI (SIH26080)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. train
    p_train = subparsers.add_parser("train", help="Train the 7 RAMP regime experts")
    p_train.add_argument("--dataset-dir", default="./data/processed/training/ramp_dataset_v0.3.0", help="Processed dataset path")
    p_train.add_argument("--models-dir", default="./data/models/ramp", help="RAMP model output directory")
    p_train.add_argument("--regimes-dir", default="./data/models/regime", help="Phase 4 regime models directory")
    p_train.add_argument("--baselines-dir", default="./data/models/baselines", help="Phase 5 baselines directory")
    p_train.add_argument("--training-mode", choices=["hard_argmax", "soft_probability_weighted"], default="hard_argmax", help="Regime assignment mode for expert training")
    p_train.add_argument("--min-samples", type=int, default=5, help="Minimum samples required to train an expert")
    p_train.add_argument("--version", default="ramp_v1.0.0", help="Model version identifier")

    # 2. evaluate
    p_eval = subparsers.add_parser("evaluate", help="Evaluate RAMP on dataset split")
    p_eval.add_argument("--dataset-dir", default="./data/processed/training/ramp_dataset_v0.3.0", help="Dataset directory")
    p_eval.add_argument("--models-dir", default="./data/models/ramp", help="RAMP model directory")
    p_eval.add_argument("--regimes-dir", default="./data/models/regime", help="Regimes model directory")
    p_eval.add_argument("--baselines-dir", default="./data/models/baselines", help="Baselines directory")
    p_eval.add_argument("--model-id", default="ramp_v1.0.0", help="RAMP model ID to evaluate")
    p_eval.add_argument("--split", choices=["train", "val", "test"], default="test", help="Dataset partition to evaluate")

    # 3. benchmark
    p_bench = subparsers.add_parser("benchmark", help="Benchmark RAMP against Phase 5 baselines")
    p_bench.add_argument("--dataset-dir", default="./data/processed/training/ramp_dataset_v0.3.0", help="Dataset directory")
    p_bench.add_argument("--models-dir", default="./data/models/ramp", help="RAMP model directory")
    p_bench.add_argument("--baselines-dir", default="./data/models/baselines", help="Baselines directory")
    p_bench.add_argument("--regimes-dir", default="./data/models/regime", help="Regimes model directory")
    p_bench.add_argument("--model-id", default="ramp_v1.0.0", help="RAMP model ID to benchmark")

    # 4. ablation
    p_abla = subparsers.add_parser("ablation", help="Evaluate MoE gating and architecture ablations")
    p_abla.add_argument("--dataset-dir", default="./data/processed/training/ramp_dataset_v0.3.0", help="Dataset directory")
    p_abla.add_argument("--models-dir", default="./data/models/ramp", help="RAMP model directory")
    p_abla.add_argument("--model-id", default="ramp_v1.0.0", help="RAMP model ID")

    # 5. verify
    p_ver = subparsers.add_parser("verify", help="Verify mathematical invariants of RAMP MoE")
    p_ver.add_argument("--dataset-dir", default="./data/processed/training/ramp_dataset_v0.3.0", help="Dataset directory")
    p_ver.add_argument("--models-dir", default="./data/models/ramp", help="RAMP model directory")
    p_ver.add_argument("--baselines-dir", default="./data/models/baselines", help="Baselines directory")
    p_ver.add_argument("--regimes-dir", default="./data/models/regime", help="Regimes model directory")
    p_ver.add_argument("--model-id", default="ramp_v1.0.0", help="RAMP model ID")

    # 6. inspect
    p_insp = subparsers.add_parser("inspect", help="Inspect trained RAMP model, experts, and diversity")
    p_insp.add_argument("--models-dir", default="./data/models/ramp", help="RAMP model directory")
    p_insp.add_argument("--model-id", default="ramp_v1.0.0", help="RAMP model ID")

    # 7. predict
    p_pred = subparsers.add_parser("predict", help="Predict rainfall using RAMP model")
    p_pred.add_argument("--models-dir", default="./data/models/ramp", help="RAMP model directory")
    p_pred.add_argument("--baselines-dir", default="./data/models/baselines", help="Baselines directory")
    p_pred.add_argument("--regimes-dir", default="./data/models/regime", help="Regimes model directory")
    p_pred.add_argument("--model-id", default="ramp_v1.0.0", help="RAMP model ID")
    p_pred.add_argument("--input-file", help="Path to parquet or csv file")
    p_pred.add_argument("--sample-id", help="Predict a single sample from test dataset by sample_id")
    p_pred.add_argument("--output", help="Optional output path for predictions")

    return parser


def cmd_train(args: argparse.Namespace) -> None:
    print(f"\n[RAMP TRAINER] Initializing training pipeline (Version: {args.version})...")
    print(f"  Dataset:       {args.dataset_dir}")
    print(f"  Models Output: {args.models_dir}")
    print(f"  Training Mode: {args.training_mode}")
    print(f"  Min Samples:   {args.min_samples}")

    trainer = RAMPTrainer(
        dataset_dir=args.dataset_dir,
        models_dir=args.models_dir,
        regimes_dir=args.regimes_dir,
        baselines_dir=args.baselines_dir,
        training_mode=args.training_mode,
        min_samples_per_expert=args.min_samples,
        version=args.version,
    )
    model, summary = trainer.train_all_experts()

    print("\n[RAMP TRAINER] Training completed successfully!")
    print(f"  Saved artifacts to: {summary['saved_dir']}")
    print("\n  Expert Training Summary:")
    for regime, meta in summary["expert_metrics"].items():
        rmse_str = f"RMSE={meta['train_rmse']:.2f} mm" if meta['train_rmse'] is not None else "N/A"
        print(f"    - {regime:<22} | Status: {meta['status']:<18} | Samples: {meta['train_samples']:<4} | {rmse_str}")

    print("\n  Overfitting Audit (Validation Split):")
    for regime, val_meta in summary["overfit_report"].items():
        print(f"    - {regime:<22} | {val_meta}")

    print("\n  Expert Specialization Diversity:")
    div = summary["diversity_report"]
    print(f"    Evaluated Experts: {div['num_evaluated_experts']} | Status: {div['specialization_summary']}")


def cmd_benchmark(args: argparse.Namespace) -> None:
    print(f"\n[RAMP BENCHMARK] Executing full benchmark on TEST split (Model: {args.model_id})...")
    engine = RAMPBenchmarkEngine(
        dataset_dir=args.dataset_dir,
        models_dir=args.models_dir,
        baselines_dir=args.baselines_dir,
        regimes_dir=args.regimes_dir,
    )
    res = engine.run_benchmark(model_id=args.model_id)

    print("\n" + "=" * 90)
    print("MASTER FORECASTING SYSTEM BENCHMARK (TEST SPLIT, N=63)")
    print("=" * 90)
    print(f"{'SYSTEM':<20} | {'RMSE (mm)':<10} | {'MAE (mm)':<10} | {'BIAS (mm)':<10} | {'PEARSON r':<10} | {'HEAVY CSI':<10}")
    print("-" * 90)
    for row in res["benchmark_matrix"]:
        print(f"{row['model'].upper():<20} | {row['rmse']:<10.2f} | {row['mae']:<10.2f} | {row['mean_bias']:<10.2f} | {row['pearson_r']:<10.4f} | {row['heavy_rain_csi_64_5']:<10.4f}")
    print("=" * 90)
    print(f"Notice: {res['performance_notice']}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    print(f"\n[RAMP EVALUATE] Evaluating {args.model_id} on {args.split}.parquet...")
    split_path = Path(args.dataset_dir) / f"{args.split}.parquet"
    if not split_path.exists():
        print(f"Error: Split file not found at {split_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_parquet(split_path)
    reg_reg = RAMPModelRegistry(models_dir=args.models_dir)
    ramp_model, meta = reg_reg.load_model(args.model_id, baselines_dir=args.baselines_dir)

    reg_models = RegimeModelRegistry(models_dir=args.regimes_dir).list_models()
    clf, cal, _ = RegimeModelRegistry(models_dir=args.regimes_dir).load_model(reg_models[0].model_id)
    regime_service = RegimeInferenceService(classifier=clf, calibrator=cal)

    service = RAMPInferenceService(ramp_model=ramp_model, regime_service=regime_service)
    batch_res = service.predict_batch(df)

    if "observed_rainfall_mm" in df.columns:
        y_obs = df["observed_rainfall_mm"].values
        y_pred = batch_res["ramp_prediction"].values
        from ml.baselines.verification.metrics import calculate_continuous_metrics, calculate_all_threshold_metrics
        c_m = calculate_continuous_metrics(y_pred, y_obs)
        t_m = calculate_all_threshold_metrics(y_pred, y_obs)
        print(f"\nResults on {args.split.upper()} (N={len(df)}):")
        print(f"  RMSE:      {c_m['rmse']:.2f} mm")
        print(f"  MAE:       {c_m['mae']:.2f} mm")
        print(f"  Mean Bias: {c_m['mean_bias']:.2f} mm")
        print(f"  Pearson r: {c_m['pearson_r']:.4f}")
        print(f"  Heavy CSI (>64.5mm): {t_m['heavy_rainfall']['csi']:.4f}")
    else:
        print(f"Predictions generated for {len(df)} samples (no observations found for verification).")


def cmd_ablation(args: argparse.Namespace) -> None:
    print(f"\n[RAMP ABLATION] Inspecting gating and architecture ablation results for {args.model_id}...")
    ab_path = Path(args.models_dir) / args.model_id / "ramp_ablation.json"
    if not ab_path.exists():
        print("Ablation file not found. Running benchmark to generate ablations...")
        engine = RAMPBenchmarkEngine(models_dir=args.models_dir)
        res = engine.run_benchmark(model_id=args.model_id)
        ablation_rows = res["ablation_comparison"]
    else:
        with open(ab_path, "r", encoding="utf-8") as f:
            ablation_rows = json.load(f)

    print("\n" + "=" * 80)
    print("RAMP ABLATION STUDY: GATING MECHANISM COMPARISON")
    print("=" * 80)
    print(f"{'ABLATION CONFIGURATION':<28} | {'RMSE (mm)':<10} | {'MAE (mm)':<10} | {'BIAS (mm)':<10} | {'HEAVY CSI':<10}")
    print("-" * 80)
    for row in ablation_rows:
        print(f"{row['ablation_tier']:<28} | {row['rmse']:<10.2f} | {row['mae']:<10.2f} | {row['mean_bias']:<10.2f} | {row['heavy_rain_csi_64_5']:<10.4f}")
    print("=" * 80)


def cmd_verify(args: argparse.Namespace) -> None:
    print(f"\n[RAMP VERIFY] Verifying mathematical invariants for {args.model_id}...")

    # Load model
    ramp_reg = RAMPModelRegistry(models_dir=args.models_dir)
    ramp_model, _ = ramp_reg.load_model(args.model_id, baselines_dir=args.baselines_dir)

    # 1. Gate Weights Invariant
    print("  [1/6] Testing Gate Weights Invariant (sum=1.0, non-negativity)...")
    valid_gates = [0.4, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05]
    gw = RegimeGatingEngine.create_gate_weights(valid_gates)
    assert abs(np.sum(gw.as_array()) - 1.0) < 1e-4, "Sum should equal 1.0"
    assert (gw.as_array() >= 0.0).all(), "All gates must be >= 0"
    print("        PASSED: Gate sum and non-negativity strictly validated.")

    # 2. Gate Weights Malformed Loud Rejection
    print("  [2/6] Testing Loud Rejection of Corrupt/Malformed Gates...")
    try:
        RegimeGatingEngine.create_gate_weights([0.5, 0.5, 0.5, 0, 0, 0, 0])
        raise AssertionError("Failed to reject sum=1.5 gate vector!")
    except ValueError:
        print("        PASSED: Corrupt gating vectors reject loudly.")

    # 3. Non-negativity of Expert Predictions and RAMP
    print("  [3/6] Testing Physical Non-negativity Invariant (R >= 0)...")
    dummy_x = {col: 0.0 for col in RegimeExpert.DEFAULT_FEATURE_COLUMNS}
    dummy_x["raw_nwp_rainfall"] = 10.0
    res = ramp_model.predict_sample(dummy_x, gates=gw)
    assert res["ramp_prediction"] >= 0.0, "RAMP prediction must be non-negative"
    for r_name, val in res["expert_predictions"].items():
        assert val >= 0.0, f"Expert {r_name} prediction must be >= 0"
    print(f"        PASSED: RAMP prediction ({res['ramp_prediction']:.2f} mm) is non-negative.")

    # 4. Mathematical Convexity Invariant: min(E_k) <= RAMP <= max(E_k)
    print("  [4/6] Testing Mathematical Convexity Invariant (min E_k <= RAMP <= max E_k)...")
    expert_vals = list(res["expert_predictions"].values())
    min_e = min(expert_vals)
    max_e = max(expert_vals)
    assert min_e - 1e-3 <= res["ramp_prediction"] <= max_e + 1e-3, (
        f"Convexity failed: {res['ramp_prediction']} not in [{min_e}, {max_e}]"
    )
    print(f"        PASSED: {min_e:.2f} mm <= {res['ramp_prediction']:.2f} mm <= {max_e:.2f} mm.")

    # 5. One-Hot Gating Invariant: p_k=1 produces E_k
    print("  [5/6] Testing One-Hot Gating Identity (p_k=1 -> RAMP=E_k)...")
    for regime in REGIME_ORDER:
        one_hot = RegimeGatingEngine.create_one_hot_gate(regime)
        res_oh = ramp_model.predict_sample(dummy_x, gates=one_hot)
        expected = res_oh["expert_predictions"][regime.value]
        diff = abs(res_oh["ramp_prediction"] - expected)
        assert diff < 1e-3, f"One-hot gating for {regime.value} yielded diff={diff}"
    print("        PASSED: Pure regime gate identically equals specialized expert output.")

    # 6. Uniform Gating Invariant: p_k=1/7 produces Arithmetic Mean
    print("  [6/6] Testing Uniform Gating Invariant (p_k=1/7 -> Arithmetic Mean)...")
    uniform_gates = RegimeGatingEngine.create_uniform_gates()
    res_unif = ramp_model.predict_sample(dummy_x, gates=uniform_gates)
    mean_e = float(np.mean(list(res_unif["expert_predictions"].values())))
    diff_unif = abs(res_unif["ramp_prediction"] - mean_e)
    assert diff_unif < 1e-3, f"Uniform gating diff={diff_unif}"
    print(f"        PASSED: Uniform gating matches mean ({mean_e:.2f} mm vs {res_unif['ramp_prediction']:.2f} mm).")

    print("\nALL RAMP MATHEMATICAL INVARIANTS VERIFIED SUCCESSFULLY (6/6).")


def cmd_inspect(args: argparse.Namespace) -> None:
    print(f"\n[RAMP INSPECT] Inspecting model artifacts for {args.model_id}...")
    model_dir = Path(args.models_dir) / args.model_id
    meta_path = model_dir / "ramp_model_metadata.json"
    if not meta_path.exists():
        print(f"Error: Model not found at {model_dir}", file=sys.stderr)
        sys.exit(1)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("\n" + "=" * 70)
    print(f"RAMP MODEL CARD & ARCHITECTURE METADATA: {args.model_id}")
    print("=" * 70)
    print(f"  Dataset Version:          {meta.get('dataset_version')}")
    print(f"  Phase 4 Regime Model:     {meta.get('phase4_model_version')}")
    print(f"  Phase 5 Baseline Model:   {meta.get('phase5_baseline_version')}")
    print(f"  Training Mode:            {meta.get('training_mode')}")
    print(f"  Created At:               {meta.get('created_at')}")

    print("\n  Specialized Regime Experts:")
    for regime in REGIME_ORDER:
        r_name = regime.value
        status = meta.get("expert_statuses", {}).get(r_name, "UNKNOWN")
        v = meta.get("expert_versions", {}).get(r_name, "v1")
        print(f"    - {r_name:<22} | Version: {v:<12} | Status: {status}")

    # Inspect diversity if available
    div_path = model_dir / "expert_diversity.json"
    if div_path.exists():
        with open(div_path, "r", encoding="utf-8") as f:
            div = json.load(f)
        print("\n  Pairwise Expert Prediction Correlation Matrix:")
        corr = div.get("correlation_matrix", {})
        names = list(corr.keys())
        header = f"{'EXPERT':<18} " + " ".join([f"{n[:6]:>7}" for n in names])
        print("  " + header)
        for n1 in names:
            row_str = f"  {n1[:18]:<18} " + " ".join([f"{corr[n1].get(n2, 0.0):>7.2f}" for n2 in names])
            print(row_str)
    print("=" * 70)


def cmd_predict(args: argparse.Namespace) -> None:
    print(f"\n[RAMP PREDICT] Executing inference with {args.model_id}...")
    ramp_reg = RAMPModelRegistry(models_dir=args.models_dir)
    ramp_model, _ = ramp_reg.load_model(args.model_id, baselines_dir=args.baselines_dir)

    reg_models = RegimeModelRegistry(models_dir=args.regimes_dir).list_models()
    clf, cal, _ = RegimeModelRegistry(models_dir=args.regimes_dir).load_model(reg_models[0].model_id)
    regime_service = RegimeInferenceService(classifier=clf, calibrator=cal)
    service = RAMPInferenceService(ramp_model=ramp_model, regime_service=regime_service)

    if args.sample_id:
        test_path = Path("./data/processed/training/ramp_dataset_v0.3.0/test.parquet")
        df = pd.read_parquet(test_path)
        matching = df[df["sample_id"] == args.sample_id]
        if matching.empty:
            print(f"Sample {args.sample_id} not found in test partition.", file=sys.stderr)
            sys.exit(1)
        rec = service.predict_sample(matching.iloc[0])
        print("\nPrediction Record:")
        print(json.dumps(rec.model_dump(), indent=2))
    elif args.input_file:
        in_path = Path(args.input_file)
        df = pd.read_parquet(in_path) if in_path.suffix == ".parquet" else pd.read_csv(in_path)
        preds_df = service.predict_batch(df)
        if args.output:
            preds_df.to_parquet(args.output)
            print(f"Predictions written to {args.output}")
        else:
            print(preds_df[["sample_id", "raw_nwp_rainfall", "ramp_prediction"]].head(10))
    else:
        print("Please specify either --sample-id or --input-file. Run with --help for info.", file=sys.stderr)


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "train":
        cmd_train(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "ablation":
        cmd_ablation(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "predict":
        cmd_predict(args)


if __name__ == "__main__":
    main()
