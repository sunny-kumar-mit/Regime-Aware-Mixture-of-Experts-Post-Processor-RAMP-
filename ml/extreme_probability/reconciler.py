"""
Phase 7 Monotonic Probability Reconciler
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Enforces strict stochastic monotonicity invariant:
  P(R > 0.1) ≥ P(R > 64.5) ≥ P(R > 115.6) ≥ P(R > 204.5)

Uses Pool Adjacent Violators (isotonic regression) on the probability vector
when any violation is detected. Corrections are tracked and reported.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np


# Threshold ordering: highest first for violation detection
THRESHOLD_ORDER = [0.1, 64.5, 115.6, 204.5]
THRESHOLD_KEYS = ["p_trace", "p_heavy", "p_very_heavy", "p_extreme"]


class MonotonicProbabilityReconciler:
    """
    Enforces P(R > T1) >= P(R > T2) for all T1 < T2 using isotonic regression
    (Pool Adjacent Violators algorithm) on the probability vector.
    """

    def __init__(self) -> None:
        self.total_vectors_processed: int = 0
        self.total_corrections_applied: int = 0

    def reconcile_vector(
        self, probs: List[float]
    ) -> Tuple[List[float], bool, int]:
        """
        Reconcile a single probability vector [p_trace, p_heavy, p_very_heavy, p_extreme].

        Returns:
            (reconciled_probs, was_violated, n_corrections)
        """
        p = np.array(probs, dtype=float)
        n = len(p)
        self.total_vectors_processed += 1

        # Check if monotonicity is already satisfied
        # p[0] >= p[1] >= p[2] >= p[3]
        violations = sum(1 for i in range(n - 1) if p[i] < p[i + 1])

        if violations == 0:
            return probs, False, 0

        # Apply isotonic regression (decreasing) to enforce monotonicity
        reconciled = self._pav_decreasing(p)
        corrections = int(np.sum(np.abs(reconciled - p) > 1e-8))
        self.total_corrections_applied += corrections

        return reconciled.clip(0.0, 1.0).tolist(), True, corrections

    def reconcile_dict(
        self, prob_dict: Dict[str, float]
    ) -> Tuple[Dict[str, float], bool, int]:
        """
        Reconcile from a dict with keys: p_trace, p_heavy, p_very_heavy, p_extreme.
        """
        vec = [prob_dict.get(k, 0.0) for k in THRESHOLD_KEYS]
        reconciled, violated, n_corr = self.reconcile_vector(vec)
        result = {k: round(v, 6) for k, v in zip(THRESHOLD_KEYS, reconciled)}
        return result, violated, n_corr

    def reconcile_batch(
        self, probs_matrix: np.ndarray
    ) -> Tuple[np.ndarray, int]:
        """
        Reconcile a batch of shape (n_samples, 4) probability vectors.
        Returns (reconciled_matrix, total_corrections).
        """
        n = probs_matrix.shape[0]
        reconciled = np.zeros_like(probs_matrix)
        total = 0

        for i in range(n):
            row, _, n_corr = self.reconcile_vector(probs_matrix[i].tolist())
            reconciled[i] = row
            total += n_corr

        return reconciled, total

    @staticmethod
    def _pav_decreasing(p: np.ndarray) -> np.ndarray:
        """
        Pool Adjacent Violators for decreasing sequence.
        This is isotonic regression with decreasing order constraint.
        """
        n = len(p)
        if n == 0:
            return p

        # We negate to use the standard PAV (increasing) algorithm
        neg_p = -p.copy()
        result = MonotonicProbabilityReconciler._pav_increasing(neg_p)
        return -result

    @staticmethod
    def _pav_increasing(p: np.ndarray) -> np.ndarray:
        """
        Standard Pool Adjacent Violators for increasing sequence (PAVA).
        Returns isotonically non-decreasing array.
        """
        n = len(p)
        # Use blocks: each block has a mean value
        blocks = [[p[i], 1] for i in range(n)]  # [value_sum/count, count] -> [mean, count]

        i = 0
        while i < len(blocks) - 1:
            if blocks[i][0] > blocks[i + 1][0]:
                # Merge blocks i and i+1
                total = blocks[i][0] * blocks[i][1] + blocks[i + 1][0] * blocks[i + 1][1]
                count = blocks[i][1] + blocks[i + 1][1]
                blocks[i] = [total / count, count]
                blocks.pop(i + 1)
                if i > 0:
                    i -= 1
            else:
                i += 1

        # Expand blocks back to array
        result = np.zeros(n)
        pos = 0
        for mean, count in blocks:
            for _ in range(count):
                result[pos] = mean
                pos += 1

        return result

    def check_monotonicity(self, probs: List[float]) -> bool:
        """Returns True if the probability vector satisfies monotonicity."""
        for i in range(len(probs) - 1):
            if probs[i] < probs[i + 1] - 1e-8:
                return False
        return True

    def get_statistics(self) -> Dict[str, int]:
        return {
            "total_vectors_processed": self.total_vectors_processed,
            "total_corrections_applied": self.total_corrections_applied,
        }
