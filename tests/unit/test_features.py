"""Unit tests for pipeline/features.py."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.features import (
    add_prior_rainfall,
    add_rolling_features,
    add_temporal_features,
    engineer_features,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    records = []
    for lat in [15.0, 16.0]:
        for lon in [76.0, 77.0]:
            for d in dates:
                records.append(
                    {
                        "Date": d,
                        "Latitude": lat,
                        "Longitude": lon,
                        "Rainfall": max(0, rng.exponential(5)),
                        "MaxTemp": rng.uniform(25, 38),
                        "MinTemp": rng.uniform(15, 22),
                    }
                )
    return pd.DataFrame(records)


class TestAddTemporalFeatures:
    def test_adds_all_features(self, sample_df: pd.DataFrame):
        df = add_temporal_features(sample_df.copy())
        for col in ["DayOfYear", "Month", "Week", "Season", "Monsoon"]:
            assert col in df.columns
        assert df["Month"].between(1, 12).all()
        assert df["Monsoon"].isin([0, 1]).all()

    def test_season_mapping(self):
        dates = pd.date_range("2020-06-01", periods=5, freq="D")
        df = pd.DataFrame({"Date": dates, "Latitude": 15.0, "Longitude": 76.0})
        df = add_temporal_features(df)
        june_monsoon = df[df["Month"] == 6]["Season"].iloc[0]
        assert june_monsoon == "Monsoon"

    def test_monsoon_indicator(self):
        dates = pd.date_range("2020-06-01", periods=5, freq="D")
        df = pd.DataFrame({"Date": dates, "Latitude": 15.0, "Longitude": 76.0})
        df = add_temporal_features(df)
        assert df[df["Month"].isin([6, 7, 8, 9])]["Monsoon"].all()
        jan_dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df_jan = pd.DataFrame({"Date": jan_dates, "Latitude": 15.0, "Longitude": 76.0})
        df_jan = add_temporal_features(df_jan)
        assert not df_jan[df_jan["Month"] == 1]["Monsoon"].any()


class TestAddRollingFeatures:
    def test_adds_all_rolling_features(self, sample_df: pd.DataFrame):
        df = add_rolling_features(sample_df.copy())
        for col in ["RollingRain7", "RollingRain30", "RollingTemp7", "RollingTemp30", "TempDiff"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_rolling_values_reasonable(self, sample_df: pd.DataFrame):
        df = add_rolling_features(sample_df.copy())
        assert df["RollingRain7"].notna().all()
        assert df["RollingRain30"].notna().all()
        assert df["RollingTemp7"].notna().all()
        assert df["RollingTemp30"].notna().all()

    def test_temperature_difference(self, sample_df: pd.DataFrame):
        df = add_rolling_features(sample_df.copy())
        assert (df["TempDiff"] >= 0).all()


class TestAddPriorRainfall:
    def test_adds_prior_rainfall_features(self, sample_df: pd.DataFrame):
        df = add_prior_rainfall(sample_df.copy())
        for col in ["PriorRain7", "PriorRain30"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_prior_values_filled(self, sample_df: pd.DataFrame):
        df = add_prior_rainfall(sample_df.copy())
        assert df["PriorRain7"].notna().all()
        assert df["PriorRain30"].notna().all()


class TestEngineerFeatures:
    def test_full_feature_pipeline(self, sample_df: pd.DataFrame, tmp_path: Path):
        out_path = tmp_path / "features.parquet"
        df = engineer_features(sample_df.copy(), output_path=out_path)
        assert out_path.exists()
        assert len(df) == len(sample_df)

    def test_output_contains_required_columns(self, sample_df: pd.DataFrame):
        df = engineer_features(sample_df.copy())
        expected = [
            "DayOfYear",
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
            "PriorRain7",
            "PriorRain30",
        ]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"
