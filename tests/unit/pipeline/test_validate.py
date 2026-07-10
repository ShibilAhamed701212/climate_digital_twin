from __future__ import annotations

import json

import pandas as pd
import pytest
import yaml

from pipeline.validate import (
    detect_duplicates,
    detect_missing_values,
    generate_quality_report,
    load_config,
    save_quality_report,
    validate_columns,
    validate_date_range,
    validate_file_exists,
    validate_lat_lon_bounds,
    validate_value_ranges,
)


class TestLoadConfig:
    def test_loads_yaml(self, tmp_path):
        cfg = {"key": "value", "nested": {"a": 1}}
        p = tmp_path / "config.yaml"
        with open(p, "w") as f:
            yaml.dump(cfg, f)
        assert load_config(str(p)) == cfg

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")


class TestValidateFileExists:
    def test_file_exists_and_nonempty(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("a,b,c\n1,2,3")
        assert validate_file_exists(p) is True

    def test_file_not_exists(self, tmp_path):
        assert validate_file_exists(tmp_path / "missing.csv") is False

    def test_file_empty(self, tmp_path):
        p = tmp_path / "empty.csv"
        p.write_text("")
        assert validate_file_exists(p) is False


class TestValidateColumns:
    def test_all_present(self):
        df = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        assert validate_columns(df, ["A", "B"], "test") == []

    def test_some_missing(self):
        df = pd.DataFrame({"A": [1]})
        assert validate_columns(df, ["A", "B", "C"], "test") == ["B", "C"]

    def test_empty_expected(self):
        df = pd.DataFrame({"A": [1]})
        assert validate_columns(df, [], "test") == []


class TestValidateDateRange:
    def test_all_within_range(self):
        df = pd.DataFrame({"Date": ["2024-01-01", "2024-06-15", "2024-12-31"]})
        assert validate_date_range(df, "2024-01-01", "2024-12-31", "test") is True

    def test_some_outside_range(self):
        df = pd.DataFrame({"Date": ["2023-12-31", "2024-06-15", "2025-01-01"]})
        assert validate_date_range(df, "2024-01-01", "2024-12-31", "test") is False

    def test_missing_date_column(self):
        df = pd.DataFrame({"A": [1]})
        assert validate_date_range(df, "2024-01-01", "2024-12-31", "test") is False

    def test_empty_dataframe(self):
        df = pd.DataFrame({"Date": []})
        assert validate_date_range(df, "2024-01-01", "2024-12-31", "test") is True


class TestValidateLatLonBounds:
    def test_all_within_bounds(self):
        df = pd.DataFrame({"Latitude": [15.0, 16.0], "Longitude": [75.0, 76.0]})
        bounds = {"min_lat": 10.0, "max_lat": 20.0, "min_lon": 70.0, "max_lon": 80.0}
        assert validate_lat_lon_bounds(df, bounds, "test") is True

    def test_some_outside_bounds(self):
        df = pd.DataFrame({"Latitude": [5.0, 15.0], "Longitude": [75.0, 76.0]})
        bounds = {"min_lat": 10.0, "max_lat": 20.0, "min_lon": 70.0, "max_lon": 80.0}
        assert validate_lat_lon_bounds(df, bounds, "test") is False


class TestValidateValueRanges:
    def test_no_issues(self):
        df = pd.DataFrame({"Rainfall": [10.0], "MaxTemp": [30.0], "MinTemp": [20.0]})
        assert validate_value_ranges(df, "test") == {}

    def test_negative_rainfall(self):
        df = pd.DataFrame({"Rainfall": [-1.0]})
        assert validate_value_ranges(df, "test") == {"negative_rainfall": 1}

    def test_max_temp_above_50(self):
        df = pd.DataFrame({"MaxTemp": [55.0]})
        result = validate_value_ranges(df, "test")
        assert result.get("max_temp_above_50") == 1

    def test_min_temp_below_neg5(self):
        df = pd.DataFrame({"MinTemp": [-10.0]})
        result = validate_value_ranges(df, "test")
        assert result.get("min_temp_below_-5") == 1

    def test_max_temp_below_min_temp(self):
        df = pd.DataFrame({"MaxTemp": [15.0], "MinTemp": [25.0]})
        result = validate_value_ranges(df, "test")
        assert result.get("max_temp_below_min_temp") == 1


class TestDetectMissingValues:
    def test_no_missing(self):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        assert detect_missing_values(df, "test") == {}

    def test_some_missing(self):
        df = pd.DataFrame({"A": [1, None], "B": [3, 4]})
        assert detect_missing_values(df, "test") == {"A": 1}

    def test_all_missing(self):
        df = pd.DataFrame({"A": [None, None], "B": [1, 2]})
        assert detect_missing_values(df, "test") == {"A": 2}


class TestDetectDuplicates:
    def test_no_duplicates(self):
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        assert detect_duplicates(df, ["A"], "test") == 0

    def test_has_duplicates(self):
        df = pd.DataFrame({"A": [1, 1, 2], "B": [4, 5, 6]})
        assert detect_duplicates(df, ["A"], "test") == 1


class TestGenerateQualityReport:
    def test_all_pass(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text(
            "Date,Latitude,Longitude,Rainfall\n2024-06-01,15.0,75.0,10.0\n2024-06-02,16.0,76.0,20.0\n"
        )
        dataset_files = {"rainfall": csv_file}
        config = {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "karnataka_bounds": {
                "min_lat": 10.0,
                "max_lat": 20.0,
                "min_lon": 70.0,
                "max_lon": 80.0,
            },
        }
        report = generate_quality_report(dataset_files, config)
        assert report["datasets"]["rainfall"]["passed"] is True
        assert report["summary"]["passed"] == 1

    def test_file_not_exists(self, tmp_path):
        dataset_files = {"rainfall": tmp_path / "nonexistent.csv"}
        config = {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "karnataka_bounds": {
                "min_lat": 10.0,
                "max_lat": 20.0,
                "min_lon": 70.0,
                "max_lon": 80.0,
            },
        }
        report = generate_quality_report(dataset_files, config)
        assert report["summary"]["failed"] == 1
        assert report["datasets"]["rainfall"]["checks"]["file_exists"] is False

    def test_binary_file_skips_validation(self, tmp_path):
        bin_file = tmp_path / "data.bin"
        bin_file.write_bytes(b"\x00\x01\x02")
        dataset_files = {"rainfall": bin_file}
        config = {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "karnataka_bounds": {
                "min_lat": 10.0,
                "max_lat": 20.0,
                "min_lon": 70.0,
                "max_lon": 80.0,
            },
        }
        report = generate_quality_report(dataset_files, config)
        assert report["summary"]["passed"] == 1
        assert report["datasets"]["rainfall"]["note"] == "Binary file, skipping column validation"

    def test_read_error(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b"\x00\x01\x02\xff")
        dataset_files = {"rainfall": csv_file}
        config = {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "karnataka_bounds": {
                "min_lat": 10.0,
                "max_lat": 20.0,
                "min_lon": 70.0,
                "max_lon": 80.0,
            },
        }
        report = generate_quality_report(dataset_files, config)
        assert "read_error" in report["datasets"]["rainfall"]
        assert report["summary"]["failed"] == 1

    def test_parquet_file(self, tmp_path):
        df = pd.DataFrame(
            {"Date": ["2024-06-01"], "Latitude": [15.0], "Longitude": [75.0], "Rainfall": [10.0]}
        )
        pq_file = tmp_path / "data.parquet"
        df.to_parquet(pq_file, index=False)
        dataset_files = {"rainfall": pq_file}
        config = {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "karnataka_bounds": {
                "min_lat": 10.0,
                "max_lat": 20.0,
                "min_lon": 70.0,
                "max_lon": 80.0,
            },
        }
        report = generate_quality_report(dataset_files, config)
        assert report["datasets"]["rainfall"]["passed"] is True
        assert report["summary"]["passed"] == 1

    def test_check_failure_reports_failed(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Date,Latitude,Longitude,Rainfall\n2024-06-01,5.0,75.0,10.0\n")
        dataset_files = {"rainfall": csv_file}
        config = {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "karnataka_bounds": {
                "min_lat": 10.0,
                "max_lat": 20.0,
                "min_lon": 70.0,
                "max_lon": 80.0,
            },
        }
        report = generate_quality_report(dataset_files, config)
        assert report["datasets"]["rainfall"]["passed"] is False
        assert report["summary"]["failed"] == 1


class TestSaveQualityReport:
    def test_saves_json(self, tmp_path):
        report = {"key": "value", "nested": [1, 2, 3]}
        output = tmp_path / "report.json"
        result = save_quality_report(report, str(output))
        assert result == str(output)
        with open(output) as f:
            assert json.load(f) == report

    def test_creates_parent_directories(self, tmp_path):
        report = {"a": 1}
        output = tmp_path / "sub" / "nested" / "report.json"
        result = save_quality_report(report, str(output))
        assert result == str(output)
        assert output.exists()
