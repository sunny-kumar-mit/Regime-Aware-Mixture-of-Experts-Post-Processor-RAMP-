"""
RAMP Scientific CLI — Phase 10
SIH26080 | MoES / NCMRWF

python -m ml.scientific <command>

Commands:
  inspect      Show verification engine status
  verify       Compute continuous metrics
  thresholds   Compute threshold verification
  regimes      Compute regime-stratified verification
  lead-time    Compute lead-time verification curves
  spatial      Compute spatial verification
  calibration  Compute probability calibration
  bootstrap    Run paired bootstrap significance tests
  failures     Run failure analysis
  explain      Run explainability analysis
  cases        List and replay case studies
  report       Generate all scientific reports
  pipeline     Run full Phase 10 pipeline
  jury-demo    Prepare jury demo data
"""

from __future__ import annotations

import argparse
import json
import sys

from ml.scientific.benchmarks import ModelBenchmarkComparison
from ml.scientific.calibration import CalibrationAnalyzer
from ml.scientific.case_study import CaseStudyReplayEngine
from ml.scientific.explainability import ExplainabilityEngine
from ml.scientific.expert_analysis import ExpertGatingAnalyzer
from ml.scientific.failure_analysis import FailureAnalysisEngine
from ml.scientific.feature_attribution import FeatureAttributionEngine
from ml.scientific.lead_time import LeadTimeVerification
from ml.scientific.regimes import RegimeStratifiedVerification
from ml.scientific.registry import ScientificRegistry, SCIENTIFIC_VERSION
from ml.scientific.report import ScientificReportGenerator
from ml.scientific.significance import BootstrapSignificanceEngine
from ml.scientific.spatial import SpatialVerificationEngine
from ml.scientific.verification import ScientificVerificationEngine


def _print_json(data):
    print(json.dumps(data, indent=2, default=str))


def cmd_inspect(args):
    engine = ScientificVerificationEngine()
    print("=== RAMP Phase 10 — Scientific Verification Engine ===")
    status = engine.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")

    explain = ExplainabilityEngine()
    xai_status = explain.get_status()
    print("\n=== Explainability Engine ===")
    for k, v in xai_status.items():
        print(f"  {k}: {v}")

    print(f"\n  scientific_version: {SCIENTIFIC_VERSION}")
    print("  Status: READY (SYNTHETIC_DEMO mode)")


def cmd_verify(args):
    print("=== Continuous Verification Metrics ===")
    engine = ScientificVerificationEngine()
    metrics = engine.compute_all_continuous_metrics()
    table = engine.compute_neutral_comparison_table(metrics)
    _print_json(table)


def cmd_thresholds(args):
    print("=== Threshold Verification (0.1 / 64.5 / 115.6 / 204.5 mm) ===")
    engine = ThresholdVerificationEngine = __import__(
        "ml.scientific.thresholds", fromlist=["ThresholdVerificationEngine"]
    ).ThresholdVerificationEngine
    tv = engine()
    results = tv.compute_all_thresholds()
    table = tv.flat_table(results)
    _print_json(table[:4])  # Show first 4 rows
    print(f"\n  Total threshold metric rows: {len(table)}")


def cmd_regimes(args):
    print("=== Regime-Stratified Verification ===")
    engine = RegimeStratifiedVerification()
    metrics = engine.compute_synthetic_regime_metrics()
    table = engine.regime_comparison_table(metrics)
    _print_json(table)


def cmd_lead_time(args):
    print("=== Lead-Time Verification Curves (Day 1 to Day 5) ===")
    engine = LeadTimeVerification()
    curves = engine.compute_lead_time_curves()
    table = engine.flat_table(curves)
    print(f"  Total lead-time points: {len(table)}")
    for model in ["RAMP_MOE", "RAW_NWP"]:
        model_rows = [r for r in table if r["model"] == model]
        print(f"\n  {model}:")
        for row in model_rows:
            print(f"    {row['lead_time_name']}: RMSE={row['rmse']} mm, CSI={row['csi']} (n={row['n_samples']})")


def cmd_spatial(args):
    print("=== Spatial Verification ===")
    engine = SpatialVerificationEngine()
    records = engine._synthetic_district_records()
    summary = engine.get_spatial_summary(records)
    _print_json(summary)
    print(f"\n  District records: {len(records)}")


def cmd_calibration(args):
    print("=== Probability Calibration Analysis ===")
    engine = CalibrationAnalyzer()
    results = engine.analyze_all_thresholds()
    for thr, metrics in results.items():
        print(f"\n  Threshold {thr} mm: {metrics.availability_status}")
        if metrics.brier is not None:
            print(f"    Brier={metrics.brier}, ECE={metrics.ece}, BSS={metrics.bss}")


def cmd_bootstrap(args):
    print("=== Paired Bootstrap Significance Tests ===")
    engine = BootstrapSignificanceEngine()
    results = engine.run_pairwise_battery()
    for r in results[:6]:  # Show first 6
        print(f"  {r.model_a} vs {r.model_b} [{r.metric}]: {r.conclusion} "
              f"(diff={r.difference}, CI=[{r.ci_lower}, {r.ci_upper}])")
    print(f"\n  Total bootstrap comparisons: {len(results)}")


def cmd_failures(args):
    print("=== Failure Analysis ===")
    engine = FailureAnalysisEngine()
    summary = engine._synthetic_failure_summary()
    print(f"  Total cases: {summary.total_cases_analyzed}")
    print(f"  Underpredictions: {summary.n_underprediction}")
    print(f"  Overpredictions: {summary.n_overprediction}")
    print(f"  Missed heavy events: {summary.n_miss_heavy}")
    print(f"  False alarms: {summary.n_false_alarm_heavy}")
    print(f"  Large divergences: {summary.n_large_divergence}")
    print(f"  Availability: {summary.availability_status}")


def cmd_explain(args):
    print("=== Explainability Analysis ===")
    engine = ExplainabilityEngine()
    status = engine.get_status()
    print(f"  SHAP available: {status['shap_available']}")
    print(f"  SHAP status: {status['shap_status']}")

    explanation = engine.explain_synthetic_sample()
    print(f"\n  Sample ID: {explanation.sample_id}")
    print(f"  Regime: {explanation.dominant_regime} (entropy={explanation.regime_entropy})")
    print(f"  Raw NWP: {explanation.raw_nwp_mm} mm → RAMP: {explanation.ramp_prediction_mm} mm")
    print(f"  Top expert: {explanation.top_expert} (weight={explanation.top_expert_weight})")
    print(f"  Top 3 features:")
    for feat in explanation.top_features[:3]:
        print(f"    {feat['feature_name']} ({feat['feature_group']}): {feat.get('gain_importance')}")


def cmd_cases(args):
    print("=== Case Study Replay ===")
    engine = CaseStudyReplayEngine()
    cases = engine.list_cases()
    for c in cases:
        print(f"  [{c['case_id']}] {c['case_label']}")
        print(f"    Date: {c['date']} | Regime: {c['regime']} | District: {c['district']}")

    if args.case_id:
        case = engine.get_case(args.case_id)
        if case:
            print(f"\n  Pipeline for {case.case_id}:")
            for stage in case.pipeline_stages:
                print(f"    [{stage.status}] {stage.stage}")
        else:
            print(f"  Case '{args.case_id}' not found.")


def cmd_report(args):
    print("=== Generating Scientific Reports ===")
    generator = ScientificReportGenerator()
    generated = generator.generate_all()
    print(f"  Generated {len(generated)} report/export files:")
    for fname, path in sorted(generated.items()):
        print(f"    {fname}")
    print("\n  [OK] All scientific reports generated successfully.")


def cmd_pipeline(args):
    print("=" * 60)
    print("RAMP Phase 10 — Full Scientific Verification Pipeline")
    print("=" * 60)
    print("\nDATA MODE: SYNTHETIC_DEMO")
    print("REAL IMD/NCMRWF ARCHIVES: NOT MOUNTED\n")

    print("[1/12] Verifying continuous metrics...")
    cmd_verify(args)
    print("\n[2/12] Verifying threshold metrics...")
    cmd_thresholds(args)
    print("\n[3/12] Regime-stratified verification...")
    cmd_regimes(args)
    print("\n[4/12] Lead-time verification...")
    cmd_lead_time(args)
    print("\n[5/12] Spatial verification...")
    cmd_spatial(args)
    print("\n[6/12] Calibration analysis...")
    cmd_calibration(args)
    print("\n[7/12] Bootstrap significance...")
    cmd_bootstrap(args)
    print("\n[8/12] Failure analysis...")
    cmd_failures(args)
    print("\n[9/12] Explainability...")
    cmd_explain(args)
    print("\n[10/12] Case study replay...")
    cmd_cases(args)
    print("\n[11/12] Generating reports...")
    cmd_report(args)
    print("\n[12/12] Recording audit manifest...")

    reg = ScientificRegistry()
    manifest = reg.create_run_manifest()
    print(f"  Run ID: {manifest.run_id}")
    print(f"\n✓ Phase 10 pipeline complete. All outputs labeled SYNTHETIC_DEMO.")


def cmd_jury_demo(args):
    print("=== Jury Demo Data Preparation ===")
    # Generate all data needed for /jury-demo page
    benchmark = ModelBenchmarkComparison()
    summary = benchmark.summary_table()

    case_engine = CaseStudyReplayEngine()
    cases = case_engine.replay_all()

    explain_engine = ExplainabilityEngine()
    explanation = explain_engine.explain_synthetic_sample()

    expert_analyzer = ExpertGatingAnalyzer()
    matrix = expert_analyzer._synthetic_regime_expert_matrix()

    print(f"  Benchmark models: {len(summary)}")
    print(f"  Case studies: {len(cases)}")
    print(f"  Explanation generated: {explanation.sample_id}")
    print(f"  Regime-expert matrix: {len(matrix.matrix)} regimes")
    print("\n  ✓ Jury demo data ready for /jury-demo frontend.")


def main():
    parser = argparse.ArgumentParser(
        prog="python -m ml.scientific",
        description="RAMP Phase 10 Scientific Verification CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("inspect", help="Show engine status")
    subparsers.add_parser("verify", help="Compute continuous metrics")
    subparsers.add_parser("thresholds", help="Compute threshold verification")
    subparsers.add_parser("regimes", help="Regime-stratified verification")
    sub_lt = subparsers.add_parser("lead-time", help="Lead-time verification")
    subparsers.add_parser("spatial", help="Spatial verification")
    subparsers.add_parser("calibration", help="Probability calibration")
    subparsers.add_parser("bootstrap", help="Bootstrap significance tests")
    subparsers.add_parser("failures", help="Failure analysis")
    subparsers.add_parser("explain", help="Explainability analysis")
    case_sub = subparsers.add_parser("cases", help="Case study replay")
    case_sub.add_argument("--case-id", dest="case_id", default=None, help="Specific case ID to replay")
    subparsers.add_parser("report", help="Generate all scientific reports")
    subparsers.add_parser("pipeline", help="Run full Phase 10 pipeline")
    subparsers.add_parser("jury-demo", help="Prepare jury demo data")

    args = parser.parse_args()

    commands = {
        "inspect": cmd_inspect,
        "verify": cmd_verify,
        "thresholds": cmd_thresholds,
        "regimes": cmd_regimes,
        "lead-time": cmd_lead_time,
        "spatial": cmd_spatial,
        "calibration": cmd_calibration,
        "bootstrap": cmd_bootstrap,
        "failures": cmd_failures,
        "explain": cmd_explain,
        "cases": cmd_cases,
        "report": cmd_report,
        "pipeline": cmd_pipeline,
        "jury-demo": cmd_jury_demo,
    }

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
