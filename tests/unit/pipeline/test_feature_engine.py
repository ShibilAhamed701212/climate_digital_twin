"""Tests for pipeline FeatureEngine and window_features."""

import numpy as np
import pandas as pd
import pytest

from pipeline.feature_engine import FeatureEngine, FeatureMetadata
from pipeline.functions.window_features import (
    compute_all_window_features,
    compute_lag_features,
    compute_rolling_features,
    compute_seasonal_features,
)

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def sample_df():
    rng = np.random.default_rng(42)
    n = 100
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=n, freq="h"),
            "temperature_2m": 20 + rng.normal(0, 5, n).cumsum() * 0.1,
            "precipitation_mm": np.maximum(0, rng.exponential(2, n)),
            "humidity_pct": 50 + rng.normal(0, 10, n),
            "latitude": [15.0] * n,
            "longitude": [75.0] * n,
        }
    )


@pytest.fixture
def sample_canonical_df():
    rng = np.random.default_rng(42)
    n = 100
    return pd.DataFrame(
        {
            "Date": pd.date_range("2020-01-01", periods=n, freq="h"),
            "MaxTemp": 30 + rng.normal(0, 3, n),
            "MinTemp": 20 + rng.normal(0, 2, n),
            "Rainfall": np.maximum(0, rng.exponential(2, n)),
            "Latitude": [15.0] * n,
            "Longitude": [75.0] * n,
        }
    )


# ── FeatureEngine Tests ───────────────────────────────────────────


class TestFeatureEngine:
    def test_init(self):
        engine = FeatureEngine()
        assert engine._feature_store is None
        assert engine._feature_names == []
        assert engine._feature_metadata == {}

    def test_create_features_adds_columns(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_features(sample_df)
        assert len(result.columns) > len(sample_df.columns)
        assert "hour" in result.columns
        assert "month" in result.columns
        assert "season" in result.columns

    def test_create_features_lag_columns(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_features(sample_df)
        lag_cols = [c for c in result.columns if "lag" in c]
        assert len(lag_cols) > 0
        assert "temperature_2m_lag_1h" in result.columns

    def test_create_features_rolling_columns(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_features(sample_df)
        rolling_cols = [c for c in result.columns if "rolling" in c]
        assert len(rolling_cols) > 0
        assert "temperature_2m_rolling_mean_3h" in result.columns

    def test_create_features_interaction_columns(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_features(sample_df)
        assert "temperature_2m_humidity_pct_interaction" in result.columns
        assert "temperature_2m_humidity_pct_ratio" in result.columns
        assert "temperature_2m_precipitation_mm_interaction" in result.columns

    def test_create_features_derived_columns(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_features(sample_df)
        assert "diurnal_range" in result.columns
        assert "precipitation_intensity" in result.columns
        assert "humidity_index" in result.columns

    def test_get_feature_names(self, sample_df):
        engine = FeatureEngine()
        engine.create_features(sample_df)
        names = engine.get_feature_names()
        assert len(names) > 0
        assert all(isinstance(n, str) for n in names)

    def test_get_feature_metadata(self, sample_df):
        engine = FeatureEngine()
        engine.create_features(sample_df)
        meta = engine.get_feature_metadata()
        assert len(meta) > 0
        for name, m in meta.items():
            assert isinstance(m, FeatureMetadata)
            assert m.name == name
            assert m.feature_group in (
                "temporal",
                "lag",
                "rolling",
                "seasonal",
                "derived",
                "spatial",
                "interaction",
            )

    def test_set_monsoon_months(self, sample_df):
        engine = FeatureEngine()
        engine.set_monsoon_months([1, 2, 3])
        result = engine.create_features(sample_df)
        assert "is_monsoon" in result.columns

    def test_lag_features_direct(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_lag_features(sample_df, ["temperature_2m"], [1, 2])
        assert "temperature_2m_lag_1h" in result.columns
        assert "temperature_2m_lag_2h" in result.columns
        assert result["temperature_2m_lag_1h"].isna().iloc[0]

    def test_rolling_features_direct(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_rolling_features(sample_df, ["temperature_2m"], [3])
        assert "temperature_2m_rolling_mean_3h" in result.columns
        assert "temperature_2m_rolling_std_3h" in result.columns

    def test_seasonal_features_direct(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_seasonal_features(sample_df, "timestamp")
        assert "hour" in result.columns
        assert "day" in result.columns
        assert "month" in result.columns
        assert "season" in result.columns
        assert "day_of_year" in result.columns
        assert "is_weekend" in result.columns
        assert "is_monsoon" in result.columns
        assert "quarter" in result.columns
        assert "day_of_week" in result.columns

    def test_interaction_features_direct(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_interaction_features(sample_df, [("temperature_2m", "humidity_pct")])
        assert "temperature_2m_humidity_pct_interaction" in result.columns
        assert "temperature_2m_humidity_pct_ratio" in result.columns

    def test_spatial_features_no_location_id(self, sample_df):
        engine = FeatureEngine()
        result = engine.create_spatial_features(sample_df, None)
        pd.testing.assert_frame_equal(result, sample_df)

    def test_canonical_df_integration(self, sample_canonical_df):
        engine = FeatureEngine()
        result = engine.create_features(sample_canonical_df)
        assert len(result.columns) > len(sample_canonical_df.columns)

    def test_feature_metadata_integrity(self, sample_df):
        engine = FeatureEngine()
        _result = engine.create_features(sample_df)
        meta = engine.get_feature_metadata()
        tracked = engine.get_feature_names()
        for name in meta:
            assert name in tracked


# ── Window Features Tests ─────────────────────────────────────────


class TestWindowFeatures:
    def test_compute_lag_features(self):
        df = pd.DataFrame({"val": [1, 2, 3, 4, 5]})
        result = compute_lag_features(df, "val", lags=[1, 2])
        assert "val_lag_1" in result.columns
        assert "val_lag_2" in result.columns
        assert np.isnan(result["val_lag_1"].iloc[0])
        assert result["val_lag_1"].iloc[1] == 1.0
        assert result["val_lag_1"].iloc[2] == 2.0
        assert result["val_lag_1"].iloc[3] == 3.0
        assert result["val_lag_1"].iloc[4] == 4.0

    def test_compute_lag_features_default_lags(self):
        df = pd.DataFrame({"val": range(50)})
        result = compute_lag_features(df, "val")
        assert "val_lag_1" in result.columns
        assert "val_lag_7" in result.columns
        assert "val_lag_30" in result.columns

    def test_compute_rolling_features(self):
        df = pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = compute_rolling_features(df, "val", windows=[3])
        assert "val_rolling_mean_3" in result.columns
        assert "val_rolling_std_3" in result.columns
        assert result["val_rolling_mean_3"].iloc[2] == pytest.approx(2.0)

    def test_compute_rolling_features_default_windows(self):
        df = pd.DataFrame({"val": range(100)})
        result = compute_rolling_features(df, "val")
        assert "val_rolling_mean_7" in result.columns
        assert "val_rolling_mean_30" in result.columns
        assert "val_rolling_mean_90" in result.columns

    def test_compute_seasonal_features(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=365, freq="D")})
        result = compute_seasonal_features(df, "date")
        assert "year" in result.columns
        assert "month" in result.columns
        assert "day" in result.columns
        assert "day_of_year" in result.columns
        assert "day_of_week" in result.columns
        assert "quarter" in result.columns
        assert "is_weekend" in result.columns
        assert "season" in result.columns

    def test_compute_seasonal_features_values(self):
        df = pd.DataFrame({"date": pd.to_datetime(["2024-06-15", "2024-12-25"])})
        result = compute_seasonal_features(df, "date")
        assert result["month"].tolist() == [6, 12]
        assert result["season"].tolist() == ["summer", "winter"]

    def test_compute_all_window_features(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=100, freq="D"),
                "temp": 20 + rng.normal(0, 5, 100),
                "rain": np.maximum(0, rng.exponential(2, 100)),
            }
        )
        result = compute_all_window_features(df, "date")
        assert "year" in result.columns
        assert "temp_lag_1" in result.columns
        assert "temp_rolling_mean_7" in result.columns
        assert "rain_lag_1" in result.columns
        assert "rain_rolling_mean_7" in result.columns

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"val": [1, 2, 3]})
        df_orig = df.copy()
        compute_lag_features(df, "val", lags=[1])
        pd.testing.assert_frame_equal(df, df_orig)

    def test_handles_empty_lags(self):
        df = pd.DataFrame({"val": [1, 2, 3]})
        result = compute_lag_features(df, "val", lags=[])
        pd.testing.assert_frame_equal(result, df)

    def test_handles_empty_windows(self):
        df = pd.DataFrame({"val": [1, 2, 3]})
        result = compute_rolling_features(df, "val", windows=[])
        pd.testing.assert_frame_equal(result, df)


# ── Additional FeatureEngine Coverage ──────────────────────────────


class TestFeatureEngineSpatial:
    def test_spatial_features_no_location_id_returns_unchanged(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"temperature_2m": [20.0]})
        result = engine.create_spatial_features(df, None)
        pd.testing.assert_frame_equal(result, df)

    def test_interaction_missing_column_skipped(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"a": [1.0, 2.0]})
        result = engine.create_interaction_features(df, [("a", "missing")])
        pd.testing.assert_frame_equal(result, df)

    def test_interaction_zero_denominator(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"a": [10.0], "b": [0.0]})
        result = engine.create_interaction_features(df, [("a", "b")])
        assert "a_b_ratio" in result.columns
        assert result["a_b_ratio"].iloc[0] == 10.0 / 1e-10

    def test_create_features_empty_df(self):
        engine = FeatureEngine()
        result = engine.create_features(pd.DataFrame())
        assert result.empty


class TestFeatureEngineDerived:
    def test_diurnal_range_single_value(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"temperature_2m": [25.0]})
        result = engine._add_diurnal_features(df)
        assert "diurnal_range" in result.columns
        assert result["diurnal_range"].iloc[0] == 0.0

    def test_diurnal_range_missing_column(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"other": [1.0]})
        result = engine._add_diurnal_features(df)
        pd.testing.assert_frame_equal(result, df)

    def test_precip_intensity_none(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"precipitation_mm": [0.0, 1.0, 5.0, 20.0, 60.0]})
        result = engine._add_precip_intensity(df)
        cats = result["precipitation_intensity"].tolist()
        assert cats == ["none", "light", "moderate", "heavy", "extreme"]

    def test_precip_intensity_missing_column(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"other": [1.0]})
        result = engine._add_precip_intensity(df)
        pd.testing.assert_frame_equal(result, df)

    def test_humidity_index(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"humidity_pct": [20.0, 40.0, 60.0, 80.0]})
        result = engine._add_humidity_index(df)
        assert result["humidity_index"].tolist() == ["dry", "comfortable", "humid", "very_humid"]

    def test_humidity_index_missing_column(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"other": [1.0]})
        result = engine._add_humidity_index(df)
        pd.testing.assert_frame_equal(result, df)


class TestFeatureEngineSpatialHelpers:
    def test_latitude_band_tropical_north(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"latitude": [10.0]})
        result = engine._add_latitude_band(df)
        assert result["latitude_band"].iloc[0] == "tropical_north"

    def test_latitude_band_polar_south(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"latitude": [-80.0]})
        result = engine._add_latitude_band(df)
        assert result["latitude_band"].iloc[0] == "polar_south"

    def test_latitude_band_unknown(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"latitude": [100.0]})
        result = engine._add_latitude_band(df)
        assert result["latitude_band"].iloc[0] == "unknown"

    def test_latitude_band_missing_column(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"other": [1.0]})
        result = engine._add_latitude_band(df)
        pd.testing.assert_frame_equal(result, df)

    def test_longitude_zone_west(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"longitude": [-100.0]})
        result = engine._add_longitude_zone(df)
        assert result["longitude_zone"].iloc[0] == "west"

    def test_longitude_zone_central_west(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"longitude": [-45.0]})
        result = engine._add_longitude_zone(df)
        assert result["longitude_zone"].iloc[0] == "central_west"

    def test_longitude_zone_central_east(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"longitude": [45.0]})
        result = engine._add_longitude_zone(df)
        assert result["longitude_zone"].iloc[0] == "central_east"

    def test_longitude_zone_east(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"longitude": [100.0]})
        result = engine._add_longitude_zone(df)
        assert result["longitude_zone"].iloc[0] == "east"

    def test_longitude_zone_missing_column(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"other": [1.0]})
        result = engine._add_longitude_zone(df)
        pd.testing.assert_frame_equal(result, df)


class TestClassifyClimateZone:
    def test_alpine(self):
        assert FeatureEngine._classify_climate_zone("temperate_north", 3000) == "alpine"

    def test_highland(self):
        assert FeatureEngine._classify_climate_zone("temperate_north", 2000) == "highland"

    def test_tropical_highland(self):
        assert FeatureEngine._classify_climate_zone("tropical_north", 1000) == "tropical_highland"

    def test_tropical(self):
        assert FeatureEngine._classify_climate_zone("tropical_north", 100) == "tropical"

    def test_temperate(self):
        assert FeatureEngine._classify_climate_zone("temperate_north", 100) == "temperate"

    def test_polar(self):
        assert FeatureEngine._classify_climate_zone("polar_north", 100) == "polar"

    def test_unknown_band(self):
        assert FeatureEngine._classify_climate_zone("unknown", 100) == "unknown"


class TestCanonicalFeaturePath:
    def test_canonical_column_mapping(self):
        engine = FeatureEngine()
        rng = np.random.default_rng(42)
        n = 10
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2020-01-01", periods=n, freq="D"),
                "temperature_2m": 25 + rng.normal(0, 1, n),
                "temperature_2m_min": 20 + rng.normal(0, 1, n),
                "precipitation_mm": np.maximum(0, rng.exponential(1, n)),
                "latitude": [15.0] * n,
                "longitude": [75.0] * n,
            }
        )
        result = engine.create_features(df)
        assert "DayOfYear" in result.columns
        assert "Season" in result.columns
        assert "RollingRain7" in result.columns
        assert "TempDiff" in result.columns

    def test_canonical_features_skipped_when_missing_columns(self):
        engine = FeatureEngine()
        df = pd.DataFrame({"a": [1], "b": [2]})
        result = engine.create_features(df)
        assert "DayOfYear" not in result.columns


class TestFeatureMetadataRegistration:
    def test_metadata_created_for_all_groups(self, sample_df):
        engine = FeatureEngine()
        engine.create_features(sample_df)
        meta = engine.get_feature_metadata()
        groups = {m.feature_group for m in meta.values()}
        assert groups.issuperset(
            {"temporal", "lag", "rolling", "seasonal", "derived", "interaction"}
        )

    def test_feature_names_matches_metadata(self, sample_df):
        engine = FeatureEngine()
        engine.create_features(sample_df)
        names = set(engine.get_feature_names())
        meta_names = set(engine.get_feature_metadata().keys())
        assert meta_names.issubset(names)
