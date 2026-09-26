"""
Tests for RAMP Unit Normalization
SIH26080 | Unit conversion correctness
"""

import numpy as np
import pytest

from ramp.harmonisation.units import (
    CANONICAL_TARGET_UNITS,
    convert_units,
    get_target_unit,
    _canonical,
)
from ramp.ingestion.base import UnitConversionError


class TestCanonicalAlias:
    def test_kelvin_aliases(self):
        assert _canonical("kelvin") == "K"
        assert _canonical("k") == "K"

    def test_celsius_aliases(self):
        assert _canonical("celsius") == "degC"
        assert _canonical("°C") == "degC"
        assert _canonical("degc") == "degC"

    def test_hpa_aliases(self):
        assert _canonical("mb") == "hPa"
        assert _canonical("millibar") == "hPa"
        assert _canonical("mbar") == "hPa"

    def test_kg_m2_aliases(self):
        assert _canonical("kg m-2") == "kg/m²"
        assert _canonical("kg/m2") == "kg/m²"


class TestConvertUnits:
    def test_kelvin_to_celsius(self):
        data = np.array([273.15, 300.0, 200.0])
        converted, src, tgt = convert_units(data, "K", "t850")
        np.testing.assert_allclose(converted, [0.0, 26.85, -73.15], atol=0.01)
        assert src == "K"
        assert tgt == "degC"

    def test_pa_to_hpa(self):
        data = np.array([101325.0, 85000.0])
        converted, src, tgt = convert_units(data, "Pa", "mslp")
        np.testing.assert_allclose(converted, [1013.25, 850.0], atol=0.01)
        assert tgt == "hPa"

    def test_kg_m2_to_mm(self):
        data = np.array([10.0, 25.5, 0.0])
        converted, src, tgt = convert_units(data, "kg/m²", "precip_nwp_raw")
        np.testing.assert_allclose(converted, [10.0, 25.5, 0.0])
        assert tgt == "mm"

    def test_m_water_to_mm(self):
        """ERA5-style precipitation in metres of water."""
        data = np.array([0.01, 0.025])  # 10 mm and 25 mm
        converted, src, tgt = convert_units(data, "m", "precip_nwp_raw")
        np.testing.assert_allclose(converted, [10.0, 25.0])
        assert tgt == "mm"

    def test_knots_to_ms(self):
        data = np.array([10.0, 20.0])
        converted, src, tgt = convert_units(data, "knots", "u850")
        np.testing.assert_allclose(converted, [5.14444, 10.28888], atol=0.01)
        assert tgt == "m/s"

    def test_identity_mm(self):
        data = np.array([15.0, 30.0, 0.0])
        converted, src, tgt = convert_units(data, "mm", "rainfall_mm")
        np.testing.assert_array_equal(converted, data)
        assert src == tgt == "mm"

    def test_unknown_conversion_raises(self):
        data = np.array([1.0])
        with pytest.raises(UnitConversionError):
            convert_units(data, "furlongs_per_fortnight", "u850")

    def test_extreme_values_not_clipped(self):
        """Extreme rainfall must not be clipped during unit conversion."""
        data = np.array([500.0])  # 500 kg/m² = 500 mm
        converted, _, _ = convert_units(data, "kg/m²", "precip_nwp_raw")
        assert converted[0] == 500.0, "Extreme rainfall must not be clipped during conversion."

    def test_negative_handling_preserved(self):
        """Negative values (e.g. from NWP artefacts) must be preserved — not silently zeroed."""
        data = np.array([-0.05, 0.0, 10.0])
        converted, _, _ = convert_units(data, "kg/m²", "precip_nwp_raw")
        assert converted[0] < 0, "Negative artefacts should pass through conversion unmodified."


class TestGetTargetUnit:
    def test_known_variable(self):
        assert get_target_unit("precip_nwp_raw") == "mm"
        assert get_target_unit("mslp") == "hPa"
        assert get_target_unit("t850") == "degC"

    def test_unknown_variable(self):
        assert get_target_unit("non_existent_var") is None
