"""
Unit tests for DatasetVersionManager, hashing, and DATASET_CARD generation.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timezone
import pandas as pd
import pytest

from ml.dataset.versioning import DatasetVersionManager
from ml.schemas import SplitManifest, SplitStatistics


def test_versioning_manifest_and_card(tmp_path):
    """Verify version manifest creation and DATASET_CARD markdown generation."""
    vm = DatasetVersionManager(dataset_id="ramp_dataset_v0.3.0", version="0.3.0", data_mode="SYNTHETIC_DEMO")

    df = pd.DataFrame({
        "forecast_valid_time": [datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)],
        "latitude": [20.0],
        "longitude": [78.0],
    })

    v_manifest = vm.create_version_manifest(df, feature_columns=["raw_nwp_rainfall", "u850"], source_datasets=["GFS"])
    assert v_manifest.version == "0.3.0"
    assert v_manifest.row_count == 1
    assert v_manifest.feature_count == 2
    assert v_manifest.target_count == 6

    # Test export
    v_file = tmp_path / "dataset_version.json"
    vm.export_version_json(v_manifest, v_file)
    assert v_file.exists()

    # Test card generation
    split_manifest = SplitManifest(
        split_type="chronological",
        train_rows=100,
        val_rows=20,
        test_rows=20,
        purge_gap_hours=24,
    )
    stats = {
        "TRAIN": SplitStatistics(split_name="TRAIN", row_count=100, rainfall_mean=12.0),
    }
    card_path = tmp_path / "DATASET_CARD.md"
    vm.generate_dataset_card(v_manifest, split_manifest, stats, card_path)
    assert card_path.exists()
    content = card_path.read_text(encoding="utf-8")
    assert "RAMP Dataset Card: ramp_dataset_v0.3.0" in content
    assert "SYNTHETIC_DEMO" in content
