"""
RAMP Model Registry Engine & Promotion Gates
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part V, W, X, AG:
- Model Registry Storage under ml/model_registry/
- 12 Strict Promotion Gates
- Immutable Versioning & No-Overwrite Guard
- Comprehensive Model Card Generator
"""

from __future__ import annotations

import json
import logging
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ml.training.config import (
    FEATURE_SCHEMA_VERSION,
    PROMOTION_GATES,
    TARGET_SCHEMA_VERSION,
    ModelLifecycle,
)
from ml.training.feature_contract import APPROVED_PREDICTORS
from ml.training.provenance import compute_file_sha256, get_git_commit, get_library_versions

logger = logging.getLogger(__name__)

def _resolve_default_registry_path() -> Path:
    candidates = [
        Path("ml/model_registry"),
        Path("../ml/model_registry"),
        Path(__file__).resolve().parent.parent / "model_registry",
        Path("d:/SIH26080/ml/model_registry"),
    ]
    for c in candidates:
        if (c / "registry.json").exists():
            return c
    return Path(__file__).resolve().parent.parent / "model_registry"


DEFAULT_REGISTRY_PATH = _resolve_default_registry_path()


class ModelOverwriteError(RuntimeError):
    """Raised when an attempt is made to overwrite an existing immutable model version."""
    pass


class GateValidationError(RuntimeError):
    """Raised when one or more mandatory model promotion gates fail."""
    pass


class ModelRegistry:
    """
    Manages versioned, audited model registration with strict promotion gates.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or DEFAULT_REGISTRY_PATH
        self.models_dir = self.root_dir / "models"
        self.metrics_dir = self.root_dir / "metrics"
        self.calibration_dir = self.root_dir / "calibration"
        self.manifests_dir = self.root_dir / "manifests"
        self.checksums_dir = self.root_dir / "checksums"
        self.index_file = self.root_dir / "registry.json"

        # Ensure directory structure exists
        for d in [self.root_dir, self.models_dir, self.metrics_dir, self.calibration_dir, self.manifests_dir, self.checksums_dir]:
            d.mkdir(parents=True, exist_ok=True)

        if not self.index_file.exists():
            self._write_index({
                "registry_version": "2.0.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "registered_models": {},
                "active_models": {},
            })

    def _read_index(self) -> Dict[str, Any]:
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"registry_version": "2.0.0", "registered_models": {}, "active_models": {}}

    def _write_index(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def evaluate_gates(
        self,
        gate_statuses: Dict[str, bool],
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> Dict[str, Any]:
        """
        Evaluate the 12 model promotion gates.
        Returns detailed status for every gate and overall promotion eligibility.
        """
        results = {}
        all_passed = True

        for gate in PROMOTION_GATES:
            passed = bool(gate_statuses.get(gate, False))
            results[gate] = {
                "passed": passed,
                "status": "PASS" if passed else "FAIL",
            }
            if not passed:
                all_passed = False

        # Additional Scientific Integrity Rule:
        # Models trained on SYNTHETIC_DEMO data can NEVER be promoted to PRODUCTION_READY.
        synthetic_block = (data_mode == "SYNTHETIC_DEMO")

        return {
            "all_gates_passed": all_passed,
            "synthetic_block_applied": synthetic_block,
            "promotion_eligible": all_passed and not synthetic_block,
            "recommended_lifecycle": (
                ModelLifecycle.DEVELOPMENT.value
                if synthetic_block
                else (ModelLifecycle.PRODUCTION_READY.value if all_passed else ModelLifecycle.BLOCKED.value)
            ),
            "gate_evaluations": results,
        }

    def register_model(
        self,
        model_id: str,
        model_object: Any,
        model_type: str,
        dataset_version: str,
        data_mode: str,
        training_config: Dict[str, Any],
        metrics: Dict[str, Any],
        calibration_data: Optional[Dict[str, Any]] = None,
        provenance_data: Optional[Dict[str, Any]] = None,
        gate_statuses: Optional[Dict[str, bool]] = None,
        allow_overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Register a trained model artifact with complete audit manifest, model card, and checksums.
        Enforces immutable versioning (No-overwrite invariant).
        """
        model_path = self.models_dir / model_id
        if model_path.exists() and not allow_overwrite:
            raise ModelOverwriteError(
                f"Model '{model_id}' is already registered and immutable. "
                "Overwriting production model artifacts is strictly forbidden."
            )

        model_path.mkdir(parents=True, exist_ok=True)

        # 1. Serialize model binary
        bin_file = model_path / "model.bin"
        with open(bin_file, "wb") as f:
            pickle.dump(model_object, f)
        model_checksum = compute_file_sha256(str(bin_file))

        # Write checksum file
        with open(model_path / "checksum.sha256", "w", encoding="utf-8") as f:
            f.write(f"{model_checksum}  model.bin\n")
        with open(self.checksums_dir / f"{model_id}.sha256", "w", encoding="utf-8") as f:
            f.write(f"{model_checksum}  {model_id}/model.bin\n")

        # 2. Gate evaluation & lifecycle assignment
        gate_eval = self.evaluate_gates(gate_statuses or {}, data_mode=data_mode)
        lifecycle = gate_eval["recommended_lifecycle"]

        # 3. Schemas
        feature_schema = {
            "schema_version": FEATURE_SCHEMA_VERSION,
            "approved_predictor_count": len(APPROVED_PREDICTORS),
            "approved_predictors": APPROVED_PREDICTORS,
        }
        with open(model_path / "feature_schema.json", "w", encoding="utf-8") as f:
            json.dump(feature_schema, f, indent=2)

        target_schema = {
            "schema_version": TARGET_SCHEMA_VERSION,
            "continuous_target": "observed_rainfall_mm",
            "threshold_targets": [0.1, 64.5, 115.6, 204.5],
        }
        with open(model_path / "target_schema.json", "w", encoding="utf-8") as f:
            json.dump(target_schema, f, indent=2)

        # 4. Training config
        with open(model_path / "training_config.json", "w", encoding="utf-8") as f:
            json.dump(training_config, f, indent=2)

        # 5. Metrics
        with open(model_path / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        with open(self.metrics_dir / f"{model_id}_metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        # 6. Calibration
        cal_obj = calibration_data or {"status": "NOT_CALIBRATED"}
        with open(model_path / "calibration.json", "w", encoding="utf-8") as f:
            json.dump(cal_obj, f, indent=2)
        with open(self.calibration_dir / f"{model_id}_calibration.json", "w", encoding="utf-8") as f:
            json.dump(cal_obj, f, indent=2)

        # 7. Provenance
        prov_obj = provenance_data or {
            "git_commit": get_git_commit(),
            "libraries": get_library_versions(),
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(model_path / "provenance.json", "w", encoding="utf-8") as f:
            json.dump(prov_obj, f, indent=2)

        # 8. Model Manifest
        manifest = {
            "model_id": model_id,
            "model_type": model_type,
            "lifecycle_status": lifecycle,
            "dataset_version": dataset_version,
            "data_mode": data_mode,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "target_schema_version": TARGET_SCHEMA_VERSION,
            "model_checksum_sha256": model_checksum,
            "promotion_gates": gate_eval,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(model_path / "model_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        with open(self.manifests_dir / f"{model_id}_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 9. Model Card
        card_content = self._generate_model_card(
            model_id=model_id,
            model_type=model_type,
            lifecycle=lifecycle,
            dataset_version=dataset_version,
            data_mode=data_mode,
            metrics=metrics,
            checksum=model_checksum,
            gate_eval=gate_eval,
        )
        with open(model_path / "MODEL_CARD.md", "w", encoding="utf-8") as f:
            f.write(card_content)

        # 10. Update index
        index_data = self._read_index()
        index_data["registered_models"][model_id] = {
            "model_id": model_id,
            "model_type": model_type,
            "lifecycle_status": lifecycle,
            "dataset_version": dataset_version,
            "data_mode": data_mode,
            "registered_at": manifest["registered_at"],
            "model_checksum": model_checksum,
            "promotion_eligible": gate_eval["promotion_eligible"],
        }
        # Mark as active for its type if not blocked
        if lifecycle in (ModelLifecycle.PRODUCTION_READY.value, ModelLifecycle.DEVELOPMENT.value, ModelLifecycle.VALIDATED.value):
            index_data["active_models"][model_type] = model_id

        self._write_index(index_data)

        logger.info(f"Registered model {model_id} [lifecycle={lifecycle}, mode={data_mode}]")
        return manifest

    def _generate_model_card(
        self,
        model_id: str,
        model_type: str,
        lifecycle: str,
        dataset_version: str,
        data_mode: str,
        metrics: Dict[str, Any],
        checksum: str,
        gate_eval: Dict[str, Any],
    ) -> str:
        """Render complete, authoritative Markdown Model Card."""
        lines = [
            f"# MODEL CARD: {model_id}",
            "",
            "## 1. Model Overview",
            f"- **Model Identifier:** `{model_id}`",
            f"- **Model Type:** `{model_type}`",
            f"- **Lifecycle Status:** `{lifecycle}`",
            f"- **Data Mode:** `{data_mode}`",
            f"- **Dataset Version:** `{dataset_version}`",
            f"- **Feature Schema Version:** `{FEATURE_SCHEMA_VERSION}`",
            f"- **Target Schema Version:** `{TARGET_SCHEMA_VERSION}`",
            f"- **Model SHA-256 Checksum:** `{checksum}`",
            "",
            "## 2. Intended Meteorological Purpose",
            "Post-processing of numerical weather prediction (NWP) rainfall forecasts over India",
            "using regime-conditioned statistical machine learning. Enforces physical rainfall non-negativity",
            "and multi-threshold probability monotonicity.",
            "",
            "## 3. Training & Validation Gate Audit",
            f"- **All 12 Gates Passed:** `{gate_eval['all_gates_passed']}`",
            f"- **Synthetic Mode Guard Active:** `{gate_eval['synthetic_block_applied']}`",
            f"- **Production Promotion Eligible:** `{gate_eval['promotion_eligible']}`",
            "",
            "### Gate Status Table",
            "| Promotion Gate | Status |",
            "|---|---|",
        ]
        for gate, res in gate_eval.get("gate_evaluations", {}).items():
            lines.append(f"| `{gate}` | **{res['status']}** |")

        lines.extend([
            "",
            "## 4. Summary Verification Metrics",
            "```json",
            json.dumps(metrics.get("overall", metrics), indent=2),
            "```",
            "",
            "## 5. Known Limitations & Scientific Honesty Notice",
            f"Trained in `{data_mode}` mode. "
            + (
                "**WARNING:** Because authoritative NCMRWF/IMD training datasets are not mounted in this environment, "
                "this model artifact is strictly classified as DEVELOPMENT and must NOT be used for real operational forecasting."
                if data_mode == "SYNTHETIC_DEMO"
                else "Model validated against paired real meteorological records."
            ),
            "",
            "---",
            "*NCMRWF / MoES Regime-Aware Mixture-of-Experts (RAMP) Project*",
        ])
        return "\n".join(lines)

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models."""
        index = self._read_index()
        return list(index.get("registered_models", {}).values())

    def get_model_manifest(self, model_id: str) -> Optional[Dict[str, Any]]:
        m_file = self.models_dir / model_id / "model_manifest.json"
        if m_file.exists():
            with open(m_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_model_metrics(self, model_id: str) -> Optional[Dict[str, Any]]:
        m_file = self.models_dir / model_id / "metrics.json"
        if m_file.exists():
            with open(m_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_model_calibration(self, model_id: str) -> Optional[Dict[str, Any]]:
        c_file = self.models_dir / model_id / "calibration.json"
        if c_file.exists():
            with open(c_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_model_provenance(self, model_id: str) -> Optional[Dict[str, Any]]:
        p_file = self.models_dir / model_id / "provenance.json"
        if p_file.exists():
            with open(p_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_active_models(self) -> Dict[str, str]:
        index = self._read_index()
        return index.get("active_models", {})
