from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from models.ensemble.meta_learner import EnsembleMetaLearner


@pytest.fixture
def sample_data():
    n = 50
    targets = np.random.randn(n).astype(np.float64)
    base_preds = {
        "lstm": np.random.randn(n).astype(np.float64),
        "transformer": np.random.randn(n).astype(np.float64),
        "baseline": np.random.randn(n).astype(np.float64),
    }
    return base_preds, targets


@pytest.fixture
def multi_target_data():
    n = 50
    targets = np.random.randn(n, 3).astype(np.float64)
    base_preds = {
        "lstm": np.random.randn(n, 3).astype(np.float64),
        "transformer": np.random.randn(n, 3).astype(np.float64),
    }
    return base_preds, targets


class TestEnsembleMetaLearner:
    def test_fit_and_predict(self, sample_data):
        base_preds, targets = sample_data
        ensemble = EnsembleMetaLearner()
        result = ensemble.fit(base_preds, targets)
        assert "rmse" in result
        assert "mae" in result
        assert "r2" in result
        assert ensemble.is_fitted

        preds = ensemble.predict(base_preds)
        assert preds.shape == targets.shape
        assert isinstance(preds, np.ndarray)

    def test_predict_before_fit_raises(self):
        ensemble = EnsembleMetaLearner()
        dummy = {"lstm": np.array([1.0, 2.0]), "transformer": np.array([1.5, 2.5])}
        with pytest.raises(RuntimeError, match="fitted"):
            ensemble.predict(dummy)

    def test_fit_with_single_model_raises(self):
        ensemble = EnsembleMetaLearner()
        dummy = {"lstm": np.array([1.0, 2.0])}
        targets = np.array([1.5, 2.5])
        with pytest.raises(ValueError, match="at least 2"):
            ensemble.fit(dummy, targets)

    def test_multi_target(self, multi_target_data):
        base_preds, targets = multi_target_data
        ensemble = EnsembleMetaLearner()
        result = ensemble.fit(base_preds, targets)
        assert "rmse" in result
        preds = ensemble.predict(base_preds)
        assert preds.shape == targets.shape
        assert ensemble.is_fitted

    def test_get_weights(self, sample_data):
        base_preds, targets = sample_data
        ensemble = EnsembleMetaLearner()
        ensemble.fit(base_preds, targets)
        weights = ensemble.get_weights()
        assert set(weights.keys()) == {"lstm", "transformer", "baseline"}
        for name in weights:
            assert 0 in weights[name]
            assert isinstance(weights[name][0], float)

    def test_save_and_load(self, sample_data):
        base_preds, targets = sample_data
        ensemble = EnsembleMetaLearner()
        ensemble.fit(base_preds, targets)
        orig_preds = ensemble.predict(base_preds)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name
        try:
            ensemble.save(path)
            loaded = EnsembleMetaLearner.load(path)
            assert loaded.is_fitted
            assert loaded.alpha == ensemble.alpha
            assert loaded._base_model_names == ensemble._base_model_names

            loaded_preds = loaded.predict(base_preds)
            np.testing.assert_array_almost_equal(orig_preds, loaded_preds)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_without_scaler(self, sample_data):
        base_preds, targets = sample_data
        ensemble = EnsembleMetaLearner(use_scaler=False)
        result = ensemble.fit(base_preds, targets)
        assert "rmse" in result
        preds = ensemble.predict(base_preds)
        assert preds.shape == targets.shape
        assert not ensemble._scalers

    def test_alpha_parameter(self, sample_data):
        base_preds, targets = sample_data
        ensemble_l2 = EnsembleMetaLearner(alpha=10.0)
        ensemble_l1 = EnsembleMetaLearner(alpha=0.1)
        r2_l2 = ensemble_l2.fit(base_preds, targets)["r2"]
        r2_l1 = ensemble_l1.fit(base_preds, targets)["r2"]
        assert isinstance(r2_l2, float)
        assert isinstance(r2_l1, float)

    def test_is_fitted_property(self):
        ensemble = EnsembleMetaLearner()
        assert not ensemble.is_fitted
        base = {"a": np.array([1.0, 2.0]), "b": np.array([1.1, 2.1])}
        ensemble.fit(base, np.array([1.5, 2.5]))
        assert ensemble.is_fitted

    def test_perfect_prediction(self):
        n = 20
        rng = np.random.RandomState(42)
        targets = np.arange(n, dtype=np.float64)
        base_preds = {
            "a": targets + 0.01 * rng.randn(n),
            "b": targets + 0.02 * rng.randn(n),
        }
        ensemble = EnsembleMetaLearner(alpha=0.0)
        result = ensemble.fit(base_preds, targets)
        assert result["r2"] == pytest.approx(1.0, abs=0.1)

    def test_save_load_no_scaler(self, sample_data):
        base_preds, targets = sample_data
        ensemble = EnsembleMetaLearner(use_scaler=False)
        ensemble.fit(base_preds, targets)
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            path = f.name
        try:
            ensemble.save(path)
            loaded = EnsembleMetaLearner.load(path)
            assert loaded.is_fitted
            assert loaded.use_scaler is False
            np.testing.assert_array_almost_equal(
                ensemble.predict(base_preds), loaded.predict(base_preds)
            )
        finally:
            Path(path).unlink(missing_ok=True)

    def test_weights_reflect_coefficients(self, sample_data):
        base_preds, targets = sample_data
        ensemble = EnsembleMetaLearner(alpha=0.0)
        ensemble.fit(base_preds, targets)
        weights = ensemble.get_weights()
        coef_sum = sum(weights[name][0] for name in weights)
        assert isinstance(coef_sum, float)
