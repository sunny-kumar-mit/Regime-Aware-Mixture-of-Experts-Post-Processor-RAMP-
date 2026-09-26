"""
RAMP Synthetic Data Generator
SIH26080 | SYNTHETIC_DEMO Data for UI/API Testing Only

⚠️  CRITICAL WARNING ⚠️
This module generates COMPLETELY ARTIFICIAL meteorological data.
It is labelled SYNTHETIC_DEMO and must NEVER be:
  - Used to claim scientific model performance.
  - Passed to the verification pipeline as if it were real observations.
  - Called "IMD rainfall" or attributed to any real provider.
  - Mixed with real data without explicit tagging.

Permitted uses:
  - UI integration testing
  - API smoke testing
  - Pipeline plumbing verification
  - Demos where data_mode=SYNTHETIC_DEMO is prominently displayed
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

from ramp.ingestion.base import (
    BoundingBox,
    DataMode,
    DataProvenance,
    FileFormat,
    ForecastTimeSpec,
    INDIA_DOMAIN,
    NWPForecastBundle,
    ObservationBundle,
    ObservationProvider,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    ValidationReport,
    VariableDescriptor,
    WeatherForecastProvider,
)
from ramp.harmonisation.grid import make_target_lats, make_target_lons, RAMP_TARGET_GRID

logger = logging.getLogger("ramp.ingestion.synthetic")


def _ramp_seed(initialization_time: datetime, lead: int) -> int:
    """Deterministic seed for reproducible synthetic data."""
    ts = int(initialization_time.timestamp())
    return (ts + lead * 1000037) % (2**31 - 1)


def generate_synthetic_rainfall_field(
    lats: np.ndarray,
    lons: np.ndarray,
    seed: int = 42,
    max_mm: float = 150.0,
) -> np.ndarray:
    """
    Generate a physically-plausible synthetic rainfall field using a Gamma distribution
    with spatial correlation imposed via Gaussian blur.

    The generated field:
      - Has a realistic right-skewed distribution (many zeros/light rain, few heavy).
      - Includes spatially coherent rain bands.
      - Is clearly NOT real IMD or NWP data.

    SYNTHETIC_DEMO only.
    """
    rng = np.random.default_rng(seed)
    n_lat, n_lon = len(lats), len(lons)

    # Gamma distribution: shape=0.5 (very skewed), scale=20 mm
    raw = rng.gamma(shape=0.5, scale=20.0, size=(n_lat, n_lon))

    # Spatial coherence: convolve with Gaussian kernel
    try:
        from scipy.ndimage import gaussian_filter
        raw = gaussian_filter(raw, sigma=3.0)
    except ImportError:
        pass  # Skip smoothing if scipy unavailable

    # Clip negative values (can appear after convolution)
    raw = np.clip(raw, 0.0, max_mm)

    # Introduce realistic dry regions (break-like)
    dry_mask = rng.random((n_lat, n_lon)) > 0.65
    raw[dry_mask] *= 0.1

    return raw.astype(np.float32)


def generate_synthetic_wind_field(
    lats: np.ndarray,
    lons: np.ndarray,
    base_u: float = 8.0,
    base_v: float = 2.0,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic wind components with spatial variability. SYNTHETIC_DEMO only."""
    rng = np.random.default_rng(seed + 1)
    n_lat, n_lon = len(lats), len(lons)
    u = base_u + rng.normal(0, 2.0, size=(n_lat, n_lon))
    v = base_v + rng.normal(0, 1.5, size=(n_lat, n_lon))
    return u.astype(np.float32), v.astype(np.float32)


class SyntheticNWPProvider(WeatherForecastProvider):
    """
    Generates SYNTHETIC_DEMO NWP forecast bundles.

    ⚠️ SYNTHETIC_DEMO ONLY — NOT real forecasts.
       Every output is tagged DataMode.SYNTHETIC_DEMO.
       The forecaster MUST NOT use these for operational decisions.
    """

    PROVIDER_ID = "synthetic_nwp"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.NWP

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_id=self.PROVIDER_ID,
            name="⚠️ SYNTHETIC_DEMO NWP Generator (NOT REAL DATA)",
            provider_type=ProviderType.NWP,
            status=ProviderStatus.AVAILABLE,
            description=(
                "Generates physically-plausible but entirely synthetic NWP-like data. "
                "SYNTHETIC_DEMO mode only. Never use for scientific claims."
            ),
            supported_formats=[FileFormat.NETCDF],
            available_variables=["precip_nwp_raw", "u850", "v850", "u200", "mslp",
                                 "t850", "q850", "pw", "cape"],
            spatial_resolution_deg=0.25,
            notes=(
                "⚠️ DATA MODE: SYNTHETIC_DEMO — DEMO / SYNTHETIC — NOT REAL OBSERVATIONS. "
                "This provider exists for pipeline smoke testing only."
            ),
        )

    def get_available_times(self) -> List[datetime]:
        """Returns a fixed list of synthetic initialization times for demo purposes."""
        return [
            datetime(2025, 7, 1, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 2, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 3, 0, tzinfo=timezone.utc),
        ]

    def get_forecast(
        self,
        initialization_time: datetime,
        lead_time_hours: int,
        variables: Optional[List[str]] = None,
        domain: BoundingBox = INDIA_DOMAIN,
    ) -> NWPForecastBundle:
        """
        Generate a SYNTHETIC_DEMO NWP forecast bundle.

        WARNING: Output is DataMode.SYNTHETIC_DEMO — NOT suitable for scientific use.
        """
        seed = _ramp_seed(initialization_time, lead_time_hours)
        lats = make_target_lats(RAMP_TARGET_GRID)
        lons = make_target_lons(RAMP_TARGET_GRID)

        precip = generate_synthetic_rainfall_field(lats, lons, seed=seed)
        u850, v850 = generate_synthetic_wind_field(lats, lons, seed=seed)

        time_spec = ForecastTimeSpec(
            initialization_time=initialization_time.astimezone(timezone.utc),
            lead_time_hours=lead_time_hours,
        )

        provenance = DataProvenance(
            source_provider="SYNTHETIC_DEMO",
            source_model="SYNTHETIC_NWP",
            data_mode=DataMode.SYNTHETIC_DEMO,
            original_units={
                "precip_nwp_raw": "mm",
                "u850": "m/s",
                "v850": "m/s",
            },
            normalized_units={
                "precip_nwp_raw": "mm",
                "u850": "m/s",
                "v850": "m/s",
            },
        )
        provenance.add_step(
            "⚠️ SYNTHETIC_DEMO: Gamma-distributed rainfall + Gaussian wind field generated. "
            "NOT real NWP data."
        )

        # Build minimal numpy-based bundle (no xarray needed for synthetic)
        var_descriptors = {
            "precip_nwp_raw": VariableDescriptor(
                name="precip_nwp_raw",
                source_name="synthetic_precip",
                standard_units="mm",
                source_units="mm",
                present=True,
            ),
            "u850": VariableDescriptor(
                name="u850", source_name="synthetic_u850",
                standard_units="m/s", source_units="m/s", present=True,
            ),
            "v850": VariableDescriptor(
                name="v850", source_name="synthetic_v850",
                standard_units="m/s", source_units="m/s", present=True,
            ),
        }

        logger.warning(
            "⚠️ SYNTHETIC_DEMO NWP bundle generated: init=%s lead=%dh valid=%s — NOT REAL DATA",
            initialization_time.isoformat(), lead_time_hours,
            time_spec.forecast_valid_time.isoformat(),
        )

        bundle = NWPForecastBundle(
            time_spec=time_spec,
            provider_id=self.PROVIDER_ID,
            model_name="SYNTHETIC_NWP",
            ensemble_member=None,
            variables=var_descriptors,
            data_mode=DataMode.SYNTHETIC_DEMO,
            provenance=provenance,
        )
        # Store synthetic arrays in a simple dict attached to bundle
        bundle.xr_dataset = {  # type: ignore[assignment]
            "precip_nwp_raw": (lats, lons, precip),
            "u850": (lats, lons, u850),
            "v850": (lats, lons, v850),
        }
        return bundle

    def validate_source(self) -> ValidationReport:
        report = ValidationReport(
            dataset_name="Synthetic NWP Generator",
            provider_id=self.PROVIDER_ID,
            data_mode=DataMode.SYNTHETIC_DEMO,
        )
        report.notes = (
            "⚠️ SYNTHETIC_DEMO: This provider generates artificial data for testing only."
        )
        return report


class SyntheticObservationProvider(ObservationProvider):
    """
    Generates SYNTHETIC_DEMO observation bundles.

    ⚠️ SYNTHETIC_DEMO ONLY — NOT real IMD observations.
    """

    PROVIDER_ID = "synthetic_obs"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_id=self.PROVIDER_ID,
            name="⚠️ SYNTHETIC_DEMO Observation Generator (NOT REAL DATA)",
            provider_type=ProviderType.OBSERVATION,
            status=ProviderStatus.AVAILABLE,
            description="Generates synthetic observation-like rainfall grids for testing only.",
            available_variables=["observed_rainfall_mm"],
            spatial_resolution_deg=0.25,
            notes="⚠️ DEMO / SYNTHETIC — NOT REAL OBSERVATIONS",
        )

    def get_available_times(self) -> List[datetime]:
        return [
            datetime(2025, 7, 2, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 3, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 4, 0, tzinfo=timezone.utc),
        ]

    def get_observations(
        self,
        observation_time: datetime,
        domain: BoundingBox = INDIA_DOMAIN,
    ) -> ObservationBundle:
        """Generate SYNTHETIC_DEMO observation — NOT real IMD data."""
        obs_utc = observation_time.astimezone(timezone.utc)
        seed = _ramp_seed(obs_utc, lead=0)
        lats = make_target_lats(RAMP_TARGET_GRID)
        lons = make_target_lons(RAMP_TARGET_GRID)
        rainfall = generate_synthetic_rainfall_field(lats, lons, seed=seed + 99999)

        provenance = DataProvenance(
            source_provider="SYNTHETIC_DEMO",
            source_model="SYNTHETIC_OBS",
            data_mode=DataMode.SYNTHETIC_DEMO,
            original_units={"observed_rainfall_mm": "mm"},
            normalized_units={"observed_rainfall_mm": "mm"},
        )
        provenance.add_step(
            "⚠️ SYNTHETIC_DEMO: Artificial rainfall field generated. NOT real IMD data."
        )

        logger.warning(
            "⚠️ SYNTHETIC_DEMO observation generated for %s — NOT REAL DATA",
            obs_utc.date()
        )

        return ObservationBundle(
            observation_time=obs_utc,
            provider_id=self.PROVIDER_ID,
            source="⚠️ DEMO / SYNTHETIC — NOT REAL OBSERVATIONS",
            observed_rainfall_mm=rainfall,
            missing_fraction=0.0,
            data_mode=DataMode.SYNTHETIC_DEMO,
            provenance=provenance,
        )

    def validate_source(self) -> ValidationReport:
        report = ValidationReport(
            dataset_name="Synthetic Observation Generator",
            provider_id=self.PROVIDER_ID,
            data_mode=DataMode.SYNTHETIC_DEMO,
        )
        report.notes = "⚠️ SYNTHETIC_DEMO provider — generates artificial data for testing only."
        return report
