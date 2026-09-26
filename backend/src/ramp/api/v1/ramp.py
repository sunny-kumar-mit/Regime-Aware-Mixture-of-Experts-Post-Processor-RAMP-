"""
RAMP Mixture-of-Experts Post-Processor API Router
SIH26080 | /api/ramp/* endpoints
MoES / NCMRWF

Endpoints:
  GET /api/ramp/status                  - RAMP engine status, data mode, active models
  GET /api/ramp/models                  - Catalog of registered RAMP models
  GET /api/ramp/current                 - Current active RAMP model details & model card
  GET /api/ramp/prediction/{sample_id}  - End-to-end RAMP prediction with MoE decomposition
  GET /api/ramp/experts                 - 7 specialized regime experts metadata & status
  GET /api/ramp/gating                  - Calibrated regime soft gating diagnostics
  GET /api/ramp/metrics                 - Overall continuous verification metrics
  GET /api/ramp/metrics/lead-time       - Day 1..5 lead-time stratified metrics
  GET /api/ramp/metrics/threshold       - Categorical extreme rainfall contingency metrics
  GET /api/ramp/metrics/regime          - Regime-stratified comparison (RAW vs ML vs RAMP)
  GET /api/ramp/metrics/spatial         - Gridded spatial error distributions
  GET /api/ramp/benchmark               - 5-system master benchmark ladder with bootstrap CI
  GET /api/ramp/diagnostics             - Expert diversity correlation & ablation results
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ramp.config import settings
from ml.ramp.gating import GateWeights, RegimeGatingEngine
from ml.ramp.inference import RAMPInferenceService, RAMPPredictionRecord
from ml.ramp.model import RAMPModel
from ml.ramp.model_registry import RAMPModelMetadata, RAMPModelRegistry
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime
from ml.regimes.inference import RegimeInferenceService
from ml.regimes.model_registry import RegimeModelRegistry

router = APIRouter(prefix="/ramp", tags=["RAMP Mixture-of-Experts"])

DATA_DIR = Path(getattr(settings, "RAMP_DATA_ROOT", "./data"))
MODELS_DIR = DATA_DIR / "models" / "ramp"
REGIMES_DIR = DATA_DIR / "models" / "regime"
BASELINES_DIR = DATA_DIR / "models" / "baselines"
PROCESSED_DIR = DATA_DIR / "processed" / "training" / "ramp_dataset_v0.3.0"

_ramp_inference_service: Optional[RAMPInferenceService] = None


def get_ramp_service() -> RAMPInferenceService:
    global _ramp_inference_service
    if _ramp_inference_service is None:
        ramp_reg = RAMPModelRegistry(models_dir=MODELS_DIR)
        ramp_model, _ = ramp_reg.load_model("ramp_v1.0.0", baselines_dir=BASELINES_DIR)

        reg_reg = RegimeModelRegistry(models_dir=REGIMES_DIR)
        reg_models = reg_reg.list_models()
        if reg_models:
            clf, cal, _ = reg_reg.load_model(reg_models[0].model_id)
            reg_service = RegimeInferenceService(classifier=clf, calibrator=cal)
        else:
            reg_service = RegimeInferenceService()

        _ramp_inference_service = RAMPInferenceService(
            ramp_model=ramp_model,
            regime_service=reg_service,
            data_mode="SYNTHETIC_DEMO",
        )
    return _ramp_inference_service


# Schemas
class RAMPStatusResponse(BaseModel):
    status: str
    data_mode: str
    real_data_available: bool
    performance_notice: str
    active_model_id: str
    phase4_regime_model: str
    phase5_baseline_model: str
    expert_count: int
    fallback_count: int
    dataset_version: str


class RAMPBenchmarkRow(BaseModel):
    model: str
    rmse: float
    mae: float
    mean_bias: float
    pearson_r: float
    rain_occurrence_csi: Optional[float] = None
    heavy_rain_csi_64_5: Optional[float] = None
    heavy_rain_pod_64_5: Optional[float] = None
    heavy_rain_far_64_5: Optional[float] = None
    heavy_rain_ets_64_5: Optional[float] = None
    very_heavy_csi_115_6: Optional[float] = None
    extremely_heavy_csi_204_5: Optional[float] = None


class RAMPBenchmarkResponse(BaseModel):
    data_mode: str
    performance_notice: str
    test_sample_count: int
    benchmark_matrix: List[RAMPBenchmarkRow]
    bootstrap_significance: Dict[str, Any]
    systems_evaluated: List[str]


@router.get("/status", response_model=RAMPStatusResponse)
def get_ramp_status():
    """Returns RAMP engine readiness, active model versions, and real data mode."""
    reg = RAMPModelRegistry(models_dir=MODELS_DIR)
    models = reg.list_models()
    active_id = models[0].ramp_model_id if models else "ramp_v1.0.0"

    version_file = PROCESSED_DIR / "dataset_version.json"
    data_mode = "SYNTHETIC_DEMO"
    real_avail = False
    if version_file.exists():
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                vmeta = json.load(f)
            data_mode = vmeta.get("data_mode", "SYNTHETIC_DEMO")
            real_avail = (data_mode == "REAL")
        except Exception:
            pass

    # Read expert statuses
    exp_file = MODELS_DIR / active_id / "expert_metrics.json"
    fallbacks = 0
    expert_cnt = 7
    if exp_file.exists():
        try:
            with open(exp_file, "r", encoding="utf-8") as f:
                em = json.load(f)
            fallbacks = sum(1 for m in em.values() if m.get("status") == "INSUFFICIENT_DATA")
        except Exception:
            pass

    return RAMPStatusResponse(
        status="OPERATIONAL",
        data_mode=data_mode,
        real_data_available=real_avail,
        performance_notice="SYNTHETIC DEMONSTRATION ONLY — Real training data is not available.",
        active_model_id=active_id,
        phase4_regime_model="regime_lgbm_v0.1.0",
        phase5_baseline_model="global_lgbm_v1",
        expert_count=expert_cnt,
        fallback_count=fallbacks,
        dataset_version="v0.3.0",
    )


@router.get("/models")
def list_ramp_models():
    """Lists registered RAMP models with metadata and expert versions."""
    reg = RAMPModelRegistry(models_dir=MODELS_DIR)
    models = reg.list_models()
    return {
        "total": len(models),
        "models": [m.model_dump() for m in models],
    }


@router.get("/current")
def get_current_model():
    """Returns metadata and model card of active RAMP model."""
    meta_path = MODELS_DIR / "ramp_v1.0.0" / "ramp_model_metadata.json"
    card_path = MODELS_DIR / "ramp_v1.0.0" / "RAMP_MODEL_CARD.md"

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="RAMP model metadata not found.")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    card_text = ""
    if card_path.exists():
        with open(card_path, "r", encoding="utf-8") as f:
            card_text = f.read()

    return {
        "metadata": meta,
        "model_card": card_text,
    }


@router.get("/prediction/{sample_id}", response_model=RAMPPredictionRecord)
def get_ramp_prediction(sample_id: str):
    """Computes end-to-end RAMP prediction with full MoE decomposition for a given sample."""
    test_path = PROCESSED_DIR / "test.parquet"
    if not test_path.exists():
        raise HTTPException(status_code=404, detail="Test dataset not found.")

    df = pd.read_parquet(test_path)
    matching = df[df["sample_id"] == sample_id]
    if matching.empty:
        # Check train or val
        for split in ["val.parquet", "train.parquet"]:
            sp_path = PROCESSED_DIR / split
            if sp_path.exists():
                sp_df = pd.read_parquet(sp_path)
                m = sp_df[sp_df["sample_id"] == sample_id]
                if not m.empty:
                    matching = m
                    break

    if matching.empty:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found in dataset partitions.")

    service = get_ramp_service()
    return service.predict_sample(matching.iloc[0])


@router.get("/experts")
def get_expert_details():
    """Returns metadata, sample distribution, and feature importances for all 7 experts."""
    exp_file = MODELS_DIR / "ramp_v1.0.0" / "expert_metrics.json"
    if not exp_file.exists():
        raise HTTPException(status_code=404, detail="Expert metrics not found.")

    with open(exp_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "experts": data,
    }


@router.get("/gating")
def get_gating_diagnostics():
    """Returns soft gating diagnostics, entropy distributions, and sample routing records."""
    gating_file = MODELS_DIR / "ramp_v1.0.0" / "gating_diagnostics.json"
    if not gating_file.exists():
        raise HTTPException(status_code=404, detail="Gating diagnostics not found.")

    with open(gating_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "performance_notice": "SYNTHETIC DEMONSTRATION ONLY — Real training data is not available.",
        "diagnostics": data,
    }


@router.get("/metrics")
def get_ramp_metrics():
    """Returns overall continuous metrics comparing RAMP and all baselines."""
    metrics_file = MODELS_DIR / "ramp_v1.0.0" / "ramp_metrics.json"
    if not metrics_file.exists():
        raise HTTPException(status_code=404, detail="RAMP metrics not found.")

    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "performance_notice": "SYNTHETIC DEMONSTRATION ONLY — Real training data is not available.",
        "metrics": metrics,
    }


@router.get("/metrics/lead-time")
def get_ramp_lead_time_metrics():
    """Returns lead-time stratified metrics (Day 1..5)."""
    lead_file = MODELS_DIR / "ramp_v1.0.0" / "ramp_lead_time_metrics.json"
    if not lead_file.exists():
        raise HTTPException(status_code=404, detail="Lead-time metrics not found.")

    with open(lead_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_metrics": data,
    }


@router.get("/metrics/threshold")
def get_ramp_threshold_metrics():
    """Returns extreme rainfall categorical contingency metrics (0.1, 64.5, 115.6, 204.5 mm)."""
    thresh_file = MODELS_DIR / "ramp_v1.0.0" / "ramp_threshold_metrics.json"
    if not thresh_file.exists():
        raise HTTPException(status_code=404, detail="Threshold metrics not found.")

    with open(thresh_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "threshold_metrics": data,
    }


@router.get("/metrics/regime")
def get_ramp_regime_metrics():
    """Returns regime-stratified metrics comparing RAW NWP vs GLOBAL ML vs RAMP."""
    reg_file = MODELS_DIR / "ramp_v1.0.0" / "ramp_regime_metrics.json"
    if not reg_file.exists():
        raise HTTPException(status_code=404, detail="Regime-stratified metrics not found.")

    with open(reg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "regime_metrics": data,
    }


@router.get("/metrics/spatial")
def get_ramp_spatial_metrics():
    """Returns spatial grid point evaluation metrics."""
    sp_file = MODELS_DIR / "ramp_v1.0.0" / "ramp_spatial_metrics.json"
    if not sp_file.exists():
        raise HTTPException(status_code=404, detail="Spatial metrics not found.")

    with open(sp_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "spatial_metrics": data,
    }


@router.get("/benchmark", response_model=RAMPBenchmarkResponse)
def get_ramp_benchmark():
    """Returns complete 5-system benchmark ladder (RAW, MEAN BIAS, QM, GLOBAL ML, RAMP) and bootstrap CI."""
    bench_file = MODELS_DIR / "ramp_v1.0.0" / "ramp_benchmark.json"
    if not bench_file.exists():
        raise HTTPException(status_code=404, detail="Benchmark artifacts not found.")

    with open(bench_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    matrix = [RAMPBenchmarkRow(**row) for row in data.get("benchmark_matrix", [])]

    return RAMPBenchmarkResponse(
        data_mode=data.get("data_mode", "SYNTHETIC_DEMO"),
        performance_notice=data.get("performance_notice", ""),
        test_sample_count=data.get("test_sample_count", 63),
        benchmark_matrix=matrix,
        bootstrap_significance=data.get("bootstrap_significance", {}),
        systems_evaluated=["raw_nwp", "mean_bias", "quantile_mapping", "global_ml", "ramp"],
    )


@router.get("/diagnostics")
def get_ramp_diagnostics():
    """Returns expert diversity correlation matrix, overfitting report, and ablation study."""
    div_file = MODELS_DIR / "ramp_v1.0.0" / "expert_diversity.json"
    ab_file = MODELS_DIR / "ramp_v1.0.0" / "ramp_ablation.json"

    div_data = {}
    if div_file.exists():
        with open(div_file, "r", encoding="utf-8") as f:
            div_data = json.load(f)

    ab_data = []
    if ab_file.exists():
        with open(ab_file, "r", encoding="utf-8") as f:
            ab_data = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "expert_diversity": div_data,
        "ablation_comparison": ab_data,
    }
