"""
RAMP Unified Inference Service
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Executes end-to-end RAMP inference:
  Phase 3 Predictors -> Phase 4 Calibrated Regime Gating -> Phase 6 Specialized Experts -> RAMP Prediction
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ml.ramp.gating import GateWeights, RegimeGatingEngine
from ml.ramp.model import RAMPModel
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime
from ml.regimes.inference import RegimeInferenceService


class RAMPPredictionRecord(BaseModel):
    """Unified schema for RAMP predictions and explainable MoE decomposition."""
    sample_id: str
    forecast_valid_time: str
    latitude: float
    longitude: float
    lead_time_hours: int

    raw_nwp_prediction: float
    global_ml_prediction: float
    ramp_prediction: float

    gate_probabilities: Dict[str, float]
    expert_predictions: Dict[str, float]
    weighted_contributions: Dict[str, float]

    top_regime: str
    top_probability: float
    entropy: float
    uncertainty: str
    transition_state: str = "STABLE"

    fallback_used: bool = False
    expert_sources: Dict[str, str] = Field(default_factory=dict)
    data_mode: str = "SYNTHETIC_DEMO"
    model_version: str = "ramp_v1.0.0"
    observed_rainfall: Optional[float] = None


class RAMPInferenceService:
    """
    Production inference engine coordinating Phase 4 regime intelligence and
    Phase 6 mixture-of-experts post-processing.
    """

    def __init__(
        self,
        ramp_model: Optional[RAMPModel] = None,
        regime_service: Optional[RegimeInferenceService] = None,
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> None:
        self.ramp_model = ramp_model or RAMPModel()
        self.regime_service = regime_service or RegimeInferenceService()
        self.data_mode = data_mode

    def predict_sample(
        self,
        row: Dict[str, Any] | pd.Series,
        mode: str = "soft_gating",
    ) -> RAMPPredictionRecord:
        """
        Executes end-to-end RAMP prediction on a single sample.
        """
        row_dict = row.to_dict() if isinstance(row, pd.Series) else dict(row)

        # 1. Phase 4 Regime Inference
        reg_res = self.regime_service.predict_sample(row_dict)
        probs_dict = reg_res["probabilities"]
        top_regime = reg_res["top_regime"]
        top_prob = reg_res["confidence"]
        entropy = reg_res["entropy"]
        unc_level = reg_res["uncertainty_level"]

        # 2. Phase 6 RAMP Mixture-of-Experts Prediction
        gw = RegimeGatingEngine.create_gate_weights(probs_dict)
        ramp_res = self.ramp_model.predict_sample(
            feature_row=row_dict,
            gates=gw,
            mode=mode,
            uncertainty_level=unc_level,
        )

        obs_val = None
        if "observed_rainfall_mm" in row_dict and not pd.isna(row_dict["observed_rainfall_mm"]):
            obs_val = round(float(row_dict["observed_rainfall_mm"]), 2)

        return RAMPPredictionRecord(
            sample_id=str(row_dict.get("sample_id", "sample_000")),
            forecast_valid_time=str(row_dict.get("forecast_valid_time", "2026-07-01T00:00:00Z")),
            latitude=float(row_dict.get("latitude", 20.0)),
            longitude=float(row_dict.get("longitude", 78.0)),
            lead_time_hours=int(row_dict.get("lead_time_hours", 24)),
            raw_nwp_prediction=ramp_res["raw_nwp_prediction"],
            global_ml_prediction=ramp_res["global_ml_prediction"],
            ramp_prediction=ramp_res["ramp_prediction"],
            gate_probabilities=ramp_res["gate_weights"],
            expert_predictions=ramp_res["expert_predictions"],
            weighted_contributions=ramp_res["weighted_contributions"],
            top_regime=top_regime,
            top_probability=top_prob,
            entropy=entropy,
            uncertainty=unc_level,
            transition_state="STABLE",
            fallback_used=ramp_res["fallback_used"],
            expert_sources=ramp_res["expert_sources"],
            data_mode=self.data_mode,
            model_version=self.ramp_model.version,
            observed_rainfall=obs_val,
        )

    def predict_batch(
        self,
        df: pd.DataFrame,
        mode: str = "soft_gating",
    ) -> pd.DataFrame:
        """
        Executes batch RAMP prediction with Phase 4 regime routing.
        """
        n = len(df)
        gate_matrix = np.zeros((n, len(REGIME_ORDER)), dtype=float)

        # Compute regime probabilities for each sample
        for i in range(n):
            row_dict = df.iloc[i].to_dict()
            reg_res = self.regime_service.predict_sample(row_dict)
            gw = RegimeGatingEngine.create_gate_weights(reg_res["probabilities"])
            gate_matrix[i, :] = gw.as_array()

        return self.ramp_model.predict_batch(df, gate_matrix, mode=mode)

    def predict_grid(
        self,
        grid_df: pd.DataFrame,
        mode: str = "soft_gating",
    ) -> Dict[str, Any]:
        """
        Computes 2D gridded RAMP predictions and spatial layer arrays.
        """
        if grid_df.empty:
            return {"total_points": 0, "layers": {}, "top_regimes": []}

        preds_df = self.predict_batch(grid_df, mode=mode)

        lats = [round(float(x), 2) for x in preds_df.get("latitude", [])]
        lons = [round(float(x), 2) for x in preds_df.get("longitude", [])]
        raw_nwp = [round(float(x), 2) for x in preds_df.get("raw_nwp_rainfall", preds_df.get("raw_nwp", []))]
        ramp_vals = [round(float(x), 2) for x in preds_df.get("ramp_prediction", [])]

        return {
            "total_points": len(preds_df),
            "latitudes": lats,
            "longitudes": lons,
            "raw_nwp": raw_nwp,
            "ramp_prediction": ramp_vals,
            "difference": [round(r - n, 2) for r, n in zip(ramp_vals, raw_nwp)],
        }
