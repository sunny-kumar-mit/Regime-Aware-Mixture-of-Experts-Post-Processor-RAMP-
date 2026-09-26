"""
Unit Tests for Regime Transition Detection Engine
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import numpy as np
import pytest

from ml.regimes.definitions import TransitionState, WeatherRegime
from ml.regimes.transition import RegimeTransitionDetector


@pytest.fixture
def detector():
    return RegimeTransitionDetector(tvd_transition_threshold=0.20)


def test_tvd_identical_and_orthogonal_distributions(detector):
    """TVD of identical distributions is 0.0; orthogonal distributions is 1.0."""
    p1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    p2 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    p3 = np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    assert np.isclose(detector.total_variation_distance(p1, p2), 0.0)
    assert np.isclose(detector.total_variation_distance(p1, p3), 1.0)


def test_sequential_transition_detection(detector):
    """Detects transitioning state when regime switches over sequential timesteps."""
    time_steps = ["2026-07-01T00:00:00", "2026-07-01T06:00:00", "2026-07-01T12:00:00"]
    # Transitioning from Active Monsoon to Low/Depression
    prob_sequence = [
        [0.80, 0.05, 0.05, 0.03, 0.03, 0.02, 0.02],  # T0: Active
        [0.45, 0.05, 0.40, 0.03, 0.03, 0.02, 0.02],  # T1: Shifting
        [0.10, 0.05, 0.75, 0.03, 0.03, 0.02, 0.02],  # T2: Low/Depression
    ]

    report = detector.detect_transitions(time_steps, prob_sequence)
    assert report["transitions_detected"] >= 1
    assert report["transition_state"] in [
        TransitionState.TRANSITIONING.value,
        TransitionState.HIGH_VARIANCE.value,
    ]
    assert report["max_tvd"] > 0.20
    assert len(report["history"]) == 2


def test_stable_regime_trajectory(detector):
    """Stable regime trajectory should yield 0 transitions and STABLE state."""
    time_steps = ["T0", "T1", "T2"]
    prob_sequence = [
        [0.72, 0.05, 0.10, 0.05, 0.03, 0.02, 0.03],
        [0.70, 0.06, 0.11, 0.05, 0.03, 0.02, 0.03],
        [0.74, 0.04, 0.09, 0.05, 0.03, 0.02, 0.03],
    ]
    report = detector.detect_transitions(time_steps, prob_sequence)
    assert report["transition_state"] == TransitionState.STABLE.value
    assert report["transitions_detected"] == 0
