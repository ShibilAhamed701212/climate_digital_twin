"""Unit tests for pipeline/download.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
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


@pytest.fixture
def nasa_power_downloader(tmp_path: Path) -> DataDownloader:
    """Create a DataDownloader with NASA POWER source config."""
    config = {
        "data": {"raw_dir": str(tmp_path / "raw")},
        "sources": {
            "primary": "nasa_power",
            "nasa_power": {
                "endpoint": "https://example.com/api",
                "community": "AG",
                "format": "JSON",
                "max_workers": 4,
                "parameters": {
                    "rainfall": "PRECTOTCORR",
                    "max_temp": "T2M_MAX",
                    "min_temp": "T2M_MIN",
                },
            },
        },
        "datasets": {
            "rainfall": {"filename": "rainfall.parquet"},
            "max_temp": {"filename": "maxtemp.parquet"},
            "min_temp": {"filename": "mintemp.parquet"},
        },
        "date_range": {"start": "2020-01-01", "end": "2020-01-10"},
        "karnataka_bounds": {
            "min_lat": 11.5,
            "max_lat": 18.5,
            "min_lon": 74.0,
            "max_lon": 78.5,
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

    def test_download_dataset_already_exists(self, downloader: DataDownloader):
        ds_config = downloader.config["datasets"]["rainfall"]
        parquet_path = downloader.raw_dir / ds_config["filename"]
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        parquet_path.write_text("existing data")
        path = downloader.download_dataset("rainfall")
        assert path == parquet_path
        assert path.read_text() == "existing data"

    def test_download_dataset_unknown_key(self, tmp_path: Path):
        config = {
            "data": {"raw_dir": str(tmp_path / "raw")},
            "datasets": {
                "rainfall": {"filename": "rainfall.parquet"},
                "custom": {"filename": "custom.parquet"},
            },
            "date_range": {"start": "2020-01-01", "end": "2020-01-10"},
            "karnataka_bounds": {
                "min_lat": 11.5,
                "max_lat": 18.5,
                "min_lon": 74.0,
                "max_lon": 78.5,
            },
        }
        config_path = tmp_path / "custom_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        dl = DataDownloader(str(config_path))
        with pytest.raises(ValueError, match="Unknown dataset key"):
            dl.download_dataset("custom")

    def test_verify_checksum_file_not_found(self, downloader: DataDownloader):
        result = downloader.verify_checksum(Path("/nonexistent/file"))
        assert result is False

    def test_verify_checksum_mismatch(self, downloader: DataDownloader):
        path = downloader.download_dataset("rainfall")
        result = downloader.verify_checksum(path, expected_hash="0" * 64)
        assert result is False

    def test_verify_checksum_with_hash_match(self, downloader: DataDownloader):
        path = downloader.download_dataset("rainfall")
        data = path.read_bytes()
        import hashlib

        expected = hashlib.sha256(data).hexdigest()
        assert downloader.verify_checksum(path, expected_hash=expected) is True


class TestTryDownload:
    def test_successful_download(self, downloader: DataDownloader, tmp_path: Path):
        filepath = tmp_path / "test.nc"
        with patch("pipeline.download.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.iter_content.return_value = [b"hello"]
            mock_get.return_value = mock_resp
            result = downloader._try_download("https://example.com/file", filepath)
        assert result is True
        assert filepath.read_bytes() == b"hello"

    def test_resume_download(self, downloader: DataDownloader, tmp_path: Path):
        filepath = tmp_path / "test.nc"
        filepath.write_bytes(b"partial")
        with patch("pipeline.download.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 206
            mock_resp.iter_content.return_value = [b"_continued"]
            mock_get.return_value = mock_resp
            result = downloader._try_download("https://example.com/file", filepath)
        assert result is True
        assert filepath.read_bytes() == b"partial_continued"

    def test_http_error(self, downloader: DataDownloader, tmp_path: Path):
        filepath = tmp_path / "test.nc"
        with patch("pipeline.download.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp
            result = downloader._try_download("https://example.com/file", filepath)
        assert result is False

    def test_request_exception(self, downloader: DataDownloader, tmp_path: Path):
        filepath = tmp_path / "test.nc"
        with patch("pipeline.download.requests.get") as mock_get:
            mock_get.side_effect = __import__("requests").RequestException("timeout")
            result = downloader._try_download("https://example.com/file", filepath)
        assert result is False


class TestIsHtmlFile:
    def test_doctype_html(self, downloader: DataDownloader, tmp_path: Path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"<!doctype html><html>...")
        assert downloader._is_html_file(f) is True

    def test_html_tag(self, downloader: DataDownloader, tmp_path: Path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"<html><body>Error</body></html>")
        assert downloader._is_html_file(f) is True

    def test_binary_data(self, downloader: DataDownloader, tmp_path: Path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"\x00\x01\x02\x03\x04")
        assert downloader._is_html_file(f) is False

    def test_os_error(self, downloader: DataDownloader):
        f = Path("/nonexistent/file")
        assert downloader._is_html_file(f) is False


class TestNasaPower:
    def test_nasa_power_success(self, nasa_power_downloader: DataDownloader):
        mock_df = pd.DataFrame({"Rainfall": [1.0]})
        with patch(
            "pipeline.sources.nasa_power.fetch_nasa_power_grid",
            return_value={"rainfall": mock_df},
        ):
            result = nasa_power_downloader.download_dataset("rainfall")
        assert result.exists()
        assert result.stat().st_size > 0

    def test_nasa_power_fallback_on_exception(self, nasa_power_downloader: DataDownloader):
        with patch(
            "pipeline.sources.nasa_power.fetch_nasa_power_grid",
            side_effect=RuntimeError("API down"),
        ):
            result = nasa_power_downloader.download_dataset("rainfall")
        assert result.exists()
        assert result.stat().st_size > 0

    def test_nasa_power_key_not_found_fallback(self, nasa_power_downloader: DataDownloader):
        with patch(
            "pipeline.sources.nasa_power.fetch_nasa_power_grid",
            return_value={"other_key": pd.DataFrame()},
        ):
            result = nasa_power_downloader.download_dataset("rainfall")
        assert result.exists()
        assert result.stat().st_size > 0

    def test_nasa_power_caches(self, nasa_power_downloader: DataDownloader):
        mock_df = pd.DataFrame({"Rainfall": [1.0]})
        with patch(
            "pipeline.sources.nasa_power.fetch_nasa_power_grid",
            return_value={"rainfall": mock_df, "max_temp": pd.DataFrame({"MaxTemp": [1.0]})},
        ) as mock_fetch:
            nasa_power_downloader.download_dataset("rainfall")
            nasa_power_downloader.download_dataset("max_temp")
            assert mock_fetch.call_count == 1
