"""
Unit Tests: Soft Regime Gating Engine
SIH26080 | RAMP Mixture-of-Experts
"""

import numpy as np
import pytest

from ml.ramp.gating import GateWeights, RegimeGatingEngine
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime


def test_gate_weights_validation_success():
    gw = GateWeights(
        p_active=0.4,
        p_break=0.2,
        p_low_dep=0.1,
        p_coastal=0.1,
        p_orographic=0.1,
        p_western_disturbance=0.05,
        p_transition=0.05,
    )
    arr = gw.as_array()
    assert len(arr) == 7
    assert abs(np.sum(arr) - 1.0) < 1e-4
    assert (arr >= 0.0).all()

    top_reg, top_p = gw.top_regime()
    assert top_reg == "ACTIVE_MONSOON"
    assert top_p == 0.4


def test_gate_weights_fails_loudly_on_invalid_sum():
    with pytest.raises(ValueError, match="Regime gate weights must sum to 1.0"):
        GateWeights(
            p_active=0.5,
            p_break=0.5,
            p_low_dep=0.5,
            p_coastal=0.0,
            p_orographic=0.0,
            p_western_disturbance=0.0,
            p_transition=0.0,
        )


def test_gate_weights_fails_loudly_on_negative_weight():
    with pytest.raises(Exception):
        GateWeights(
            p_active=-0.1,
            p_break=0.5,
            p_low_dep=0.2,
            p_coastal=0.1,
            p_orographic=0.1,
            p_western_disturbance=0.1,
            p_transition=0.1,
        )


def test_create_uniform_gates():
    gw = RegimeGatingEngine.create_uniform_gates()
    arr = gw.as_array()
    assert abs(np.sum(arr) - 1.0) < 1e-5
    for val in arr:
        assert abs(val - 1.0 / 7.0) < 1e-4


def test_create_one_hot_gate():
    gw = RegimeGatingEngine.create_one_hot_gate(WeatherRegime.ACTIVE_MONSOON)
    arr = gw.as_array()
    assert arr[0] == 1.0
    assert np.sum(arr) == 1.0
    assert np.all(arr[1:] == 0.0)


def test_blend_uncertainty():
    # LOW: no change
    res_low = RegimeGatingEngine.blend_uncertainty(10.0, 5.0, "LOW", enabled=True)
    assert res_low == 10.0

    # MEDIUM: 80% RAMP + 20% Global
    res_med = RegimeGatingEngine.blend_uncertainty(10.0, 5.0, "MEDIUM", enabled=True)
    assert abs(res_med - 9.0) < 1e-5

    # HIGH: 50% RAMP + 50% Global
    res_high = RegimeGatingEngine.blend_uncertainty(10.0, 5.0, "HIGH", enabled=True)
    assert abs(res_high - 7.5) < 1e-5
