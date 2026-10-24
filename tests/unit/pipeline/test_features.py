from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from pipeline.features import load_config


class TestLoadConfig:
    def test_loads_yaml(self, tmp_path):
        cfg = {"key": "value", "nested": {"a": 1}}
        p = tmp_path / "config.yaml"
        with open(p, "w") as f:
            yaml.dump(cfg, f)
        assert load_config(str(p)) == cfg


class TestRollingOlsSlope:
    """The vectorised RainfallTrend must match the per-window polyfit it replaced."""

    @staticmethod
    def _polyfit_reference(x: pd.Series) -> pd.Series:
        return x.rolling(30, min_periods=1).apply(
            lambda y: np.polyfit(range(len(y)), y, 1)[0] if len(y) >= 2 else 0.0
        )

    def test_matches_polyfit_reference(self) -> None:
        from pipeline.features import _rolling_ols_slope

        rng = np.random.default_rng(7)
        x = pd.Series(rng.exponential(5, 120) * rng.integers(0, 2, 120))

        np.testing.assert_allclose(_rolling_ols_slope(x, 30), self._polyfit_reference(x), atol=1e-9)

    def test_single_point_window_is_zero(self) -> None:
        from pipeline.features import _rolling_ols_slope

        assert _rolling_ols_slope(pd.Series([4.2]), 30).iloc[0] == 0.0

    def test_linear_series_has_constant_slope(self) -> None:
        from pipeline.features import _rolling_ols_slope

        slope = _rolling_ols_slope(pd.Series(np.arange(50) * 1.5), 30)

        np.testing.assert_allclose(slope.iloc[1:], 1.5)
