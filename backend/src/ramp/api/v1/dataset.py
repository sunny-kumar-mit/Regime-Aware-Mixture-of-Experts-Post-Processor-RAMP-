"""
RAMP Dataset API Router
SIH26080 | /api/datasets/* endpoints
MoES / NCMRWF

Provides metadata inspection endpoints:
  GET /api/datasets/training          - List available training datasets
  GET /api/datasets/training/{id}     - Single dataset details
  GET /api/datasets/features          - Centralized feature registry
  GET /api/datasets/statistics        - Split-wise distribution statistics
  GET /api/datasets/splits            - Temporal split manifest
  GET /api/datasets/leakage           - Leakage audit report
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ramp.config import settings

router = APIRouter(prefix="/datasets", tags=["Dataset Layer"])

# Resolve paths
DATA_DIR = Path(getattr(settings, "RAMP_DATA_ROOT", "./data"))
TRAINING_DIR = DATA_DIR / "processed" / "training"
METADATA_DIR = DATA_DIR / "metadata" / "datasets"


# =============================================================================
# Pydantic Response Models
# =============================================================================

class DatasetSummaryResponse(BaseModel):
    dataset_id: str
    version: str
    data_mode: str
    real_data_available: bool
    created_at: str
    row_count: int
    feature_count: int
    target_count: int
    time_range: Dict[str, str] = Field(default_factory=dict)
    spatial_range: Dict[str, float] = Field(default_factory=dict)
    status: str = "AVAILABLE"


class DatasetsListResponse(BaseModel):
    total: int
    real_data_available: bool
    status_message: str
    datasets: List[DatasetSummaryResponse]


class FeatureItemResponse(BaseModel):
    name: str
    description: str
    source: str
    unit: str
    dtype: str
    required: bool
    derivation: Optional[str] = None
    leakage_risk: str
    available: bool


class FeaturesRegistryResponse(BaseModel):
    total: int
    features: List[FeatureItemResponse]


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/training", response_model=DatasetsListResponse)
def list_training_datasets():
    """Lists all generated training datasets and reports real data status."""
    datasets: List[DatasetSummaryResponse] = []
    real_available = False

    if TRAINING_DIR.exists():
        for d in sorted(TRAINING_DIR.iterdir()):
            v_file = d / "dataset_version.json"
            if v_file.exists():
                try:
                    with open(v_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    mode = meta.get("data_mode", "SYNTHETIC_DEMO")
                    if mode == "REAL":
                        real_available = True

                    datasets.append(
                        DatasetSummaryResponse(
                            dataset_id=meta.get("dataset_id", d.name),
                            version=meta.get("version", "0.0.0"),
                            data_mode=mode,
                            real_data_available=(mode == "REAL"),
                            created_at=meta.get("created_at", ""),
                            row_count=meta.get("row_count", 0),
                            feature_count=meta.get("feature_count", 0),
                            target_count=meta.get("target_count", 6),
                            time_range=meta.get("time_range", {}),
                            spatial_range=meta.get("spatial_range", {}),
                            status="AVAILABLE",
                        )
                    )
                except Exception:
                    pass

    status_msg = (
        "REAL TRAINING DATA AVAILABLE"
        if real_available
        else "NO REAL TRAINING DATA LOADED (SYNTHETIC_DEMO AVAILABLE)"
        if datasets
        else "NO TRAINING DATASETS GENERATED"
    )

    return DatasetsListResponse(
        total=len(datasets),
        real_data_available=real_available,
        status_message=status_msg,
        datasets=datasets,
    )


@router.get("/training/{dataset_id}")
def get_training_dataset(dataset_id: str):
    """Retrieves full version manifest for a specific dataset."""
    target_dir = TRAINING_DIR / dataset_id
    v_file = target_dir / "dataset_version.json"
    if not v_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in {TRAINING_DIR}",
        )
    with open(v_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/features", response_model=FeaturesRegistryResponse)
def get_features_registry():
    """Retrieves canonical feature registry with descriptions, derivations, and availability."""
    reg_file = METADATA_DIR / "feature_registry.json"
    if not reg_file.exists():
        # Fallback to importing from ml.feature_registry
        from ml.feature_registry import feature_registry
        features = [f.model_dump() for f in feature_registry.list_features()]
        return FeaturesRegistryResponse(
            total=len(features),
            features=[FeatureItemResponse(**f) for f in features],
        )

    with open(reg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = [FeatureItemResponse(**spec) for spec in data.values()]
    return FeaturesRegistryResponse(total=len(items), features=items)


@router.get("/statistics")
def get_dataset_statistics(dataset_id: Optional[str] = None):
    """Retrieves split-specific distribution statistics (TRAIN, VALIDATION, TEST)."""
    d_dir = (TRAINING_DIR / dataset_id) if dataset_id else (TRAINING_DIR / "ramp_dataset_v0.3.0")
    stats_file = d_dir / "dataset_statistics.json"
    if not stats_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statistics file not found for dataset '{d_dir.name}'.",
        )
    with open(stats_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/splits")
def get_dataset_splits(dataset_id: Optional[str] = None):
    """Retrieves temporal split manifest and purge gaps."""
    d_dir = (TRAINING_DIR / dataset_id) if dataset_id else (TRAINING_DIR / "ramp_dataset_v0.3.0")
    split_file = d_dir / "split_manifest.json"
    if not split_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split manifest not found for dataset '{d_dir.name}'.",
        )
    with open(split_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/leakage")
def get_dataset_leakage_report(dataset_id: Optional[str] = None):
    """Retrieves 10-point leakage audit report."""
    d_dir = (TRAINING_DIR / dataset_id) if dataset_id else (TRAINING_DIR / "ramp_dataset_v0.3.0")
    leak_file = d_dir / "leakage_report.json"
    if not leak_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leakage report not found for dataset '{d_dir.name}'.",
        )
    with open(leak_file, "r", encoding="utf-8") as f:
        return json.load(f)
