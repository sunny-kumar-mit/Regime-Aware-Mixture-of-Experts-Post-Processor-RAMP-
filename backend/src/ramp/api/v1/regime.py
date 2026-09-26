"""
RAMP Weather Regime API Router
SIH26080 | /api/regime/* endpoints
MoES / NCMRWF

Provides regime intelligence endpoints:
  GET /api/regime/status       - Engine health, model version, data mode
  GET /api/regime/models       - Model registry catalogue & metadata
  GET /api/regime/current      - Current forecast regime probability vector
  GET /api/regime/grid         - Gridded 0.25° regime probability layers
  GET /api/regime/{sample_id}  - Single-sample regime prediction & attribution
  GET /api/regime/metrics      - Regime-wise metrics & confusion matrix
  GET /api/regime/calibration  - Probability calibration report
  GET /api/regime/transitions  - Sequential regime transition trajectory
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ramp.config import settings
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime
from ml.regimes.inference import RegimeInferenceService
from ml.regimes.model_registry import RegimeModelRegistry

router = APIRouter(prefix="/regime", tags=["Regime Intelligence"])

DATA_DIR = Path(getattr(settings, "RAMP_DATA_ROOT", "./data"))
MODELS_DIR = DATA_DIR / "models" / "regime"
PROCESSED_DIR = DATA_DIR / "processed" / "training" / "ramp_dataset_v0.3.0"

# Service initialization helper
_service_instance: Optional[RegimeInferenceService] = None


def get_inference_service() -> RegimeInferenceService:
    global _service_instance
    if _service_instance is None:
        reg = RegimeModelRegistry(models_dir=MODELS_DIR)
        models = reg.list_models()
        if models:
            latest = models[0]
            try:
                clf, cal, meta = reg.load_model(latest.model_id)
                _service_instance = RegimeInferenceService(
                    classifier=clf,
                    calibrator=cal,
                    model_version=latest.model_id,
                )
                return _service_instance
            except Exception:
                pass
        _service_instance = RegimeInferenceService()
    return _service_instance


# =============================================================================
# Response Schemas
# =============================================================================

class RegimeStatusResponse(BaseModel):
    status: str
    active_model: str
    data_mode: str
    real_data_available: bool
    num_regimes: int = 7
    regimes: List[str]


class RegimePredictionResponse(BaseModel):
    top_regime: str
    probabilities: Dict[str, float]
    confidence: float
    entropy: float
    normalized_entropy: float
    uncertainty_level: str
    transition_state: str = "STABLE"
    model_version: str
    feature_availability: Dict[str, bool] = Field(default_factory=dict)
    top_attribution_features: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/status", response_model=RegimeStatusResponse)
def get_regime_status():
    """Returns engine readiness, active model version, and honest real data availability."""
    reg = RegimeModelRegistry(models_dir=MODELS_DIR)
    models = reg.list_models()
    active_model = models[0].model_id if models else "RuleBased_Baseline"

    # Honest real data check
    train_file = PROCESSED_DIR / "dataset_version.json"
    data_mode = "SYNTHETIC_DEMO"
    real_avail = False
    if train_file.exists():
        with open(train_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        data_mode = meta.get("data_mode", "SYNTHETIC_DEMO")
        real_avail = (data_mode == "REAL")

    return RegimeStatusResponse(
        status="OPERATIONAL",
        active_model=active_model,
        data_mode=data_mode,
        real_data_available=real_avail,
        num_regimes=len(REGIME_ORDER),
        regimes=[r.value for r in REGIME_ORDER],
    )


@router.get("/models")
def list_regime_models():
    """Lists registered regime classification models with metadata and hyperparameters."""
    reg = RegimeModelRegistry(models_dir=MODELS_DIR)
    models = reg.list_models()
    return {
        "total": len(models),
        "models": [m.model_dump() for m in models],
    }


@router.get("/current", response_model=RegimePredictionResponse)
def get_current_regime():
    """
    Returns regime probability vector for the latest forecast cycle or representative sample.
    """
    service = get_inference_service()

    # Load representative sample from test set if available
    sample_path = PROCESSED_DIR / "test.parquet"
    if sample_path.exists():
        import pandas as pd
        df = pd.read_parquet(sample_path)
        if not df.empty:
            sample_row = df.iloc[0]
            pred = service.predict_sample(sample_row)
            return RegimePredictionResponse(**pred)

    # Default meteorological setup if dataset not yet generated
    default_sample = {
        "raw_nwp_rainfall": 18.5,
        "u850": 9.2,
        "v850": 2.4,
        "wind_speed_850": 9.5,
        "wind_direction_850": 255.0,
        "mslp": 100250.0,
        "mslp_anomaly": -220.0,
        "temperature": 299.5,
        "relative_humidity": 84.0,
        "precipitable_water": 54.0,
        "cape": 1150.0,
        "geopotential_height": 5850.0,
        "latitude": 21.0,
        "longitude": 78.5,
        "monsoon": 1,
        "winter": 0,
    }
    pred = service.predict_sample(default_sample)
    return RegimePredictionResponse(**pred)


@router.get("/grid")
def get_regime_grid():
    """
    Returns gridded regime probability layers across spatial coordinates.
    """
    service = get_inference_service()
    sample_path = PROCESSED_DIR / "test.parquet"

    if sample_path.exists():
        import pandas as pd
        df = pd.read_parquet(sample_path)
        # Limit grid to 100 points for light JSON payload
        grid_subset = df.head(100)
        return service.predict_grid(grid_subset)

    return {
        "total_points": 0,
        "top_regimes": [],
        "layers": {},
        "message": "No gridded forecast data staged.",
    }


@router.get("/metrics")
def get_regime_metrics(model_id: Optional[str] = None):
    """Returns classification accuracy, balanced accuracy, F1, and confusion matrix."""
    target_dir = (MODELS_DIR / model_id) if model_id else (MODELS_DIR / "regime_lgbm_v0.1.0")

    metrics_file = target_dir / "regime_metrics.json"
    cm_file = target_dir / "regime_confusion_matrix.json"
    dist_file = target_dir / "regime_distribution.json"

    if not metrics_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metrics not found for model in {target_dir}",
        )

    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    cm = {}
    if cm_file.exists():
        with open(cm_file, "r", encoding="utf-8") as f:
            cm = json.load(f)

    dist = {}
    if dist_file.exists():
        with open(dist_file, "r", encoding="utf-8") as f:
            dist = json.load(f)

    return {
        "model_id": target_dir.name,
        "data_mode": "SYNTHETIC_DEMO",
        "performance_notice": "SYNTHETIC DEMONSTRATION ONLY — Real training data not available.",
        "metrics": metrics,
        "confusion_matrix": cm,
        "class_distribution": dist,
    }


@router.get("/calibration")
def get_regime_calibration(model_id: Optional[str] = None):
    """Returns probability calibration diagnostics comparing uncalibrated vs calibrated."""
    target_dir = (MODELS_DIR / model_id) if model_id else (MODELS_DIR / "regime_lgbm_v0.1.0")
    cal_file = target_dir / "regime_calibration.json"

    if not cal_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calibration report not found in {target_dir}",
        )

    with open(cal_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/transitions")
def get_regime_transitions(model_id: Optional[str] = None):
    """Returns sequential regime transition trajectory and stability state."""
    target_dir = (MODELS_DIR / model_id) if model_id else (MODELS_DIR / "regime_lgbm_v0.1.0")
    trans_file = target_dir / "regime_transition_report.json"

    if not trans_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transition report not found in {target_dir}",
        )

    with open(trans_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/{sample_id}", response_model=RegimePredictionResponse)
def get_regime_by_sample_id(sample_id: str):
    """Runs regime inference on a specific sample ID from the dataset."""
    sample_path = PROCESSED_DIR / "ramp_dataset.parquet"
    if not sample_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found.",
        )

    import pandas as pd
    df = pd.read_parquet(sample_path)
    match = df[df["sample_id"] == sample_id] if "sample_id" in df.columns else pd.DataFrame()

    if match.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )

    service = get_inference_service()
    pred = service.predict_sample(match.iloc[0])
    return RegimePredictionResponse(**pred)
