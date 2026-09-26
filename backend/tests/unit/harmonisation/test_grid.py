"""
Tests for RAMP Grid Harmonization
SIH26080 | Coordinate normalization, clipping, regridding
"""

import numpy as np
import pytest

from ramp.harmonisation.grid import (
    clip_to_domain,
    ensure_ascending_latitudes,
    make_target_lats,
    make_target_lons,
    normalize_longitudes,
    normalize_longitudes_to_0_360,
    normalize_longitudes_to_m180_180,
    regrid_field,
)
from ramp.ingestion.base import INDIA_DOMAIN, RAMP_TARGET_GRID


class TestLongitudeNormalization:
    def test_negative_to_0_360(self):
        lons = np.array([-180.0, 0.0, 180.0, -90.0])
        result = normalize_longitudes_to_0_360(lons)
        assert result[0] == pytest.approx(180.0)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(180.0)
        assert result[3] == pytest.approx(270.0)

    def test_positive_to_m180_180(self):
        lons = np.array([270.0, 0.0, 180.0, 90.0])
        result = normalize_longitudes_to_m180_180(lons)
        assert result[0] == pytest.approx(-90.0)
        assert result[3] == pytest.approx(90.0)


class TestEnsureAscendingLatitudes:
    def test_ascending_unchanged(self):
        lats = np.array([6.5, 7.0, 7.5, 38.5])
        data = np.ones((4, 5))
        sorted_lats, sorted_data = ensure_ascending_latitudes(lats, data)
        np.testing.assert_array_equal(sorted_lats, lats)

    def test_descending_flipped(self):
        lats = np.array([38.5, 7.5, 7.0, 6.5])  # Descending (e.g. ERA5)
        sorted_lats, _ = ensure_ascending_latitudes(lats)
        assert sorted_lats[0] < sorted_lats[-1]


class TestClipToDomain:
    def test_clips_global_to_india(self):
        lats = np.arange(-90, 91, 5.0)
        lons = np.arange(-180, 181, 5.0)
        clipped_lats, clipped_lons, _ = clip_to_domain(lats, lons, domain=INDIA_DOMAIN)
        assert clipped_lats.min() >= INDIA_DOMAIN.lat_min
        assert clipped_lats.max() <= INDIA_DOMAIN.lat_max
        assert clipped_lons.min() >= INDIA_DOMAIN.lon_min
        assert clipped_lons.max() <= INDIA_DOMAIN.lon_max

    def test_data_shape_preserved(self):
        lats = np.arange(0, 50, 1.0)
        lons = np.arange(60, 110, 1.0)
        data = np.ones((len(lats), len(lons)))
        c_lats, c_lons, c_data = clip_to_domain(lats, lons, data, domain=INDIA_DOMAIN)
        assert c_data.shape == (len(c_lats), len(c_lons))


class TestTargetGrid:
    def test_target_lats_shape(self):
        lats = make_target_lats(RAMP_TARGET_GRID)
        assert lats[0] == pytest.approx(6.5)
        assert lats[-1] == pytest.approx(38.5)
        assert len(lats) == 129

    def test_target_lons_shape(self):
        lons = make_target_lons(RAMP_TARGET_GRID)
        assert lons[0] == pytest.approx(66.5)
        assert lons[-1] == pytest.approx(100.5)
        assert len(lons) == 137

    def test_target_grid_spacing(self):
        lats = make_target_lats(RAMP_TARGET_GRID)
        spacings = np.diff(lats)
        np.testing.assert_allclose(spacings, 0.25, atol=1e-6)


class TestRegridField:
    def test_bilinear_regrid_output_shape(self):
        src_lats = np.arange(6.0, 40.0, 0.5)
        src_lons = np.arange(66.0, 101.0, 0.5)
        src_data = np.ones((len(src_lats), len(src_lons)))
        tgt_lats, tgt_lons, regridded = regrid_field(
            src_lats, src_lons, src_data, method="bilinear"
        )
        # Should match RAMP target grid
        assert len(tgt_lats) == 129
        assert len(tgt_lons) == 137
        assert regridded.shape == (129, 137)

    def test_bilinear_constant_field_preserved(self):
        """Bilinear interpolation of a constant field must return the same constant."""
        src_lats = np.arange(5.0, 40.0, 1.0)
        src_lons = np.arange(65.0, 102.0, 1.0)
        constant = 15.0
        src_data = np.full((len(src_lats), len(src_lons)), constant)
        _, _, regridded = regrid_field(src_lats, src_lons, src_data, method="bilinear")
        # Interior points should be approximately the constant
        interior = regridded[10:-10, 10:-10]
        np.testing.assert_allclose(interior, constant, atol=0.01)

    def test_precipitation_uses_nearest(self):
        """Precipitation regridding must not produce negative values."""
        src_lats = np.arange(5.0, 40.0, 1.0)
        src_lons = np.arange(65.0, 102.0, 1.0)
        src_data = np.random.default_rng(42).gamma(0.5, 20, size=(len(src_lats), len(src_lons)))
        src_data = np.clip(src_data, 0, None)
        _, _, regridded = regrid_field(
            src_lats, src_lons, src_data, method="bilinear", is_precipitation=True
        )
        assert np.all(
            regridded[~np.isnan(regridded)] >= 0
        ), "Precipitation regridding must not produce negative values."
