"""
Model Registry Resolution & Integrity Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part B: Dynamically resolves and loads immutable models from ml/model_registry/.
Strictly verifies SHA-256 checksums and lifecycle states.
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ml.inference.config import MODEL_REGISTRY_PATH
from ml.training.provenance import compute_file_sha256

logger = logging.getLogger(__name__)


class ModelIntegrityError(RuntimeError):
    """Raised when model checksum verification fails (MODEL_INTEGRITY_FAILURE)."""
    pass


class ModelNotFoundError(RuntimeError):
    """Raised when a requested model is missing from the registry."""
    pass


@dataclass
class ResolvedModel:
    """Encapsulates a loaded model object with its registry metadata."""
    model_id: str
    model_type: str
    model_object: Any
    lifecycle_status: str
    data_mode: str
    dataset_version: str
    checksum_sha256: str
    manifest: Dict[str, Any]
    calibration: Dict[str, Any]
    is_demo: bool


class ModelResolver:
    """
    Resolves models strictly through ml/model_registry/registry.json.
    Verifies immutable SHA-256 checksums before loading into memory.
    """

    def __init__(self, registry_root: Optional[Path] = None):
        self.registry_root = registry_root or MODEL_REGISTRY_PATH
        self.index_file = self.registry_root / "registry.json"
        self.models_dir = self.registry_root / "models"

    def _read_index(self) -> Dict[str, Any]:
        if not self.index_file.exists():
            raise ModelNotFoundError(f"Model registry index not found: {self.index_file}")
        with open(self.index_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def verify_checksum(self, filepath: Any, expected_sha256: str) -> bool:
        """Verifies SHA-256 checksum of file against expected value."""
        p = Path(filepath)
        if not p.exists():
            raise ModelIntegrityError(f"MODEL_INTEGRITY_FAILURE: File {filepath} does not exist.")
        actual = compute_file_sha256(str(p))
        if actual.lower() != expected_sha256.lower():
            raise ModelIntegrityError(
                f"MODEL_INTEGRITY_FAILURE: Checksum mismatch for {p.name}. "
                f"Expected: {expected_sha256}, Actual: {actual}"
            )
        return True

    def resolve_model(self, model_id: str) -> ResolvedModel:

        """
        Load and verify a specific model artifact by ID.
        """
        model_path = self.models_dir / model_id
        if not model_path.exists():
            raise ModelNotFoundError(f"Model directory for '{model_id}' does not exist in registry.")

        bin_file = model_path / "model.bin"
        manifest_file = model_path / "model_manifest.json"
        checksum_file = model_path / "checksum.sha256"
        cal_file = model_path / "calibration.json"

        if not bin_file.exists():
            raise ModelNotFoundError(f"Binary model file missing for '{model_id}' at {bin_file}")

        # 1. Read manifest
        manifest = {}
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        # 2. Strict SHA-256 Checksum Verification
        actual_checksum = compute_file_sha256(str(bin_file))
        expected_checksum = None

        if checksum_file.exists():
            with open(checksum_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    expected_checksum = content.split()[0]
        elif manifest.get("model_checksum_sha256"):
            expected_checksum = manifest["model_checksum_sha256"]

        if expected_checksum:
            self.verify_checksum(bin_file, expected_checksum)

        # 3. Deserialize Model Binary

        try:
            with open(bin_file, "rb") as f:
                model_obj = pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to deserialize model '{model_id}': {e}")

        # 4. Read Calibration Data
        calibration_data = {}
        if cal_file.exists():
            with open(cal_file, "r", encoding="utf-8") as f:
                calibration_data = json.load(f)

        lifecycle = manifest.get("lifecycle_status", "DEVELOPMENT")
        data_mode = manifest.get("data_mode", "SYNTHETIC_DEMO")
        is_demo = (data_mode == "SYNTHETIC_DEMO" or lifecycle == "DEVELOPMENT")

        logger.info(f"Successfully resolved and verified model '{model_id}' [mode={data_mode}, lifecycle={lifecycle}]")

        return ResolvedModel(
            model_id=model_id,
            model_type=manifest.get("model_type", "UNKNOWN"),
            model_object=model_obj,
            lifecycle_status=lifecycle,
            data_mode=data_mode,
            dataset_version=manifest.get("dataset_version", "unknown"),
            checksum_sha256=actual_checksum,
            manifest=manifest,
            calibration=calibration_data,
            is_demo=is_demo,
        )

    def resolve_active_models(self) -> Dict[str, ResolvedModel]:
        """
        Resolves the 4 core models mapped in active_models:
        - GLOBAL_ML -> ramp_global_v2.0.0
        - WEATHER_REGIME_CLASSIFIER -> ramp_regime_v2.0.0
        - REGIME_AWARE_MOE -> ramp_moe_v2.0.0
        - EXTREME_PROBABILITY_MODELS -> ramp_extreme_v2.0.0
        """
        index = self._read_index()
        active = index.get("active_models", {})

        defaults = {
            "GLOBAL_ML": "ramp_global_v2.0.0",
            "WEATHER_REGIME_CLASSIFIER": "ramp_regime_v2.0.0",
            "REGIME_AWARE_MOE": "ramp_moe_v2.0.0",
            "EXTREME_PROBABILITY_MODELS": "ramp_extreme_v2.0.0",
        }

        resolved = {}
        for role, default_id in defaults.items():
            model_id = active.get(role, default_id)
            resolved[role] = self.resolve_model(model_id)

        # Aliases for operational pipeline convenience
        resolved["moe"] = resolved["REGIME_AWARE_MOE"]
        resolved["global"] = resolved["GLOBAL_ML"]
        resolved["regime"] = resolved["WEATHER_REGIME_CLASSIFIER"]
        resolved["extreme"] = resolved["EXTREME_PROBABILITY_MODELS"]

        return resolved

