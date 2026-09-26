"""
RAMP Scientific Verification REST API — Phase 10
SIH26080 | MoES / NCMRWF

19 endpoints under /api/scientific/*:
  status, verification, thresholds, regimes, lead-time, spatial,
  fss, calibration, bootstrap, failures, cases, case/{id},
  explainability, shap, features, experts, provenance, report, jury-demo

Every response includes: data_mode, model_version, run_id, timestamp,
sample_count, availability_status, provenance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

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

router = APIRouter(prefix="/scientific", tags=["Phase 10 — Scientific Verification"])

DATA_MODE = "SYNTHETIC_DEMO"
DATASET_VERSION = "ramp_dataset_v0.3.0"
MODEL_VERSION = "ramp_v1.0.0"
PHASE_VERSION = SCIENTIFIC_VERSION


def _envelope(data: Any, availability: str = "SYNTHETIC_DEMO", sample_count: int = 0) -> Dict[str, Any]:
    """Standard Phase 10 API response envelope."""
    return {
        "data_mode": DATA_MODE,
        "dataset_version": DATASET_VERSION,
        "model_version": MODEL_VERSION,
        "phase_version": PHASE_VERSION,
        "run_id": f"api_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "sample_count": sample_count,
        "availability_status": availability,
        "provenance": {
            "scientific_version": SCIENTIFIC_VERSION,
            "thresholds_mm": [0.1, 64.5, 115.6, 204.5],
            "bootstrap_samples": 300,
            "random_seed": 42,
        },
        "data": data,
    }


@router.get("/status")
def scientific_status() -> Dict[str, Any]:
    """Phase 10 scientific verification service status."""
    engine = ScientificVerificationEngine()
    status = engine.get_status()

    explain = ExplainabilityEngine()
    xai_status = explain.get_status()

    reg = ScientificRegistry()
    provenance = reg.get_standard_provenance()

    return _envelope({
        **status,
        "explainability": xai_status,
        "scientific_version": SCIENTIFIC_VERSION,
        "data_mode_note": (
            "SYNTHETIC DEMONSTRATION — REAL OPERATIONAL DATA NOT AVAILABLE. "
            "REAL IMD/NCMRWF OBSERVATIONAL ARCHIVES ARE NOT CURRENTLY MOUNTED."
        ),
        "provenance": provenance,
    }, availability="SYNTHETIC_DEMO")


@router.get("/verification")
def scientific_verification() -> Dict[str, Any]:
    """Continuous verification metrics for all 6 forecast systems."""
    engine = ScientificVerificationEngine()
    metrics = engine.compute_all_continuous_metrics()
    table = engine.compute_neutral_comparison_table(metrics)
    return _envelope(table, availability="SYNTHETIC_DEMO", sample_count=200)


@router.get("/thresholds")
def scientific_thresholds(
    threshold_mm: Optional[float] = Query(None, description="Filter by specific threshold (0.1, 64.5, 115.6, 204.5)")
) -> Dict[str, Any]:
    """Threshold-based categorical verification (POD, FAR, CSI, ETS)."""
    engine = __import__(
        "ml.scientific.thresholds", fromlist=["ThresholdVerificationEngine"]
    ).ThresholdVerificationEngine()
    results = engine.compute_all_thresholds()
    table = engine.flat_table(results)

    if threshold_mm is not None:
        table = [r for r in table if r.get("threshold_mm") == threshold_mm]

    return _envelope(table, availability="SYNTHETIC_DEMO", sample_count=200)


@router.get("/regimes")
def scientific_regimes() -> Dict[str, Any]:
    """Regime-stratified verification using Phase 4 forecast-time regimes."""
    engine = RegimeStratifiedVerification()
    metrics = engine.compute_synthetic_regime_metrics()
    table = engine.regime_comparison_table(metrics)
    return _envelope(table, availability="SYNTHETIC_DEMO", sample_count=200)


@router.get("/lead-time")
def scientific_lead_time() -> Dict[str, Any]:
    """Lead-time verification curves (Day 1 to Day 5)."""
    engine = LeadTimeVerification()
    curves = engine.compute_lead_time_curves()
    table = engine.flat_table(curves)
    return _envelope(table, availability="SYNTHETIC_DEMO", sample_count=len(table))


@router.get("/spatial")
def scientific_spatial() -> Dict[str, Any]:
    """Spatial verification consuming Phase 9 district products."""
    engine = SpatialVerificationEngine()
    records = engine._synthetic_district_records()
    summary = engine.get_spatial_summary(records)
    return _envelope({
        "summary": summary,
        "districts": [d.to_dict() for d in records],
    }, availability="SYNTHETIC_DEMO", sample_count=len(records))


@router.get("/fss")
def scientific_fss() -> Dict[str, Any]:
    """
    Fractions Skill Score analysis from Phase 9.
    Real FSS requires observations — returns NOT_AVAILABLE.
    """
    return _envelope({
        "fss_note": (
            "FSS requires collocated observed precipitation grids. "
            "Real observations are NOT_AVAILABLE in SYNTHETIC_DEMO mode."
        ),
        "scales_km": [5, 25, 50, 100, 200],
        "thresholds_mm": [0.1, 64.5, 115.6, 204.5],
        "availability_status": "NOT_AVAILABLE",
        "reference": "Phase 9 FractionsSkillScoreService provides FSS engine.",
    }, availability="NOT_AVAILABLE", sample_count=0)


@router.get("/calibration")
def scientific_calibration() -> Dict[str, Any]:
    """Probability calibration analysis (Brier, ECE, MCE, reliability diagrams)."""
    engine = CalibrationAnalyzer()
    results = engine.analyze_all_thresholds()
    calibration_data = {str(thr): m.to_dict() for thr, m in results.items()}
    return _envelope(calibration_data, availability="SYNTHETIC_DEMO", sample_count=200)


@router.get("/bootstrap")
def scientific_bootstrap() -> Dict[str, Any]:
    """Paired bootstrap confidence intervals for model comparisons."""
    engine = BootstrapSignificanceEngine()
    results = engine.run_pairwise_battery()
    return _envelope(
        [r.to_dict() for r in results],
        availability="SYNTHETIC_DEMO",
        sample_count=200,
    )


@router.get("/failures")
def scientific_failures() -> Dict[str, Any]:
    """Failure analysis: missed events, false alarms, large divergences."""
    engine = FailureAnalysisEngine()
    summary = engine._synthetic_failure_summary()
    data = summary.to_dict()
    data["failure_cases"] = [c.to_dict() for c in summary.failure_cases]
    return _envelope(data, availability="SYNTHETIC_DEMO", sample_count=summary.total_cases_analyzed)


@router.get("/cases")
def scientific_cases() -> Dict[str, Any]:
    """List available case studies."""
    engine = CaseStudyReplayEngine()
    cases = engine.list_cases()
    return _envelope(cases, availability="SYNTHETIC_DEMO", sample_count=len(cases))


@router.get("/case/{case_id}")
def scientific_case(case_id: str) -> Dict[str, Any]:
    """Detailed case study with full 9-stage pipeline replay."""
    engine = CaseStudyReplayEngine()
    case = engine.get_case(case_id)
    if case is None:
        return _envelope(
            {"error": f"Case '{case_id}' not found.", "available_cases": [c["case_id"] for c in engine.list_cases()]},
            availability="NOT_AVAILABLE",
        )
    return _envelope(case.to_dict(), availability="SYNTHETIC_DEMO")


@router.get("/explainability")
def scientific_explainability() -> Dict[str, Any]:
    """Full prediction explanation with expert gating and feature attribution."""
    engine = ExplainabilityEngine()
    explanation = engine.explain_synthetic_sample()
    return _envelope(explanation.to_dict(), availability="SYNTHETIC_DEMO")


@router.get("/shap")
def scientific_shap() -> Dict[str, Any]:
    """SHAP attribution analysis. Returns SHAP_NOT_AVAILABLE with graceful fallback."""
    attr_engine = FeatureAttributionEngine()
    shap_avail = attr_engine._check_shap_available()

    if not shap_avail:
        # Graceful fallback to gain importance
        attr = attr_engine.get_synthetic_attribution()
        return _envelope({
            "shap_status": "SHAP_NOT_AVAILABLE",
            "fallback_method": "GAIN_IMPORTANCE",
            "feature_importances": [f.to_dict() for f in attr.feature_importances[:15]],
            "note": "Install 'shap' package for TreeExplainer SHAP values.",
        }, availability="FEATURE_IMPORTANCE_AVAILABLE", sample_count=len(attr.feature_importances))

    return _envelope({
        "shap_status": "AVAILABLE",
        "method": "TreeExplainer",
    }, availability="AVAILABLE")


@router.get("/features")
def scientific_features() -> Dict[str, Any]:
    """Feature importance grouped by feature category."""
    attr_engine = FeatureAttributionEngine()
    attr = attr_engine.get_synthetic_attribution()
    group_summary = attr_engine.group_summary(attr)

    return _envelope({
        "method": attr.method,
        "availability": attr.availability,
        "n_features": attr.n_features,
        "feature_importances": [f.to_dict() for f in attr.feature_importances],
        "group_summary": group_summary,
        "leakage_detected": attr.leakage_detected,
    }, availability="FEATURE_IMPORTANCE_AVAILABLE", sample_count=attr.n_features)


@router.get("/experts")
def scientific_experts() -> Dict[str, Any]:
    """Regime × Expert gating interaction matrix."""
    analyzer = ExpertGatingAnalyzer()
    matrix = analyzer._synthetic_regime_expert_matrix()
    summary = analyzer.get_regime_expert_summary(matrix)
    return _envelope({
        "matrix": matrix.to_dict(),
        "summary_table": summary,
    }, availability="SYNTHETIC_DEMO", sample_count=sum(matrix.sample_counts.values()))


@router.get("/provenance")
def scientific_provenance() -> Dict[str, Any]:
    """Full scientific run provenance and reproducibility metadata."""
    reg = ScientificRegistry()
    manifest = reg.create_run_manifest()
    provenance = reg.get_standard_provenance()
    return _envelope({
        "manifest": manifest.to_dict(),
        "provenance": provenance,
    }, availability="AVAILABLE")


@router.get("/report")
def scientific_report() -> Dict[str, Any]:
    """Generate all scientific reports and return manifest of generated files."""
    generator = ScientificReportGenerator()
    generated = generator.generate_all()
    return _envelope({
        "generated_files": generated,
        "n_files": len(generated),
        "report_directory": "data/scientific_reports/",
        "export_directory": "data/scientific_exports/",
    }, availability="AVAILABLE")


@router.get("/jury-demo")
def scientific_jury_demo() -> Dict[str, Any]:
    """Complete jury demonstration data package."""
    benchmark = ModelBenchmarkComparison()
    summary_table = benchmark.summary_table()

    case_engine = CaseStudyReplayEngine()
    cases = case_engine.list_cases()
    first_case = case_engine.get_case("CASE_001")

    explain_engine = ExplainabilityEngine()
    explanation = explain_engine.explain_synthetic_sample()

    expert_analyzer = ExpertGatingAnalyzer()
    matrix = expert_analyzer._synthetic_regime_expert_matrix()
    expert_summary = expert_analyzer.get_regime_expert_summary(matrix)

    return _envelope({
        "jury_demo_version": "1.0.0",
        "stages": [
            {"stage": 1, "title": "Problem Statement", "description": "Bias in NWP monsoon rainfall forecasts"},
            {"stage": 2, "title": "Raw NWP Forecast", "description": "GFS/NCMRWF 0.25° grid input"},
            {"stage": 3, "title": "Weather Regime Detection", "description": "Phase 4 LightGBM regime classifier"},
            {"stage": 4, "title": "RAMP Mixture-of-Experts", "description": "7 specialized regime experts"},
            {"stage": 5, "title": "Extreme Rainfall Probability", "description": "Phase 7 calibrated exceedance"},
            {"stage": 6, "title": "Spatial District Product", "description": "Phase 9 area-weighted aggregation"},
            {"stage": 7, "title": "Explainability", "description": "Feature attribution and expert gating"},
            {"stage": 8, "title": "Scientific Verification", "description": "Neutral benchmark comparison"},
        ],
        "benchmark_summary": summary_table,
        "case_studies": cases,
        "featured_case": first_case.to_dict() if first_case else None,
        "example_explanation": explanation.to_dict(),
        "regime_expert_matrix": expert_summary,
        "data_mode_banner": (
            "SYNTHETIC DEMONSTRATION — REAL OPERATIONAL DATA NOT AVAILABLE. "
            "REAL IMD/NCMRWF OBSERVATIONAL ARCHIVES ARE NOT CURRENTLY MOUNTED."
        ),
    }, availability="SYNTHETIC_DEMO", sample_count=200)
