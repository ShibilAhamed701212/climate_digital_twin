from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from pipeline.clean import (
    clip_outliers,
    handle_missing_values,
    load_config,
    normalize_date_format,
)


class TestLoadConfig:
    def test_loads_yaml(self, tmp_path):
        cfg = {"key": "value", "nested": {"a": 1}}
        p = tmp_path / "config.yaml"
        with open(p, "w") as f:
            yaml.dump(cfg, f)
        assert load_config(str(p)) == cfg


class TestHandleMissingValues:
    def test_interpolate_fills_all_with_valid(self):
        df = pd.DataFrame({"val": [np.nan, 1.0, np.nan, np.nan, np.nan]})
        result = handle_missing_values(df)
        assert result["val"].isnull().sum() == 0

    def test_all_nan_column_unchanged(self):
        df = pd.DataFrame({"val": [np.nan, np.nan, np.nan]})
        result = handle_missing_values(df)
        assert result["val"].isnull().sum() == 3

    def test_categorical_ffill_bfill(self):
        df = pd.DataFrame({"cat": ["a", None, "b"]})
        result = handle_missing_values(df)
        assert result["cat"].isnull().sum() == 0


class TestClipOutliers:
    def test_missing_column_returns_early(self):
        df = pd.DataFrame({"a": [1.0]})
        result = clip_outliers(df, "nonexistent")
        assert "nonexistent" not in result.columns


class TestNormalizeDateFormat:
    def test_no_date_column_returns_early(self):
        df = pd.DataFrame({"a": [1]})
        result = normalize_date_format(df)
        assert "Date" not in result.columns
