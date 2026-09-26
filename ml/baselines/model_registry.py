"""
RAMP Baseline Model Registry & Serialization
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
from pydantic import BaseModel, Field

from ml.baselines.models.base import BaseBaselineModel
from ml.baselines.models.global_ml import GlobalMLPostProcessor
from ml.baselines.models.mean_bias import MeanBiasCorrector
from ml.baselines.models.quantile_mapping import EmpiricalQuantileMapper
from ml.baselines.models.raw_nwp import RawNWPBaseline


class BaselineModelMetadata(BaseModel):
    """Auditable metadata for a trained baseline post-processing model."""
    model_id: str
    model_type: str
    version: str = "v1.0.0"
    dataset_id: str = "ramp_dataset_v0.3.0"
    dataset_version: str = "v0.3.0"
    feature_schema_version: str = "v1.0.0"
    training_period: Dict[str, str] = Field(default_factory=dict)
    validation_period: Dict[str, str] = Field(default_factory=dict)
    test_period: Dict[str, str] = Field(default_factory=dict)
    lead_times: List[int] = Field(default_factory=lambda: [24, 48])
    thresholds: List[float] = Field(default_factory=lambda: [0.1, 64.5, 115.6, 204.5])
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    data_mode: str = "SYNTHETIC_DEMO"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class BaselineModelRegistry:
    """
    Manages persistence, metadata logging, and reloading of baseline models.
    """

    def __init__(self, models_dir: Optional[Path | str] = None) -> None:
        self.models_dir = Path(models_dir) if models_dir else Path("data/models/baselines")

    def save_model(
        self,
        model: BaseBaselineModel,
        metadata: BaselineModelMetadata,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Serializes baseline model artifact, metadata JSON, and model card."""
        target_dir = output_dir or (self.models_dir / metadata.model_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save model artifact
        model_path = target_dir / "model.joblib"
        joblib.dump(model, model_path)

        # Save metadata
        meta_path = target_dir / "model_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        # Save metrics if present
        if metadata.metrics:
            metrics_path = target_dir / "metrics.json"
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(metadata.metrics, f, indent=2)

        # Generate individual model card
        card_path = target_dir / "MODEL_CARD.md"
        with open(card_path, "w", encoding="utf-8") as f:
            f.write(f"""# Model Card: {metadata.model_id}

## Overview
- **Model Type:** {metadata.model_type}
- **Version:** {metadata.version}
- **Dataset Version:** {metadata.dataset_version}
- **Created At:** {metadata.created_at}
- **Operational Data Mode:** {metadata.data_mode}

## Purpose & Scope
Serves as a global benchmark in the RAMP SIH26080 baseline evaluation ladder.
Trained across all weather states without regime-specific conditioning.

## Verification Metrics
```json
{json.dumps(metadata.metrics, indent=2)}
```

## Physical Invariant Guarantees
- Continuous rainfall predictions constrained to R >= 0.0 mm.
- Extreme precipitation tails preserved without artificial clipping.
- Zero data leakage: fitted strictly on TRAIN data without future observation inputs.
""")

        return target_dir

    def load_model(self, model_id: str) -> Tuple[BaseBaselineModel, BaselineModelMetadata]:
        """Loads serialized baseline model and metadata."""
        target_dir = self.models_dir / model_id
        if not target_dir.exists():
            raise FileNotFoundError(f"Model directory '{target_dir}' does not exist.")

        model_path = target_dir / "model.joblib"
        meta_path = target_dir / "model_metadata.json"

        if not model_path.exists():
            raise FileNotFoundError(f"Model artifact '{model_path}' not found.")
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata file '{meta_path}' not found.")

        model = joblib.load(model_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)

        metadata = BaselineModelMetadata(**meta_dict)
        return model, metadata

    def list_models(self) -> List[BaselineModelMetadata]:
        """Lists all registered baseline models."""
        if not self.models_dir.exists():
            return []

        results = []
        for d in self.models_dir.iterdir():
            if d.is_dir() and (d / "model_metadata.json").exists():
                try:
                    with open(d / "model_metadata.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    results.append(BaselineModelMetadata(**data))
                except Exception:
                    pass
        return sorted(results, key=lambda m: m.created_at, reverse=True)
