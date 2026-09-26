"""
RAMP Baseline Rainfall Post-Processing API Router
SIH26080 | /api/baselines/* endpoints
MoES / NCMRWF

Endpoints:
  GET /api/baselines/status              - Baseline engine health and active models
  GET /api/baselines/models              - Catalog of registered baseline models
  GET /api/baselines/metrics             - Overall continuous and threshold metrics
  GET /api/baselines/metrics/lead-time   - Cross-lead-time metrics (Day 1..5)
  GET /api/baselines/metrics/threshold   - Threshold contingency metrics (0.1, 64.5, 115.6, 204.5 mm)
  GET /api/baselines/metrics/regime      - Post-hoc regime-stratified error diagnostics
  GET /api/baselines/benchmark           - Full benchmark comparison matrix & paired significance
  GET /api/baselines/prediction/{sample_id} - Predict all 4 baselines on a specific sample
  GET /api/baselines/spatial             - Gridded spatial error distributions
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ramp.config import settings
from ml.baselines.inference import BaselineInferenceService, PredictionRecord
from ml.baselines.model_registry import BaselineModelRegistry

router = APIRouter(prefix="/baselines", tags=["Baseline Post-Processing"])

DATA_DIR = Path(getattr(settings, "RAMP_DATA_ROOT", "./data"))
MODELS_DIR = DATA_DIR / "models" / "baselines"
PROCESSED_DIR = DATA_DIR / "processed" / "training" / "ramp_dataset_v0.3.0"

_inference_service: Optional[BaselineInferenceService] = None


def get_inference_service() -> BaselineInferenceService:
    global _inference_service
    if _inference_service is None:
        reg = BaselineModelRegistry(models_dir=MODELS_DIR)
        models_dict = {}
        for m_key, m_id in [
            ("raw_nwp", "raw_nwp_v1"),
            ("mean_bias", "mean_bias_v1"),
            ("quantile_mapping", "quantile_mapping_v1"),
            ("global_ml", "global_lgbm_v1"),
        ]:
            try:
                mod, _ = reg.load_model(m_id)
                models_dict[m_key] = mod
            except Exception:
                pass

        _inference_service = BaselineInferenceService(
            raw_nwp=models_dict.get("raw_nwp"),
            mean_bias=models_dict.get("mean_bias"),
            quantile_mapping=models_dict.get("quantile_mapping"),
            global_ml=models_dict.get("global_ml"),
            dataset_version="v0.3.0",
            data_mode="SYNTHETIC_DEMO",
        )
    return _inference_service


class BaselineStatusResponse(BaseModel):
    status: str
    data_mode: str
    real_data_available: bool
    models_available: List[str]
    dataset_version: str


@router.get("/status", response_model=BaselineStatusResponse)
def get_baseline_status():
    """Returns baseline post-processing readiness and honest real data mode."""
    reg = BaselineModelRegistry(models_dir=MODELS_DIR)
    models = reg.list_models()
    model_ids = [m.model_id for m in models] if models else ["raw_nwp_v1", "mean_bias_v1", "quantile_mapping_v1", "global_lgbm_v1"]

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

    return BaselineStatusResponse(
        status="OPERATIONAL",
        data_mode=data_mode,
        real_data_available=real_avail,
        models_available=model_ids,
        dataset_version="v0.3.0",
    )


@router.get("/models")
def list_baseline_models():
    """Lists registered baseline models with metadata and training parameters."""
    reg = BaselineModelRegistry(models_dir=MODELS_DIR)
    models = reg.list_models()
    return {
        "total": len(models),
        "models": [m.model_dump() for m in models],
    }


@router.get("/metrics")
def get_baseline_metrics():
    """Returns overall continuous verification metrics (RMSE, MAE, Mean Bias) across all 4 baselines."""
    metrics_file = MODELS_DIR / "baseline_metrics.json"
    if not metrics_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline metrics not found. Run baseline training pipeline first.",
        )

    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "performance_notice": "SYNTHETIC DEMONSTRATION ONLY — Real training data is not available.",
        "metrics": metrics,
    }


@router.get("/metrics/lead-time")
def get_lead_time_metrics():
    """Returns verification metrics stratified across lead times (Day 1..5)."""
    lead_file = MODELS_DIR / "baseline_lead_time_metrics.json"
    if not lead_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead-time metrics artifact not found.",
        )

    with open(lead_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/metrics/threshold")
def get_threshold_metrics():
    """Returns contingency metrics across thresholds (0.1, 64.5, 115.6, 204.5 mm)."""
    thresh_file = MODELS_DIR / "baseline_threshold_metrics.json"
    if not thresh_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Threshold metrics artifact not found.",
        )

    with open(thresh_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/metrics/regime")
def get_regime_metrics():
    """Returns post-hoc regime-stratified error diagnostics exposing conditional failure modes."""
    regime_file = MODELS_DIR / "baseline_regime_metrics.json"
    if not regime_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regime error diagnostics artifact not found.",
        )

    with open(regime_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/benchmark")
def get_master_benchmark():
    """Returns complete benchmark matrix and paired bootstrap comparison against RAW NWP."""
    bm_file = MODELS_DIR / "baseline_benchmark.json"
    if not bm_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark artifact not found. Execute training pipeline.",
        )

    with open(bm_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/spatial")
def get_spatial_metrics():
    """Returns gridded spatial error fields across coordinate points."""
    spatial_file = MODELS_DIR / "baseline_spatial_metrics.json"
    if not spatial_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spatial metrics artifact not found.",
        )

    with open(spatial_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/prediction/{sample_id}", response_model=PredictionRecord)
def get_prediction_for_sample(sample_id: str):
    """Executes all 4 baseline predictions for a specific sample ID."""
    test_file = PROCESSED_DIR / "test.parquet"
    train_file = PROCESSED_DIR / "train.parquet"

    target_row = None
    for fpath in [test_file, train_file]:
        if fpath.exists():
            import pandas as pd
            df = pd.read_parquet(fpath)
            if "sample_id" in df.columns:
                match = df[df["sample_id"] == sample_id]
                if not match.empty:
                    target_row = match.iloc[0]
                    break

    if target_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found in staged datasets.",
        )

    service = get_inference_service()
    return service.predict_sample(target_row)
