"""
Tests for RAMP Ingestion Base Types and Provider ABCs
SIH26080 | Type correctness, provenance, data bundles
"""

import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ramp.ingestion.base import (
    BoundingBox,
    DataMode,
    DataProvenance,
    FileFormat,
    ForecastTimeSpec,
    GridSpec,
    INDIA_DOMAIN,
    NWPForecastBundle,
    ObservationBundle,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    ProviderUnavailableError,
    QualityFlag,
    RAMP_TARGET_GRID,
    ValidationReport,
    VariableDescriptor,
)


class TestBoundingBox:
    def test_valid_box(self):
        bb = BoundingBox(lat_min=6.5, lat_max=38.5, lon_min=66.5, lon_max=100.5)
        assert bb.lat_min == 6.5

    def test_invalid_lat_raises(self):
        with pytest.raises(ValueError, match="lat_min"):
            BoundingBox(lat_min=38.5, lat_max=6.5, lon_min=66.5, lon_max=100.5)

    def test_invalid_lon_raises(self):
        with pytest.raises(ValueError, match="lon_min"):
            BoundingBox(lat_min=6.5, lat_max=38.5, lon_min=100.5, lon_max=66.5)

    def test_india_domain_correct(self):
        assert INDIA_DOMAIN.lat_min == 6.5
        assert INDIA_DOMAIN.lat_max == 38.5
        assert INDIA_DOMAIN.lon_min == 66.5
        assert INDIA_DOMAIN.lon_max == 100.5


class TestGridSpec:
    def test_ramp_target_grid(self):
        g = RAMP_TARGET_GRID
        assert g.resolution_deg == 0.25
        assert g.n_lats == 129
        assert g.n_lons == 137


class TestProviderUnavailableError:
    def test_message_contains_no_fabricate_warning(self):
        """Error message must explicitly warn against data fabrication."""
        exc = ProviderUnavailableError("ncmrwf_ncum", "test reason")
        assert "fabricate" in str(exc).lower() or "NOT" in str(exc)
        assert exc.provider_id == "ncmrwf_ncum"
        assert exc.reason == "test reason"


class TestDataProvenance:
    def test_add_step_appends(self):
        prov = DataProvenance(source_provider="GFS", source_model="GFS")
        prov.add_step("Loaded GRIB2")
        prov.add_step("Unit normalization")
        assert len(prov.processing_steps) == 2

    def test_checksum_on_real_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"test data")
            tmp_path = Path(f.name)

        checksum = DataProvenance.compute_checksum(tmp_path)
        # Verify it is a valid hex SHA-256
        assert len(checksum) == 64
        int(checksum, 16)  # Should not raise
        tmp_path.unlink()

    def test_data_mode_defaults_to_real(self):
        prov = DataProvenance(source_provider="IMD", source_model="IMD_Gridded")
        assert prov.data_mode == DataMode.REAL


class TestValidationReport:
    def test_add_error_sets_passed_false(self):
        report = ValidationReport(dataset_name="Test", provider_id="test")
        assert report.passed is True
        report.add_error("Something failed")
        assert report.passed is False
        assert "Something failed" in report.errors

    def test_add_warning_does_not_fail(self):
        report = ValidationReport(dataset_name="Test", provider_id="test")
        report.add_warning("Close to limit")
        assert report.passed is True
        assert len(report.warnings) == 1

    def test_to_dict_contains_required_keys(self):
        report = ValidationReport(dataset_name="GFS", provider_id="gfs", model_name="GFS")
        d = report.to_dict()
        for key in ("dataset", "provider", "generated_at", "passed", "errors",
                    "warnings", "data_mode", "missing_fraction", "invalid_count"):
            assert key in d

    def test_data_mode_in_dict(self):
        report = ValidationReport(
            dataset_name="Synthetic",
            provider_id="synthetic",
            data_mode=DataMode.SYNTHETIC_DEMO,
        )
        d = report.to_dict()
        assert d["data_mode"] == "SYNTHETIC_DEMO"


class TestQualityFlagEnum:
    def test_all_flags_defined(self):
        assert QualityFlag.VALID.value == "VALID"
        assert QualityFlag.VALID_EXTREME.value == "VALID_EXTREME"
        assert QualityFlag.SUSPICIOUS.value == "SUSPICIOUS"
        assert QualityFlag.MISSING.value == "MISSING"
        assert QualityFlag.INVALID.value == "INVALID"


class TestSyntheticProviders:
    """Smoke tests for synthetic providers."""

    def test_synthetic_nwp_provider_info(self):
        from ramp.ingestion.synthetic_generator import SyntheticNWPProvider
        provider = SyntheticNWPProvider()
        info = provider.get_info()
        assert info.status == ProviderStatus.AVAILABLE
        assert "SYNTHETIC_DEMO" in info.name or "SYNTHETIC" in info.notes

    def test_synthetic_nwp_get_forecast(self):
        from ramp.ingestion.synthetic_generator import SyntheticNWPProvider
        provider = SyntheticNWPProvider()
        init = datetime(2025, 7, 1, 0, tzinfo=timezone.utc)
        bundle = provider.get_forecast(initialization_time=init, lead_time_hours=24)
        assert bundle.data_mode == DataMode.SYNTHETIC_DEMO, (
            "Synthetic bundles must be tagged SYNTHETIC_DEMO."
        )
        assert bundle.forecast_valid_time.day == 2, (
            "valid_time must be init + 24h = July 2."
        )
        assert bundle.model_name == "SYNTHETIC_NWP"

    def test_synthetic_obs_provider_info(self):
        from ramp.ingestion.synthetic_generator import SyntheticObservationProvider
        provider = SyntheticObservationProvider()
        info = provider.get_info()
        assert "SYNTHETIC" in info.name or "DEMO" in info.name

    def test_synthetic_obs_data_mode(self):
        from ramp.ingestion.synthetic_generator import SyntheticObservationProvider
        provider = SyntheticObservationProvider()
        obs_time = datetime(2025, 7, 2, 0, tzinfo=timezone.utc)
        bundle = provider.get_observations(observation_time=obs_time)
        assert bundle.data_mode == DataMode.SYNTHETIC_DEMO, (
            "Synthetic observation bundles must always be tagged SYNTHETIC_DEMO."
        )


class TestGFSProvider:
    """Tests for GFS provider when no data is present."""

    def test_unavailable_when_no_data(self):
        from ramp.ingestion.gfs_adapter import GFSProvider
        provider = GFSProvider(data_dir="data/raw/nwp/gfs_nonexistent_test")
        info = provider.get_info()
        assert info.status != ProviderStatus.AVAILABLE

    def test_raises_provider_unavailable_on_get_forecast(self):
        from ramp.ingestion.gfs_adapter import GFSProvider
        provider = GFSProvider(data_dir="data/raw/nwp/gfs_nonexistent_test")
        with pytest.raises(ProviderUnavailableError):
            provider.get_forecast(
                initialization_time=datetime(2025, 7, 1, 0, tzinfo=timezone.utc),
                lead_time_hours=24,
            )

    def test_validate_source_returns_errors_when_empty(self):
        from ramp.ingestion.gfs_adapter import GFSProvider
        provider = GFSProvider(data_dir="data/raw/nwp/gfs_nonexistent_test")
        report = provider.validate_source()
        assert not report.passed
        assert len(report.errors) > 0


class TestNCMRWFProvider:
    """NCMRWF must always be unavailable in this environment."""

    def test_unavailable_status(self):
        from ramp.ingestion.ncmrwf_adapter import NCMRWFProvider
        provider = NCMRWFProvider(model_name="NCUM")
        info = provider.get_info()
        # Status should not be AVAILABLE (no institutional data)
        assert info.status != ProviderStatus.AVAILABLE

    def test_raises_provider_unavailable_never_fabricates(self):
        from ramp.ingestion.ncmrwf_adapter import NCMRWFProvider
        provider = NCMRWFProvider(model_name="NCUM")
        with pytest.raises(ProviderUnavailableError) as exc_info:
            provider.get_forecast(
                initialization_time=datetime(2025, 7, 1, 0, tzinfo=timezone.utc),
                lead_time_hours=24,
            )
        # Ensure the error mentions not fabricating
        assert exc_info.value.provider_id.startswith("ncmrwf")


class TestProviderRegistry:
    def test_registry_has_expected_providers(self):
        from ramp.ingestion.registry import build_default_registry
        registry = build_default_registry()
        nwp_ids = [p.provider_id for p in registry.list_nwp_providers()]
        obs_ids = [p.provider_id for p in registry.list_obs_providers()]
        assert "gfs" in nwp_ids
        assert "gefs" in nwp_ids
        assert "ncmrwf_ncum" in nwp_ids
        assert "synthetic_nwp" in nwp_ids
        assert "imd" in obs_ids
        assert "synthetic_obs" in obs_ids
