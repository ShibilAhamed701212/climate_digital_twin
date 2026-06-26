"""Unit tests for models/evaluator.py."""

import torch

from models.evaluator import (
    compute_mae,
    compute_mape,
    compute_metrics,
    compute_r2,
    compute_rmse,
    evaluate_model,
)


class TestComputeRMSE:
    def test_perfect_prediction(self):
        y_true = torch.tensor([1.0, 2.0, 3.0])
        y_pred = torch.tensor([1.0, 2.0, 3.0])
        assert compute_rmse(y_true, y_pred) == 0.0

    def test_imperfect_prediction(self):
        y_true = torch.tensor([1.0, 2.0, 3.0])
        y_pred = torch.tensor([1.5, 2.5, 3.5])
        rmse = compute_rmse(y_true, y_pred)
        assert rmse > 0.0


class TestComputeMAE:
    def test_perfect_prediction(self):
        y_true = torch.tensor([1.0, 2.0, 3.0])
        y_pred = torch.tensor([1.0, 2.0, 3.0])
        assert compute_mae(y_true, y_pred) == 0.0


class TestComputeR2:
    def test_perfect_prediction(self):
        y_true = torch.tensor([1.0, 2.0, 3.0])
        y_pred = torch.tensor([1.0, 2.0, 3.0])
        assert compute_r2(y_true, y_pred) == 1.0

    def test_constant_prediction(self):
        y_true = torch.tensor([1.0, 2.0, 3.0])
        y_pred = torch.tensor([2.0, 2.0, 2.0])
        r2 = compute_r2(y_true, y_pred)
        assert r2 < 1.0


class TestComputeMAPE:
    def test_perfect_prediction(self):
        y_true = torch.tensor([10.0, 20.0, 30.0])
        y_pred = torch.tensor([10.0, 20.0, 30.0])
        assert compute_mape(y_true, y_pred) == 0.0


class TestComputeMetrics:
    def test_returns_all_metrics(self):
        y_true = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        y_pred = torch.tensor([[1.1, 2.1], [3.1, 4.1]])
        metrics = compute_metrics(y_true, y_pred)
        for key in ["rmse", "mae", "r2", "mape"]:
            assert key in metrics
        assert metrics["rmse"] > 0


class TestEvaluateModel:
    def test_returns_metrics_and_predictions(self):
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        model = nn.Linear(5, 2)
        data = TensorDataset(torch.randn(20, 5), torch.randn(20, 2))
        loader = DataLoader(data, batch_size=4)
        result = evaluate_model(model, loader, torch.device("cpu"))
        assert "metrics" in result
        assert "predictions" in result
        assert "targets" in result
        assert result["predictions"].shape == result["targets"].shape
