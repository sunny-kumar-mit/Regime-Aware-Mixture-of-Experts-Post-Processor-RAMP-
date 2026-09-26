"""
RAMP Baseline Inference Service
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ml.baselines.models.base import BaseBaselineModel
from ml.baselines.models.global_ml import GlobalMLPostProcessor
from ml.baselines.models.mean_bias import MeanBiasCorrector
from ml.baselines.models.quantile_mapping import EmpiricalQuantileMapper
from ml.baselines.models.raw_nwp import RawNWPBaseline


class PredictionRecord(BaseModel):
    """Unified prediction schema for baseline post-processing systems."""
    sample_id: str
    forecast_valid_time: str
    latitude: float
    longitude: float
    lead_time_hours: int

    raw_nwp_prediction: float
    mean_bias_prediction: float
    quantile_mapping_prediction: float
    global_ml_prediction: float

    observed_rainfall: Optional[float] = None
    data_mode: str = "SYNTHETIC_DEMO"
    dataset_version: str = "v0.3.0"
    model_versions: Dict[str, str] = Field(default_factory=dict)


class BaselineInferenceService:
    """
    Unified multi-model inference service executing all 4 baseline systems.
    """

    def __init__(
        self,
        raw_nwp: Optional[RawNWPBaseline] = None,
        mean_bias: Optional[MeanBiasCorrector] = None,
        quantile_mapping: Optional[EmpiricalQuantileMapper] = None,
        global_ml: Optional[GlobalMLPostProcessor] = None,
        dataset_version: str = "v0.3.0",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> None:
        self.raw_nwp = raw_nwp or RawNWPBaseline()
        self.mean_bias = mean_bias or MeanBiasCorrector()
        self.quantile_mapping = quantile_mapping or EmpiricalQuantileMapper()
        self.global_ml = global_ml or GlobalMLPostProcessor()
        self.dataset_version = dataset_version
        self.data_mode = data_mode

    def predict_sample(self, row: Dict[str, Any] | pd.Series) -> PredictionRecord:
        """Runs all 4 baselines on a single feature record."""
        df = pd.DataFrame([row.to_dict() if isinstance(row, pd.Series) else row])
        preds_df = self.predict_batch(df)
        rec = preds_df.iloc[0].to_dict()

        return PredictionRecord(
            sample_id=str(rec.get("sample_id", "sample_000")),
            forecast_valid_time=str(rec.get("forecast_valid_time", "2026-07-01T00:00:00Z")),
            latitude=float(rec.get("latitude", 20.0)),
            longitude=float(rec.get("longitude", 78.0)),
            lead_time_hours=int(rec.get("lead_time_hours", 24)),
            raw_nwp_prediction=round(float(rec["raw_nwp"]), 2),
            mean_bias_prediction=round(float(rec["mean_bias"]), 2),
            quantile_mapping_prediction=round(float(rec["quantile_mapping"]), 2),
            global_ml_prediction=round(float(rec["global_ml"]), 2),
            observed_rainfall=round(float(rec["observed_rainfall_mm"]), 2) if "observed_rainfall_mm" in rec and not pd.isna(rec["observed_rainfall_mm"]) else None,
            data_mode=self.data_mode,
            dataset_version=self.dataset_version,
            model_versions={
                "raw_nwp": self.raw_nwp.version,
                "mean_bias": self.mean_bias.version,
                "quantile_mapping": self.quantile_mapping.version,
                "global_ml": self.global_ml.version,
            },
        )

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes inference across all 4 baselines on a batch DataFrame.
        Appends prediction columns: raw_nwp, mean_bias, quantile_mapping, global_ml.
        """
        out = df.copy()

        # 1. Raw NWP
        out["raw_nwp"] = self.raw_nwp.predict(df)

        # 2. Mean Bias
        if self.mean_bias.is_fitted:
            out["mean_bias"] = self.mean_bias.predict(df)
        else:
            out["mean_bias"] = out["raw_nwp"]

        # 3. Quantile Mapping
        if self.quantile_mapping.is_fitted:
            out["quantile_mapping"] = self.quantile_mapping.predict(df)
        else:
            out["quantile_mapping"] = out["raw_nwp"]

        # 4. Global ML
        if self.global_ml.is_fitted:
            out["global_ml"] = self.global_ml.predict(df)
        else:
            out["global_ml"] = out["raw_nwp"]

        return out

    def predict_grid(self, grid_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs spatial grid inference returning coordinate arrays and layer values.
        """
        if grid_df.empty:
            return {"total_points": 0, "layers": {}}

        preds_df = self.predict_batch(grid_df)

        return {
            "total_points": len(preds_df),
            "latitudes": preds_df["latitude"].tolist() if "latitude" in preds_df.columns else [],
            "longitudes": preds_df["longitude"].tolist() if "longitude" in preds_df.columns else [],
            "layers": {
                "raw_nwp": [round(float(v), 2) for v in preds_df["raw_nwp"]],
                "mean_bias": [round(float(v), 2) for v in preds_df["mean_bias"]],
                "quantile_mapping": [round(float(v), 2) for v in preds_df["quantile_mapping"]],
                "global_ml": [round(float(v), 2) for v in preds_df["global_ml"]],
            },
        }
