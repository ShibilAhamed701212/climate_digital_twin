"""Tests for models/tuning/optimizer.py and models/run_forecast.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

try:
    import torch
except (ImportError, OSError):
    torch = None  # type: ignore[assignment]


class TestHyperparameterOptimizer:
    @pytest.fixture
    def optimizer(self):
        from models.tuning.optimizer import HyperparameterOptimizer

        return HyperparameterOptimizer(random_seed=42)

    @pytest.fixture
    def mock_model_class(self):
        def mock_init(**_kwargs: Any) -> MagicMock:
            instance = MagicMock()
            instance.train.return_value = MagicMock(
                best_val_loss=0.5,
                training_duration=1.0,
                train_losses=[0.6, 0.55, 0.5],
                val_losses=[0.65, 0.6, 0.55],
                best_epoch=3,
            )
            instance.predict.return_value = np.array([0.5, 0.6])
            return instance

        mock_cls = MagicMock()
        mock_cls.side_effect = mock_init
        return mock_cls

    def test_grid_search(
        self,
        optimizer,
        mock_model_class: MagicMock,
    ) -> None:
        X = np.random.randn(20, 5)  # noqa: N806
        y = np.random.randn(20)
        X_val = np.random.randn(10, 5)  # noqa: N806
        y_val = np.random.randn(10)

        best_params, best_metrics = optimizer.grid_search(
            model_class=mock_model_class,
            param_grid={"max_depth": [4, 6], "n_estimators": [50, 100]},
            X_train=X,
            y_train=y,
            X_val=X_val,
            y_val=y_val,
            metric="rmse",
        )
        assert isinstance(best_params, dict)
        assert isinstance(best_metrics, dict)
        assert len(optimizer.get_trial_history()) > 0

    def test_grid_search_empty_grid(self, optimizer) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            optimizer.grid_search(
                model_class=MagicMock(),
                param_grid={},
                X_train=np.array([0]),
                y_train=np.array([0]),
                X_val=np.array([0]),
                y_val=np.array([0]),
            )

    def test_random_search(
        self,
        optimizer,
        mock_model_class: MagicMock,
    ) -> None:
        X = np.random.randn(20, 5)  # noqa: N806
        y = np.random.randn(20)
        X_val = np.random.randn(10, 5)  # noqa: N806
        y_val = np.random.randn(10)

        best_params, best_metrics = optimizer.random_search(
            model_class=mock_model_class,
            param_distributions={"max_depth": [4, 6, 8], "n_estimators": [50, 100, 200]},
            n_iter=3,
            X_train=X,
            y_train=y,
            X_val=X_val,
            y_val=y_val,
            metric="rmse",
        )
        assert isinstance(best_params, dict)
        assert len(optimizer.get_trial_history()) == 3

    def test_random_search_empty_grid(self, optimizer) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            optimizer.random_search(
                model_class=MagicMock(),
                param_distributions={},
                n_iter=5,
                X_train=np.array([0]),
                y_train=np.array([0]),
                X_val=np.array([0]),
                y_val=np.array([0]),
            )

    def test_properties(self, optimizer) -> None:
        assert optimizer.best_params == {}
        assert optimizer.best_metrics == {}

    def test_plot_optimization(self, optimizer) -> None:
        result = optimizer.plot_optimization()
        assert "scores" in result
        assert "best_params" in result

    def test_to_dataframe(self, optimizer) -> None:  # noqa: ARG002
        from models.tuning.optimizer import HyperparameterOptimizer

        X = np.random.randn(10, 3)  # noqa: N806
        df = HyperparameterOptimizer._to_dataframe(X)
        assert df.shape == (10, 3)

    def test_to_dataframe_1d(self, optimizer) -> None:  # noqa: ARG002
        from models.tuning.optimizer import HyperparameterOptimizer

        X = np.random.randn(10)  # noqa: N806
        df = HyperparameterOptimizer._to_dataframe(X)
        assert df.shape == (10, 1)

    def test_to_series(self, optimizer) -> None:  # noqa: ARG002
        from models.tuning.optimizer import HyperparameterOptimizer

        y = np.random.randn(10)
        s = HyperparameterOptimizer._to_series(y)
        assert len(s) == 10


@pytest.mark.skipif(torch is None, reason="torch not available")
class TestRunForecast:
    def test_setup_logging(self, tmp_path: Path) -> None:
        from models.run_forecast import setup_logging

        logger = setup_logging(log_dir=str(tmp_path / "logs"))
        assert logger.name == "forecast"
        assert (tmp_path / "logs" / "forecast_pipeline.log").parent.exists()

    @patch("models.run_forecast.yaml")
    @patch("models.run_forecast.load_data")
    @patch("models.run_forecast.create_model")
    @patch("models.run_forecast.train_model")
    @patch("models.run_forecast.evaluate_model")
    def test_run_forecast_pipeline(
        self,
        mock_evaluate: MagicMock,
        mock_train: MagicMock,
        mock_create: MagicMock,
        mock_load: MagicMock,
        mock_yaml: MagicMock,
        tmp_path: Path,  # noqa: ARG002
    ) -> None:
        from models.run_forecast import run_forecast

        mock_yaml.safe_load.return_value = {
            "data": {
                "sequence_length": 10,
                "batch_size": 8,
                "feature_columns": ["Rainfall", "MaxTemp"],
                "target_columns": ["MinTemp"],
            },
            "training": {"device": "cpu", "random_seed": 42, "loss": "mse", "optimizer": "adam"},
            "baseline": {"learning_rate": 0.001, "epochs": 2},
            "lstm": {"learning_rate": 0.001, "epochs": 2},
            "transformer": {"learning_rate": 0.001, "epochs": 2},
        }

        mock_loader = MagicMock()
        mock_load.return_value = (mock_loader, mock_loader, mock_loader, MagicMock(), MagicMock())

        mock_model = MagicMock()
        mock_model.state_dict = MagicMock(return_value={})
        mock_create.return_value = mock_model

        mock_train.return_value = {
            "train_loss": [0.5],
            "val_loss": [0.4],
            "best_epoch": 1,
            "best_val_loss": 0.4,
            "epochs_trained": 2,
            "model_name": "baseline",
        }

        mock_evaluate.return_value = {
            "metrics": {"rmse": 0.5, "mae": 0.4, "r2": 0.8, "smape": 10.0},
            "predictions": MagicMock(),
            "targets": MagicMock(),
        }

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("models.run_forecast.save_training_history"),
            patch("models.run_forecast.generate_plots"),
            patch("models.run_forecast.save_evaluation_report"),
            patch("models.run_forecast.export_model"),
        ):
            exit_code = run_forecast()

        assert exit_code == 0
