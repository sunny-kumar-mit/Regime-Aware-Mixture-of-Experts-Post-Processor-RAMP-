"""
RAMP Weather Regime Inference Service
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Provides production inference capabilities:
  - Single-cell feature vector inference
  - Full canonical India-grid (0.25°) probability layer generation
  - Uncertainty and Shannon entropy estimation
  - Top model-attribution features ("Why this regime?")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.feature_registry import feature_registry
from ml.regimes.calibration import RegimeCalibrator
from ml.regimes.classifier import BaseRegimeClassifier, RuleBasedBaselineClassifier
from ml.regimes.definitions import REGIME_ORDER, UncertaintyLevel, WeatherRegime
from ml.regimes.uncertainty import UncertaintyEngine


class RegimeInferenceService:
    """
    Unified inference service providing calibrated regime probability vectors
    and gridded regime field layers.
    """

    def __init__(
        self,
        classifier: Optional[BaseRegimeClassifier] = None,
        calibrator: Optional[RegimeCalibrator] = None,
        model_version: str = "regime_model_v0.1.0",
    ) -> None:
        self.classifier = classifier or RuleBasedBaselineClassifier()
        self.calibrator = calibrator
        self.model_version = model_version

    def predict_sample(self, feature_row: Dict[str, Any] | pd.Series) -> Dict[str, Any]:
        """
        Runs regime inference on a single sample feature record.
        """
        if isinstance(feature_row, pd.Series):
            df = pd.DataFrame([feature_row.to_dict()])
        else:
            df = pd.DataFrame([feature_row])

        # Filter to feature columns if available, or exclude known target columns
        if hasattr(self.classifier, "feature_columns") and self.classifier.feature_columns:
            pred_df = df.reindex(columns=self.classifier.feature_columns, fill_value=0.0)
        else:
            from ml.dataset.leakage_guard import LeakageGuard
            pred_df = df.drop(columns=[c for c in LeakageGuard.TARGET_COLUMNS if c in df.columns], errors="ignore")

        # Raw probabilities from classifier
        raw_probs = self.classifier.predict_proba(pred_df)[0]

        # Calibrate if calibrator is present
        calibrated_probs = (
            self.calibrator.calibrate(raw_probs)
            if self.calibrator and self.calibrator.is_fitted
            else raw_probs
        )

        top_idx = int(np.argmax(calibrated_probs))
        top_regime = REGIME_ORDER[top_idx].value
        confidence = float(calibrated_probs[top_idx])

        # Compute entropy & uncertainty
        entropy, norm_entropy = UncertaintyEngine.calculate_entropy(calibrated_probs)
        unc_level = UncertaintyEngine.get_uncertainty_level(calibrated_probs)

        # Feature availability
        avail = {
            "elevation": bool(df["elevation"].notnull().any()) if "elevation" in df.columns else False,
            "distance_to_coast": bool(df["distance_to_coast"].notnull().any()) if "distance_to_coast" in df.columns else False,
            "cape": bool(df["cape"].notnull().any()) if "cape" in df.columns else False,
        }

        # Model attribution features (if classifier provides feature_importances)
        attributions = []
        if hasattr(self.classifier, "feature_importances") and self.classifier.feature_importances:
            sorted_imp = sorted(
                self.classifier.feature_importances.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
            attributions = [{"feature": k, "importance": v} for k, v in sorted_imp]

        probs_dict = {
            REGIME_ORDER[i].value: round(float(calibrated_probs[i]), 4)
            for i in range(len(REGIME_ORDER))
        }

        return {
            "top_regime": top_regime,
            "probabilities": probs_dict,
            "confidence": round(confidence, 4),
            "entropy": round(float(entropy), 4),
            "normalized_entropy": round(float(norm_entropy), 4),
            "uncertainty_level": unc_level.value if isinstance(unc_level, UncertaintyLevel) else unc_level,
            "model_version": self.model_version,
            "feature_availability": avail,
            "top_attribution_features": attributions,
        }

    def predict_grid(
        self,
        grid_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Executes inference over a 2D spatial grid (e.g. India canonical 0.25° grid).
        Returns regime probability layers and top regime grid.
        """
        if grid_df.empty:
            return {"total_points": 0, "layers": {}, "top_regimes": []}

        if hasattr(self.classifier, "feature_columns") and self.classifier.feature_columns:
            pred_grid = grid_df.reindex(columns=self.classifier.feature_columns, fill_value=0.0)
        else:
            from ml.dataset.leakage_guard import LeakageGuard
            pred_grid = grid_df.drop(columns=[c for c in LeakageGuard.TARGET_COLUMNS if c in grid_df.columns], errors="ignore")

        raw_probs = self.classifier.predict_proba(pred_grid)
        calibrated_probs = (
            self.calibrator.calibrate(raw_probs)
            if self.calibrator and self.calibrator.is_fitted
            else raw_probs
        )

        top_indices = np.argmax(calibrated_probs, axis=1)
        top_regimes = [REGIME_ORDER[i].value for i in top_indices]

        # Entropy per grid cell
        entropy, norm_entropy = UncertaintyEngine.calculate_entropy(calibrated_probs)

        # Assemble probability layers
        layers = {}
        for r_idx, reg in enumerate(REGIME_ORDER):
            layers[reg.value] = calibrated_probs[:, r_idx].tolist()

        return {
            "total_points": len(grid_df),
            "latitudes": grid_df["latitude"].tolist() if "latitude" in grid_df.columns else [],
            "longitudes": grid_df["longitude"].tolist() if "longitude" in grid_df.columns else [],
            "top_regimes": top_regimes,
            "entropy": [round(float(e), 3) for e in entropy],
            "normalized_entropy": [round(float(ne), 3) for ne in norm_entropy],
            "layers": layers,
        }
