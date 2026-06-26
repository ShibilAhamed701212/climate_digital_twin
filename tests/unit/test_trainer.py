"""Unit tests for models/trainer.py."""

import pytest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from models.trainer import (
    EarlyStopping,
    get_device,
    get_loss_fn,
    get_optimizer,
    set_random_seed,
    train_one_epoch,
    validate_one_epoch,
)


class TestGetDevice:
    def test_returns_device(self):
        device = get_device("cpu")
        assert device.type == "cpu"


class TestSetRandomSeed:
    def test_runs_without_error(self):
        set_random_seed(42)


class TestLossFn:
    def test_mse(self):
        fn = get_loss_fn("mse")
        assert isinstance(fn, nn.MSELoss)

    def test_mae(self):
        fn = get_loss_fn("mae")
        assert isinstance(fn, nn.L1Loss)

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            get_loss_fn("unknown")


class TestOptimizer:
    def test_adam(self):
        model = nn.Linear(2, 1)
        opt = get_optimizer("adam", model.parameters(), 0.01)
        assert isinstance(opt, torch.optim.Adam)

    def test_sgd(self):
        model = nn.Linear(2, 1)
        opt = get_optimizer("sgd", model.parameters(), 0.01)
        assert isinstance(opt, torch.optim.SGD)


class TestEarlyStopping:
    def test_does_not_stop_initially(self):
        es = EarlyStopping(patience=3)
        es(0.5)
        assert not es.early_stop

    def test_stops_after_patience(self):
        es = EarlyStopping(patience=3)
        es(0.5)
        es(0.6)
        es(0.6)
        es(0.6)
        assert es.early_stop

    def test_resets_on_improvement(self):
        es = EarlyStopping(patience=3)
        es(0.5)
        es(0.6)
        es(0.4)
        assert es.counter == 0


class TestTrainOneEpoch:
    def test_returns_loss(self):
        model = nn.Linear(5, 2)
        data = TensorDataset(torch.randn(20, 5), torch.randn(20, 2))
        loader = DataLoader(data, batch_size=4)
        loss_fn = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        loss = train_one_epoch(model, loader, loss_fn, optimizer, torch.device("cpu"))
        assert isinstance(loss, float)
        assert loss > 0


class TestValidateOneEpoch:
    def test_returns_loss(self):
        model = nn.Linear(5, 2)
        data = TensorDataset(torch.randn(20, 5), torch.randn(20, 2))
        loader = DataLoader(data, batch_size=4)
        loss_fn = nn.MSELoss()
        loss = validate_one_epoch(model, loader, loss_fn, torch.device("cpu"))
        assert isinstance(loss, float)
