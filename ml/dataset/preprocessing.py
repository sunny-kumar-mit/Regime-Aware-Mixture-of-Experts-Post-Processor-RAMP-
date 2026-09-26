"""
RAMP Preprocessing Pipeline
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Handles missing data imputation and optional feature normalization.
CRITICAL INVARIANTS:
  1. Fit strictly on TRAIN data partition only.
  2. Serialize fitted parameters to preprocessing_manifest.json.
  3. Apply identical transformations to Validation and Test splits without refitting.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from ml.schemas import ImputationStrategy, PreprocessingManifest


class PreprocessingPipeline:
    """
    Leakage-safe preprocessing transformer fitted strictly on the training partition.
    """

    def __init__(
        self,
        imputation_strategy: ImputationStrategy = ImputationStrategy.MEDIAN_TRAIN,
        scale_features: bool = False,
        feature_columns: Optional[List[str]] = None,
    ) -> None:
        self.imputation_strategy = imputation_strategy
        self.scale_features = scale_features
        self.feature_columns = feature_columns or []
        self.fitted_medians: Dict[str, float] = {}
        self.fitted_means: Dict[str, float] = {}
        self.fitted_stds: Dict[str, float] = {}
        self.is_fitted: bool = False
        self.fitted_split: Optional[str] = None
        self.training_time_range: Dict[str, str] = {}

    def fit(self, train_df: pd.DataFrame, split_label: str = "TRAIN") -> "PreprocessingPipeline":
        """
        Fits imputation statistics and normalization parameters strictly on TRAIN.
        """
        if split_label != "TRAIN":
            raise ValueError(
                f"Data Leakage Violation: Preprocessing fitted on split '{split_label}'. "
                "Must be fitted strictly on 'TRAIN'."
            )

        cols_to_fit = self.feature_columns if self.feature_columns else [
            c for c in train_df.columns if pd.api.types.is_numeric_dtype(train_df[c])
        ]

        self.fitted_medians = {}
        self.fitted_means = {}
        self.fitted_stds = {}

        for col in cols_to_fit:
            if col in train_df.columns and pd.api.types.is_numeric_dtype(train_df[col]):
                series = train_df[col].dropna()
                if not series.empty:
                    med = float(series.median())
                    mean_val = float(series.mean())
                    std_val = float(series.std()) if len(series) > 1 else 1.0
                    self.fitted_medians[col] = med
                    self.fitted_means[col] = mean_val
                    self.fitted_stds[col] = std_val if std_val > 1e-6 else 1.0
                else:
                    self.fitted_medians[col] = 0.0
                    self.fitted_means[col] = 0.0
                    self.fitted_stds[col] = 1.0

        if "forecast_valid_time" in train_df.columns and not train_df.empty:
            t = pd.to_datetime(train_df["forecast_valid_time"], utc=True)
            self.training_time_range = {
                "start": t.min().isoformat(),
                "end": t.max().isoformat(),
            }

        self.is_fitted = True
        self.fitted_split = split_label
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies fitted statistics to impute missing values and optionally scale.
        """
        if not self.is_fitted:
            raise RuntimeError("PreprocessingPipeline must be fitted on TRAIN before calling transform()")

        out = df.copy()

        # 1. Imputation Strategy
        if self.imputation_strategy == ImputationStrategy.MEDIAN_TRAIN:
            for col, med in self.fitted_medians.items():
                if col in out.columns and out[col].isnull().any():
                    out[col] = out[col].fillna(med)
        elif self.imputation_strategy == ImputationStrategy.DROP:
            cols = [c for c in self.fitted_medians.keys() if c in out.columns]
            out = out.dropna(subset=cols)
        elif self.imputation_strategy == ImputationStrategy.FORWARD_ONLY:
            out = out.ffill()
        # MODEL_NATIVE retains missing values for tree algorithms

        # 2. Scaling (if requested for neural baselines)
        if self.scale_features:
            for col, mean_val in self.fitted_means.items():
                if col in out.columns:
                    std_val = self.fitted_stds.get(col, 1.0)
                    out[col] = ((out[col] - mean_val) / std_val).astype(np.float32)

        return out

    def get_manifest(self) -> PreprocessingManifest:
        """Generates auditable PreprocessingManifest."""
        if not self.is_fitted:
            raise RuntimeError("Pipeline not fitted yet")

        return PreprocessingManifest(
            fitted_on_split=self.fitted_split or "TRAIN",
            imputation_strategy=self.imputation_strategy.value,
            fitted_statistics={
                "medians": self.fitted_medians,
                "means": self.fitted_means,
                "stds": self.fitted_stds,
            },
            feature_transformations={
                "scaling": "z-score (train mean, std)" if self.scale_features else "none",
                "imputation": self.imputation_strategy.value,
            },
            training_period=self.training_time_range,
            created_at=datetime.now().isoformat(),
        )

    def export_manifest(self, output_path: Path) -> Path:
        """Exports manifest to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = self.get_manifest()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)
        return output_path
