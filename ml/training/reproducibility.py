"""
RAMP Training Reproducibility & Run Manifest Generator
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part U: Generates comprehensive training_manifest.json and provenance.json artifacts.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ml.training.config import (
    FEATURE_SCHEMA_VERSION,
    TARGET_SCHEMA_VERSION,
)
from ml.training.provenance import (
    get_git_commit,
    get_library_versions,
    get_system_hardware,
)


def create_training_run_manifest(
    run_id: Optional[str] = None,
    dataset_version: str = "ramp_dataset_real_v1.0.0",
    dataset_checksum: str = "UNKNOWN",
    data_mode: str = "SYNTHETIC_DEMO",
    models_trained: Optional[list] = None,
    hyperparameters: Optional[Dict[str, Any]] = None,
    random_seed: int = 42,
    training_duration_seconds: float = 0.0,
    status: str = "COMPLETED",
) -> Dict[str, Any]:
    """Assemble authoritative training_manifest.json."""
    actual_run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    manifest = {
        "run_id": actual_run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "dataset": {
            "version": dataset_version,
            "checksum": dataset_checksum,
            "data_mode": data_mode,
        },
        "schemas": {
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "target_schema_version": TARGET_SCHEMA_VERSION,
        },
        "models_trained": models_trained or [],
        "hyperparameters": hyperparameters or {},
        "random_seed": random_seed,
        "duration_seconds": round(training_duration_seconds, 3),
        "environment": {
            "git_commit": get_git_commit(),
            "libraries": get_library_versions(),
            "hardware": get_system_hardware(),
        },
    }
    return manifest
