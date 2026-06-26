"""Unit tests for models/data_loader.py."""

import pandas as pd
import pytest
import torch
from torch.utils.data import DataLoader

from models.data_loader import (
    ClimateDataset,
    DataShapeError,
    Scaler,
    _generate_synthetic_training_data,
    load_data,
)


class TestClimateDataset:
    def test_dataset_length(self):
        data = pd.DataFrame({"a": range(100), "b": range(100)})
        ds = ClimateDataset(data, ["a"], ["b"], sequence_length=10)
        assert len(ds) == 90

    def test_dataset_item_shape(self):
        data = pd.DataFrame({"a": range(100), "b": range(100)})
        ds = ClimateDataset(data, ["a"], ["b"], sequence_length=10)
        x, y = ds[0]
        assert x.shape == (10, 1)
        assert y.shape == (1,)

    def test_dataset_too_short_raises(self):
        data = pd.DataFrame({"a": range(5), "b": range(5)})
        with pytest.raises(DataShapeError):
            ClimateDataset(data, ["a"], ["b"], sequence_length=10)


class TestScaler:
    def test_fit_transform(self):
        data = torch.tensor([[1.0, 10.0], [3.0, 30.0], [5.0, 50.0]])
        scaler = Scaler()
        scaler.fit(data)
        scaled = scaler.transform(data)
        assert torch.allclose(scaled.min(dim=0).values, torch.tensor([0.0, 0.0]))
        assert torch.allclose(scaled.max(dim=0).values, torch.tensor([1.0, 1.0]))

    def test_inverse_transform(self):
        data = torch.tensor([[1.0, 10.0], [3.0, 30.0], [5.0, 50.0]])
        scaler = Scaler()
        scaler.fit(data)
        scaled = scaler.transform(data)
        restored = scaler.inverse_transform(scaled)
        assert torch.allclose(restored, data, atol=1e-5)

    def test_no_op_when_not_fitted(self):
        scaler = Scaler()
        result = scaler.transform(torch.tensor([1.0, 2.0]))
        assert torch.allclose(result, torch.tensor([1.0, 2.0]))


class TestSyntheticData:
    def test_generates_correct_columns(self):
        df = _generate_synthetic_training_data(100)
        expected = [
            "Rainfall", "MaxTemp", "MinTemp", "Month", "Week",
            "Season", "Monsoon", "RollingRain7", "RollingRain30",
            "RollingTemp7", "RollingTemp30",
        ]
        for col in expected:
            assert col in df.columns

    def test_generates_sufficient_samples(self):
        df = _generate_synthetic_training_data(1000, sequence_length=30)
        assert len(df) >= 1000 + 30


class TestLoadData:
    def test_load_data_returns_loaders(self):
        config = {
            "data": {
                "sequence_length": 10,
                "batch_size": 8,
                "feature_columns": ["Rainfall", "MaxTemp", "MinTemp"],
                "target_columns": ["Rainfall", "MaxTemp", "MinTemp"],
            },
            "training": {"random_seed": 42},
        }
        train_loader, val_loader, test_loader, feat_scaler, tgt_scaler = load_data(
            config, data_dir="/tmp/nonexistent"
        )
        assert isinstance(train_loader, DataLoader)
        assert isinstance(val_loader, DataLoader)
        assert isinstance(test_loader, DataLoader)
        assert feat_scaler is not None
        assert tgt_scaler is not None
