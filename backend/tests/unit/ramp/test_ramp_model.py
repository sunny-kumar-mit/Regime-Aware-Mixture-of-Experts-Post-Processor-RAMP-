"""
Unit Tests: RAMP Mixture-of-Experts Model & Mathematical Invariants
SIH26080 | RAMP Mixture-of-Experts
"""

import numpy as np
import pandas as pd
import pytest

from ml.ramp.experts import RegimeExpert
from ml.ramp.gating import GateWeights, RegimeGatingEngine
from ml.ramp.model import RAMPModel
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime


class MockExpert:
    """Deterministic mock expert returning a fixed constant prediction."""
    def __init__(self, regime: WeatherRegime, fixed_val: float):
        self.regime = regime
        self.regime_name = regime.value
        self.is_fitted = True
        self.status = "TRAINED"
        self.version = "mock_v1"
        self.fixed_val = fixed_val

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.fixed_val, dtype=float)

    def metadata(self):
        return {"regime": self.regime_name, "status": "TRAINED"}


@pytest.fixture
def mock_ramp_model():
    # 7 experts with ascending fixed predictions: 10, 20, 30, 40, 50, 60, 70 mm
    experts = {
        r.value: MockExpert(r, float((idx + 1) * 10))
        for idx, r in enumerate(REGIME_ORDER)
    }
    return RAMPModel(experts=experts, version="ramp_mock_v1")


def test_soft_gating_linear_combination(mock_ramp_model):
    # Equal 50/50 mix between active (10 mm) and break (20 mm)
    gw = GateWeights(
        p_active=0.5,
        p_break=0.5,
        p_low_dep=0.0,
        p_coastal=0.0,
        p_orographic=0.0,
        p_western_disturbance=0.0,
        p_transition=0.0,
    )
    dummy_x = {"raw_nwp_rainfall": 15.0}
    res = mock_ramp_model.predict_sample(dummy_x, gates=gw, mode="soft_gating")

    # Expected: 0.5 * 10 + 0.5 * 20 = 15.0 mm
    assert abs(res["ramp_prediction"] - 15.0) < 1e-4
    assert res["expert_predictions"]["ACTIVE_MONSOON"] == 10.0
    assert res["expert_predictions"]["BREAK_MONSOON"] == 20.0
    assert res["weighted_contributions"]["ACTIVE_MONSOON"] == 5.0
    assert res["weighted_contributions"]["BREAK_MONSOON"] == 10.0


def test_convexity_invariant(mock_ramp_model):
    # Any valid probability vector must produce prediction within [min_k(E_k), max_k(E_k)]
    np.random.seed(123)
    for _ in range(20):
        raw_p = np.random.uniform(0.1, 1.0, size=7)
        norm_p = raw_p / np.sum(raw_p)
        gw = RegimeGatingEngine.create_gate_weights(norm_p)

        res = mock_ramp_model.predict_sample({"raw_nwp_rainfall": 0.0}, gates=gw)
        ramp_val = res["ramp_prediction"]

        # min E_k is 10.0, max E_k is 70.0
        assert 10.0 - 1e-3 <= ramp_val <= 70.0 + 1e-3


def test_one_hot_gating_identity(mock_ramp_model):
    # If p_k = 1.0, RAMP prediction must match that expert exactly
    for idx, regime in enumerate(REGIME_ORDER):
        gw = RegimeGatingEngine.create_one_hot_gate(regime)
        res = mock_ramp_model.predict_sample({"raw_nwp_rainfall": 0.0}, gates=gw)

        expected = float((idx + 1) * 10)
        assert abs(res["ramp_prediction"] - expected) < 1e-4


def test_uniform_gating_identity(mock_ramp_model):
    # If p_k = 1/7, RAMP prediction must equal the arithmetic mean of the experts
    gw = RegimeGatingEngine.create_uniform_gates()
    res = mock_ramp_model.predict_sample({"raw_nwp_rainfall": 0.0}, gates=gw, mode="uniform_gating")

    # Mean of [10, 20, 30, 40, 50, 60, 70] = 40.0 mm
    assert abs(res["ramp_prediction"] - 40.0) < 1e-3


def test_physical_non_negativity():
    # If an expert produces negative values, RAMP clamps to 0.0 mm
    class NegativeExpert(MockExpert):
        def predict(self, X):
            return np.full(len(X), -15.0)

    exp_dict = {
        r.value: NegativeExpert(r, -15.0)
        for r in REGIME_ORDER
    }
    model = RAMPModel(experts=exp_dict)
    gw = RegimeGatingEngine.create_uniform_gates()
    res = model.predict_sample({"raw_nwp_rainfall": 0.0}, gates=gw)

    assert res["ramp_prediction"] == 0.0


def test_expert_fallback_when_unfitted():
    # Model with unfitted expert and no global fallback should fall back to raw_nwp_rainfall
    class UnfittedExpert:
        def __init__(self, regime):
            self.regime = regime
            self.regime_name = regime.value
            self.is_fitted = False
            self.status = "INSUFFICIENT_DATA"

    exp_dict = {
        r.value: UnfittedExpert(r)
        for r in REGIME_ORDER
    }
    model = RAMPModel(experts=exp_dict, global_fallback=None)
    gw = RegimeGatingEngine.create_one_hot_gate(WeatherRegime.COASTAL)
    res = model.predict_sample({"raw_nwp_rainfall": 18.5}, gates=gw)

    assert res["fallback_used"] is True
    assert res["expert_sources"]["COASTAL"] == "GLOBAL_ML_FALLBACK"
    assert abs(res["ramp_prediction"] - 18.5) < 1e-3
