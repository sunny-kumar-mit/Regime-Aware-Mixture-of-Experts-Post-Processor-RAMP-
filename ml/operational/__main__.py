"""
Phase 8 Operational CLI Entrypoint
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Commands:
  python -m ml.operational readiness
  python -m ml.operational ingest [--path <path>]
  python -m ml.operational validate [--dataset <path>]
  python -m ml.operational replay [--dataset <path>] [--samples <N>]
  python -m ml.operational verify [--dataset <path>]
  python -m ml.operational benchmark [--dataset <path>]
  python -m ml.operational report [--out <path>]
  python -m ml.operational inspect [--dir <path>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import pandas as pd

from ml.data.discovery import DataDiscoveryService
from ml.data.manifest import DatasetManifest
from ml.data.providers.real_provider import RealDataProvider
from ml.data.quality import MeteorologicalQualityControl
from ml.data.readiness import RealDataReadinessChecker
from ml.operational.readiness import OperationalReadinessEvaluator
from ml.operational.registry import OperationalModelRegistry
from ml.operational.verification import OperationalVerificationEngine
from ml.pipeline.replay import PipelineReplayer


def cmd_readiness(args):
    evaluator = OperationalReadinessEvaluator()
    assessment = evaluator.evaluate()

    print("=" * 65)
    print("  RAMP OPERATIONAL READINESS ASSESSMENT | SIH26080")
    print("=" * 65)
    print(f"Current Engineering Readiness: {assessment.current_level_name}")
    print(f"Data Mode:                     {assessment.data_mode}")
    print(f"Real Data Available:           {'YES' if assessment.is_real_data_available else 'NO'}")
    print("-" * 65)
    print(assessment.summary)
    print("\n[READINESS TIERS PROGRESSION]")
    for tier in assessment.tiers:
        status_symbol = "[X]" if tier.status == "ACHIEVED" else ("[>]" if tier.status == "CURRENT_ACTIVE" else "[ ]")
        print(f"  {status_symbol} Level {tier.level}: {tier.name:<32} ({tier.status})")
    print("\n[DISCLAIMER]")
    print(assessment.disclaimer)
    print("=" * 65)


def cmd_ingest(args):
    provider = RealDataProvider()
    print("=" * 65)
    print("  RAMP DATA INGESTION ENGINE")
    print("=" * 65)
    df = provider.load_canonical()
    contract = provider.get_contract()
    print(f"Provider:        {provider.get_source_name()}")
    print(f"Data Mode:       {provider.get_mode().value}")
    print(f"Dataset ID:      {contract.dataset_id}")
    print(f"Records Ingested:{len(df):,}")
    print(f"Columns:         {', '.join(df.columns[:10])}...")
    print("=" * 65)


def cmd_validate(args):
    provider = RealDataProvider()
    df = provider.load_canonical()
    qc = MeteorologicalQualityControl()
    valid_df, report = qc.inspect_and_filter(df, dataset_id="cli_validation", data_mode=provider.get_mode().value)
    qc.save_reports(report)

    print("=" * 65)
    print("  METEOROLOGICAL DATA QUALITY CONTROL (13 CHECKS)")
    print("=" * 65)
    print(f"Overall Status:        {report.overall_status}")
    print(f"Total Records:         {report.total_records:,}")
    print(f"Valid Passed:          {report.valid_records:,}")
    print(f"Invalid Rejected:      {report.invalid_records:,}")
    print(f"Extreme Preserved:     {report.extreme_but_valid_rain_count:,} records (>=204.5 mm)")
    print("-" * 65)
    print(f"{'ID':<4} {'Check Name':<40} {'Status':<8} {'Affected':<8}")
    print("-" * 65)
    for c in report.checks_summary:
        st = "PASS" if c["passed"] else "FAIL"
        print(f"{c['check_id']:<4} {c['name']:<40} {st:<8} {c['affected_count']:<8}")
    print("=" * 65)


def cmd_replay(args):
    samples = getattr(args, "samples", 1000)
    dataset = getattr(args, "dataset", None)
    replayer = PipelineReplayer()
    summary = replayer.replay(dataset_source=dataset, max_samples=samples)

    print("=" * 65)
    print(f"  RAMP PIPELINE REPLAY: {summary.overall_status}")
    print("=" * 65)
    print(f"Run ID:        {summary.run_id}")
    print(f"Total Time:    {summary.total_duration_sec}s")
    for s in summary.stages:
        print(f"  {s.stage_name:<42} [{s.status}] ({s.duration_ms:.1f}ms)")
    print("=" * 65)


def cmd_verify(args):
    provider = RealDataProvider()
    df = provider.load_canonical()
    verifier = OperationalVerificationEngine(data_mode=provider.get_mode().value)
    results = verifier.verify_dataset(df)

    print("=" * 65)
    print("  RAMP OPERATIONAL VERIFICATION METRICS")
    print("=" * 65)
    print(f"Data Mode:    {results['data_mode']}")
    print(f"Sample Count: {results['sample_count']}")
    print("\n[CONTINUOUS METRICS: RAMP vs RAW NWP]")
    c_ramp = results["continuous_metrics"]["RAMP_MoE"]
    c_nwp = results["continuous_metrics"]["RAW_NWP"]
    print(f"  RMSE:       RAMP = {c_ramp['rmse']} mm | RAW NWP = {c_nwp['rmse']} mm")
    print(f"  MAE:        RAMP = {c_ramp['mae']} mm | RAW NWP = {c_nwp['mae']} mm")
    print(f"  Pearson r:  RAMP = {c_ramp['pearson_r']} | RAW NWP = {c_nwp['pearson_r']}")

    print("\n[THRESHOLD METRICS (64.5 mm Heavy Rain)]")
    t_heavy = results["threshold_metrics"]["64.5mm"]["RAMP_MoE"]
    print(f"  CSI:        {t_heavy['csi']}")
    print(f"  POD:        {t_heavy['pod']}")
    print(f"  FAR:        {t_heavy['far']}")

    print("\n[PROBABILITY METRICS (64.5 mm Heavy Rain)]")
    p_heavy = results["extreme_probability_metrics"]["64.5mm"]
    print(f"  Brier Score:{p_heavy['ramp_prob_brier']}")
    print(f"  BSS:        {p_heavy['bss_vs_climatology']}")
    print(f"  PR-AUC:     {p_heavy['pr_auc']}")
    print(f"  ECE:        {p_heavy['ece']}")
    print("=" * 65)


def cmd_benchmark(args):
    provider = RealDataProvider()
    df = provider.load_canonical()
    verifier = OperationalVerificationEngine(data_mode=provider.get_mode().value)
    results = verifier.verify_dataset(df)

    matrix = results.get("benchmark_matrix", [])
    print("=" * 85)
    print("  RAMP UNIFIED OPERATIONAL BENCHMARK LADDER")
    print("=" * 85)
    print(f"{'SYSTEM':<26} {'RMSE':<8} {'MAE':<8} {'Bias':<8} {'RainCSI':<8} {'HvyCSI':<8} {'Brier':<8} {'PR-AUC':<8}")
    print("-" * 85)
    for row in matrix:
        print(
            f"{row['system']:<26} {row['rmse']:<8.2f} {row['mae']:<8.2f} "
            f"{row['mean_bias']:<8.2f} {row['rain_csi']:<8.3f} {row['heavy_csi']:<8.3f} "
            f"{row['brier_heavy']:<8.4f} {row['pr_auc']:<8.3f}"
        )
    print("=" * 85)


def cmd_report(args):
    print("=" * 65)
    print("  RAMP OPERATIONAL REPORTS REGISTRY")
    print("=" * 65)
    print("Quality Report:        data/quality/data_quality_report.json")
    print("Quality Markdown:      data/quality/DATA_QUALITY_REPORT.md")
    print("Dataset Manifest:      data/manifests/dataset_manifest.json")
    print("Audit Runs Directory:  data/audit/runs/")
    print("Phase 7 Report:        docs/reports/PHASE_7_PROJECT_REPORT.md")
    print("Phase 8 Report:        docs/reports/PHASE_8_PROJECT_REPORT.md")
    print("=" * 65)


def cmd_inspect(args):
    search_dir = getattr(args, "dir", "data/raw")
    service = DataDiscoveryService([search_dir, "data/processed", "data/real"])
    summary = service.discover()

    print("=" * 65)
    print("  RAMP DATA DISCOVERY & METADATA INSPECTOR")
    print("=" * 65)
    print(f"Total Files Scanned: {summary.total_files_scanned}")
    print(f"NetCDF Archives:     {summary.netcdf_files_count}")
    print(f"GRIB Archives:       {summary.grib_files_count}")
    print(f"Parquet Files:       {summary.parquet_files_count}")
    print(f"CSV Files:           {summary.csv_files_count}")
    print(f"Data Mode Inferred:  {summary.data_mode}")
    print(f"Discovered Vars:     {', '.join(summary.discovered_variables[:12])}...")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="RAMP Operational Command Line Interface")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("readiness", help="Check operational readiness level and real-data status")
    p_ingest = subparsers.add_parser("ingest", help="Ingest meteorological dataset")
    p_ingest.add_argument("--path", type=str, default=None)

    p_val = subparsers.add_parser("validate", help="Run 13 quality checks on dataset")
    p_val.add_argument("--dataset", type=str, default=None)

    p_rep = subparsers.add_parser("replay", help="Run full pipeline replay")
    p_rep.add_argument("--dataset", type=str, default=None)
    p_rep.add_argument("--samples", type=int, default=1000)

    p_ver = subparsers.add_parser("verify", help="Run operational verification")
    p_ver.add_argument("--dataset", type=str, default=None)

    p_bm = subparsers.add_parser("benchmark", help="Output benchmark comparison ladder")
    p_bm.add_argument("--dataset", type=str, default=None)

    p_rep_out = subparsers.add_parser("report", help="List and inspect reports")
    p_rep_out.add_argument("--out", type=str, default=None)

    p_insp = subparsers.add_parser("inspect", help="Inspect raw files metadata")
    p_insp.add_argument("--dir", type=str, default="data/raw")

    args = parser.parse_args()

    commands = {
        "readiness": cmd_readiness,
        "ingest": cmd_ingest,
        "validate": cmd_validate,
        "replay": cmd_replay,
        "verify": cmd_verify,
        "benchmark": cmd_benchmark,
        "report": cmd_report,
        "inspect": cmd_inspect,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        # Default action
        cmd_readiness(args)


if __name__ == "__main__":
    main()
