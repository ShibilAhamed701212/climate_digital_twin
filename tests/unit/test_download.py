"""Unit tests for pipeline/download.py."""

from pathlib import Path

import pytest
import yaml

from pipeline.download import DataDownloader


@pytest.fixture
def downloader(tmp_path: Path) -> DataDownloader:
    """Create a DataDownloader with temporary config."""
    config = {
        "data": {"raw_dir": str(tmp_path / "raw")},
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
        "date_range": {"start": "2020-01-01", "end": "2020-01-10"},
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
    return DataDownloader(str(config_path))


class TestDataDownloader:
    def test_generate_grid(self, downloader: DataDownloader):
        bounds = downloader.config["karnataka_bounds"]
        grid = downloader._generate_grid(1.0, bounds)
        assert len(grid) > 0
        assert "Latitude" in grid.columns
        assert "Longitude" in grid.columns

    def test_generate_synthetic_rainfall(self, downloader: DataDownloader):
        bounds = downloader.config["karnataka_bounds"]
        grid = downloader._generate_grid(1.0, bounds)
        df = downloader._generate_synthetic_rainfall(
            downloader.start_date, downloader.end_date, grid
        )
        assert len(df) > 0
        assert "Rainfall" in df.columns
        assert (df["Rainfall"] >= 0).all()

    def test_generate_synthetic_temperature(self, downloader: DataDownloader):
        bounds = downloader.config["karnataka_bounds"]
        grid = downloader._generate_grid(1.0, bounds)
        df_max = downloader._generate_synthetic_temperature(
            downloader.start_date, downloader.end_date, grid, is_max=True
        )
        df_min = downloader._generate_synthetic_temperature(
            downloader.start_date, downloader.end_date, grid, is_max=False
        )
        assert "MaxTemp" in df_max.columns or "MinTemp" in df_min.columns
        assert df_max["MaxTemp"].mean() > df_min["MinTemp"].mean()

    def test_download_dataset_synthetic_fallback(self, downloader: DataDownloader):
        path = downloader.download_dataset("rainfall")
        assert path.exists()
        assert path.stat().st_size > 0

    def test_download_all_datasets(self, downloader: DataDownloader):
        results = downloader.download_all()
        assert len(results) == 3
        for key, path in results.items():
            assert path.exists(), f"{key} not found at {path}"

    def test_verify_checksum(self, downloader: DataDownloader):
        path = downloader.download_dataset("rainfall")
        result = downloader.verify_checksum(path)
        assert result is True
