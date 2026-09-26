"""
RAMP Ensemble Regime Intelligence Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Calculates regime probabilities across NWP ensemble members (e.g. GEFS / NEPS):
  - Preserves member-level classification distributions.
  - Computes ensemble consensus probability distribution.
  - Measures ensemble member agreement / inter-member spread.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.regimes.definitions import REGIME_ORDER, WeatherRegime


class EnsembleRegimeEvaluator:
    """
    Evaluates regime probability distributions across ensemble forecast members.
    """

    @staticmethod
    def aggregate_ensemble_probabilities(
        member_probabilities: List[np.ndarray | List[float]],
        member_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates member-level probability vectors into an ensemble consensus distribution.
        """
        if not member_probabilities:
            return {
                "is_ensemble": False,
                "consensus_probabilities": {},
                "top_regime": WeatherRegime.TRANSITION_OTHER.value,
                "agreement_ratio": 0.0,
                "member_count": 0,
            }

        mat = np.array(member_probabilities, dtype=float)
        # Normalize each row
        mat = mat / np.sum(mat, axis=1, keepdims=True)

        n_members = mat.shape[0]
        consensus = np.mean(mat, axis=0)
        consensus = consensus / np.sum(consensus)

        top_idx = int(np.argmax(consensus))
        top_regime = REGIME_ORDER[top_idx].value

        # Count how many members had this same top regime
        member_tops = np.argmax(mat, axis=1)
        agreement_count = int(np.sum(member_tops == top_idx))
        agreement_ratio = round(agreement_count / n_members, 4)

        consensus_dict = {
            REGIME_ORDER[i].value: round(float(consensus[i]), 4)
            for i in range(len(REGIME_ORDER))
        }

        member_details = []
        for m_idx in range(n_members):
            m_id = member_ids[m_idx] if member_ids and m_idx < len(member_ids) else f"mem_{m_idx:02d}"
            member_details.append({
                "member_id": m_id,
                "top_regime": REGIME_ORDER[int(member_tops[m_idx])].value,
                "probabilities": {REGIME_ORDER[i].value: round(float(mat[m_idx, i]), 4) for i in range(len(REGIME_ORDER))},
            })

        return {
            "is_ensemble": n_members > 1,
            "consensus_probabilities": consensus_dict,
            "top_regime": top_regime,
            "agreement_ratio": agreement_ratio,
            "member_count": n_members,
            "members": member_details,
        }
