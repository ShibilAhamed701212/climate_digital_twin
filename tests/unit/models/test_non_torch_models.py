"""Tests for non-PyTorch models (Prophet, XGBoost) — safe on all platforms."""

import numpy as np
import pytest


def test_xgboost_model():
    """Test XGBoost model can be instantiated and trained."""
    try:
        from models.xgboost.model import XGBoostModel

        model = XGBoostModel()
        X = np.random.randn(20, 5)  # noqa: N806
        y = np.random.randn(20)
        import pandas as pd

        X_df = pd.DataFrame(X, columns=[f"f{i}" for i in range(5)])  # noqa: N806
        y_s = pd.Series(y)
        model.train(X_df, y_s)
        preds = model.predict(X_df[:3])
        assert preds.shape == (3,), f"Expected (3,), got {preds.shape}"
        print(f"XGBoost predict OK: {preds}")
    except ImportError as e:
        pytest.skip(f"XGBoost model not importable: {e}")


def test_prophet_model():
    """Test Prophet model can be instantiated."""
    try:
        from models.prophet.model import ProphetModel

        model = ProphetModel()
        assert model is not None
        print("Prophet model instantiated OK")
    except ImportError as e:
        pytest.skip(f"Prophet model not importable: {e}")
