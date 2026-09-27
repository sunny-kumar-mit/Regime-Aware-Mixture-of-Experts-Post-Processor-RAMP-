"""
RAMP Real Operational Verification API Endpoints
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART AF & PART T & PART U Endpoints:
  GET /api/verification/real
  GET /api/verification/real/{cycle_id}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from ml.ingestion.verification import RealVerificationEngine

router = APIRouter(prefix="/verification", tags=["Operational Verification"])

_verification_engine = RealVerificationEngine()


@router.get("/real", summary="Get factual real operational forecast verification and baseline comparisons")
async def get_real_verification(
    cycle: str = Query(default="00Z", description="Synoptic cycle"),
    lead_time: int = Query(default=24, description="Forecast lead time in hours"),
    threshold_mm: float = Query(default=0.1, description="IMD rainfall threshold in mm"),
) -> Dict[str, Any]:
    """
    Returns real operational verification scores comparing Raw NWP, Simple Bias Correction,
    Global ML, and RAMP MoE. If authoritative observations are absent, returns NOT_AVAILABLE.
    """
    # Evaluate cycle with None observations (no fabricated scores permitted)
    report = _verification_engine.evaluate_cycle(
        observations=None,
        model_predictions={},
        forecast_cycle=cycle,
        lead_time_hours=lead_time,
    )

    data = report.to_dict()
    # Provide candidate baseline models for UI table rendering
    data["baseline_models"] = [
        "Raw NWP (NCUM)",
        "Simple Bias Correction (Quantile Mapping)",
        "Global ML (LightGBM Baseline)",
        "RAMP Regime-Aware MoE (Operational Candidate)",
    ]
    data["thresholds_available"] = [0.1, 64.5, 115.6, 204.5]
    data["selected_threshold_mm"] = threshold_mm
    return data


@router.get("/real/{cycle_id}", summary="Get verification report for a specific forecast cycle")
async def get_real_verification_by_cycle(
    cycle_id: str,
    threshold_mm: float = Query(default=0.1),
) -> Dict[str, Any]:
    report = _verification_engine.evaluate_cycle(
        observations=None,
        model_predictions={},
        forecast_cycle=cycle_id,
    )
    data = report.to_dict()
    data["cycle_id"] = cycle_id
    data["selected_threshold_mm"] = threshold_mm
    return data
