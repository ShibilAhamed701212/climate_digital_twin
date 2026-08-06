"""Tests for models/build_dataset.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture
def mock_open_meteo_response():
    import datetime

    dates = []
    max_temps = []
    min_temps = []
    rains = []
    d = datetime.date(2020, 1, 1)
    for i in range(200):
        dates.append(d.isoformat())
        max_temps.append(27.0 + (i % 10))
        min_temps.append(17.0 + (i % 5))
        rains.append(float(i % 7))
        d += datetime.timedelta(days=1)
    return json.dumps(
        {
            "latitude": 12.97,
            "longitude": 77.59,
            "daily": {
                "time": dates,
                "temperature_2m_max": max_temps,
                "temperature_2m_min": min_temps,
                "precipitation_sum": rains,
            },
        }
    )


class TestBuildDataset:
    def test_engineer_features(self):
        from models.build_dataset import engineer_features

        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2020-01-01", "2020-06-15", "2020-12-25"]),
                "MaxTemp": [28.0, 32.0, 26.0],
                "MinTemp": [18.0, 22.0, 16.0],
                "Rainfall": [0.0, 50.0, 10.0],
            }
        )
        result = engineer_features(df, 12.97, 77.59, "Test")
        assert "Month" in result.columns
        assert "Season" in result.columns
        assert "Monsoon" in result.columns
        assert "RollingRain7" in result.columns
        assert result["Month"].iloc[0] == 1
        assert result["Season"].iloc[0] == "Winter"
        assert result["Season"].iloc[1] == "Monsoon"
        assert result["Monsoon"].iloc[1] == 1

    def test_checksum(self):
        from models.build_dataset import _checksum

        tmp = Path("test_checksum_tmp.txt")
        try:
            tmp.write_text("hello")
            cs = _checksum(tmp)
            assert isinstance(cs, str)
            assert len(cs) == 16
        finally:
            tmp.unlink(missing_ok=True)

    @patch("urllib.request.urlopen")
    def test_build_dataset_integration(
        self, mock_urlopen, tmp_path: Path, mock_open_meteo_response
    ):
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_open_meteo_response.encode()
        mock_urlopen.return_value = mock_resp

        from models.build_dataset import build_dataset, verify_dataset

        manifest = build_dataset(
            lat=12.97,
            lon=77.59,
            name="TestLoc",
            years=1,
            output_dir=str(tmp_path),
        )
        assert manifest["total_records"] == 200
        assert manifest["splits"]["training"]["records"] == 140
        assert manifest["splits"]["testing"]["records"] == 30

        train_csv = tmp_path / "training.csv"
        assert train_csv.exists()
        df = pd.read_csv(train_csv)
        assert len(df) == 140

        assert verify_dataset(str(tmp_path)) is True

    def test_build_dataset_tampered_fails(self, tmp_path: Path):
        manifest = {
            "checksums": {"training.csv": "abc123"},
        }
        (tmp_path / "dataset_manifest.json").write_text(json.dumps(manifest))
        train_csv = tmp_path / "training.csv"
        train_csv.write_text("some data")

        from models.build_dataset import verify_dataset

        assert verify_dataset(str(tmp_path)) is False
