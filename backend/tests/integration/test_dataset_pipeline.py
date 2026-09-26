"""
Integration test for complete end-to-end DatasetBuilder pipeline.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from pathlib import Path
import pytest

from ml.dataset.builder import DatasetBuilder


def test_full_synthetic_dataset_build_pipeline(tmp_path):
    """Executes full end-to-end dataset build and audits generated files."""
    builder = DatasetBuilder(
        dataset_id="ramp_test_v0.3.0",
        version="0.3.0",
        data_mode="SYNTHETIC_DEMO",
        purge_gap_hours=24,
    )

    out_dir = tmp_path / "dataset_out"
    results = builder.generate_synthetic_dataset(num_days=10, output_dir=out_dir)

    # 1. Output components present
    assert "version" in results
    assert "split_manifest" in results
    assert "leakage_report" in results
    assert "statistics" in results
    assert "train_df" in results
    assert "val_df" in results
    assert "test_df" in results

    # 2. Leakage check passed
    assert results["leakage_report"].status == "PASS"

    # 3. Splits populated
    assert results["split_manifest"].train_rows > 0
    assert results["split_manifest"].val_rows > 0
    assert results["split_manifest"].test_rows > 0

    # 4. Parquet and metadata files written
    assert (out_dir / "train.parquet").exists()
    assert (out_dir / "val.parquet").exists()
    assert (out_dir / "test.parquet").exists()
    assert (out_dir / "ramp_dataset.parquet").exists()
    assert (out_dir / "dataset_version.json").exists()
    assert (out_dir / "split_manifest.json").exists()
    assert (out_dir / "preprocessing_manifest.json").exists()
    assert (out_dir / "leakage_report.json").exists()
    assert (out_dir / "dataset_statistics.json").exists()
    assert (out_dir / "feature_registry.json").exists()
    assert (out_dir / "DATASET_CARD.md").exists()

    # 5. Schema verification: regime labels must be None in Phase 3
    train_df = results["train_df"]
    assert "regime_label" in train_df.columns
    assert train_df["regime_label"].isnull().all()
