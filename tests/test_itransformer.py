from __future__ import annotations

import pytest

try:
    import torch
    import torch.nn as nn
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.itransformer.model import ITransformerModel


def test_itransformer_forward():
    model = ITransformerModel(n_features=5, n_targets=3, d_model=64)
    x = torch.randn(4, 30, 5)
    out = model(x)
    assert out.shape == (4, 3)


def test_itransformer_is_module():
    model = ITransformerModel(n_features=5, n_targets=3)
    assert isinstance(model, nn.Module)


def test_itransformer_different_params():
    model = ITransformerModel(
        n_features=10,
        n_targets=1,
        d_model=128,
        nhead=8,
        num_encoder_layers=2,
        dim_feedforward=256,
        dropout=0.2,
    )
    x = torch.randn(2, 30, 10)
    out = model(x)
    assert out.shape == (2, 1)


def test_itransformer_gradient_flows():
    model = ITransformerModel(n_features=3, n_targets=2, d_model=32)
    x = torch.randn(4, 20, 3)
    out = model(x)
    loss = out.sum()
    loss.backward()
    for p in model.parameters():
        assert p.grad is not None


def test_itransformer_single_feature():
    model = ITransformerModel(n_features=1, n_targets=1, d_model=32)
    x = torch.randn(4, 30, 1)
    out = model(x)
    assert out.shape == (4, 1)
