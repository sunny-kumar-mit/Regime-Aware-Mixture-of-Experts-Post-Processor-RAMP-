"""
RAMP Model Registry & Training API Router
SIH26080 | /api/models/* endpoints
MoES / NCMRWF

Section Part Y Endpoints:
  GET  /api/models
  GET  /api/models/status
  GET  /api/models/active
  GET  /api/models/{model_id}
  GET  /api/models/{model_id}/metrics
  GET  /api/models/{model_id}/manifest
  GET  /api/models/{model_id}/provenance
  GET  /api/models/{model_id}/calibration
  POST /api/models/pipeline
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ml.training.dataset_gate import DatasetGate, RealTrainingEligibilityGate
from ml.training.pipeline import TrainingPipeline
from ml.training.registry import ModelRegistry

router = APIRouter(prefix="/models", tags=["Model Registry & Training"])

REGISTRY_ROOT = Path("ml/model_registry")


def get_registry() -> ModelRegistry:
    return ModelRegistry(REGISTRY_ROOT)


# ---------------------------------------------------------------------------
# Pydantic Schemas for Documentation
# ---------------------------------------------------------------------------

class PipelineRunRequest(BaseModel):
    dataset_version: Optional[str] = "ramp_dataset_real_v1.0.0"
    calibration_method: Optional[str] = "isotonic"
    seed: Optional[int] = 42
    allow_synthetic_fixture: Optional[bool] = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", summary="List all registered models")
def list_models() -> Dict[str, Any]:
    """Retrieve all models currently registered in the RAMP model registry."""
    reg = get_registry()
    models = reg.list_models()
    return {
        "status": "SUCCESS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_models": len(models),
        "models": models,
    }


@router.get("/status", summary="Registry and Training Environment Status")
def registry_status() -> Dict[str, Any]:
    """Exposes registry summary, active models, real data eligibility, and gate posture."""
    reg = get_registry()
    models = reg.list_models()
    active = reg.get_active_models()

    ds_path = "ml/datasets/real/ramp_dataset_real_v1.0.0"
    ds_gate = DatasetGate.validate(ds_path)
    eligibility = RealTrainingEligibilityGate.evaluate(ds_path)

    # Read latest training run if available
    latest_run = {}
    latest_run_file = REGISTRY_ROOT / "manifests" / "latest_training_run.json"
    if latest_run_file.exists():
        try:
            with open(latest_run_file, "r", encoding="utf-8") as f:
                latest_run = json.load(f)
        except Exception:
            pass

    return {
        "status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "registry_version": "2.0.0",
        "total_models": len(models),
        "active_models": active,
        "dataset_gate": ds_gate,
        "eligibility_gate": eligibility,
        "real_training_status": {
            "real_data_available": eligibility["real_data_available"],
            "real_production_training": "DEFERRED" if eligibility["real_training_deferred"] else "AVAILABLE",
            "active_mode": eligibility["effective_mode"],
            "honesty_notice": eligibility["message"],
        },
        "latest_training_run": latest_run,
    }


@router.get("/active", summary="Get currently active production/development models")
def get_active_models() -> Dict[str, Any]:
    """Returns mapping of active model identifiers by architectural role."""
    reg = get_registry()
    active = reg.get_active_models()
    models_detail = {}
    for role, mid in active.items():
        manifest = reg.get_model_manifest(mid)
        if manifest:
            models_detail[role] = {
                "model_id": mid,
                "model_type": manifest.get("model_type"),
                "lifecycle_status": manifest.get("lifecycle_status"),
                "data_mode": manifest.get("data_mode"),
                "checksum": manifest.get("model_checksum_sha256"),
                "registered_at": manifest.get("registered_at"),
            }
        else:
            models_detail[role] = {"model_id": mid}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_models": active,
        "details": models_detail,
    }


@router.get("/{model_id}", summary="Get model summary and card")
def get_model(model_id: str) -> Dict[str, Any]:
    """Retrieve complete metadata, promotion gates, and model card for a model."""
    reg = get_registry()
    manifest = reg.get_model_manifest(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry.")

    # Read MODEL_CARD.md if present
    card_text = ""
    card_path = REGISTRY_ROOT / "models" / model_id / "MODEL_CARD.md"
    if card_path.exists():
        try:
            with open(card_path, "r", encoding="utf-8") as f:
                card_text = f.read()
        except Exception:
            pass

    return {
        "model_id": model_id,
        "manifest": manifest,
        "model_card_markdown": card_text,
    }


@router.get("/{model_id}/metrics", summary="Get model verification metrics")
def get_model_metrics(model_id: str) -> Dict[str, Any]:
    """Retrieve detailed verification metrics, stratified scores, and confusion matrix."""
    reg = get_registry()
    metrics = reg.get_model_metrics(model_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Metrics for model '{model_id}' not found.")
    return {
        "model_id": model_id,
        "metrics": metrics,
    }


@router.get("/{model_id}/manifest", summary="Get raw model manifest")
def get_model_manifest(model_id: str) -> Dict[str, Any]:
    """Retrieve raw immutable model manifest."""
    reg = get_registry()
    manifest = reg.get_model_manifest(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Manifest for model '{model_id}' not found.")
    return manifest


@router.get("/{model_id}/provenance", summary="Get model provenance and environment telemetry")
def get_model_provenance(model_id: str) -> Dict[str, Any]:
    """Retrieve Git commit, Python environment, and library versions used for training."""
    reg = get_registry()
    prov = reg.get_model_provenance(model_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Provenance for model '{model_id}' not found.")
    return {
        "model_id": model_id,
        "provenance": prov,
    }


@router.get("/{model_id}/calibration", summary="Get model calibration artifacts")
def get_model_calibration(model_id: str) -> Dict[str, Any]:
    """Retrieve calibration method, parameters, and reliability curve bin data."""
    reg = get_registry()
    cal = reg.get_model_calibration(model_id)
    if not cal:
        raise HTTPException(status_code=404, detail=f"Calibration data for model '{model_id}' not found.")
    return {
        "model_id": model_id,
        "calibration": cal,
    }


@router.post("/pipeline", summary="Execute training pipeline run")
def trigger_training_pipeline(req: PipelineRunRequest) -> Dict[str, Any]:
    """
    Trigger reproducible model training and evaluation pipeline.
    Respects scientific honesty: tags synthetic-mode runs as DEVELOPMENT.
    """
    ds_dir = req.dataset_version or "ramp_dataset_real_v1.0.0"
    if not ds_dir.startswith("ml/datasets"):
        ds_dir = f"ml/datasets/real/{ds_dir}"

    pipeline = TrainingPipeline(dataset_dir=ds_dir, random_seed=req.seed or 42)
    result = pipeline.run_pipeline(
        allow_synthetic_fixture=bool(req.allow_synthetic_fixture),
        calibration_method=req.calibration_method or "isotonic",
        allow_overwrite=True,
    )
    return result
