"""Integration tests for the full Phase 2 data pipeline.

Tests end-to-end pipeline execution on synthetic data.
Generates sample data, runs all pipeline stages, and verifies outputs.
"""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from pipeline.clean import clean_dataset, merge_datasets
from pipeline.download import DataDownloader
from pipeline.export import export_datasets
from pipeline.features import engineer_features
from pipeline.validate import generate_quality_report, save_quality_report


@pytest.fixture
def pipeline_config(tmp_path: Path) -> Path:
    """Create a temporary pipeline configuration for integration testing."""
    config = {
        "data": {
            "raw_dir": str(tmp_path / "raw"),
            "interim_dir": str(tmp_path / "interim"),
            "processed_dir": str(tmp_path / "processed"),
            "external_dir": str(tmp_path / "external"),
            "metadata_dir": str(tmp_path / "metadata"),
            "log_dir": str(tmp_path / "logs"),
        },
        "datasets": {
            "rainfall": {
                "url": "https://example.com/rainfall.nc",
                "resolution": "0.25x0.25",
                "filename": "imd_rainfall.nc",
            },
            "max_temp": {
                "url": "https://example.com/maxtemp.nc",
                "resolution": "1x1",
                "filename": "imd_maxtemp.nc",
            },
            "min_temp": {
                "url": "https://example.com/mintemp.nc",
                "resolution": "1x1",
                "filename": "imd_mintemp.nc",
            },
        },
        "date_range": {"start": "2020-01-01", "end": "2020-12-31"},
        "karnataka_bounds": {
            "min_lat": 11.5,
            "max_lat": 18.5,
            "min_lon": 74.0,
            "max_lon": 78.5,
        },
        "pipeline": {
            "train_split": 0.70,
            "val_split": 0.15,
            "test_split": 0.15,
            "sequence_length": 30,
            "batch_size": 64,
            "random_seed": 42,
        },
    }
    config_path = tmp_path / "data_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    return config_path


class TestFullPipeline:
    """End-to-end pipeline integration tests."""

    def test_download_step(self, pipeline_config: Path):
        downloader = DataDownloader(str(pipeline_config))
        results = downloader.download_all()
        assert len(results) == 3
        for key, path in results.items():
            assert path.exists(), f"{key} not at {path}"
            assert path.stat().st_size > 0, f"{key} is empty"

    def test_merge_datasets(self, pipeline_config: Path):
        downloader = DataDownloader(str(pipeline_config))
        results = downloader.download_all()
        rainfall = pd.read_parquet(results["rainfall"])
        max_temp = pd.read_parquet(results["max_temp"])
        min_temp = pd.read_parquet(results["min_temp"])
        merged = merge_datasets(rainfall, max_temp, min_temp)
        assert len(merged) > 0
        assert "Rainfall" in merged.columns
        assert "MaxTemp" in merged.columns
        assert "MinTemp" in merged.columns

    def test_clean_step(self, pipeline_config: Path):
        downloader = DataDownloader(str(pipeline_config))
        results = downloader.download_all()
        rainfall = pd.read_parquet(results["rainfall"])
        max_temp = pd.read_parquet(results["max_temp"])
        min_temp = pd.read_parquet(results["min_temp"])
        merged = merge_datasets(rainfall, max_temp, min_temp)
        with open(pipeline_config) as f:
            config = yaml.safe_load(f)
        bounds = config["karnataka_bounds"]
        cleaned = clean_dataset(merged, bounds)
        assert len(cleaned) > 0
        assert cleaned.isnull().sum().sum() == 0

    def test_feature_engineering_step(self, pipeline_config: Path):
        downloader = DataDownloader(str(pipeline_config))
        results = downloader.download_all()
        rainfall = pd.read_parquet(results["rainfall"])
        max_temp = pd.read_parquet(results["max_temp"])
        min_temp = pd.read_parquet(results["min_temp"])
        with open(pipeline_config) as f:
            config = yaml.safe_load(f)
        merged = merge_datasets(rainfall, max_temp, min_temp)
        bounds = config["karnataka_bounds"]
        cleaned = clean_dataset(merged, bounds)
        featured = engineer_features(cleaned)
        required = [
            "Month",
            "Week",
            "Season",
            "Monsoon",
            "RollingRain7",
            "RollingRain30",
            "RollingTemp7",
            "RollingTemp30",
            "TempDiff",
            "RainfallTrend",
        ]
        for col in required:
            assert col in featured.columns, f"Missing feature column: {col}"

    def test_export_step(self, pipeline_config: Path, tmp_path: Path):
        downloader = DataDownloader(str(pipeline_config))
        results = downloader.download_all()
        rainfall = pd.read_parquet(results["rainfall"])
        max_temp = pd.read_parquet(results["max_temp"])
        min_temp = pd.read_parquet(results["min_temp"])
        with open(pipeline_config) as f:
            config = yaml.safe_load(f)
        merged = merge_datasets(rainfall, max_temp, min_temp)
        bounds = config["karnataka_bounds"]
        cleaned = clean_dataset(merged, bounds)
        featured = engineer_features(cleaned)
        exported = export_datasets(featured, config, output_dir=tmp_path / "processed")
        assert "training" in exported
        assert "validation" in exported
        assert "testing" in exported
        train_df = pd.read_csv(exported["training"])
        assert "RollingRain7" in train_df.columns
        assert len(train_df) > 0

    def test_quality_report_generation(self, pipeline_config: Path, tmp_path: Path):
        downloader = DataDownloader(str(pipeline_config))
        results = downloader.download_all()
        with open(pipeline_config) as f:
            config = yaml.safe_load(f)
        report = generate_quality_report(results, config)
        report_path = tmp_path / "quality_report.json"
        save_quality_report(report, str(report_path))
        assert report_path.exists()
        with open(report_path) as f:
            loaded = json.load(f)
        assert "datasets" in loaded
        assert loaded["summary"]["total_datasets"] == 3

    def test_full_pipeline_end_to_end(self, pipeline_config: Path, tmp_path: Path):
        """Run the complete pipeline from download through export."""
        downloader = DataDownloader(str(pipeline_config))
        dataset_files = downloader.download_all()
        with open(pipeline_config) as f:
            config = yaml.safe_load(f)
        report = generate_quality_report(dataset_files, config)
        save_quality_report(report, str(tmp_path / "quality_report.json"))
        rainfall = pd.read_parquet(dataset_files["rainfall"])
        max_temp = pd.read_parquet(dataset_files["max_temp"])
        min_temp = pd.read_parquet(dataset_files["min_temp"])
        merged = merge_datasets(rainfall, max_temp, min_temp)
        bounds = config["karnataka_bounds"]
        interim_path = tmp_path / "interim" / "cleaned.parquet"
        cleaned = clean_dataset(merged, bounds, output_path=interim_path)
        assert interim_path.exists()
        featured = engineer_features(cleaned)
        processed_dir = tmp_path / "processed"
        exported = export_datasets(featured, config, output_dir=processed_dir)
        for split_name in ["training", "validation", "testing"]:
            assert split_name in exported
            csv_path = Path(exported[split_name])
            assert csv_path.exists()
            df = pd.read_csv(csv_path)
            assert len(df) > 0, f"{split_name} split is empty"
