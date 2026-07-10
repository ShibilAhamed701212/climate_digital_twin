"""Unit tests for pipeline/export.py."""

from pathlib import Path

import pandas as pd
import pytest

from pipeline.export import (
    EXPECTED_OUTPUT_COLUMNS,
    export_datasets,
    save_split,
    select_output_columns,
    temporal_train_val_test_split,
)


@pytest.fixture
def sample_featured_df() -> pd.DataFrame:
    rng = __import__("numpy").random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    data = {
        "Date": dates,
        "Latitude": 15.0,
        "Longitude": 76.0,
        "Rainfall": [max(0, rng.exponential(5)) for _ in range(200)],
        "MaxTemp": [rng.uniform(25, 38) for _ in range(200)],
        "MinTemp": [rng.uniform(15, 22) for _ in range(200)],
        "DayOfYear": dates.dayofyear,
        "Month": dates.month,
        "Week": dates.isocalendar().week.astype(int),
        "Season": "Summer",
        "Monsoon": [1 if m in [6, 7, 8, 9] else 0 for m in dates.month],
        "RainfallTrend": [rng.uniform(-0.5, 0.5) for _ in range(200)],
        "PriorRain7": [max(0, rng.exponential(3)) for _ in range(200)],
        "PriorRain30": [max(0, rng.exponential(10)) for _ in range(200)],
        "TempDiff": [rng.uniform(5, 15) for _ in range(200)],
        "RollingRain7": [rng.exponential(3) for _ in range(200)],
        "RollingRain30": [rng.exponential(3) for _ in range(200)],
        "RollingTemp7": [rng.uniform(26, 34) for _ in range(200)],
        "RollingTemp30": [rng.uniform(26, 34) for _ in range(200)],
        "ExtraColumn": [1] * 200,
    }
    return pd.DataFrame(data)


@pytest.fixture
def config() -> dict:
    return {
        "data": {"processed_dir": "/tmp/processed"},
        "pipeline": {
            "train_split": 0.70,
            "val_split": 0.15,
            "test_split": 0.15,
            "random_seed": 42,
        },
    }


class TestSelectOutputColumns:
    def test_selects_expected_columns(self, sample_featured_df: pd.DataFrame):
        result = select_output_columns(sample_featured_df)
        assert len(result.columns) == len(EXPECTED_OUTPUT_COLUMNS)
        for col in EXPECTED_OUTPUT_COLUMNS:
            assert col in result.columns
        assert "ExtraColumn" not in result.columns

    def test_handles_missing_columns(self):
        df = pd.DataFrame({"Date": [1], "Latitude": [2]})
        result = select_output_columns(df)
        assert "Date" in result.columns


class TestTemporalTrainValTestSplit:
    def test_splits_correctly(self, sample_featured_df: pd.DataFrame):
        train, val, test = temporal_train_val_test_split(sample_featured_df)
        total = len(sample_featured_df)
        assert len(train) == int(total * 0.70)
        assert len(val) == int(total * 0.15)
        assert len(test) == total - len(train) - len(val)

    def test_maintains_temporal_order(self, sample_featured_df: pd.DataFrame):
        train, val, test = temporal_train_val_test_split(sample_featured_df)
        assert train["Date"].max() <= val["Date"].min()
        assert val["Date"].max() <= test["Date"].min()

    def test_handles_empty_df(self):
        train, val, test = temporal_train_val_test_split(pd.DataFrame())
        assert len(train) == 0
        assert len(val) == 0
        assert len(test) == 0


class TestSaveSplit:
    def test_saves_csv(self, tmp_path: Path):
        df = pd.DataFrame({"a": [1, 2, 3]})
        path = save_split(df, tmp_path, "test.csv")
        assert path.exists()
        loaded = pd.read_csv(path)
        assert len(loaded) == 3

    def test_creates_parent_dirs(self, tmp_path: Path):
        df = pd.DataFrame({"a": [1]})
        nested = tmp_path / "nested" / "dir"
        path = save_split(df, nested, "test.csv")
        assert path.exists()


class TestExportDatasets:
    def test_export_all_splits(self, sample_featured_df: pd.DataFrame, tmp_path: Path):
        config = {
            "data": {"processed_dir": str(tmp_path)},
            "pipeline": {
                "train_split": 0.70,
                "val_split": 0.15,
                "test_split": 0.15,
                "random_seed": 42,
            },
        }
        results = export_datasets(sample_featured_df, config, output_dir=tmp_path)
        assert "training" in results
        assert "validation" in results
        assert "testing" in results
        for path in results.values():
            assert Path(path).exists()
        train_df = pd.read_csv(results["training"])
        assert "RollingRain7" in train_df.columns
