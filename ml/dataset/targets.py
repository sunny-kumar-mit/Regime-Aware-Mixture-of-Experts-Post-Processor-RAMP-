"""
RAMP Target Construction Pipeline
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Constructs canonical observation targets for ML post-processing:
  Target 1: observed_rainfall_mm
  Target 2: rainfall_occurrence (configurable threshold, default 0.1mm)
  Target 3: heavy_rainfall (>= 64.5 mm / 24h - IMD standard)
  Target 4: very_heavy_rainfall (>= 115.6 mm / 24h - IMD standard)
  Target 5: extremely_heavy_rainfall (>= 204.5 mm / 24h - IMD standard)
  Target 6: rainfall_anomaly (fitted strictly on training period climatology)

Strict Scientific Constraints:
  - Climatological baseline MUST be fitted on training period only (NO future test data leakage).
  - Extreme rainfall (200-400mm) must NEVER be clipped or removed.
  - Regime labels are reserved for Phase 4 and initialized as None.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd


class ClimatologyBaseline:
    """
    Computes climatological daily rainfall baselines strictly from training observations.
    
    Prevents temporal data leakage by ensuring test and validation observations
    never influence the climatological mean.
    """

    def __init__(self, smoothing_days: int = 7) -> None:
        self.smoothing_days = smoothing_days
        self._lookup: Dict[Tuple[float, float, int], float] = {}
        self.is_fitted: bool = False
        self.fitted_split: Optional[str] = None

    def fit(self, train_df: pd.DataFrame, split_label: str = "TRAIN") -> "ClimatologyBaseline":
        """
        Fit climatological mean rainfall per (latitude, longitude, day_of_year)
        using training data ONLY.
        """
        if split_label != "TRAIN":
            raise ValueError(
                f"Data Leakage Violation: Climatology cannot be fitted on split '{split_label}'. "
                "Must be fitted strictly on 'TRAIN'."
            )
        if "observed_rainfall_mm" not in train_df.columns:
            raise KeyError("train_df must contain 'observed_rainfall_mm' to compute climatology")
        if "target_valid_time" not in train_df.columns:
            raise KeyError("train_df must contain 'target_valid_time' to extract day_of_year")

        df = train_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["target_valid_time"]):
            df["target_valid_time"] = pd.to_datetime(df["target_valid_time"], utc=True)

        df["doy"] = df["target_valid_time"].dt.dayofyear
        df["lat_round"] = df["latitude"].round(2)
        df["lon_round"] = df["longitude"].round(2)

        grouped = df.groupby(["lat_round", "lon_round", "doy"])["observed_rainfall_mm"].mean()
        self._lookup = grouped.to_dict()
        self.is_fitted = True
        self.fitted_split = split_label
        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """
        Look up climatological mean for each observation row in df.
        Defaults to grid-cell global mean or regional overall mean if exact DOY missing.
        """
        if not self.is_fitted:
            raise RuntimeError("ClimatologyBaseline must be fitted before predict() is called")

        if not pd.api.types.is_datetime64_any_dtype(df["target_valid_time"]):
            target_times = pd.to_datetime(df["target_valid_time"], utc=True)
        else:
            target_times = df["target_valid_time"]

        doys = target_times.dt.dayofyear
        lats = df["latitude"].round(2)
        lons = df["longitude"].round(2)

        climo_vals = []
        overall_mean = float(np.mean(list(self._lookup.values()))) if self._lookup else 0.0

        for lat, lon, doy in zip(lats, lons, doys):
            val = self._lookup.get((lat, lon, doy), overall_mean)
            climo_vals.append(val)

        return pd.Series(climo_vals, index=df.index, dtype="float32")


class TargetBuilder:
    """
    Constructs and audits canonical observation targets for the RAMP pipeline.
    """

    def __init__(
        self,
        occurrence_threshold_mm: float = 0.1,
        heavy_threshold_mm: float = 64.5,
        very_heavy_threshold_mm: float = 115.6,
        extremely_heavy_threshold_mm: float = 204.5,
    ) -> None:
        """
        Configurable meteorological thresholds.
        Default 0.1 mm: IMD threshold for measurable precipitation (trace amounts <0.1mm are dry).
        Default 64.5 mm: IMD Heavy Rainfall threshold.
        Default 115.6 mm: IMD Very Heavy Rainfall threshold.
        Default 204.5 mm: IMD Extremely Heavy Rainfall threshold.
        """
        self.occurrence_threshold_mm = occurrence_threshold_mm
        self.heavy_threshold_mm = heavy_threshold_mm
        self.very_heavy_threshold_mm = very_heavy_threshold_mm
        self.extremely_heavy_threshold_mm = extremely_heavy_threshold_mm
        self.climatology: Optional[ClimatologyBaseline] = None

    def fit_climatology(self, train_df: pd.DataFrame) -> None:
        """Fit climatology strictly on training data."""
        self.climatology = ClimatologyBaseline().fit(train_df, split_label="TRAIN")

    def build_targets(
        self,
        df: pd.DataFrame,
        observation_col: str = "observed_rainfall_mm",
        quality_col: str = "observation_quality_flag",
        source_col: str = "observation_source",
    ) -> pd.DataFrame:
        """
        Generates canonical target columns and attaches target metadata.
        """
        if observation_col not in df.columns:
            raise KeyError(f"Expected observation column '{observation_col}' in input DataFrame")

        out = df.copy()
        obs = out[observation_col]

        # Target 2: Rainfall occurrence (binary: 0 = below measurable, 1 = event)
        out["rainfall_occurrence"] = (obs >= self.occurrence_threshold_mm).astype(np.int32)

        # Target 3: Heavy rainfall (>= 64.5 mm / 24h)
        out["heavy_rainfall"] = (obs >= self.heavy_threshold_mm).astype(np.int32)

        # Target 4: Very heavy rainfall (>= 115.6 mm / 24h)
        out["very_heavy_rainfall"] = (obs >= self.very_heavy_threshold_mm).astype(np.int32)

        # Target 5: Extremely heavy rainfall (>= 204.5 mm / 24h)
        out["extremely_heavy_rainfall"] = (obs >= self.extremely_heavy_threshold_mm).astype(np.int32)

        # Target 6: Rainfall anomaly relative to training climatology
        if self.climatology is not None and self.climatology.is_fitted:
            out["climatology_rainfall_mm"] = self.climatology.predict(out)
            out["rainfall_anomaly"] = (out[observation_col] - out["climatology_rainfall_mm"]).astype(np.float32)
        else:
            out["climatology_rainfall_mm"] = np.nan
            out["rainfall_anomaly"] = np.nan

        # Target metadata defaults if not present
        if quality_col not in out.columns:
            out["observation_quality_flag"] = "VALID"
        if source_col not in out.columns:
            out["observation_source"] = "IMD_025"

        # Phase 4 Regime reservation: MUST be None in Phase 3
        out["regime_label"] = None
        out["regime_label_source"] = None
        out["regime_label_confidence"] = None

        return out
