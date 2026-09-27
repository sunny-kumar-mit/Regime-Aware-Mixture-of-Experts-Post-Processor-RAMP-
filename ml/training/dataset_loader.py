"""
RAMP Training Dataset Loader & Partition Extractor
SIH26080 | MoES / NCMRWF

Loads paired training datasets, validates schemas, and partitions into
X (18 approved predictors) and y (observed rainfall + thresholds).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np

from ml.datasets.real.pipeline import RealDatasetPipeline
from ml.training.config import DATASET_DIR
from ml.training.feature_contract import FEATURE_NAMES, FeatureContractValidator
from ml.training.target_contract import TARGET_COLUMNS, TargetContractValidator


class TrainingDatasetLoader:
    """Loads and validates datasets for production training and smoke-testing."""

    def __init__(self, dataset_dir: Optional[Path] = None) -> None:
        self.dataset_dir = Path(dataset_dir) if dataset_dir else DATASET_DIR

    def load_partitions(
        self,
        use_fixture_if_empty: bool = False,
        fixture_sample_count: int = 150,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Loads train, val, and test DataFrames.
        If real archives are unmounted and use_fixture_if_empty is True,
        generates synthetic test fixture partitions for pipeline smoke-testing.
        """
        train_p = self.dataset_dir / "train.parquet"
        val_p = self.dataset_dir / "val.parquet"
        test_p = self.dataset_dir / "test.parquet"

        if train_p.exists() and val_p.exists() and test_p.exists():
            train_df = pd.read_parquet(train_p)
            val_df = pd.read_parquet(val_p)
            test_df = pd.read_parquet(test_p)
            data_mode = "REAL_OPERATIONAL" if "NCMRWF" in train_df.get("source_provider", pd.Series([""]))[0] else "SYNTHETIC_DEMO"
        elif use_fixture_if_empty:
            # Generate deterministic fixture partitions strictly for testing
            pipe = RealDatasetPipeline()
            records = pipe._generate_test_fixture_records(sample_count=fixture_sample_count)
            df = pd.DataFrame([r.to_dict() for r in records])
            splits, _ = pipe._split_chronological(df)
            train_df = splits["train"]
            val_df = splits["val"]
            test_df = splits["test"]
            data_mode = "SYNTHETIC_DEMO"
        else:
            raise FileNotFoundError(
                f"Parquet partitions not found in {self.dataset_dir}. Real data archives unmounted."
            )

        # Validate feature and target contracts
        feat_val = FeatureContractValidator.validate_features(train_df[FEATURE_NAMES])
        targ_val = TargetContractValidator.validate_targets(train_df)

        if not feat_val["is_valid"]:
            raise ValueError(f"Feature contract validation failed: {feat_val}")
        if not targ_val["is_valid"]:
            raise ValueError(f"Target contract validation failed: {targ_val}")

        meta = {
            "data_mode": data_mode,
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "feature_validation": feat_val,
            "target_validation": targ_val,
        }

        return train_df, val_df, test_df, meta

    @staticmethod
    def extract_xy(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Extracts X (18 predictors) and y (targets) with strict leakage guard."""
        X = df[FEATURE_NAMES].copy()
        y = df[TARGET_COLUMNS].copy()
        return X, y

    def load_splits(self, use_synthetic_if_missing: bool = True) -> Dict[str, Tuple[pd.DataFrame, pd.Series]]:
        """Convenience method returning (X, y) tuple for each split."""
        train_df, val_df, test_df, meta = self.load_partitions(use_fixture_if_empty=use_synthetic_if_missing)
        X_train, y_train = self.extract_xy(train_df)
        X_val, y_val = self.extract_xy(val_df)
        X_test, y_test = self.extract_xy(test_df)
        return {
            "train": (X_train, y_train["observed_rainfall_mm"]),
            "val": (X_val, y_val["observed_rainfall_mm"]),
            "test": (X_test, y_test["observed_rainfall_mm"]),
            "meta": meta,
        }


DatasetLoader = TrainingDatasetLoader
