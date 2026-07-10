"""Unit tests for models/evaluator.py."""

import pytest

try:
    import torch
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.evaluator import (
    compute_mae,
    compute_mape,
    compute_metrics,
    compute_r2,
    compute_rmse,
    compute_smape,
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


class TestComputeSMAPE:
    def test_perfect_prediction(self):
        y_true = torch.tensor([10.0, 20.0, 30.0])
        y_pred = torch.tensor([10.0, 20.0, 30.0])
        assert compute_smape(y_true, y_pred) == 0.0

    def test_zero_actual(self):
        """SMAPE handles zero actual values correctly — critical for rainfall."""
        y_true = torch.tensor([0.0, 0.0, 0.0])
        y_pred = torch.tensor([5.0, 10.0, 0.0])
        smape = compute_smape(y_true, y_pred)
        # With y_true=0, y_pred=[5,10,0]:
        #   element 0: 2*|0-5| / (0+5+eps) = 10/5 = 2.0 → 200%
        #   element 1: 2*|0-10| / (0+10+eps) = 20/10 = 2.0 → 200%
        #   element 2: 2*|0-0| / (0+0+eps) ≈ 0 → 0%
        #   mean = (200% + 200% + 0%) / 3 ≈ 133.33%
        assert 120.0 < smape < 145.0, f"Expected ~133%%, got {smape}"

    def test_bounded_by_200(self):
        """SMAPE is bounded by 200% even with extreme errors."""
        y_true = torch.tensor([100.0])
        y_pred = torch.tensor([0.0])
        smape = compute_smape(y_true, y_pred)
        # 2*|100-0| / (100 + 0 + eps) ≈ 200/100 = 2.0 → 200%
        assert smape <= 200.0, f"SMAPE exceeded 200%%: {smape}"
        assert smape > 190.0

    def test_symmetric(self):
        """SMAPE is symmetric — swapping y_true and y_pred gives same result."""
        y_true = torch.tensor([10.0, 20.0])
        y_pred = torch.tensor([15.0, 25.0])
        assert abs(compute_smape(y_true, y_pred) - compute_smape(y_pred, y_true)) < 1e-6


class TestComputeMetrics:
    def test_returns_all_metrics(self):
        y_true = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        y_pred = torch.tensor([[1.1, 2.1], [3.1, 4.1]])
        metrics = compute_metrics(y_true, y_pred)
        for key in ["rmse", "mae", "r2", "smape"]:
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
