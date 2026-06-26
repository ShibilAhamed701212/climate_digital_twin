"""Unit tests for pipeline/validate.py."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.validate import (
    detect_duplicates,
    detect_missing_values,
    generate_quality_report,
    save_quality_report,
    validate_columns,
    validate_date_range,
    validate_file_exists,
    validate_lat_lon_bounds,
    validate_value_ranges,
)


class TestValidateFileExists:
    def test_file_exists(self, tmp_path: Path):
        f = tmp_path / "test.nc"
        f.write_text("dummy")
        assert validate_file_exists(f) is True

    def test_file_missing(self, tmp_path: Path):
        assert validate_file_exists(tmp_path / "nonexistent.nc") is False

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.nc"
        f.touch()
        assert validate_file_exists(f) is False


class TestValidateColumns:
    def test_all_columns_present(self):
        df = pd.DataFrame({"Date": [1], "Rainfall": [2]})
        missing = validate_columns(df, ["Date", "Rainfall"], "test")
        assert missing == []

    def test_missing_columns(self):
        df = pd.DataFrame({"Date": [1]})
        missing = validate_columns(df, ["Date", "Rainfall"], "test")
        assert missing == ["Rainfall"]


class TestValidateDateRange:
    def test_dates_in_range(self):
        df = pd.DataFrame({"Date": pd.date_range("2020-06-01", periods=5)})
        assert validate_date_range(df, "2020-01-01", "2020-12-31", "test") is True

    def test_dates_out_of_range(self):
        df = pd.DataFrame({"Date": pd.date_range("2025-01-01", periods=5)})
        assert validate_date_range(df, "2020-01-01", "2020-12-31", "test") is False


class TestValidateLatLonBounds:
    def test_all_valid(self):
        df = pd.DataFrame({"Latitude": [15.0], "Longitude": [76.0]})
        bounds = {"min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.5}
        assert validate_lat_lon_bounds(df, bounds, "test") is True

    def test_invalid_lat(self):
        df = pd.DataFrame({"Latitude": [20.0], "Longitude": [76.0]})
        bounds = {"min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.5}
        assert validate_lat_lon_bounds(df, bounds, "test") is False


class TestValidateValueRanges:
    def test_valid_values(self):
        df = pd.DataFrame({"Rainfall": [10.0], "MaxTemp": [30.0], "MinTemp": [20.0]})
        issues = validate_value_ranges(df, "test")
        assert issues == {}

    def test_negative_rainfall(self):
        df = pd.DataFrame({"Rainfall": [-5.0]})
        issues = validate_value_ranges(df, "test")
        assert issues.get("negative_rainfall", 0) > 0

    def test_max_temp_below_min(self):
        df = pd.DataFrame({"MaxTemp": [15.0], "MinTemp": [25.0]})
        issues = validate_value_ranges(df, "test")
        assert issues.get("max_temp_below_min_temp", 0) > 0


class TestDetectMissingValues:
    def test_no_missing(self):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        assert detect_missing_values(df, "test") == {}

    def test_with_missing(self):
        df = pd.DataFrame({"A": [1, np.nan], "B": [3, 4]})
        result = detect_missing_values(df, "test")
        assert "A" in result
        assert result["A"] == 1


class TestDetectDuplicates:
    def test_no_duplicates(self):
        df = pd.DataFrame({"id": [1, 2], "val": [10, 20]})
        assert detect_duplicates(df, ["id"], "test") == 0

    def test_with_duplicates(self):
        df = pd.DataFrame({"id": [1, 1], "val": [10, 10]})
        assert detect_duplicates(df, ["id", "val"], "test") == 1


class TestQualityReport:
    def test_generate_report(self, tmp_path: Path):
        df = pd.DataFrame({
            "Date": pd.date_range("2020-01-01", periods=3),
            "Latitude": [15.0, 16.0, 17.0],
            "Longitude": [76.0, 77.0, 77.5],
            "Rainfall": [10.0, 20.0, 30.0],
        })
        f = tmp_path / "test_data.parquet"
        df.to_parquet(f)
        config = {
            "date_range": {"start": "2020-01-01", "end": "2020-12-31"},
            "karnataka_bounds": {
                "min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.5,
            },
        }
        report = generate_quality_report({"rainfall": f}, config)
        assert report["summary"]["total_datasets"] == 1
        assert "rainfall" in report["datasets"]

    def test_save_report(self, tmp_path: Path):
        report = {"summary": {"passed": 1, "failed": 0, "total_datasets": 1}, "datasets": {}}
        output = str(tmp_path / "quality_report.json")
        path = save_quality_report(report, output)
        assert Path(path).exists()
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["summary"]["passed"] == 1
