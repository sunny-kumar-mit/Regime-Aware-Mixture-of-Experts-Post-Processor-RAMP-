"""
Unit tests for WeatherRegime definitions, taxonomy, and registry.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

import pytest
from ml.regimes.definitions import (
    INT_TO_REGIME,
    REGIME_ORDER,
    REGIME_TO_INT,
    WeatherRegime,
    regime_registry,
)


def test_seven_canonical_regimes_present():
    """Verify all 7 mandatory regimes are defined in WeatherRegime enum."""
    expected = {
        "ACTIVE_MONSOON",
        "BREAK_MONSOON",
        "LOW_DEPRESSION",
        "COASTAL",
        "OROGRAPHIC",
        "WESTERN_DISTURBANCE",
        "TRANSITION_OTHER",
    }
    actual = {r.value for r in WeatherRegime}
    assert actual == expected
    assert len(REGIME_ORDER) == 7


def test_bijective_integer_mappings():
    """Verify bijective mapping between regime strings and integer indices."""
    assert len(REGIME_TO_INT) == 7
    assert len(INT_TO_REGIME) == 7
    for idx in range(7):
        regime_str = INT_TO_REGIME[idx]
        assert REGIME_TO_INT[regime_str] == idx


def test_regime_registry_loads_definitions():
    """Verify definitions registry loads physical indicators and metadata."""
    definitions = regime_registry.list_regimes()
    assert len(definitions) == 7

    active_def = regime_registry.get(WeatherRegime.ACTIVE_MONSOON)
    assert active_def is not None
    assert "Somali" in active_def.description or "westerlies" in str(active_def.indicators)
    assert "monsoon" in active_def.seasonal_applicability

    low_def = regime_registry.get(WeatherRegime.LOW_DEPRESSION)
    assert low_def is not None
    assert "cyclonic" in low_def.description.lower() or "trough" in low_def.description.lower()

    trans_def = regime_registry.get(WeatherRegime.TRANSITION_OTHER)
    assert trans_def is not None
    assert trans_def.code == 6
