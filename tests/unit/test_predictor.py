"""Unit tests for models/predictor.py."""

from pathlib import Path

import pytest
import torch

from models.predictor import (
    MODEL_REGISTRY,
    create_model,
    export_model,
    load_model,
    predict,
)
from models.trainer import ModelNotFoundError


@pytest.fixture
def config():
    return {
        "data": {
            "sequence_length": 10,
            "batch_size": 8,
            "feature_columns": ["a", "b", "c"],
            "target_columns": ["x", "y"],
        },
        "baseline": {"hidden_layers": [16, 8], "learning_rate": 0.01, "epochs": 2},
        "lstm": {"hidden_dim": 32, "num_layers": 1, "dropout": 0.1, "learning_rate": 0.01, "epochs": 2},
        "transformer": {"d_model": 16, "nhead": 2, "num_encoder_layers": 1, "dim_feedforward": 32, "dropout": 0.1, "learning_rate": 0.01, "epochs": 2},
        "training": {"device": "cpu", "loss": "mse", "optimizer": "adam", "early_stopping_patience": 10, "random_seed": 42},
        "evaluation": {"metrics": ["rmse", "mae", "r2", "mape"], "save_plots": True, "compare_models": True},
        "export": {"format": "torchscript", "export_dir": "models/exported"},
    }


class TestModelRegistry:
    def test_contains_all_models(self):
        assert "baseline" in MODEL_REGISTRY
        assert "lstm" in MODEL_REGISTRY
        assert "transformer" in MODEL_REGISTRY


class TestCreateModel:
    def test_creates_baseline(self, config):
        model = create_model("baseline", 3, 2, config)
        assert model is not None

    def test_creates_lstm(self, config):
        model = create_model("lstm", 3, 2, config)
        assert model is not None

    def test_creates_transformer(self, config):
        model = create_model("transformer", 3, 2, config)
        assert model is not None

    def test_unknown_model_raises(self, config):
        with pytest.raises(ModelNotFoundError):
            create_model("unknown", 3, 2, config)

    def test_models_forward(self, config):
        for name in ["baseline", "lstm", "transformer"]:
            model = create_model(name, 3, 2, config)
            x = torch.randn(2, 10, 3)
            out = model(x)
            assert out.shape == (2, 2), f"{name} output shape mismatch"


class TestPredict:
    def test_returns_structured_output(self, config):
        model = create_model("baseline", 3, 2, config)
        x = torch.randn(2, 10, 3)
        result = predict(model, x)
        assert "predictions" in result
        assert "confidence_intervals" in result
        assert "metadata" in result
        assert len(result["predictions"]) == 2

    def test_confidence_intervals(self, config):
        model = create_model("baseline", 3, 2, config)
        x = torch.randn(5, 10, 3)
        result = predict(model, x)
        ci = result["confidence_intervals"]
        assert "lower" in ci
        assert "upper" in ci


class TestExportModel:
    def test_exports_torchscript(self, config, tmp_path: Path):
        model = create_model("baseline", 3, 2, config)
        export_path = str(tmp_path / "test_model.pt")
        export_model(model, export_path)
        assert Path(export_path).exists()
        loaded = torch.jit.load(export_path)
        x = torch.randn(1, 10, 3)
        out = loaded(x)
        assert out.shape == (1, 2)


class TestLoadModel:
    def test_loads_saved_model(self, config, tmp_path: Path):
        model = create_model("baseline", 3, 2, config)
        model.eval()
        ckpt_path = tmp_path / "checkpoint.pt"
        torch.save(model.state_dict(), ckpt_path)
        loaded = load_model("baseline", str(ckpt_path), 3, 2, config)
        x = torch.randn(1, 10, 3)
        out1 = model(x)
        out2 = loaded(x)
        assert torch.allclose(out1, out2, atol=1e-5)

    def test_missing_checkpoint_raises(self, config):
        with pytest.raises(ModelNotFoundError):
            load_model("baseline", "/nonexistent/ckpt.pt", 3, 2, config)
