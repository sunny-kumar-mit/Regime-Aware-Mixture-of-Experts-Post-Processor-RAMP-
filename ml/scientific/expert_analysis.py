"""
RAMP Expert Gating Analyzer — Phase 10
SIH26080 | MoES / NCMRWF

Analyzes the RAMP Mixture-of-Experts gating mechanism.
Exposes: expert probabilities, selected expert, weighted contributions,
and Regime × Expert interaction matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

REGIMES = [
    "ACTIVE_MONSOON",
    "BREAK_MONSOON",
    "LOW_DEPRESSION",
    "COASTAL",
    "OROGRAPHIC",
    "WESTERN_DISTURBANCE",
    "TRANSITION_OTHER",
]


@dataclass
class ExpertDecomposition:
    """Single-sample RAMP expert decomposition."""
    sample_id: str
    regime: str
    gate_weights: Dict[str, float]
    expert_predictions: Dict[str, float]
    weighted_contributions: Dict[str, float]
    ramp_prediction: float
    raw_nwp_prediction: float
    top_expert: str
    top_weight: float
    fallback_used: bool
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "regime": self.regime,
            "gate_weights": self.gate_weights,
            "expert_predictions": self.expert_predictions,
            "weighted_contributions": self.weighted_contributions,
            "ramp_prediction": self.ramp_prediction,
            "raw_nwp_prediction": self.raw_nwp_prediction,
            "top_expert": self.top_expert,
            "top_weight": self.top_weight,
            "fallback_used": self.fallback_used,
            "data_mode": self.data_mode,
        }


@dataclass
class RegimeExpertMatrix:
    """
    Regime × Expert interaction matrix showing mean gating weight,
    sample count, mean prediction contribution, and uncertainty.
    """
    matrix: Dict[str, Dict[str, float]]  # regime -> expert -> mean_gate_weight
    sample_counts: Dict[str, int]  # regime -> n_samples
    mean_contributions: Dict[str, Dict[str, float]]  # regime -> expert -> mean_contribution
    uncertainty: Dict[str, float]  # regime -> gate_entropy
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matrix": self.matrix,
            "sample_counts": self.sample_counts,
            "mean_contributions": self.mean_contributions,
            "uncertainty": self.uncertainty,
            "data_mode": self.data_mode,
        }


class ExpertGatingAnalyzer:
    """
    Analyzes RAMP MoE expert gating mechanism.
    Regime × Expert matrix shows mean contribution per regime.
    """

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed

    def decompose_sample(
        self,
        sample_id: str,
        regime: str,
        gate_weights: Dict[str, float],
        expert_predictions: Dict[str, float],
        ramp_prediction: float,
        raw_nwp: float,
        fallback_used: bool = False,
    ) -> ExpertDecomposition:
        """Decompose a single RAMP prediction into expert contributions."""
        weighted = {
            r: round(float(gate_weights.get(r, 0.0)) * float(expert_predictions.get(r, 0.0)), 4)
            for r in REGIMES
        }
        top_expert = max(gate_weights, key=gate_weights.get)
        top_weight = gate_weights[top_expert]

        return ExpertDecomposition(
            sample_id=sample_id,
            regime=regime,
            gate_weights={k: round(v, 4) for k, v in gate_weights.items()},
            expert_predictions={k: round(v, 4) for k, v in expert_predictions.items()},
            weighted_contributions=weighted,
            ramp_prediction=round(ramp_prediction, 4),
            raw_nwp_prediction=round(raw_nwp, 4),
            top_expert=top_expert,
            top_weight=round(top_weight, 4),
            fallback_used=fallback_used,
            data_mode=self.data_mode,
        )

    def build_regime_expert_matrix(
        self,
        decompositions: Optional[List[ExpertDecomposition]] = None,
    ) -> RegimeExpertMatrix:
        """
        Build the Regime × Expert mean gating weight matrix.
        If no real decompositions provided, uses synthetic profile-based data.
        """
        if decompositions is None or len(decompositions) == 0:
            return self._synthetic_regime_expert_matrix()

        # Aggregate from actual decompositions
        regime_weights: Dict[str, Dict[str, List[float]]] = {r: {e: [] for e in REGIMES} for r in REGIMES}
        regime_contributions: Dict[str, Dict[str, List[float]]] = {r: {e: [] for e in REGIMES} for r in REGIMES}
        sample_counts: Dict[str, int] = {r: 0 for r in REGIMES}

        for dec in decompositions:
            reg = dec.regime
            if reg not in REGIMES:
                continue
            sample_counts[reg] += 1
            for expert in REGIMES:
                regime_weights[reg][expert].append(dec.gate_weights.get(expert, 0.0))
                regime_contributions[reg][expert].append(dec.weighted_contributions.get(expert, 0.0))

        matrix = {}
        contributions = {}
        uncertainty = {}

        for reg in REGIMES:
            matrix[reg] = {}
            contributions[reg] = {}
            for expert in REGIMES:
                wts = regime_weights[reg][expert]
                matrix[reg][expert] = round(float(np.mean(wts)), 4) if wts else 0.0
                cs = regime_contributions[reg][expert]
                contributions[reg][expert] = round(float(np.mean(cs)), 4) if cs else 0.0

            # Gate entropy for this regime
            gate_row = np.array([matrix[reg][e] for e in REGIMES])
            gate_row = gate_row / max(gate_row.sum(), 1e-9)
            entropy = float(-np.sum(gate_row * np.log(gate_row + 1e-12)))
            uncertainty[reg] = round(entropy, 4)

        return RegimeExpertMatrix(
            matrix=matrix,
            sample_counts=sample_counts,
            mean_contributions=contributions,
            uncertainty=uncertainty,
            data_mode=self.data_mode,
        )

    def _synthetic_regime_expert_matrix(self) -> RegimeExpertMatrix:
        """
        Synthetic regime × expert matrix for DEMO mode.
        Reflects expected behavior: each regime should activate its own expert most strongly.
        """
        rng = np.random.RandomState(self.random_seed)
        n_regimes = len(REGIMES)

        # Build diagonal-dominant matrix (each regime favors its expert)
        base = np.ones((n_regimes, n_regimes)) * (1.0 / (n_regimes * 3))
        for i in range(n_regimes):
            base[i, i] = 0.40 + rng.uniform(0, 0.10)

        # Row-normalize
        for i in range(n_regimes):
            base[i] /= base[i].sum()

        matrix = {}
        contributions = {}
        uncertainty = {}
        sample_counts = {}

        REGIME_SAMPLES = {
            "ACTIVE_MONSOON": 42, "BREAK_MONSOON": 25, "LOW_DEPRESSION": 18,
            "COASTAL": 30, "OROGRAPHIC": 20, "WESTERN_DISTURBANCE": 28, "TRANSITION_OTHER": 37,
        }

        for i, reg in enumerate(REGIMES):
            matrix[reg] = {}
            contributions[reg] = {}
            n = REGIME_SAMPLES[reg]
            sample_counts[reg] = n

            base_rainfall = abs(rng.exponential(10.0))
            for j, expert in enumerate(REGIMES):
                w = round(float(base[i, j]), 4)
                matrix[reg][expert] = w
                contributions[reg][expert] = round(w * base_rainfall, 4)

            gate_row = np.array([matrix[reg][e] for e in REGIMES])
            entropy = float(-np.sum(gate_row * np.log(gate_row + 1e-12)))
            uncertainty[reg] = round(entropy, 4)

        return RegimeExpertMatrix(
            matrix=matrix,
            sample_counts=sample_counts,
            mean_contributions=contributions,
            uncertainty=uncertainty,
            data_mode=self.data_mode,
        )

    def get_regime_expert_summary(
        self, matrix: RegimeExpertMatrix
    ) -> List[Dict[str, Any]]:
        """Flat table: regime, top_expert, top_weight, n_samples, uncertainty."""
        rows = []
        for reg in REGIMES:
            weights = matrix.matrix.get(reg, {})
            top_expert = max(weights, key=weights.get) if weights else "UNKNOWN"
            top_weight = weights.get(top_expert, 0.0)
            rows.append({
                "regime": reg,
                "top_expert": top_expert,
                "top_weight": top_weight,
                "n_samples": matrix.sample_counts.get(reg, 0),
                "gate_entropy": matrix.uncertainty.get(reg, 0.0),
                "data_mode": self.data_mode,
            })
        return rows
