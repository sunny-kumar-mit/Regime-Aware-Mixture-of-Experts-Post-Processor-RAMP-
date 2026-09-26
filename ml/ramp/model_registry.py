"""
RAMP Model Registry & Version Management
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Manages serialization, versioned artifact storage, and validation of RAMP models.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
from pydantic import BaseModel, Field

from ml.baselines.model_registry import BaselineModelRegistry
from ml.baselines.models.global_ml import GlobalMLPostProcessor
from ml.ramp.experts import RegimeExpert
from ml.ramp.model import RAMPModel
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime


class RAMPModelMetadata(BaseModel):
    """Metadata specification for versioned RAMP Mixture-of-Experts artifacts."""
    ramp_model_id: str = "ramp_v1.0.0"
    dataset_version: str = "v0.3.0"
    phase4_model_version: str = "regime_lgbm_v0.1.0"
    phase5_baseline_version: str = "global_lgbm_v1"
    feature_schema_version: str = "v1.0.0"
    training_period: Dict[str, str] = Field(default_factory=dict)
    validation_period: Dict[str, str] = Field(default_factory=dict)
    test_period: Dict[str, str] = Field(default_factory=dict)
    expert_versions: Dict[str, str] = Field(default_factory=dict)
    expert_statuses: Dict[str, str] = Field(default_factory=dict)
    training_mode: str = "hard_argmax"
    uncertainty_gating: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class RAMPModelRegistry:
    """
    Filesystem-backed registry for RAMP Mixture-of-Experts model artifacts.
    """

    def __init__(self, models_dir: Optional[Path | str] = None) -> None:
        self.models_dir = Path(models_dir) if models_dir else Path("./data/models/ramp")
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save_model(
        self,
        model: RAMPModel,
        metadata: RAMPModelMetadata,
    ) -> Path:
        """
        Saves full RAMP architecture including individual expert weights and metadata.
        """
        target_dir = self.models_dir / metadata.ramp_model_id
        target_dir.mkdir(parents=True, exist_ok=True)

        experts_dir = target_dir / "experts"
        experts_dir.mkdir(parents=True, exist_ok=True)

        # Save each regime expert individually
        for regime in REGIME_ORDER:
            r_name = regime.value
            r_folder = experts_dir / r_name.lower()
            r_folder.mkdir(parents=True, exist_ok=True)

            expert = model.experts.get(r_name)
            if expert and expert.is_fitted:
                joblib.dump(expert.model, r_folder / "model.joblib")
                with open(r_folder / "metadata.json", "w", encoding="utf-8") as f:
                    json.dump(expert.metadata(), f, indent=2)
            else:
                # Store un-fitted or insufficient sample placeholder
                with open(r_folder / "metadata.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "regime": r_name,
                        "status": "INSUFFICIENT_DATA",
                        "is_fitted": False,
                    }, f, indent=2)

        # Save metadata
        metadata_path = target_dir / "ramp_model_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        return target_dir

    def load_model(
        self,
        ramp_model_id: str = "ramp_v1.0.0",
        baselines_dir: Optional[Path | str] = None,
    ) -> Tuple[RAMPModel, RAMPModelMetadata]:
        """
        Loads RAMP model and associated metadata from disk.
        """
        target_dir = self.models_dir / ramp_model_id
        if not target_dir.exists():
            raise FileNotFoundError(f"RAMP model '{ramp_model_id}' not found in {self.models_dir}")

        meta_path = target_dir / "ramp_model_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Missing metadata for RAMP model '{ramp_model_id}'")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)
        metadata = RAMPModelMetadata(**meta_dict)

        # Load Global ML fallback from Phase 5 baselines if present
        b_dir = Path(baselines_dir) if baselines_dir else Path("./data/models/baselines")
        global_fallback = None
        if (b_dir / "global_lgbm_v1" / "model.joblib").exists():
            try:
                base_reg = BaselineModelRegistry(models_dir=b_dir)
                loaded_base, _ = base_reg.load_model("global_lgbm_v1")
                if isinstance(loaded_base, GlobalMLPostProcessor):
                    global_fallback = loaded_base
            except Exception:
                pass

        # Load each expert
        experts_dir = target_dir / "experts"
        loaded_experts: Dict[str, RegimeExpert] = {}

        for regime in REGIME_ORDER:
            r_name = regime.value
            r_folder = experts_dir / r_name.lower()
            model_joblib = r_folder / "model.joblib"
            meta_file = r_folder / "metadata.json"

            expert = RegimeExpert(regime=regime)

            if model_joblib.exists() and meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        exp_meta = json.load(f)

                    fitted_model = joblib.load(model_joblib)
                    expert.model = fitted_model
                    expert.is_fitted = True
                    expert.status = exp_meta.get("status", "TRAINED")
                    expert.train_sample_count = exp_meta.get("train_sample_count", 0)
                    expert.feature_importances = exp_meta.get("feature_importances", {})
                    expert.feature_columns = exp_meta.get("feature_columns", expert.DEFAULT_FEATURE_COLUMNS)
                except Exception:
                    expert.is_fitted = False
                    expert.status = "INSUFFICIENT_DATA"
            else:
                expert.is_fitted = False
                expert.status = "INSUFFICIENT_DATA"

            loaded_experts[r_name] = expert

        ramp_model = RAMPModel(
            experts=loaded_experts,
            global_fallback=global_fallback,
            version=metadata.ramp_model_id,
            uncertainty_gating=metadata.uncertainty_gating,
        )

        return ramp_model, metadata

    def list_models(self) -> List[RAMPModelMetadata]:
        """Catalogs all registered RAMP models."""
        models: List[RAMPModelMetadata] = []
        if not self.models_dir.exists():
            return models

        for d in sorted(self.models_dir.iterdir()):
            if d.is_dir() and (d / "ramp_model_metadata.json").exists():
                try:
                    with open(d / "ramp_model_metadata.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    models.append(RAMPModelMetadata(**data))
                except Exception:
                    pass
        return models
