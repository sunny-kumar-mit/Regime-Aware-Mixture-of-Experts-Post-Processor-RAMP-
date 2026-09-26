"""
RAMP Soft Regime Gating Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Consumes calibrated regime probability vectors from Phase 4 and enforces strict
mathematical invariants:
  - Non-negativity: p_k >= 0 for all k in [0..6]
  - Normalization: sum(p_k) == 1.0 +/- 1e-5
  - Strictly SOFT gating: RAMP = sum_k p_k * Expert_k
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field, model_validator

from ml.regimes.definitions import REGIME_ORDER, WeatherRegime


class GateWeights(BaseModel):
    """
    Normalized soft gating weights across the 7 canonical monsoon regimes.
    """
    p_active: float = Field(ge=0.0, description="P(ACTIVE_MONSOON)")
    p_break: float = Field(ge=0.0, description="P(BREAK_MONSOON)")
    p_low_dep: float = Field(ge=0.0, description="P(LOW_DEPRESSION)")
    p_coastal: float = Field(ge=0.0, description="P(COASTAL)")
    p_orographic: float = Field(ge=0.0, description="P(OROGRAPHIC)")
    p_western_disturbance: float = Field(ge=0.0, description="P(WESTERN_DISTURBANCE)")
    p_transition: float = Field(ge=0.0, description="P(TRANSITION_OTHER)")

    @model_validator(mode="after")
    def validate_sum_to_one(self) -> "GateWeights":
        total = (
            self.p_active
            + self.p_break
            + self.p_low_dep
            + self.p_coastal
            + self.p_orographic
            + self.p_western_disturbance
            + self.p_transition
        )
        if abs(total - 1.0) > 1e-4:
            raise ValueError(
                f"[GATING INVARIANT VIOLATION] Regime gate weights must sum to 1.0 +/- 1e-4. "
                f"Observed sum = {total:.6f} across components."
            )
        return self

    def as_array(self) -> np.ndarray:
        """Returns 7-element float array in canonical REGIME_ORDER."""
        return np.array([
            self.p_active,
            self.p_break,
            self.p_low_dep,
            self.p_coastal,
            self.p_orographic,
            self.p_western_disturbance,
            self.p_transition,
        ], dtype=float)

    def as_dict(self) -> Dict[str, float]:
        """Returns mapping of canonical regime string to probability."""
        arr = self.as_array()
        return {
            REGIME_ORDER[i].value: float(arr[i])
            for i in range(len(REGIME_ORDER))
        }

    def top_regime(self) -> Tuple[str, float]:
        """Returns (dominant_regime_name, probability)."""
        arr = self.as_array()
        idx = int(np.argmax(arr))
        return REGIME_ORDER[idx].value, float(arr[idx])


class RegimeGatingEngine:
    """
    Validates and constructs soft gating vectors from Phase 4 outputs.
    """

    @staticmethod
    def create_gate_weights(
        source: Dict[str, float] | np.ndarray | List[float] | GateWeights,
    ) -> GateWeights:
        """
        Constructs and rigorously validates GateWeights.
        Fails loudly if any component is negative or sum != 1.0.
        """
        if isinstance(source, GateWeights):
            return source

        if isinstance(source, dict):
            # Map various key formats
            p_act = source.get("ACTIVE_MONSOON", source.get("p_active", source.get("active", 0.0)))
            p_brk = source.get("BREAK_MONSOON", source.get("p_break", source.get("break", 0.0)))
            p_dep = source.get("LOW_DEPRESSION", source.get("p_low_dep", source.get("low_depression", 0.0)))
            p_cst = source.get("COASTAL", source.get("p_coastal", source.get("coastal", 0.0)))
            p_oro = source.get("OROGRAPHIC", source.get("p_orographic", source.get("orographic", 0.0)))
            p_wd = source.get("WESTERN_DISTURBANCE", source.get("p_western_disturbance", source.get("western_disturbance", 0.0)))
            p_trn = source.get("TRANSITION_OTHER", source.get("p_transition", source.get("transition", 0.0)))

            return GateWeights(
                p_active=float(p_act),
                p_break=float(p_brk),
                p_low_dep=float(p_dep),
                p_coastal=float(p_cst),
                p_orographic=float(p_oro),
                p_western_disturbance=float(p_wd),
                p_transition=float(p_trn),
            )

        arr = np.asarray(source, dtype=float)
        if len(arr) != 7:
            raise ValueError(f"[GATING INVARIANT] Expected 7 regime probabilities, got {len(arr)}.")

        return GateWeights(
            p_active=float(arr[0]),
            p_break=float(arr[1]),
            p_low_dep=float(arr[2]),
            p_coastal=float(arr[3]),
            p_orographic=float(arr[4]),
            p_western_disturbance=float(arr[5]),
            p_transition=float(arr[6]),
        )

    @staticmethod
    def create_uniform_gates() -> GateWeights:
        """Ablation: Uniform gating weights (1/7 each)."""
        val = 1.0 / 7.0
        return GateWeights(
            p_active=val,
            p_break=val,
            p_low_dep=val,
            p_coastal=val,
            p_orographic=val,
            p_western_disturbance=val,
            p_transition=1.0 - (val * 6),  # Exactly 1.0
        )

    @staticmethod
    def create_one_hot_gate(regime: WeatherRegime | str) -> GateWeights:
        """Ablation: Hard argmax gating (one-hot vector)."""
        r_name = regime.value if isinstance(regime, WeatherRegime) else regime
        d = {r.value: 0.0 for r in REGIME_ORDER}
        if r_name in d:
            d[r_name] = 1.0
        else:
            d[WeatherRegime.TRANSITION_OTHER.value] = 1.0

        return RegimeGatingEngine.create_gate_weights(d)

    @staticmethod
    def blend_uncertainty(
        ramp_prediction: float,
        global_ml_prediction: float,
        uncertainty_level: str,
        enabled: bool = False,
    ) -> float:
        """
        Optional uncertainty-aware gate blending:
          - LOW uncertainty: 100% RAMP
          - MEDIUM uncertainty: 80% RAMP + 20% Global ML
          - HIGH uncertainty: 50% RAMP + 50% Global ML
        """
        if not enabled:
            return ramp_prediction

        if uncertainty_level == "HIGH":
            return 0.5 * ramp_prediction + 0.5 * global_ml_prediction
        elif uncertainty_level == "MEDIUM":
            return 0.8 * ramp_prediction + 0.2 * global_ml_prediction
        return ramp_prediction
