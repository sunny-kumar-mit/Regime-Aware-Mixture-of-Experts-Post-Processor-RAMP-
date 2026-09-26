"""
RAMP Regime Uncertainty & Shannon Entropy Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Calculates information-theoretic Shannon entropy across the 7 regime probabilities:
  H(p) = - sum(p_i * log2(p_i))
  H_norm(p) = H(p) / log2(7)

Categorizes model certainty into: LOW, MEDIUM, HIGH.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Union
from ml.regimes.definitions import UncertaintyLevel

MAX_ENTROPY_7: float = float(np.log2(7.0))  # ~2.80735 bits


class UncertaintyEngine:
    """
    Computes Shannon entropy and model distribution uncertainty tiers.
    """

    @staticmethod
    def calculate_entropy(
        probs: np.ndarray,
        eps: float = 1e-9,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates Shannon entropy (bits) and normalized entropy in [0, 1].
        Input probs: shape (N, 7) or (7,).
        Returns: (entropy_bits, normalized_entropy).
        """
        p = np.clip(probs, eps, 1.0)
        # Normalize in case sum differs slightly from 1.0
        if p.ndim == 1:
            p = p / np.sum(p)
            entropy = -float(np.sum(p * np.log2(p)))
            norm_entropy = float(np.clip(entropy / MAX_ENTROPY_7, 0.0, 1.0))
            return np.array(entropy, dtype=np.float32), np.array(norm_entropy, dtype=np.float32)

        p = p / np.sum(p, axis=1, keepdims=True)
        entropy = -np.sum(p * np.log2(p), axis=1)
        norm_entropy = np.clip(entropy / MAX_ENTROPY_7, 0.0, 1.0)
        return entropy.astype(np.float32), norm_entropy.astype(np.float32)

    @classmethod
    def get_uncertainty_level(
        cls,
        probs: np.ndarray,
        low_threshold: float = 0.40,
        high_threshold: float = 0.75,
    ) -> UncertaintyLevel | list[UncertaintyLevel]:
        """
        Categorizes probability distribution into LOW, MEDIUM, or HIGH uncertainty.
        """
        _, norm_entropy = cls.calculate_entropy(probs)

        if norm_entropy.ndim == 0 or (isinstance(norm_entropy, np.ndarray) and norm_entropy.size == 1):
            val = float(norm_entropy)
            if val < low_threshold:
                return UncertaintyLevel.LOW
            elif val < high_threshold:
                return UncertaintyLevel.MEDIUM
            else:
                return UncertaintyLevel.HIGH

        levels = []
        for val in norm_entropy:
            if val < low_threshold:
                levels.append(UncertaintyLevel.LOW)
            elif val < high_threshold:
                levels.append(UncertaintyLevel.MEDIUM)
            else:
                levels.append(UncertaintyLevel.HIGH)
        return levels
