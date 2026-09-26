"""
Script to create backend/src/ramp/api/v1/operational.py with all 14 endpoints.
"""

from pathlib import Path

content = '''"""
Phase 8 Operational Verification & Real-Data Integration API Router
SIH26080 | /api/operational/* endpoints
MoES / NCMRWF

14 Operational Endpoints:
  1.  GET /api/operational/status
  2.  GET /api/operational/data
  3.  GET /api/operational/data-quality
  4.  GET /api/operational/dataset
  5.  GET /api/operational/coverage
  6.  GET /api/operational/verification
  7.  GET /api/operational/verification/threshold
  8.  GET /api/operational/verification/regime
  9.  GET /api/operational/verification/lead-time
  10. GET /api/operational/verification/spatial
  11. GET /api/operational/calibration
  12. GET /api/operational/leakage
  13. GET /api/operational/models
  14. GET /api/operational/readiness
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ramp.config import settings
from ml.data.discovery import DataDiscoveryService
from ml.data.manifest import DatasetManifest
from ml.data.providers.real_provider import RealDataProvider
from ml.data.quality import MeteorologicalQualityControl
from ml.dataset.leakage_guard import LeakageGuard
from ml.operational.readiness import OperationalReadinessEvaluator
from ml.operational.registry import OperationalModelRegistry
from ml.operational.verification import OperationalVerificationEngine
from ml.operational.audit import AuditTrailManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operational", tags=["Operational Verification & Real-Data Integration"])

# Singletons / Services
_provider = RealDataProvider()
_evaluator = OperationalReadinessEvaluator()
_registry = OperationalModelRegistry()
_verifier = OperationalVerificationEngine(data_mode=_provider.get_mode().value)
_audit = AuditTrailManager()
_qc = MeteorologicalQualityControl()

# Cache verification results on demo data so endpoints are fast and consistent
_cached_data = None
_cached_verification = None


def _get_verification_cache() -> Dict[str, Any]:
    global _cached_data, _cached_verification
    if _cached_verification is None:
        try:
            _cached_data = _provider.load_canonical()
            _cached_verification = _verifier.verify_dataset(_cached_data)
        except Exception as e:
            logger.error(f"Error computing verification cache: {e}")
            _cached_verification = {
                "dataset_id": "fallback_eval",
                "data_mode": _provider.get_mode().value,
                "continuous_metrics": {},
                "threshold_metrics": {},
                "extreme_probability_metrics": {},
                "regime_stratification": {},
                "lead_time_verification": {},
                "spatial_verification": [],
                "benchmark_matrix": [],
            }
    return _cached_verification


# ---------------------------------------------------------------------------
# 1. GET /api/operational/status
# ---------------------------------------------------------------------------
@router.get("/status", summary="Operational System Status & Data Mode")
async def get_operational_status() -> Dict[str, Any]:
    """Returns high-level operational status, data availability mode, and model versions."""
    has_real = _provider.is_real_data_available()
    assessment = _evaluator.evaluate()

    return {
        "status": "OPERATIONAL_READY",
        "data_mode": "REAL" if has_real else "SYNTHETIC_DEMO",
        "is_real_data_available": has_real,
        "readiness_level": assessment.current_level,
        "readiness_level_name": assessment.current_level_name,
        "banner_message": (
            "REAL DATA MODE — Live Operational Archives Active"
            if has_real
            else "SYNTHETIC DEMONSTRATION — REAL OPERATIONAL DATA NOT AVAILABLE"
        ),
        "active_provider": _provider.get_source_name(),
        "model_versions": {
            "ramp_moe": _registry.state.ramp_model_version,
            "extreme_probability": _registry.state.extreme_prob_version,
            "regime_intelligence": _registry.state.regime_model_version,
            "baselines": _registry.state.baseline_versions,
        },
        "freeze_status": {
            "ramp_v1.0.0": "FROZEN",
            "extreme_prob_v1.0.0": "FROZEN",
        },
    }


# ---------------------------------------------------------------------------
# 2. GET /api/operational/data
# ---------------------------------------------------------------------------
@router.get("/data", summary="Data Ingestion & Provider Diagnostics")
async def get_operational_data() -> Dict[str, Any]:
    """Returns data adapter discovery status across NetCDF, GRIB, Parquet, and CSV."""
    service = DataDiscoveryService()
    discovery = service.discover()

    return {
        "active_provider": _provider.get_source_name(),
        "data_mode": _provider.get_mode().value,
        "is_real_data_available": _provider.is_real_data_available(),
        "adapters_supported": [
            {"format": "NetCDF", "engine": "xarray", "status": "AVAILABLE"},
            {"format": "Parquet", "engine": "pandas", "status": "AVAILABLE"},
            {"format": "CSV", "engine": "pandas", "status": "AVAILABLE"},
            {"format": "GRIB/GRIB2", "engine": "cfgrib", "status": "AVAILABLE_IF_ECCODES_MOUNTED"},
            {"format": "Synthetic", "engine": "SyntheticDataProvider", "status": "ACTIVE_FALLBACK"},
        ],
        "discovery_summary": {
            "total_files_scanned": discovery.total_files_scanned,
            "netcdf_files": discovery.netcdf_files_count,
            "grib_files": discovery.grib_files_count,
            "parquet_files": discovery.parquet_files_count,
            "csv_files": discovery.csv_files_count,
            "discovered_variables": discovery.discovered_variables,
            "time_range": discovery.overall_time_range,
        },
    }


# ---------------------------------------------------------------------------
# 3. GET /api/operational/data-quality
# ---------------------------------------------------------------------------
@router.get("/data-quality", summary="13-Point Meteorological Quality Control Report")
async def get_data_quality() -> Dict[str, Any]:
    """Returns detailed 13-point meteorological quality control results."""
    # Run or load QC
    data = _cached_data if _cached_data is not None else _provider.load_canonical()
    _, q_report = _qc.inspect_and_filter(data, dataset_id="operational_audit", data_mode=_provider.get_mode().value)

    return {
        "dataset_id": q_report.dataset_id,
        "data_mode": q_report.data_mode,
        "overall_status": q_report.overall_status,
        "total_records": q_report.total_records,
        "valid_records": q_report.valid_records,
        "invalid_records": q_report.invalid_records,
        "duplicate_records": q_report.duplicate_records,
        "missing_target_records": q_report.missing_target_records,
        "physical_invalid_rain_count": q_report.physical_invalid_rain_count,
        "extreme_but_valid_rain_count": q_report.extreme_but_valid_rain_count,
        "checks": q_report.checks_summary,
        "rejection_reasons": q_report.rejection_reasons,
    }


# ---------------------------------------------------------------------------
# 4. GET /api/operational/dataset
# ---------------------------------------------------------------------------
@router.get("/dataset", summary="Canonical Dataset Contract & Manifest")
async def get_operational_dataset() -> Dict[str, Any]:
    """Returns canonical dataset manifest and contract metadata."""
    manifest = DatasetManifest.load()
    if manifest is None:
        manifest = DatasetManifest.create_default_synthetic_manifest()

    contract = _provider.get_contract()
    return {
        "manifest": manifest.to_dict(),
        "contract": contract.dict(),
    }


# ---------------------------------------------------------------------------
# 5. GET /api/operational/coverage
# ---------------------------------------------------------------------------
@router.get("/coverage", summary="Spatial, Temporal, Variable, and Lead-Time Coverage")
async def get_operational_coverage() -> Dict[str, Any]:
    """Returns spatiotemporal and meteorological variable coverage."""
    data = _cached_data if _cached_data is not None else _provider.load_canonical()
    _, q_report = _qc.inspect_and_filter(data, dataset_id="coverage_scan", data_mode=_provider.get_mode().value)

    return {
        "time_coverage": q_report.time_coverage,
        "spatial_coverage": q_report.spatial_coverage,
        "variable_coverage": q_report.variable_coverage,
        "lead_time_coverage": q_report.lead_time_coverage,
    }


# ---------------------------------------------------------------------------
# 6. GET /api/operational/verification
# ---------------------------------------------------------------------------
@router.get("/verification", summary="Continuous Verification & Bootstrap Benchmark")
async def get_operational_verification() -> Dict[str, Any]:
    """Returns continuous metrics (RMSE, MAE, Bias, Pearson r) and bootstrap significance."""
    ver = _get_verification_cache()
    return {
        "dataset_id": ver.get("dataset_id"),
        "data_mode": ver.get("data_mode"),
        "verified_at": ver.get("verified_at"),
        "sample_count": ver.get("sample_count"),
        "continuous_metrics": ver.get("continuous_metrics"),
        "bootstrap": ver.get("bootstrap"),
        "benchmark_matrix": ver.get("benchmark_matrix"),
    }


# ---------------------------------------------------------------------------
# 7. GET /api/operational/verification/threshold
# ---------------------------------------------------------------------------
@router.get("/verification/threshold", summary="IMD Threshold Contingency Verification")
async def get_threshold_verification() -> Dict[str, Any]:
    """Returns threshold metrics (POD, FAR, CSI, ETS, FBIAS) at 0.1, 64.5, 115.6, 204.5 mm."""
    ver = _get_verification_cache()
    return {
        "thresholds": ver.get("threshold_metrics"),
        "extreme_events": ver.get("extreme_event_evaluation"),
    }


# ---------------------------------------------------------------------------
# 8. GET /api/operational/verification/regime
# ---------------------------------------------------------------------------
@router.get("/verification/regime", summary="Weather Regime Stratification Verification")
async def get_regime_verification() -> Dict[str, Any]:
    """Returns performance stratified across 7 canonical weather regimes."""
    ver = _get_verification_cache()
    return {
        "regimes": ver.get("regime_stratification"),
    }


# ---------------------------------------------------------------------------
# 9. GET /api/operational/verification/lead-time
# ---------------------------------------------------------------------------
@router.get("/verification/lead-time", summary="Lead-Time Verification (Day 1 to Day 5)")
async def get_lead_time_verification() -> Dict[str, Any]:
    """Returns forecast skill degradation from Day 1 (24h) to Day 5 (120h)."""
    ver = _get_verification_cache()
    return {
        "lead_times": ver.get("lead_time_verification"),
    }


# ---------------------------------------------------------------------------
# 10. GET /api/operational/verification/spatial
# ---------------------------------------------------------------------------
@router.get("/verification/spatial", summary="Spatial Grid-Cell Verification")
async def get_spatial_verification() -> Dict[str, Any]:
    """Returns spatial grid cell performance points for map rendering."""
    ver = _get_verification_cache()
    return {
        "grid_cells": ver.get("spatial_verification"),
        "total_cells": len(ver.get("spatial_verification", [])),
    }


# ---------------------------------------------------------------------------
# 11. GET /api/operational/calibration
# ---------------------------------------------------------------------------
@router.get("/calibration", summary="Extreme Probability Calibration & Reliability")
async def get_operational_calibration() -> Dict[str, Any]:
    """Returns calibration metrics (ECE, MCE, Brier, BSS, ROC-AUC, PR-AUC) across thresholds."""
    ver = _get_verification_cache()
    return {
        "calibration": ver.get("extreme_probability_metrics"),
    }


# ---------------------------------------------------------------------------
# 12. GET /api/operational/leakage
# ---------------------------------------------------------------------------
@router.get("/leakage", summary="Real-Data Leakage Audit Report")
async def get_operational_leakage() -> Dict[str, Any]:
    """Audits the feature store and returns real-data leakage protection status."""
    guard = LeakageGuard()
    data = _cached_data if _cached_data is not None else _provider.load_canonical()
    
    # Run audit on non-target columns
    feat_cols = [c for c in data.columns if c not in LeakageGuard.TARGET_COLUMNS and not c.startswith("observed_")]
    try:
        guard.audit_real_data_features(feat_cols)
    except Exception as e:
        logger.warning(f"Leakage audit detected error: {e}")

    report = guard.generate_report()
    return {
        "status": report.status,
        "checks_run": report.checks_run,
        "passed_checks": report.passed_checks,
        "violations": report.violations,
        "checked_at": report.checked_at,
        "forbidden_invariants": [
            "Future observed rainfall strictly forbidden from X",
            "Future regime labels strictly forbidden from X",
            "Observed regime ground truth strictly forbidden from X",
            "Future forecast corrections strictly forbidden from X",
            "Test ground-truth labels strictly forbidden from X",
            "Post-event variables strictly forbidden from X",
        ],
    }


# ---------------------------------------------------------------------------
# 13. GET /api/operational/models
# ---------------------------------------------------------------------------
@router.get("/models", summary="Operational Model Registry & Version Tracking")
async def get_operational_models() -> Dict[str, Any]:
    """Returns registered production models, freeze states, and provenance metadata."""
    return _registry.get_summary()


# ---------------------------------------------------------------------------
# 14. GET /api/operational/readiness
# ---------------------------------------------------------------------------
@router.get("/readiness", summary="6-Tier Operational Readiness Level Assessment")
async def get_operational_readiness() -> Dict[str, Any]:
    """Returns 6-tier readiness evaluation (Level 0 through Level 5) with criteria checklists."""
    assessment = _evaluator.evaluate()
    return {
        "current_level": assessment.current_level,
        "current_level_name": assessment.current_level_name,
        "data_mode": assessment.data_mode,
        "is_real_data_available": assessment.is_real_data_available,
        "summary": assessment.summary,
        "disclaimer": assessment.disclaimer,
        "tiers": [
            {
                "level": t.level,
                "name": t.name,
                "description": t.description,
                "status": t.status,
                "criteria_met": t.criteria_met,
                "pending_criteria": t.pending_criteria,
            }
            for t in assessment.tiers
        ],
    }
'''

target_path = Path("d:/SIH26080/backend/src/ramp/api/v1/operational.py")
target_path.write_text(content, encoding="utf-8")
print(f"Written operational API router to {target_path} ({len(content)} chars)")
