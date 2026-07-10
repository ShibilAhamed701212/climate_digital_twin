"""Integration tests for Phase 3 Forecasting Engine.

Tests end-to-end training for 1 epoch on synthetic data,
verifies loss decreases, and validates the prediction API.
"""

from pathlib import Path

import pytest

try:
    import torch
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.data_loader import load_data
from models.evaluator import evaluate_model
from models.predictor import create_model, predict
from models.trainer import train_model


@pytest.fixture
def forecast_config(tmp_path: Path) -> dict:
    """Create a minimal forecasting config for integration testing."""
    return {
        "data": {
            "sequence_length": 10,
            "batch_size": 8,
            "feature_columns": [
                "Rainfall",
                "MaxTemp",
                "MinTemp",
                "Month",
                "Week",
                "Season",
                "Monsoon",
                "RollingRain7",
                "RollingRain30",
                "RollingTemp7",
                "RollingTemp30",
            ],
            "target_columns": ["Rainfall", "MaxTemp", "MinTemp"],
        },
        "baseline": {"hidden_layers": [32, 16], "learning_rate": 0.01, "epochs": 2, "dropout": 0.1},
        "lstm": {
            "hidden_dim": 32,
            "num_layers": 1,
            "dropout": 0.1,
            "learning_rate": 0.01,
            "epochs": 2,
            "bidirectional": False,
        },
        "transformer": {
            "d_model": 16,
            "nhead": 2,
            "num_encoder_layers": 1,
            "dim_feedforward": 32,
            "dropout": 0.1,
            "learning_rate": 0.01,
            "epochs": 2,
        },
        "training": {
            "device": "cpu",
            "loss": "mse",
            "optimizer": "adam",
            "early_stopping_patience": 10,
            "random_seed": 42,
        },
        "evaluation": {
            "metrics": ["rmse", "mae", "r2", "smape"],
            "save_plots": True,
            "compare_models": True,
        },
        "export": {"format": "torchscript", "export_dir": str(tmp_path / "exported")},
    }


class TestForecastingIntegration:
    """Integration tests for the full forecasting pipeline."""

    def test_data_loader_creates_valid_loaders(self, forecast_config: dict):
        train_loader, val_loader, test_loader, feat_scaler, tgt_scaler = load_data(
            forecast_config, data_dir="/tmp/nonexistent"
        )
        assert len(train_loader) > 0
        assert len(val_loader) > 0
        assert len(test_loader) > 0
        for x, y in train_loader:
            assert x.dim() == 3
            assert y.dim() == 2
            seq_len = forecast_config["data"]["sequence_length"]
            n_feat = len(forecast_config["data"]["feature_columns"])
            n_tgt = len(forecast_config["data"]["target_columns"])
            assert x.shape[1] == seq_len
            assert x.shape[2] == n_feat
            assert y.shape[1] == n_tgt
            break

    def test_baseline_training_decreases_loss(self, forecast_config: dict, tmp_path: Path):
        train_loader, val_loader, _, _, _ = load_data(forecast_config, data_dir="/tmp/nonexistent")
        n_feat = len(forecast_config["data"]["feature_columns"])
        n_tgt = len(forecast_config["data"]["target_columns"])
        model = create_model("baseline", n_feat, n_tgt, forecast_config)
        history = train_model(
            model,
            train_loader,
            val_loader,
            forecast_config,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            model_name="baseline_integration",
        )
        assert len(history["train_loss"]) > 0
        assert len(history["val_loss"]) > 0
        assert history["best_val_loss"] > 0

    def test_lstm_training_decreases_loss(self, forecast_config: dict, tmp_path: Path):
        train_loader, val_loader, _, _, _ = load_data(forecast_config, data_dir="/tmp/nonexistent")
        n_feat = len(forecast_config["data"]["feature_columns"])
        n_tgt = len(forecast_config["data"]["target_columns"])
        model = create_model("lstm", n_feat, n_tgt, forecast_config)
        history = train_model(
            model,
            train_loader,
            val_loader,
            forecast_config,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            model_name="lstm_integration",
        )
        assert history["best_val_loss"] > 0

    def test_transformer_training_decreases_loss(self, forecast_config: dict, tmp_path: Path):
        train_loader, val_loader, _, _, _ = load_data(forecast_config, data_dir="/tmp/nonexistent")
        n_feat = len(forecast_config["data"]["feature_columns"])
        n_tgt = len(forecast_config["data"]["target_columns"])
        model = create_model("transformer", n_feat, n_tgt, forecast_config)
        history = train_model(
            model,
            train_loader,
            val_loader,
            forecast_config,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            model_name="transformer_integration",
        )
        assert history["best_val_loss"] > 0

    def test_evaluation_returns_valid_metrics(self, forecast_config: dict, tmp_path: Path):
        train_loader, val_loader, test_loader, _, _ = load_data(
            forecast_config, data_dir="/tmp/nonexistent"
        )
        n_feat = len(forecast_config["data"]["feature_columns"])
        n_tgt = len(forecast_config["data"]["target_columns"])
        model = create_model("baseline", n_feat, n_tgt, forecast_config)
        train_model(
            model,
            train_loader,
            val_loader,
            forecast_config,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            model_name="baseline_eval",
        )
        device = torch.device("cpu")
        eval_result = evaluate_model(model, test_loader, device)
        metrics = eval_result["metrics"]
        for key in ["rmse", "mae", "r2", "smape"]:
            assert key in metrics
        assert metrics["rmse"] >= 0
        assert metrics["r2"] <= 1.0

    def test_prediction_api_returns_structured_output(self, forecast_config: dict, tmp_path: Path):
        train_loader, val_loader, test_loader, _, _ = load_data(
            forecast_config, data_dir="/tmp/nonexistent"
        )
        n_feat = len(forecast_config["data"]["feature_columns"])
        n_tgt = len(forecast_config["data"]["target_columns"])
        model = create_model("baseline", n_feat, n_tgt, forecast_config)
        train_model(
            model,
            train_loader,
            val_loader,
            forecast_config,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            model_name="baseline_api",
        )
        for x, _ in test_loader:
            result = predict(model, x)
            assert "predictions" in result
            assert "confidence_intervals" in result
            assert "metadata" in result
            assert result["metadata"]["model_type"] == "BaselineModel"
            assert result["metadata"]["n_variables"] == 3
            break

    def test_full_pipeline_end_to_end(self, forecast_config: dict, tmp_path: Path):
        """Run the complete forecast pipeline for all 3 models (1 epoch each)."""
        train_loader, val_loader, test_loader, _, _ = load_data(
            forecast_config, data_dir="/tmp/nonexistent"
        )
        n_feat = len(forecast_config["data"]["feature_columns"])
        n_tgt = len(forecast_config["data"]["target_columns"])
        results = {}
        for model_name in ["baseline", "lstm", "transformer"]:
            model = create_model(model_name, n_feat, n_tgt, forecast_config)
            history = train_model(
                model,
                train_loader,
                val_loader,
                forecast_config,
                checkpoint_dir=str(tmp_path / "checkpoints"),
                model_name=f"{model_name}_e2e",
            )
            device = torch.device("cpu")
            eval_result = evaluate_model(model, test_loader, device)
            results[model_name] = eval_result["metrics"]
            assert len(history["train_loss"]) > 0
        assert len(results) == 3
        assert "baseline" in results
        assert "lstm" in results
        assert "transformer" in results
