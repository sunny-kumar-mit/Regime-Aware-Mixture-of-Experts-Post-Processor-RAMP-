"""
RAMP Mixture-of-Experts Post-Processor Model
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Core Architecture:
  RAMP(x) = sum_{k=0..6} p_k(x) * Expert_k(x)

Mathematical Invariants Enforced:
  1. Soft gating (no hard switching)
  2. Physical non-negativity: RAMP(x) >= 0.0 mm
  3. Mathematical convexity: min_k E_k(x) <= RAMP(x) <= max_k E_k(x)
  4. Graceful fallback hierarchy: Regime Expert -> Global ML -> Raw NWP
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.baselines.models.global_ml import GlobalMLPostProcessor
from ml.ramp.experts import RegimeExpert
from ml.ramp.gating import GateWeights, RegimeGatingEngine
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime


class RAMPModel:
    """
    Unified Regime-Aware Mixture-of-Experts (MoE) Rainfall Post-Processor.
    """

    def __init__(
        self,
        experts: Optional[Dict[str, RegimeExpert]] = None,
        global_fallback: Optional[GlobalMLPostProcessor] = None,
        version: str = "ramp_v1.0.0",
        uncertainty_gating: bool = False,
    ) -> None:
        self.version = version
        self.uncertainty_gating = uncertainty_gating
        self.global_fallback = global_fallback

        # Initialize or assign 7 regime experts
        if experts is not None:
            self.experts = experts
        else:
            self.experts = {
                regime.value: RegimeExpert(regime=regime, version=f"{regime.value.lower()}_v1")
                for regime in REGIME_ORDER
            }

    def predict_sample(
        self,
        feature_row: Dict[str, Any] | pd.Series,
        gates: GateWeights | Dict[str, float] | np.ndarray | List[float],
        mode: str = "soft_gating",
        uncertainty_level: str = "LOW",
    ) -> Dict[str, Any]:
        """
        Executes RAMP inference on a single sample.
        Returns detailed decomposition:
          - ramp_prediction
          - expert_predictions
          - gate_weights
          - weighted_contributions
          - fallback_used
          - expert_sources
        """
        df = pd.DataFrame([feature_row.to_dict() if isinstance(feature_row, pd.Series) else feature_row])
        raw_nwp = float(df["raw_nwp_rainfall"].iloc[0]) if "raw_nwp_rainfall" in df.columns else 0.0

        # Construct and validate gate weights
        if mode == "uniform_gating":
            gw = RegimeGatingEngine.create_uniform_gates()
        elif mode == "hard_argmax":
            raw_gw = RegimeGatingEngine.create_gate_weights(gates)
            top_reg, _ = raw_gw.top_regime()
            gw = RegimeGatingEngine.create_one_hot_gate(top_reg)
        else:
            gw = RegimeGatingEngine.create_gate_weights(gates)

        # Fallback prediction if Global ML is needed
        global_ml_val = raw_nwp
        if self.global_fallback and self.global_fallback.is_fitted:
            try:
                global_ml_val = float(self.global_fallback.predict(df)[0])
            except Exception:
                global_ml_val = raw_nwp

        if mode == "global_ml_only":
            return {
                "ramp_prediction": max(0.0, global_ml_val),
                "expert_predictions": {r.value: global_ml_val for r in REGIME_ORDER},
                "gate_weights": gw.as_dict(),
                "weighted_contributions": {r.value: 0.0 for r in REGIME_ORDER},
                "fallback_used": True,
                "expert_sources": {r.value: "GLOBAL_ML_ABLATION" for r in REGIME_ORDER},
                "top_regime": gw.top_regime()[0],
                "top_probability": gw.top_regime()[1],
            }

        # Query all 7 experts with fallback tracking
        expert_preds: Dict[str, float] = {}
        expert_sources: Dict[str, str] = {}
        any_fallback_used = False

        for regime in REGIME_ORDER:
            r_name = regime.value
            expert = self.experts.get(r_name)

            if expert and expert.is_fitted:
                try:
                    pred_val = float(expert.predict(df)[0])
                    expert_preds[r_name] = max(0.0, pred_val)
                    expert_sources[r_name] = f"{r_name}_EXPERT"
                except Exception:
                    expert_preds[r_name] = global_ml_val
                    expert_sources[r_name] = "GLOBAL_ML_FALLBACK"
                    any_fallback_used = True
            else:
                expert_preds[r_name] = global_ml_val
                expert_sources[r_name] = "GLOBAL_ML_FALLBACK"
                any_fallback_used = True

        # Soft mixture calculation: RAMP = sum_k p_k * E_k
        gate_arr = gw.as_array()
        pred_arr = np.array([expert_preds[r.value] for r in REGIME_ORDER], dtype=float)

        weighted_contributions = {
            REGIME_ORDER[i].value: round(float(gate_arr[i] * pred_arr[i]), 4)
            for i in range(len(REGIME_ORDER))
        }

        ramp_raw = float(np.sum(gate_arr * pred_arr))

        # Convexity invariant check: min(E_k) <= RAMP <= max(E_k)
        min_e = float(np.min(pred_arr))
        max_e = float(np.max(pred_arr))
        if ramp_raw < min_e - 1e-3 or ramp_raw > max_e + 1e-3:
            raise ValueError(
                f"[CONVEXITY INVARIANT VIOLATION] RAMP prediction ({ramp_raw:.4f}) outside convex bounds "
                f"[{min_e:.4f}, {max_e:.4f}]."
            )

        # Optional uncertainty blending
        if self.uncertainty_gating:
            ramp_final = RegimeGatingEngine.blend_uncertainty(
                ramp_raw, global_ml_val, uncertainty_level, enabled=True
            )
        else:
            ramp_final = ramp_raw

        # Non-negativity invariant
        ramp_final = max(0.0, ramp_final)

        top_r, top_p = gw.top_regime()

        return {
            "ramp_prediction": round(ramp_final, 4),
            "raw_nwp_prediction": round(raw_nwp, 4),
            "global_ml_prediction": round(global_ml_val, 4),
            "expert_predictions": {k: round(v, 4) for k, v in expert_preds.items()},
            "gate_weights": {k: round(v, 4) for k, v in gw.as_dict().items()},
            "weighted_contributions": weighted_contributions,
            "fallback_used": any_fallback_used,
            "expert_sources": expert_sources,
            "top_regime": top_r,
            "top_probability": round(top_p, 4),
        }

    def predict_batch(
        self,
        X: pd.DataFrame,
        gates_df_or_array: pd.DataFrame | np.ndarray,
        mode: str = "soft_gating",
    ) -> pd.DataFrame:
        """
        Executes batch RAMP inference over a dataframe with aligned gating probabilities.
        """
        out = X.copy()
        n = len(X)

        if isinstance(gates_df_or_array, pd.DataFrame):
            cols = [
                f"p_{r.value.lower()}" if f"p_{r.value.lower()}" in gates_df_or_array.columns else r.value
                for r in REGIME_ORDER
            ]
            gate_matrix = gates_df_or_array[cols].values
        else:
            gate_matrix = np.asarray(gates_df_or_array, dtype=float)

        if len(gate_matrix) != n:
            raise ValueError(f"Feature count ({n}) != Gating probability count ({len(gate_matrix)}).")

        # Compute expert predictions for each regime
        expert_matrix = np.zeros((n, len(REGIME_ORDER)), dtype=float)
        global_ml_preds = None

        for idx, regime in enumerate(REGIME_ORDER):
            r_name = regime.value
            expert = self.experts.get(r_name)

            if expert and expert.is_fitted:
                try:
                    expert_matrix[:, idx] = expert.predict(X)
                except Exception:
                    if global_ml_preds is None and self.global_fallback:
                        global_ml_preds = self.global_fallback.predict(X)
                    expert_matrix[:, idx] = global_ml_preds if global_ml_preds is not None else X.get("raw_nwp_rainfall", 0.0)
            else:
                if global_ml_preds is None and self.global_fallback:
                    global_ml_preds = self.global_fallback.predict(X)
                expert_matrix[:, idx] = global_ml_preds if global_ml_preds is not None else X.get("raw_nwp_rainfall", 0.0)

        # Apply soft gating
        if mode == "uniform_gating":
            weights = np.full_like(gate_matrix, 1.0 / 7.0)
        elif mode == "hard_argmax":
            argmax_indices = np.argmax(gate_matrix, axis=1)
            weights = np.zeros_like(gate_matrix)
            for row_i, best_idx in enumerate(argmax_indices):
                weights[row_i, best_idx] = 1.0
        else:
            weights = gate_matrix

        # RAMP = sum_k p_k * E_k
        ramp_preds = np.sum(weights * expert_matrix, axis=1)
        out["ramp_prediction"] = np.maximum(ramp_preds, 0.0)

        for idx, regime in enumerate(REGIME_ORDER):
            out[f"expert_{regime.value.lower()}"] = expert_matrix[:, idx]
            out[f"gate_{regime.value.lower()}"] = weights[:, idx]

        return out

    def get_metadata(self) -> Dict[str, Any]:
        """Returns consolidated RAMP model metadata."""
        return {
            "version": self.version,
            "uncertainty_gating": self.uncertainty_gating,
            "experts": {
                r.value: self.experts[r.value].metadata()
                for r in REGIME_ORDER
                if r.value in self.experts
            },
            "global_fallback_fitted": bool(self.global_fallback and self.global_fallback.is_fitted),
        }
