"""
RAMP Training Dataset Builder & Pipeline Orchestrator
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Orchestrates the complete Phase 3 data preparation pipeline:
  1. Forecast & Observation Spatio-temporal Join
  2. Feature Engineering (Temporal cyclic, meteorological wind, 3x3 spatial)
  3. Target Construction (6 targets, IMD thresholds, zero-leakage climatology)
  4. Chronological Splitting with Embargo Purge Gap
  5. Train-Only Preprocessing & Imputation
  6. Strict 10-point Leakage Guard Audit (fails loudly)
  7. Distribution Diagnostics & Imbalance Reporting
  8. Semantic Versioning & Artifact Generation (Parquet, Manifests, DATASET_CARD)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.feature_registry import feature_registry
from ml.schemas import (
    DatasetVersion,
    ImputationStrategy,
    LeakageReport,
    QualityPolicy,
    SplitManifest,
    SplitStatistics,
    SplitType,
)
from ml.dataset.diagnostics import RainfallDistributionDiagnostics
from ml.dataset.features import FeatureEngineer
from ml.dataset.join import ForecastObservationJoiner
from ml.dataset.leakage_guard import DataLeakageError, LeakageGuard
from ml.dataset.preprocessing import PreprocessingPipeline
from ml.dataset.split import ChronologicalSplitter
from ml.dataset.targets import TargetBuilder
from ml.dataset.versioning import DatasetVersionManager


class DatasetBuilder:
    """
    Main builder coordinating end-to-end dataset creation for RAMP Phase 4-7.
    """

    def __init__(
        self,
        dataset_id: str = "ramp_dataset_v0.3.0",
        version: str = "0.3.0",
        data_mode: str = "SYNTHETIC_DEMO",
        purge_gap_hours: int = 24,
        imputation_strategy: ImputationStrategy = ImputationStrategy.MEDIAN_TRAIN,
        quality_policy: QualityPolicy = QualityPolicy.BALANCED,
    ) -> None:
        self.dataset_id = dataset_id
        self.version = version
        self.data_mode = data_mode
        self.purge_gap_hours = purge_gap_hours
        self.imputation_strategy = imputation_strategy
        self.quality_policy = quality_policy

        self.joiner = ForecastObservationJoiner(quality_policy=quality_policy)
        self.feature_engineer = FeatureEngineer(compute_spatial=True)
        self.target_builder = TargetBuilder()
        self.splitter = ChronologicalSplitter(purge_gap_hours=purge_gap_hours)
        self.diagnostics = RainfallDistributionDiagnostics()
        self.version_manager = DatasetVersionManager(
            dataset_id=dataset_id, version=version, data_mode=data_mode
        )

    def build_from_dfs(
        self,
        forecast_df: pd.DataFrame,
        observation_df: pd.DataFrame,
        auxiliary_df: Optional[pd.DataFrame] = None,
        source_datasets: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Executes complete verifiable dataset pipeline from raw DataFrames.
        """
        # Step 1: Join NWP forecast with IMD observation on (latitude, longitude, valid_time)
        joined_df = self.joiner.join(forecast_df, observation_df, auxiliary_df=auxiliary_df)
        if joined_df.empty:
            raise ValueError("Join between forecast and observations produced 0 records.")

        # Step 2: Feature Engineering (temporal cyclic, wind speed & direction, spatial)
        feat_df = self.feature_engineer.transform(joined_df)

        # Step 3: Initial Target Building (occurrence, heavy, very heavy, extremely heavy)
        targ_df = self.target_builder.build_targets(feat_df)

        # Step 4: Chronological Splitting with Purge Gap
        train_raw, val_raw, test_raw, split_manifest = self.splitter.split(
            targ_df, time_col="forecast_valid_time"
        )

        # Step 5: Fit Climatology strictly on TRAIN split (Zero Leakage)
        self.target_builder.fit_climatology(train_raw)
        train_df = self.target_builder.build_targets(train_raw)
        val_df = self.target_builder.build_targets(val_raw)
        test_df = self.target_builder.build_targets(test_raw)

        # Update split manifest row counts after final target assignment
        split_manifest = SplitManifest(
            split_type=split_manifest.split_type,
            train_range=split_manifest.train_range,
            val_range=split_manifest.val_range,
            test_range=split_manifest.test_range,
            train_rows=len(train_df),
            val_rows=len(val_df),
            test_rows=len(test_df),
            purge_gap_hours=self.purge_gap_hours,
        )

        # Step 6: Preprocessing & Imputation (Fit strictly on TRAIN)
        feature_cols = [
            f.name for f in feature_registry.list_features()
            if f.name in train_df.columns
        ]

        preprocessor = PreprocessingPipeline(
            imputation_strategy=self.imputation_strategy,
            feature_columns=feature_cols,
        )
        preprocessor.fit(train_df, split_label="TRAIN")

        train_processed = preprocessor.transform(train_df)
        val_processed = preprocessor.transform(val_df)
        test_processed = preprocessor.transform(test_df)
        preprocessing_manifest = preprocessor.get_manifest()

        # Step 7: Leakage Audit (Fails loudly on violation)
        guard = LeakageGuard()
        guard.audit_features(feature_cols)
        guard.audit_temporal_alignment(train_processed)
        guard.audit_climatology(self.target_builder.climatology.fitted_split, train_split_name="TRAIN")
        guard.audit_preprocessing_manifest(preprocessing_manifest.model_dump())
        leakage_report = guard.generate_report()

        # Step 8: Distribution Diagnostics & Imbalance Reporting
        split_stats = self.diagnostics.compute_all_splits(train_processed, val_processed, test_processed)

        # Combined dataset for inspection
        full_df = pd.concat([train_processed, val_processed, test_processed], ignore_index=True)

        # Step 9: Version Manifest & File Serialization
        version_manifest = self.version_manager.create_version_manifest(
            df=full_df,
            feature_columns=feature_cols,
            source_datasets=source_datasets or ["NWP", "IMD"],
        )

        # Serialize if output directory provided
        saved_paths: Dict[str, Path] = {}
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Parquet data exports
            train_path = output_dir / "train.parquet"
            val_path = output_dir / "val.parquet"
            test_path = output_dir / "test.parquet"
            full_path = output_dir / "ramp_dataset.parquet"

            train_processed.to_parquet(train_path, index=False)
            val_processed.to_parquet(val_path, index=False)
            test_processed.to_parquet(test_path, index=False)
            full_df.to_parquet(full_path, index=False)

            # Small CSV export for quick human inspection
            csv_sample = output_dir / "inspection_sample.csv"
            full_df.head(100).to_csv(csv_sample, index=False)

            # Metadata JSONs
            version_path = self.version_manager.export_version_json(
                version_manifest, output_dir / "dataset_version.json"
            )
            preprocessor.export_manifest(output_dir / "preprocessing_manifest.json")
            self.diagnostics.export_json(split_stats, output_dir / "dataset_statistics.json")
            feature_registry.export_json(output_dir / "feature_registry.json")

            with open(output_dir / "split_manifest.json", "w", encoding="utf-8") as f:
                json.dump(split_manifest.model_dump(), f, indent=2)

            with open(output_dir / "leakage_report.json", "w", encoding="utf-8") as f:
                json.dump(leakage_report.model_dump(), f, indent=2)

            # Target Schema JSON
            target_schema_dict = {
                "observed_rainfall_mm": "Continuous 24h rainfall (mm)",
                "rainfall_occurrence": f"Binary event (threshold >= {self.target_builder.occurrence_threshold_mm} mm)",
                "heavy_rainfall": f"Binary event (>= {self.target_builder.heavy_threshold_mm} mm)",
                "very_heavy_rainfall": f"Binary event (>= {self.target_builder.very_heavy_threshold_mm} mm)",
                "extremely_heavy_rainfall": f"Binary event (>= {self.target_builder.extremely_heavy_threshold_mm} mm)",
                "rainfall_anomaly": "Observed rainfall minus training climatology",
                "regime_label": "NULL reserved for Phase 4 classifier",
            }
            with open(output_dir / "target_schema.json", "w", encoding="utf-8") as f:
                json.dump(target_schema_dict, f, indent=2)

            # Dataset Card Markdown
            self.version_manager.generate_dataset_card(
                version_manifest=version_manifest,
                split_manifest=split_manifest,
                stats=split_stats,
                output_path=output_dir / "DATASET_CARD.md",
            )

            saved_paths = {
                "train_parquet": train_path,
                "val_parquet": val_path,
                "test_parquet": test_path,
                "dataset_parquet": full_path,
                "dataset_card": output_dir / "DATASET_CARD.md",
            }

        return {
            "version": version_manifest,
            "split_manifest": split_manifest,
            "leakage_report": leakage_report,
            "statistics": split_stats,
            "train_df": train_processed,
            "val_df": val_processed,
            "test_df": test_processed,
            "saved_paths": saved_paths,
        }

    def generate_synthetic_dataset(
        self,
        num_days: int = 20,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Generates realistic synthetic demonstration data for pipeline verification,
        testing, and UI staging.
        
        Explicitly preserved extreme events (e.g. 210mm, 280mm) to verify extreme
        rainfall handling.
        """
        rng = np.random.default_rng(2026080)
        base_init = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)

        # 3x3 sample grid over Central India (monsoon core zone)
        lats = [21.0, 21.25, 21.5]
        lons = [78.0, 78.25, 78.5]
        lead_hours = [24, 48]

        fc_rows = []
        obs_rows = []

        for d in range(num_days):
            init_t = base_init + timedelta(days=d)
            for lead in lead_hours:
                valid_t = init_t + timedelta(hours=lead)
                for lat in lats:
                    for lon in lons:
                        # Base rainfall with Gamma distribution
                        base_rain = float(rng.gamma(shape=0.6, scale=18.0))

                        # Guarantee several heavy and extreme rainfall events
                        if d == 5 and lat == 21.25 and lon == 78.25:
                            base_rain = 75.0  # Heavy (>=64.5mm)
                        elif d == 10 and lat == 21.0 and lon == 78.0:
                            base_rain = 135.0  # Very Heavy (>=115.6mm)
                        elif d == 15 and lat == 21.5 and lon == 78.5:
                            base_rain = 225.0  # Extremely Heavy (>=204.5mm)

                        # Atmospheric predictors
                        u850 = float(rng.normal(8.0, 3.0))
                        v850 = float(rng.normal(2.0, 2.0))
                        mslp = float(rng.normal(100500.0, 400.0))
                        t2m = float(rng.normal(300.0, 2.5))
                        rh = float(np.clip(rng.normal(80.0, 10.0), 30.0, 99.0))
                        pw = float(rng.normal(55.0, 8.0))
                        cape = float(rng.normal(1200.0, 400.0))
                        gh500 = float(rng.normal(5860.0, 30.0))

                        fc_rows.append({
                            "forecast_initialization_time": init_t,
                            "forecast_valid_time": valid_t,
                            "lead_time_hours": lead,
                            "latitude": lat,
                            "longitude": lon,
                            "provider": "SYNTHETIC_GFS",
                            "model": "GFS_FV3",
                            "ensemble_member": None,
                            "raw_nwp_rainfall": max(0.0, round(base_rain + rng.normal(0, 3.0), 2)),
                            "u850": u850,
                            "v850": v850,
                            "mslp": mslp,
                            "temperature": t2m,
                            "relative_humidity": rh,
                            "precipitable_water": pw,
                            "cape": cape,
                            "geopotential_height": gh500,
                        })

                        # Ground truth observation at valid_time
                        obs_rain = max(0.0, round(base_rain, 2))
                        q_flag = "VALID_EXTREME" if obs_rain >= 204.5 else "VALID"

                        obs_rows.append({
                            "target_valid_time": valid_t,
                            "latitude": lat,
                            "longitude": lon,
                            "observed_rainfall_mm": obs_rain,
                            "observation_quality_flag": q_flag,
                            "observation_source": "SYNTHETIC_IMD",
                        })

        fc_df = pd.DataFrame(fc_rows)
        obs_df = pd.DataFrame(obs_rows).drop_duplicates(subset=["target_valid_time", "latitude", "longitude"])

        return self.build_from_dfs(
            forecast_df=fc_df,
            observation_df=obs_df,
            source_datasets=["SYNTHETIC_GFS", "SYNTHETIC_IMD"],
            output_dir=output_dir,
        )
