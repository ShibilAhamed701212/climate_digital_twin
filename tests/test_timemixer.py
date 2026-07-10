from __future__ import annotations

import pytest

try:
    import torch
    import torch.nn as nn
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.timemixer.model import TimeMixerBlock, TimeMixerModel


def test_timemixerblock_forward():
    block = TimeMixerBlock(dim=64)
    x = torch.randn(4, 10, 64)
    out = block(x)
    assert out.shape == (4, 10, 64)


def test_timemixermodel_forward():
    model = TimeMixerModel(n_features=5, n_targets=3, d_model=64, num_layers=2)
    x = torch.randn(4, 30, 5)
    out = model(x)
    assert out.shape == (4, 3)


def test_timemixermodel_is_module():
    model = TimeMixerModel(n_features=5, n_targets=3)
    assert isinstance(model, nn.Module)


def test_timemixermodel_different_params():
    model = TimeMixerModel(n_features=10, n_targets=1, d_model=128, num_layers=4, dropout=0.2)
    x = torch.randn(2, 30, 10)
    out = model(x)
    assert out.shape == (2, 1)


def test_timemixermodel_gradient_flows():
    model = TimeMixerModel(n_features=3, n_targets=2, d_model=32)
    x = torch.randn(4, 20, 3)
    out = model(x)
    loss = out.sum()
    loss.backward()
    for p in model.parameters():
        assert p.grad is not None
