"""
RAMP Sequential Regime Transition Detection Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Tracks regime probability vectors across sequential forecast horizons (t0 -> t1 -> t2...):
  - Total Variation Distance (TVD)
  - Jensen-Shannon / Maximum Probability Shifts
  - Model-identified regime transition events
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from ml.regimes.definitions import REGIME_ORDER, TransitionState, WeatherRegime


class RegimeTransitionDetector:
    """
    Identifies regime transitions and instability across sequential forecast timesteps.
    """

    def __init__(self, tvd_transition_threshold: float = 0.20) -> None:
        self.tvd_transition_threshold = tvd_transition_threshold

    @staticmethod
    def total_variation_distance(p1: np.ndarray, p2: np.ndarray) -> float:
        """Computes Total Variation Distance between two probability distributions in [0, 1]."""
        return float(0.5 * np.sum(np.abs(p1 - p2)))

    def detect_transitions(
        self,
        time_steps: List[str | Any],
        probability_sequence: List[np.ndarray | List[float]],
    ) -> Dict[str, Any]:
        """
        Analyzes a sequence of probability vectors over sequential timesteps.
        Returns transition log, overall transition state, and shift magnitude.
        """
        if len(probability_sequence) < 2:
            return {
                "transition_state": TransitionState.STABLE.value,
                "transitions_detected": 0,
                "history": [],
                "max_tvd": 0.0,
            }

        history = []
        max_tvd = 0.0
        transition_count = 0

        for t in range(len(probability_sequence) - 1):
            p_prev = np.array(probability_sequence[t], dtype=float)
            p_curr = np.array(probability_sequence[t + 1], dtype=float)

            # Ensure valid normalization
            p_prev = p_prev / np.sum(p_prev)
            p_curr = p_curr / np.sum(p_curr)

            tvd = self.total_variation_distance(p_prev, p_curr)
            max_tvd = max(max_tvd, tvd)

            top_prev_idx = int(np.argmax(p_prev))
            top_curr_idx = int(np.argmax(p_curr))

            regime_prev = REGIME_ORDER[top_prev_idx].value
            regime_curr = REGIME_ORDER[top_curr_idx].value

            is_transition = (tvd >= self.tvd_transition_threshold) or (top_prev_idx != top_curr_idx)
            if is_transition:
                transition_count += 1

            history.append({
                "from_step": str(time_steps[t]),
                "to_step": str(time_steps[t + 1]),
                "from_regime": regime_prev,
                "to_regime": regime_curr,
                "tvd": round(tvd, 4),
                "regime_switched": bool(top_prev_idx != top_curr_idx),
                "is_transition": bool(is_transition),
                "prob_prev": [round(float(x), 4) for x in p_prev],
                "prob_curr": [round(float(x), 4) for x in p_curr],
            })

        # Classify overall trajectory state
        if transition_count >= 2:
            trajectory_state = TransitionState.HIGH_VARIANCE.value
        elif transition_count == 1:
            trajectory_state = TransitionState.TRANSITIONING.value
        else:
            trajectory_state = TransitionState.STABLE.value

        return {
            "transition_state": trajectory_state,
            "transitions_detected": transition_count,
            "max_tvd": round(max_tvd, 4),
            "history": history,
        }
