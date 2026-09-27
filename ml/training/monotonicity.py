"""
Monotonicity Verification & Enforcement for Multi-Threshold Probabilities
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part M: Monotonicity Invariant:
  P(R >= 204.5) <= P(R >= 115.6) <= P(R >= 64.5) <= P(R >= 0.1)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MonotonicityVerifier:
    """
    Audits and enforces monotonicity across multi-threshold rainfall probabilities.
    Threshold order: [0.1, 64.5, 115.6, 204.5] mm
    """

    THRESHOLDS = [0.1, 64.5, 115.6, 204.5]
    COLUMNS = [
        "prob_rain_0p1mm",
        "prob_heavy_64p5mm",
        "prob_very_heavy_115p6mm",
        "prob_extreme_204p5mm",
    ]

    @classmethod
    def audit(
        cls,
        probs_dict: Dict[str, np.ndarray] | np.ndarray,
    ) -> Dict[str, Any]:
        """
        Audit probabilities for monotonicity violations.
        If probs_dict is an array, shape must be (N, 4) in ascending threshold order.
        """
        if isinstance(probs_dict, dict):
            P = np.column_stack([probs_dict[c] for c in cls.COLUMNS])
        else:
            P = np.asarray(probs_dict, dtype=float)

        N = P.shape[0]
        if N == 0:
            return {
                "total_samples": 0,
                "number_of_violations": 0,
                "violation_rate": 0.0,
                "maximum_violation": 0.0,
                "is_monotonic": True,
                "violation_locations": [],
            }

        # Check consecutive pairs: P[:, 0] >= P[:, 1] >= P[:, 2] >= P[:, 3]
        # Violations occur if P[:, i] < P[:, i+1]
        violations_mask = np.zeros(N, dtype=bool)
        max_violation = 0.0
        violation_indices = []

        for i in range(3):
            diff = P[:, i + 1] - P[:, i]  # Positive means violation
            pair_violations = diff > 1e-6
            if np.any(pair_violations):
                violations_mask |= pair_violations
                current_max = float(np.max(diff[pair_violations]))
                if current_max > max_violation:
                    max_violation = current_max

        violation_indices = np.where(violations_mask)[0].tolist()
        num_violations = len(violation_indices)
        rate = float(num_violations / N) if N > 0 else 0.0

        return {
            "total_samples": N,
            "number_of_violations": num_violations,
            "violation_rate": round(rate, 6),
            "maximum_violation": round(max_violation, 6),
            "is_monotonic": (num_violations == 0),
            "violation_locations": violation_indices[:50],  # Keep first 50 for reporting
            "thresholds_evaluated": cls.THRESHOLDS,
        }

    @classmethod
    def enforce(
        cls,
        probs_dict: Dict[str, np.ndarray],
        method: str = "cumulative_min",
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Enforce monotonicity by non-increasing projection:
        P(>= 64.5) = min(P(>= 0.1), P(>= 64.5))
        P(>= 115.6) = min(P(>= 64.5), P(>= 115.6))
        P(>= 204.5) = min(P(>= 115.6), P(>= 204.5))
        """
        audit_before = cls.audit(probs_dict)
        if audit_before["is_monotonic"]:
            audit_before["correction_applied"] = "NONE"
            return probs_dict, audit_before

        P = np.column_stack([probs_dict[c] for c in cls.COLUMNS])
        # Forward pass: each threshold probability cannot exceed the previous
        for i in range(1, 4):
            P[:, i] = np.minimum(P[:, i - 1], P[:, i])

        corrected = {col: P[:, i] for i, col in enumerate(cls.COLUMNS)}
        audit_after = cls.audit(corrected)
        audit_after["correction_applied"] = method
        audit_after["violations_before"] = audit_before["number_of_violations"]
        audit_after["max_violation_before"] = audit_before["maximum_violation"]

        return corrected, audit_after
