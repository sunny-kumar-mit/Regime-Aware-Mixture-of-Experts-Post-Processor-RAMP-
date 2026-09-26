"""
Unit Tests for Uncertainty and Shannon Entropy Engine
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import numpy as np
import pytest

from ml.regimes.definitions import UncertaintyLevel
from ml.regimes.uncertainty import MAX_ENTROPY_7, UncertaintyEngine


def test_uniform_distribution_max_entropy():
    """Uniform distribution over 7 regimes should yield theoretical maximum entropy (~2.807 bits)."""
    p_uniform = np.full(7, 1.0 / 7.0)
    entropy, norm_entropy = UncertaintyEngine.calculate_entropy(p_uniform)

    assert np.isclose(float(entropy), MAX_ENTROPY_7, atol=1e-3)
    assert np.isclose(float(norm_entropy), 1.0, atol=1e-3)

    level = UncertaintyEngine.get_uncertainty_level(p_uniform)
    assert level == UncertaintyLevel.HIGH


def test_deterministic_distribution_zero_entropy():
    """Deterministic prediction (p_k = 1.0) should yield near zero entropy and LOW uncertainty."""
    p_det = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    entropy, norm_entropy = UncertaintyEngine.calculate_entropy(p_det)

    assert float(entropy) < 0.01
    assert float(norm_entropy) < 0.01

    level = UncertaintyEngine.get_uncertainty_level(p_det)
    assert level == UncertaintyLevel.LOW


def test_intermediate_uncertainty_level():
    """Moderately confident distribution (e.g. top regime ~60%) should yield MEDIUM uncertainty."""
    p_medium = np.array([0.55, 0.20, 0.10, 0.05, 0.04, 0.03, 0.03])
    level = UncertaintyEngine.get_uncertainty_level(p_medium, low_threshold=0.40, high_threshold=0.75)
    assert level == UncertaintyLevel.MEDIUM


def test_batch_entropy_calculation():
    """2D batch calculation should preserve shapes and correct per-sample levels."""
    probs_batch = np.array([
        [0.94, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01],  # LOW
        [0.15, 0.15, 0.14, 0.14, 0.14, 0.14, 0.14],  # HIGH
    ])
    entropy, norm_entropy = UncertaintyEngine.calculate_entropy(probs_batch)
    assert len(entropy) == 2
    assert len(norm_entropy) == 2
    assert norm_entropy[0] < norm_entropy[1]

    levels = UncertaintyEngine.get_uncertainty_level(probs_batch)
    assert levels == [UncertaintyLevel.LOW, UncertaintyLevel.HIGH]
