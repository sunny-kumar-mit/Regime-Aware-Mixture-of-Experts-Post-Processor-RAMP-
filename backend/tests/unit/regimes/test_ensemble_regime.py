"""
Unit Tests for Ensemble Regime Intelligence Engine
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import numpy as np
import pytest

from ml.regimes.definitions import REGIME_ORDER, WeatherRegime
from ml.regimes.ensemble_regime import EnsembleRegimeEvaluator


def test_ensemble_consensus_and_agreement():
    """Aggregates member probability distributions to consensus and agreement ratio."""
    # 5 ensemble members
    member_probs = [
        [0.70, 0.05, 0.15, 0.03, 0.03, 0.02, 0.02],  # Active
        [0.65, 0.05, 0.20, 0.03, 0.03, 0.02, 0.02],  # Active
        [0.80, 0.02, 0.10, 0.03, 0.02, 0.01, 0.02],  # Active
        [0.20, 0.05, 0.65, 0.03, 0.03, 0.02, 0.02],  # Low/Depression
        [0.55, 0.05, 0.30, 0.03, 0.03, 0.02, 0.02],  # Active
    ]
    member_ids = ["gefs_01", "gefs_02", "gefs_03", "gefs_04", "gefs_05"]

    res = EnsembleRegimeEvaluator.aggregate_ensemble_probabilities(member_probs, member_ids)

    assert res["is_ensemble"] is True
    assert res["member_count"] == 5
    assert res["top_regime"] == WeatherRegime.ACTIVE_MONSOON.value
    assert res["agreement_ratio"] == 0.80  # 4 out of 5 members agreed
    assert len(res["members"]) == 5

    # Check that consensus distribution sums to 1.0
    consensus_sum = sum(res["consensus_probabilities"].values())
    assert np.isclose(consensus_sum, 1.0, atol=1e-3)


def test_empty_ensemble_handling():
    """Handles empty ensemble without exception, reporting TRANSITION_OTHER."""
    res = EnsembleRegimeEvaluator.aggregate_ensemble_probabilities([])
    assert res["is_ensemble"] is False
    assert res["member_count"] == 0
    assert res["top_regime"] == WeatherRegime.TRANSITION_OTHER.value
