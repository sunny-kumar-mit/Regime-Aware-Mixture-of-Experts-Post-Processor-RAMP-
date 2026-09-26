"""
Phase 8 Operational Model Registry
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Unified tracking of:
  - Phase 4 Regime Model Version
  - Phase 5 Baseline Versions
  - Phase 6 RAMP MoE Version
  - Phase 7 Extreme Rainfall Probability Engine Version
  - Dataset Version
  - Feature & Target Schema Versions
  - Calibration Version

FROZEN MODELS:
  - ramp_v1.0.0 (Phase 6)
  - extreme_prob_v1.0.0 (Phase 7)
NEVER OVERWRITTEN.
Any real-data re-training creates versioned extensions (e.g. ramp_v1.1.0_real).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REGISTRY_FILE = Path("data/models/operational_model_registry.json")


@dataclass
class ModelVersionEntry:
    phase: int
    system_name: str
    version_id: str
    status: str  # FROZEN, OPERATIONAL, RETIRED, CANDIDATE
    data_mode: str  # REAL, SYNTHETIC_DEMO
    trained_at: str
    checksum: Optional[str] = None
    artifact_path: Optional[str] = None
    metrics_summary: Dict[str, float] = field(default_factory=dict)
    notes: Optional[str] = None


@dataclass
class OperationalRegistryState:
    registry_version: str
    last_updated: str
    regime_model_version: str
    baseline_versions: Dict[str, str]
    ramp_model_version: str
    extreme_prob_version: str
    dataset_version: str
    feature_schema_version: str
    calibration_version: str
    models: List[ModelVersionEntry]


class OperationalModelRegistry:
    """
    Central registry governing all production and baseline models.
    Enforces freeze locks on historical versions and validates inter-phase compatibility.
    """

    FROZEN_VERSIONS = {
        "ramp_v1.0.0",
        "extreme_prob_v1.0.0",
        "extreme_v1.0.0",
        "regime_lgbm_v0.1.0",
        "mean_bias_v1.0.0",
        "quantile_mapping_v1.0.0",
        "global_ml_v1.0.0",
    }

    def __init__(self, registry_file: Path | str = REGISTRY_FILE) -> None:
        self.registry_file = Path(registry_file)
        self.state = self._load_or_initialize()

    def _load_or_initialize(self) -> OperationalRegistryState:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                models = [ModelVersionEntry(**m) for m in data.get("models", [])]
                return OperationalRegistryState(
                    registry_version=data.get("registry_version", "v1.0.0"),
                    last_updated=data.get("last_updated", datetime.utcnow().isoformat() + "Z"),
                    regime_model_version=data.get("regime_model_version", "regime_lgbm_v0.1.0"),
                    baseline_versions=data.get("baseline_versions", {
                        "mean_bias": "mean_bias_v1.0.0",
                        "quantile_mapping": "quantile_mapping_v1.0.0",
                        "global_ml": "global_ml_v1.0.0",
                    }),
                    ramp_model_version=data.get("ramp_model_version", "ramp_v1.0.0"),
                    extreme_prob_version=data.get("extreme_prob_version", "extreme_prob_v1.0.0"),
                    dataset_version=data.get("dataset_version", "ramp_dataset_v0.3.0"),
                    feature_schema_version=data.get("feature_schema_version", "canonical_v1.0.0"),
                    calibration_version=data.get("calibration_version", "platt_sigmoid_v1.0.0"),
                    models=models,
                )
            except Exception as e:
                logger.warning(f"Failed to read operational registry {self.registry_file}: {e}. Initializing default.")

        return self._create_default_state()

    def _create_default_state(self) -> OperationalRegistryState:
        models = [
            ModelVersionEntry(
                phase=4,
                system_name="RegimeIntelligenceEngine",
                version_id="regime_lgbm_v0.1.0",
                status="FROZEN",
                data_mode="SYNTHETIC_DEMO",
                trained_at="2026-09-25T21:33:00Z",
                artifact_path="data/models/regime/regime_lgbm_v0.1.0",
                metrics_summary={"accuracy": 0.852, "macro_f1": 0.814},
                notes="Phase 4 7-regime physics-guided classifier. Calibrated posteriors.",
            ),
            ModelVersionEntry(
                phase=5,
                system_name="MeanBiasCorrector",
                version_id="mean_bias_v1.0.0",
                status="FROZEN",
                data_mode="SYNTHETIC_DEMO",
                trained_at="2026-09-26T02:24:00Z",
                artifact_path="data/models/baselines/mean_bias",
                metrics_summary={"rmse": 16.02, "mae": 7.64},
                notes="Phase 5 additive mean bias baseline.",
            ),
            ModelVersionEntry(
                phase=5,
                system_name="QuantileMappingCorrector",
                version_id="quantile_mapping_v1.0.0",
                status="FROZEN",
                data_mode="SYNTHETIC_DEMO",
                trained_at="2026-09-26T02:24:00Z",
                artifact_path="data/models/baselines/quantile_mapping",
                metrics_summary={"rmse": 15.82, "mae": 7.55},
                notes="Phase 5 empirical CDF quantile mapping baseline.",
            ),
            ModelVersionEntry(
                phase=5,
                system_name="GlobalMLRegressor",
                version_id="global_ml_v1.0.0",
                status="FROZEN",
                data_mode="SYNTHETIC_DEMO",
                trained_at="2026-09-26T02:24:00Z",
                artifact_path="data/models/baselines/global_ml",
                metrics_summary={"rmse": 15.48, "mae": 7.90},
                notes="Phase 5 monolithic LightGBM baseline without regime conditioning.",
            ),
            ModelVersionEntry(
                phase=6,
                system_name="RAMPMixtureOfExperts",
                version_id="ramp_v1.0.0",
                status="FROZEN",
                data_mode="SYNTHETIC_DEMO",
                trained_at="2026-09-26T03:03:00Z",
                artifact_path="data/models/ramp/ramp_v1.0.0",
                metrics_summary={"rmse": 13.85, "mae": 6.84, "pearson_r": 0.6697},
                notes="Phase 6 7-expert MoE with soft calibrated probability gating.",
            ),
            ModelVersionEntry(
                phase=7,
                system_name="ExtremeRainfallProbabilityEngine",
                version_id="extreme_prob_v1.0.0",
                status="FROZEN",
                data_mode="SYNTHETIC_DEMO",
                trained_at="2026-09-26T09:24:00Z",
                artifact_path="ml/extreme_probability",
                metrics_summary={"heavy_brier": 0.0541, "heavy_pr_auc": 0.421, "heavy_roc_auc": 0.8214},
                notes="Phase 7 calibrated 4-threshold probabilities with PAV monotonicity reconciliation.",
            ),
        ]

        state = OperationalRegistryState(
            registry_version="v1.0.0",
            last_updated=datetime.utcnow().isoformat() + "Z",
            regime_model_version="regime_lgbm_v0.1.0",
            baseline_versions={
                "mean_bias": "mean_bias_v1.0.0",
                "quantile_mapping": "quantile_mapping_v1.0.0",
                "global_ml": "global_ml_v1.0.0",
            },
            ramp_model_version="ramp_v1.0.0",
            extreme_prob_version="extreme_prob_v1.0.0",
            dataset_version="ramp_dataset_v0.3.0",
            feature_schema_version="canonical_v1.0.0",
            calibration_version="platt_sigmoid_v1.0.0",
            models=models,
        )
        return state

    def save(self) -> None:
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self.state)
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved OperationalModelRegistry to {self.registry_file}")

    def register_model(self, entry: ModelVersionEntry) -> None:
        """Registers a new model version. Rejects overwriting frozen models."""
        if entry.version_id in self.FROZEN_VERSIONS:
            raise ValueError(
                f"[PROTECTION VIOLATION] Version '{entry.version_id}' is permanently FROZEN. "
                "You must create a new version identifier (e.g. ramp_v1.1.0_real) instead of overwriting."
            )

        # Replace or append
        existing = next((i for i, m in enumerate(self.state.models) if m.version_id == entry.version_id), None)
        if existing is not None:
            self.state.models[existing] = entry
        else:
            self.state.models.append(entry)

        self.state.last_updated = datetime.utcnow().isoformat() + "Z"
        self.save()

    def get_summary(self) -> Dict[str, Any]:
        return {
            "registry_version": self.state.registry_version,
            "last_updated": self.state.last_updated,
            "ramp_version": self.state.ramp_model_version,
            "extreme_prob_version": self.state.extreme_prob_version,
            "regime_version": self.state.regime_model_version,
            "dataset_version": self.state.dataset_version,
            "feature_schema": self.state.feature_schema_version,
            "calibration_version": self.state.calibration_version,
            "total_registered_models": len(self.state.models),
            "models": [asdict(m) for m in self.state.models],
        }
