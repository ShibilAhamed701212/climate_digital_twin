"""Unit tests for pipeline/clean.py."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.clean import (
    clean_dataset,
    clip_outliers,
    correct_coordinates,
    handle_missing_values,
    merge_datasets,
    normalize_date_format,
    remove_duplicates,
    standardize_units,
)


class TestRemoveDuplicates:
    def test_no_duplicates(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = remove_duplicates(df)
        assert len(result) == 3

    def test_with_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [4, 4, 5]})
        result = remove_duplicates(df)
        assert len(result) == 2


class TestHandleMissingValues:
    def test_no_missing(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        result = handle_missing_values(df)
        assert result.isnull().sum().sum() == 0

    def test_interpolates_missing(self):
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        result = handle_missing_values(df)
        assert result.isnull().sum().sum() == 0
        assert result["a"].iloc[1] == pytest.approx(2.0, abs=0.5)


class TestClipOutliers:
    def test_clips_extreme_values(self):
        df = pd.DataFrame({"val": list(range(100)) + [1000]})
        result = clip_outliers(df, "val", 0.05, 0.95)
        assert result["val"].max() < 1000


class TestCorrectCoordinates:
    def test_removes_invalid(self):
        df = pd.DataFrame({
            "Latitude": [15.0, 25.0, 16.0],
            "Longitude": [76.0, 77.0, 80.0],
        })
        bounds = {"min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.5}
        result = correct_coordinates(df, bounds)
        assert len(result) == 1


class TestNormalizeDateFormat:
    def test_normalizes_dates(self):
        df = pd.DataFrame({"Date": ["2020-01-01", "2020-01-02"]})
        result = normalize_date_format(df)
        assert pd.api.types.is_datetime64_any_dtype(result["Date"])

    def test_drops_invalid_dates(self):
        df = pd.DataFrame({"Date": ["2020-01-01", "not-a-date", "2020-01-03"]})
        result = normalize_date_format(df)
        assert len(result) == 2


class TestStandardizeUnits:
    def test_standardizes_rainfall(self):
        df = pd.DataFrame({"Rainfall": [-5.0, 10.0, "15.0"]})
        result = standardize_units(df)
        assert result["Rainfall"].iloc[0] == 0.0
        assert result["Rainfall"].iloc[2] == 15.0

    def test_standardizes_temperature(self):
        df = pd.DataFrame({"MaxTemp": ["30.5", 28.0]})
        result = standardize_units(df)
        assert result["MaxTemp"].iloc[0] == 30.5


class TestMergeDatasets:
    def test_merges_on_date_lat_lon(self):
        rainfall = pd.DataFrame({
            "Date": pd.date_range("2020-01-01", periods=2),
            "Latitude": [15.0, 16.0],
            "Longitude": [76.0, 77.0],
            "Rainfall": [10.0, 20.0],
        })
        max_temp = pd.DataFrame({
            "Date": pd.date_range("2020-01-01", periods=2),
            "Latitude": [15.0, 16.0],
            "Longitude": [76.0, 77.0],
            "MaxTemp": [30.0, 32.0],
        })
        min_temp = pd.DataFrame({
            "Date": pd.date_range("2020-01-01", periods=2),
            "Latitude": [15.0, 16.0],
            "Longitude": [76.0, 77.0],
            "MinTemp": [20.0, 22.0],
        })
        result = merge_datasets(rainfall, max_temp, min_temp)
        assert "Rainfall" in result.columns
        assert "MaxTemp" in result.columns
        assert "MinTemp" in result.columns
        assert len(result) == 2


class TestCleanDataset:
    def test_full_cleaning_pipeline(self, tmp_path: Path):
        df = pd.DataFrame({
            "Date": ["2020-01-01", "2020-01-02", "2020-01-01"],
            "Latitude": [15.0, 16.0, 15.0],
            "Longitude": [76.0, 77.0, 76.0],
            "Rainfall": [10.0, np.nan, 10.0],
            "MaxTemp": [30.0, 32.0, 30.0],
            "MinTemp": [20.0, 21.0, 20.0],
        })
        bounds = {"min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.5}
        out_path = tmp_path / "cleaned.parquet"
        result = clean_dataset(df, bounds, output_path=out_path)
        assert out_path.exists()
        assert result.isnull().sum().sum() == 0
        assert len(result) == 2  # one duplicate removed
