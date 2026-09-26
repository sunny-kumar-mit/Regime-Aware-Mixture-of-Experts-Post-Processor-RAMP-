"""
RAMP Regime Model Registry & Serialization
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Safe model serialization, metadata versioning, and auditable storage.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
from pydantic import BaseModel, Field

from ml.regimes.calibration import RegimeCalibrator
from ml.regimes.classifier import BaseRegimeClassifier


class RegimeModelMetadata(BaseModel):
    """Auditable metadata for a trained regime classifier."""
    model_id: str
    model_type: str
    version: str = "0.1.0"
    dataset_id: str
    dataset_version: str
    training_period: Dict[str, str] = Field(default_factory=dict)
    validation_period: Dict[str, str] = Field(default_factory=dict)
    test_period: Dict[str, str] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)
    label_source: str = "WEAK_RULE"
    calibration_method: str = "isotonic"
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)
    regime_wise_metrics: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    data_mode: str = "SYNTHETIC_DEMO"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class RegimeModelRegistry:
    """Manages saving, metadata logging, and loading of trained regime models."""

    def __init__(self, models_dir: Optional[Path | str] = None) -> None:
        self.models_dir = Path(models_dir) if models_dir else Path("data/models/regime")

    def save_model(
        self,
        classifier: BaseRegimeClassifier,
        calibrator: Optional[RegimeCalibrator],
        metadata: RegimeModelMetadata,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Serializes classifier, calibrator, and metadata JSON."""
        target_dir = output_dir or (self.models_dir / metadata.model_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Serialize classifier
        clf_path = target_dir / "classifier.joblib"
        joblib.dump(classifier, clf_path)

        # Serialize calibrator if present
        if calibrator is not None:
            cal_path = target_dir / "calibrator.joblib"
            joblib.dump(calibrator, cal_path)

        # Serialize metadata JSON
        meta_path = target_dir / "model_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        return target_dir

    def load_model(
        self,
        model_id: str,
    ) -> Tuple[BaseRegimeClassifier, Optional[RegimeCalibrator], RegimeModelMetadata]:
        """Loads model artifacts and validates metadata."""
        target_dir = self.models_dir / model_id
        if not target_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {target_dir}")

        meta_path = target_dir / "model_metadata.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)
        metadata = RegimeModelMetadata(**meta_dict)

        clf_path = target_dir / "classifier.joblib"
        classifier = joblib.load(clf_path)

        calibrator = None
        cal_path = target_dir / "calibrator.joblib"
        if cal_path.exists():
            calibrator = joblib.load(cal_path)

        return classifier, calibrator, metadata

    def list_models(self) -> List[RegimeModelMetadata]:
        """Lists all registered models in the storage directory."""
        models = []
        if not self.models_dir.exists():
            return models

        for d in self.models_dir.iterdir():
            meta_file = d / "model_metadata.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    models.append(RegimeModelMetadata(**meta))
                except Exception:
                    pass
        return models
