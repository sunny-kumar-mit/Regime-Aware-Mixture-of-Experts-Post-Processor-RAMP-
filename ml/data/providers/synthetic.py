"""
Phase 8 Synthetic Meteorological Data Provider
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Provides demonstration datasets for pipeline verification when real archives are unmounted.
TAGGED: SYNTHETIC_DEMO across all records and contract schemas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.data.contract import CanonicalRecord, DataMode, DatasetContract
from ml.data.providers.base import BaseDataProvider

logger = logging.getLogger(__name__)


class SyntheticDataProvider(BaseDataProvider):
    """
    Synthetic demonstration provider.
    Loads existing processed synthetic datasets (ramp_dataset_v0.3.0) or
    generates synthetic monsoon demonstration samples dynamically.
    """

    PARQUET_FALLBACK_PATH = Path("data/processed/training/ramp_dataset_v0.3.0/ramp_dataset.parquet")

    def __init__(self, n_samples: int = 1000, random_seed: int = 42) -> None:
        self.n_samples = n_samples
        self.random_seed = random_seed

    def get_mode(self) -> DataMode:
        return DataMode.SYNTHETIC_DEMO

    def get_source_name(self) -> str:
        return "SyntheticMonsoonDemonstrationProvider"

    def is_available(self) -> bool:
        return True  # Always available as fallback demonstration

    def load_canonical(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lead_times: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Loads canonical synthetic demonstration DataFrame."""
        if self.PARQUET_FALLBACK_PATH.exists():
            try:
                df = pd.read_parquet(self.PARQUET_FALLBACK_PATH)
                logger.info(f"Loaded {len(df)} records from existing synthetic parquet {self.PARQUET_FALLBACK_PATH}")
                # Ensure canonical naming
                if "nwp_rainfall_mm" not in df.columns:
                    if "raw_nwp_rainfall" in df.columns:
                        df["nwp_rainfall_mm"] = df["raw_nwp_rainfall"]
                    elif "nwp_rainfall" in df.columns:
                        df["nwp_rainfall_mm"] = df["nwp_rainfall"]
                if "observed_rainfall" in df.columns and "observed_rainfall_mm" not in df.columns:
                    df["observed_rainfall_mm"] = df["observed_rainfall"]
                if "forecast_initialization_time" in df.columns and "initialization_time" not in df.columns:
                    df["initialization_time"] = df["forecast_initialization_time"]
                
                df["data_mode"] = DataMode.SYNTHETIC_DEMO.value
                return df
            except Exception as e:
                logger.warning(f"Failed to read parquet fallback: {e}. Generating dynamic synthetic data.")

        return self._generate_synthetic_df(self.n_samples)

    def _generate_synthetic_df(self, n: int) -> pd.DataFrame:
        rng = np.random.default_rng(self.random_seed)

        init_dates = pd.date_range("2023-06-01", periods=n, freq="4H", tz="UTC")
        lead_choices = [24, 48, 72, 96, 120]
        leads = rng.choice(lead_choices, size=n)
        valid_dates = [init + pd.Timedelta(hours=int(l)) for init, l in zip(init_dates, leads)]

        # Synthetic coordinates across India
        lats = np.round(rng.uniform(8.0, 35.0, size=n) * 4) / 4  # 0.25 deg grid
        lons = np.round(rng.uniform(68.0, 97.0, size=n) * 4) / 4

        # Gamma/exponential distributed rainfall
        observed_rain = rng.exponential(scale=14.0, size=n)
        # 30% zero rain days
        zero_mask = rng.uniform(0, 1, size=n) < 0.30
        observed_rain[zero_mask] = 0.0

        # Inject a few extreme events (>64.5, >115.6, >204.5) to test extreme handlers
        observed_rain[0] = 72.4
        observed_rain[1] = 128.6
        observed_rain[2] = 215.0

        # NWP forecast with bias and noise
        nwp_rain = np.maximum(0.0, observed_rain * rng.uniform(0.7, 1.3, size=n) + rng.normal(1.5, 3.0, size=n))
        nwp_rain[zero_mask & (rng.uniform(0, 1, size=n) < 0.5)] = 0.0

        df = pd.DataFrame({
            "dataset_id": "ramp_synthetic_monsoon_demo_v1",
            "dataset_version": "v1.0.0",
            "source": self.get_source_name(),
            "data_mode": DataMode.SYNTHETIC_DEMO.value,
            "initialization_time": init_dates,
            "forecast_valid_time": valid_dates,
            "lead_time_hours": leads,
            "latitude": lats,
            "longitude": lons,
            "nwp_rainfall_mm": np.round(nwp_rain, 2),
            "observed_rainfall_mm": np.round(observed_rain, 2),
            "mslp_pa": rng.normal(100800, 700, size=n),
            "u850_ms": rng.normal(6.5, 3.5, size=n),
            "v850_ms": rng.normal(2.0, 3.0, size=n),
            "cape_jkg": rng.exponential(scale=450, size=n),
            "rh700_pct": np.clip(rng.normal(75, 15, size=n), 10, 100),
            "tpw_kgm2": np.clip(rng.normal(48, 12, size=n), 10, 80),
            "temp2m_k": rng.normal(301.5, 4.0, size=n),
            "gh500_m": rng.normal(5870, 150, size=n),
        })
        return df

    def get_contract(self) -> DatasetContract:
        return DatasetContract(
            dataset_id="ramp_synthetic_monsoon_demo_v1",
            dataset_version="v1.0.0",
            source=self.get_source_name(),
            data_mode=DataMode.SYNTHETIC_DEMO,
            time_range={"start": "2023-06-01T00:00:00Z", "end": "2023-09-30T00:00:00Z"},
            spatial_extent={"lat_min": 8.0, "lat_max": 35.0, "lon_min": 68.0, "lon_max": 97.0},
            resolution="0.25 deg",
            lead_times=[24, 48, 72, 96, 120],
            feature_schema_version="canonical_v1.0.0",
            target_schema_version="imd_rainfall_v1.0.0",
            total_records=self.n_samples,
            valid_records=self.n_samples,
            quality_status="PASS",
            variables=["nwp_rainfall_mm", "observed_rainfall_mm", "mslp_pa", "u850_ms", "v850_ms", "cape_jkg"],
        )
