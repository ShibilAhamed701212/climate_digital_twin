"""Tests for all model architectures and infrastructure modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

try:
    import torch
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.baseline.model import BaselineModel
from models.data_loader import ClimateDataset, DataShapeError, Scaler
from models.ensemble.meta_learner import EnsembleMetaLearner
from models.evaluator import (
    compute_mae,
    compute_mape,
    compute_metrics,
    compute_r2,
    compute_rmse,
    compute_smape,
    evaluate_model,
)
from models.itransformer.model import ITransformerModel
from models.lstm.model import LSTMModel
from models.patchtst.model import PatchTSTModel
from models.physics import PhysicsValidator
from models.predictor import (
    MODEL_REGISTRY,
    configure_physics_validator,
    create_model,
    predict,
)
from models.registry import ModelRegistry
from models.timemixer.model import TimeMixerModel
from models.trainer import (
    EarlyStopping,
    ModelNotFoundError,
    get_device,
    get_loss_fn,
    get_optimizer,
    train_one_epoch,
    validate_one_epoch,
)
from models.transformer.model import PositionalEncoding, TransformerModel


@pytest.fixture
def sample_batch():
    return torch.randn(4, 10, 5)


@pytest.fixture
def sample_1d_targets() -> torch.Tensor:
    return torch.tensor([1.0, 2.0, 3.0, 4.0])


class TestBaselineModel:
    def test_forward_shape(self, sample_batch: torch.Tensor) -> None:
        model = BaselineModel(n_features=5, n_targets=3, sequence_length=10)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch: torch.Tensor) -> None:
        model = BaselineModel(n_features=5, n_targets=3, sequence_length=10)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_different_hidden_layers(self, sample_batch: torch.Tensor) -> None:
        model = BaselineModel(
            n_features=5, n_targets=3, sequence_length=10, hidden_layers=[128, 64, 32]
        )
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_default_hidden_layers(self) -> None:
        model = BaselineModel(n_features=5, n_targets=3, sequence_length=10)
        assert len(model.network) == 7

    def test_single_target(self) -> None:
        x = torch.randn(2, 10, 5)
        model = BaselineModel(n_features=5, n_targets=1, sequence_length=10)
        output = model(x)
        assert output.shape == (2, 1)


class TestLSTMModel:
    def test_forward_shape(self, sample_batch: torch.Tensor) -> None:
        model = LSTMModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch: torch.Tensor) -> None:
        model = LSTMModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_bidirectional(self, sample_batch: torch.Tensor) -> None:
        model = LSTMModel(n_features=5, n_targets=3, bidirectional=True)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_different_hidden_dim(self, sample_batch: torch.Tensor) -> None:
        model = LSTMModel(n_features=5, n_targets=3, hidden_dim=256, num_layers=3)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_default_parameters(self) -> None:
        model = LSTMModel(n_features=5, n_targets=3)
        assert model.hidden_dim == 128
        assert model.num_layers == 2
        assert model.bidirectional is False


class TestTransformerModel:
    def test_forward_shape(self, sample_batch: torch.Tensor) -> None:
        model = TransformerModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch: torch.Tensor) -> None:
        model = TransformerModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_large_config(self, sample_batch: torch.Tensor) -> None:
        model = TransformerModel(
            n_features=5,
            n_targets=3,
            d_model=256,
            nhead=8,
            num_encoder_layers=6,
            dim_feedforward=1024,
        )
        output = model(sample_batch)
        assert output.shape == (4, 3)


class TestPositionalEncoding:
    def test_output_shape(self) -> None:
        pe = PositionalEncoding(d_model=128, max_len=100)
        x = torch.randn(2, 50, 128)
        output = pe(x)
        assert output.shape == x.shape

    def test_adds_position_info(self) -> None:
        pe = PositionalEncoding(d_model=128, max_len=100)
        x = torch.zeros(1, 10, 128)
        output = pe(x)
        assert not torch.allclose(output, x)


class TestTimeMixerModel:
    def test_forward_shape(self, sample_batch: torch.Tensor) -> None:
        model = TimeMixerModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch: torch.Tensor) -> None:
        model = TimeMixerModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_multiple_layers(self, sample_batch: torch.Tensor) -> None:
        model = TimeMixerModel(n_features=5, n_targets=3, d_model=64, num_layers=6)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_single_layer(self, sample_batch: torch.Tensor) -> None:
        model = TimeMixerModel(n_features=5, n_targets=3, d_model=64, num_layers=1)
        output = model(sample_batch)
        assert output.shape == (4, 3)


class TestPatchTSTModel:
    def test_forward_shape(self, sample_batch: torch.Tensor) -> None:
        model = PatchTSTModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch: torch.Tensor) -> None:
        model = PatchTSTModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_different_patch_len(self) -> None:
        model = PatchTSTModel(n_features=5, n_targets=3, patch_len=4, d_model=64)
        x = torch.randn(2, 16, 5)
        output = model(x)
        assert output.shape == (2, 3)


class TestITransformerModel:
    def test_forward_shape(self, sample_batch: torch.Tensor) -> None:
        model = ITransformerModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch: torch.Tensor) -> None:
        model = ITransformerModel(n_features=5, n_targets=3)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_default_config(self) -> None:
        model = ITransformerModel(n_features=5, n_targets=3)
        assert isinstance(model.fc, torch.nn.Linear)


class TestModelRegistry:
    @pytest.fixture
    def registry(self, tmp_path: Path) -> ModelRegistry:
        return ModelRegistry(registry_path=str(tmp_path / "registry.json"))

    def test_register_and_get(self, registry: ModelRegistry) -> None:
        entry = registry.register(
            name="test_model",
            architecture="baseline",
            checkpoint_path="/tmp/test.pt",
            metrics={"rmse": 0.5},
        )
        assert entry["name"] == "test_model"
        assert registry.contains("test_model")

        fetched = registry.get("test_model")
        assert fetched["name"] == "test_model"

    def test_get_nonexistent(self, registry: ModelRegistry) -> None:
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_list_models(self, registry: ModelRegistry) -> None:
        registry.register(name="m1", architecture="lstm", checkpoint_path="/tmp/m1.pt")
        registry.register(name="m2", architecture="baseline", checkpoint_path="/tmp/m2.pt")
        models = registry.list_models()
        assert len(models) == 2

    def test_get_best(self, registry: ModelRegistry) -> None:
        registry.register(
            name="m1", architecture="lstm", checkpoint_path="/tmp/m1.pt", metrics={"rmse": 0.5}
        )
        registry.register(
            name="m2", architecture="baseline", checkpoint_path="/tmp/m2.pt", metrics={"rmse": 0.3}
        )
        best = registry.get_best(metric="rmse", ascending=True)
        assert best["name"] == "m2"

    def test_get_best_no_metric(self, registry: ModelRegistry) -> None:
        registry.register(name="m1", architecture="lstm", checkpoint_path="/tmp/m1.pt")
        with pytest.raises(KeyError):
            registry.get_best(metric="rmse")

    def test_update_metrics(self, registry: ModelRegistry) -> None:
        registry.register(
            name="m1", architecture="lstm", checkpoint_path="/tmp/m1.pt", metrics={"rmse": 0.5}
        )
        registry.update_metrics("m1", {"rmse": 0.3, "mae": 0.2})
        assert registry.get("m1")["metrics"]["rmse"] == 0.3

    def test_delete(self, registry: ModelRegistry) -> None:
        registry.register(name="m1", architecture="lstm", checkpoint_path="/tmp/m1.pt")
        assert registry.delete("m1") is True
        assert registry.delete("m1") is False

    def test_count(self, registry: ModelRegistry) -> None:
        registry.register(name="m1", architecture="lstm", checkpoint_path="/tmp/m1.pt")
        registry.register(name="m2", architecture="baseline", checkpoint_path="/tmp/m2.pt")
        assert registry.count() == 2

    def test_get_available_architectures(self, registry: ModelRegistry) -> None:
        registry.register(name="m1", architecture="lstm", checkpoint_path="/tmp/m1.pt")
        registry.register(name="m2", architecture="baseline", checkpoint_path="/tmp/m2.pt")
        arches = registry.get_available_architectures()
        assert "lstm" in arches
        assert "baseline" in arches


class TestPhysicsValidator:
    @pytest.fixture
    def validator(self) -> PhysicsValidator:
        return PhysicsValidator()

    def test_clamps_negative_rainfall(self, validator: PhysicsValidator) -> None:
        preds = torch.tensor([[-5.0, 30.0, 20.0]])
        result = validator.validate(preds)
        assert result[0, 0] == 0.0

    def test_swaps_tmin_tmax(self, validator: PhysicsValidator) -> None:
        preds = torch.tensor([[10.0, 20.0, 35.0]])
        result = validator.validate(preds)
        assert result[0, 1] >= result[0, 2]

    def test_clamps_high_rainfall(self, validator: PhysicsValidator) -> None:
        preds = torch.tensor([[600.0, 30.0, 20.0]])
        result = validator.validate(preds)
        assert result[0, 0] == 500.0

    def test_clamps_extreme_temps(self, validator: PhysicsValidator) -> None:
        preds = torch.tensor([[10.0, 60.0, -20.0]])
        result = validator.validate(preds)
        assert result[0, 1] <= 55.0
        assert result[0, 2] >= -10.0

    def test_passthrough_valid(self, validator: PhysicsValidator) -> None:
        preds = torch.tensor([[10.0, 30.0, 20.0]])
        result = validator.validate(preds)
        assert torch.allclose(result, preds)

    def test_single_column(self, validator: PhysicsValidator) -> None:
        preds = torch.tensor([[-10.0], [50.0], [600.0]])
        result = validator.validate(preds)
        assert result[0, 0] == 0.0
        assert result[2, 0] == 500.0

    def test_two_column(self) -> None:
        v = PhysicsValidator(target_names=["Rainfall", "MaxTemp"])
        preds = torch.tensor([[-5.0, 30.0]])
        result = v.validate(preds)
        assert result[0, 0] == 0.0
        assert result[0, 1] == 30.0

    def test_validate_single(self, validator: PhysicsValidator) -> None:
        rainfall, maxt, mint = validator.validate_single(-5.0, 35.0, 20.0)
        assert rainfall == 0.0

    def test_raises_on_non_float(self, validator: PhysicsValidator) -> None:
        with pytest.raises(TypeError):
            validator.validate(torch.tensor([[1, 2, 3]]))

    def test_raises_on_3d(self, validator: PhysicsValidator) -> None:
        with pytest.raises(ValueError):
            validator.validate(torch.randn(2, 3, 4))

    def test_repr(self, validator: PhysicsValidator) -> None:
        r = repr(validator)
        assert "rainfall_upper=500.0" in r

    def test_configure_global_validator(self) -> None:
        v = configure_physics_validator(rainfall_upper=300.0)
        assert v.rainfall_upper == 300.0

    def test_custom_target_names(self) -> None:
        v = PhysicsValidator(target_names=["Rainfall", "MaxTemp", "MinTemp", "Wind"])
        preds = torch.tensor([[-1.0, 30.0, 20.0, 10.0]])
        result = v.validate(preds)
        assert result.shape == (1, 4)
        assert result[0, 0] == 0.0


class TestPredictor:
    def test_create_baseline(self) -> None:
        config: dict[str, Any] = {
            "data": {"sequence_length": 10},
            "baseline": {"hidden_layers": [32, 16], "dropout": 0.1},
        }
        model = create_model("baseline", n_features=5, n_targets=3, config=config)
        assert isinstance(model, BaselineModel)

    def test_create_lstm(self) -> None:
        config: dict[str, Any] = {
            "data": {"sequence_length": 10},
            "lstm": {"hidden_dim": 64, "num_layers": 2},
        }
        model = create_model("lstm", n_features=5, n_targets=3, config=config)
        assert isinstance(model, LSTMModel)

    def test_create_transformer(self) -> None:
        config: dict[str, Any] = {
            "data": {"sequence_length": 10},
            "transformer": {"d_model": 64, "nhead": 4},
        }
        model = create_model("transformer", n_features=5, n_targets=3, config=config)
        assert isinstance(model, TransformerModel)

    def test_create_unknown_model(self) -> None:
        config: dict[str, Any] = {"data": {"sequence_length": 10}}
        with pytest.raises(ModelNotFoundError):
            create_model("unknown", 5, 3, config)

    def test_predict_returns_expected_keys(self) -> None:
        model = BaselineModel(n_features=5, n_targets=3, sequence_length=10)
        x = torch.randn(2, 10, 5)
        result = predict(model, x)
        assert "predictions" in result
        assert "confidence_intervals" in result
        assert "metadata" in result

    def test_predict_with_scaler(self) -> None:
        model = BaselineModel(n_features=5, n_targets=3, sequence_length=10)
        scaler = Scaler()
        scaler.fit(torch.tensor([[0.0, 0.0, 0.0], [100.0, 50.0, 40.0]], dtype=torch.float32))
        x = torch.randn(2, 10, 5)
        result = predict(model, x, target_scaler=scaler)
        assert len(result["predictions"]) == 2

    def test_model_registry_has_expected_keys(self) -> None:
        assert "baseline" in MODEL_REGISTRY
        assert "lstm" in MODEL_REGISTRY
        assert "transformer" in MODEL_REGISTRY


class TestTrainer:
    def test_get_device_cpu(self) -> None:
        device = get_device("cpu")
        assert device.type == "cpu"

    def test_get_loss_fn_mse(self) -> None:
        loss_fn = get_loss_fn("mse")
        assert isinstance(loss_fn, torch.nn.MSELoss)

    def test_get_loss_fn_mae(self) -> None:
        loss_fn = get_loss_fn("mae")
        assert isinstance(loss_fn, torch.nn.L1Loss)

    def test_get_loss_fn_unknown(self) -> None:
        with pytest.raises(ValueError):
            get_loss_fn("unknown")

    def test_get_optimizer_adam(self) -> None:
        model = torch.nn.Linear(10, 3)
        opt = get_optimizer("adam", model.parameters(), lr=0.001)
        assert isinstance(opt, torch.optim.Adam)

    def test_get_optimizer_sgd(self) -> None:
        model = torch.nn.Linear(10, 3)
        opt = get_optimizer("sgd", model.parameters(), lr=0.01)
        assert isinstance(opt, torch.optim.SGD)

    def test_get_optimizer_unknown(self) -> None:
        model = torch.nn.Linear(10, 3)
        with pytest.raises(ValueError):
            get_optimizer("unknown", model.parameters(), lr=0.001)

    def test_early_stopping_no_improvement(self) -> None:
        es = EarlyStopping(patience=3, min_delta=0.01)
        es(1.0)
        es(1.05)
        es(1.04)
        assert not es.early_stop
        es(1.06)
        assert es.early_stop

    def test_early_stopping_improves(self) -> None:
        es = EarlyStopping(patience=3, min_delta=0.01)
        es(1.0)
        es(0.9)
        es(0.8)
        assert not es.early_stop

    def test_early_stopping_resets_on_improvement(self) -> None:
        es = EarlyStopping(patience=2, min_delta=0.01)
        es(1.0)
        es(1.05)
        es(0.8)
        es(0.81)
        assert not es.early_stop

    def test_train_one_epoch(self, _sample_batch: torch.Tensor) -> None:
        model = torch.nn.Linear(10, 3)
        x = torch.randn(8, 10)
        y = torch.randn(8, 3)
        loader = torch.utils.data.DataLoader(list(zip(x, y, strict=False)), batch_size=4)
        loss_fn = torch.nn.MSELoss()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        loss = train_one_epoch(model, loader, loss_fn, optimizer, torch.device("cpu"))
        assert loss > 0

    def test_validate_one_epoch(self, _sample_batch: torch.Tensor) -> None:
        model = torch.nn.Linear(10, 3)
        x = torch.randn(8, 10)
        y = torch.randn(8, 3)
        loader = torch.utils.data.DataLoader(list(zip(x, y, strict=False)), batch_size=4)
        loss_fn = torch.nn.MSELoss()
        loss = validate_one_epoch(model, loader, loss_fn, torch.device("cpu"))
        assert loss > 0


class TestDataLoader:
    def test_climate_dataset(self) -> None:
        data = pd.DataFrame(
            {
                "feat1": np.random.randn(50),
                "feat2": np.random.randn(50),
                "target": np.random.randn(50),
            }
        )
        ds = ClimateDataset(
            data, feature_columns=["feat1", "feat2"], target_columns=["target"], sequence_length=10
        )
        x, y = ds[0]
        assert x.shape == (10, 2)
        assert y.shape == (1,)

    def test_climate_dataset_too_short(self) -> None:
        data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
        with pytest.raises(DataShapeError):
            ClimateDataset(
                data, feature_columns=["a", "b"], target_columns=["c"], sequence_length=10
            )

    def test_climate_dataset_length(self) -> None:
        data = pd.DataFrame(
            {
                "feat1": np.random.randn(100),
                "feat2": np.random.randn(100),
                "target": np.random.randn(100),
            }
        )
        ds = ClimateDataset(data, ["feat1", "feat2"], ["target"], sequence_length=20)
        assert len(ds) == 80

    def test_scaler_fit_transform(self) -> None:
        scaler = Scaler()
        data = torch.tensor([[0.0, 10.0], [1.0, 20.0], [2.0, 30.0]], dtype=torch.float32)
        scaler.fit(data)
        transformed = scaler.transform(data)
        assert torch.allclose(transformed[0], torch.tensor([0.0, 0.0]))
        assert torch.allclose(transformed[-1], torch.tensor([1.0, 1.0]))

    def test_scaler_inverse_transform(self) -> None:
        scaler = Scaler()
        data = torch.tensor([[0.0, 10.0], [1.0, 20.0]], dtype=torch.float32)
        scaler.fit(data)
        transformed = scaler.transform(data)
        reconstructed = scaler.inverse_transform(transformed)
        assert torch.allclose(reconstructed, data)

    def test_scaler_no_fit(self) -> None:
        scaler = Scaler()
        data = torch.tensor([[1.0, 2.0]])
        assert torch.allclose(scaler.transform(data), data)
        assert torch.allclose(scaler.inverse_transform(data), data)

    def test_scaler_zero_range(self) -> None:
        scaler = Scaler()
        data = torch.tensor([[5.0, 10.0], [5.0, 20.0]], dtype=torch.float32)
        scaler.fit(data)
        transformed = scaler.transform(data)
        assert transformed[0, 0] == 0.0


class TestEvaluator:
    @pytest.fixture
    def y_true(self) -> torch.Tensor:
        return torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])

    @pytest.fixture
    def y_pred(self) -> torch.Tensor:
        return torch.tensor([1.1, 2.0, 2.9, 4.2, 4.8])

    def test_compute_rmse(self, y_true: torch.Tensor, y_pred: torch.Tensor) -> None:
        rmse = compute_rmse(y_true, y_pred)
        assert rmse > 0

    def test_compute_mae(self, y_true: torch.Tensor, y_pred: torch.Tensor) -> None:
        mae = compute_mae(y_true, y_pred)
        assert mae > 0

    def test_compute_r2(self, y_true: torch.Tensor, y_pred: torch.Tensor) -> None:
        r2 = compute_r2(y_true, y_pred)
        assert r2 > 0

    def test_compute_r2_zero_variance(self) -> None:
        y = torch.tensor([5.0, 5.0, 5.0])
        r2 = compute_r2(y, y)
        assert r2 == 0.0

    def test_compute_smape(self, y_true: torch.Tensor, y_pred: torch.Tensor) -> None:
        smape = compute_smape(y_true, y_pred)
        assert smape > 0

    def test_compute_smape_handles_zeros(self) -> None:
        smape = compute_smape(torch.tensor([0.0, 0.0]), torch.tensor([0.1, 0.0]))
        assert smape > 0

    def test_compute_mape(self, y_true: torch.Tensor, y_pred: torch.Tensor) -> None:
        mape = compute_mape(y_true, y_pred)
        assert mape > 0

    def test_compute_metrics(self, y_true: torch.Tensor, y_pred: torch.Tensor) -> None:
        metrics = compute_metrics(y_true, y_pred)
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics
        assert "smape" in metrics

    def test_evaluate_model(self) -> None:
        model = torch.nn.Linear(10, 3)
        x = torch.randn(8, 10)
        y = torch.randn(8, 3)
        loader = torch.utils.data.DataLoader(list(zip(x, y, strict=False)), batch_size=4)
        results = evaluate_model(model, loader, torch.device("cpu"))
        assert "metrics" in results
        assert "predictions" in results
        assert "targets" in results


class TestEnsembleMetaLearner:
    @pytest.fixture
    def base_preds(self) -> dict[str, np.ndarray]:
        n = 20
        return {
            "lstm": np.random.randn(n, 3),
            "transformer": np.random.randn(n, 3),
            "baseline": np.random.randn(n, 3),
        }

    @pytest.fixture
    def targets(self) -> np.ndarray:
        return np.random.randn(20, 3)

    def test_fit_and_predict(self, base_preds: dict[str, np.ndarray], targets: np.ndarray) -> None:
        ensemble = EnsembleMetaLearner(alpha=1.0)
        metrics = ensemble.fit(base_preds, targets)
        assert "rmse" in metrics
        assert ensemble.is_fitted

        preds = ensemble.predict(base_preds)
        assert preds.shape == (20, 3)

    def test_fit_1d_targets(self) -> None:
        ensemble = EnsembleMetaLearner()
        base = {"lstm": np.random.randn(20), "transformer": np.random.randn(20)}
        targets = np.random.randn(20)
        ensemble.fit(base, targets)
        preds = ensemble.predict(base)
        assert preds.ndim == 1

    def test_not_enough_models(self) -> None:
        ensemble = EnsembleMetaLearner()
        with pytest.raises(ValueError, match="at least 2"):
            ensemble.fit({"lstm": np.random.randn(10)}, np.random.randn(10))

    def test_predict_before_fit(self) -> None:
        ensemble = EnsembleMetaLearner()
        with pytest.raises(RuntimeError):
            ensemble.predict({"lstm": np.random.randn(5)})

    def test_get_weights(self, base_preds: dict[str, np.ndarray], targets: np.ndarray) -> None:
        ensemble = EnsembleMetaLearner()
        ensemble.fit(
            {"lstm": base_preds["lstm"], "transformer": base_preds["transformer"]}, targets[:, 0]
        )
        weights = ensemble.get_weights()
        assert "lstm" in weights
        assert "transformer" in weights

    def test_no_scaler(self, base_preds: dict[str, np.ndarray], targets: np.ndarray) -> None:
        ensemble = EnsembleMetaLearner(use_scaler=False)
        ensemble.fit(base_preds, targets)
        assert ensemble.is_fitted

    def test_save_load(
        self, tmp_path: Path, base_preds: dict[str, np.ndarray], targets: np.ndarray
    ) -> None:
        ensemble = EnsembleMetaLearner()
        ensemble.fit(base_preds, targets)
        path = str(tmp_path / "ensemble.joblib")
        ensemble.save(path)
        loaded = EnsembleMetaLearner.load(path)
        assert loaded.is_fitted
        preds_original = ensemble.predict(base_preds)
        preds_loaded = loaded.predict(base_preds)
        np.testing.assert_array_almost_equal(preds_original, preds_loaded)
