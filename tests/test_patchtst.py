from __future__ import annotations

import pytest

try:
    import torch
    import torch.nn as nn
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.patchtst.model import PatchTSTModel


def test_patchtst_forward():
    model = PatchTSTModel(n_features=5, n_targets=3, patch_len=8, d_model=64)
    x = torch.randn(4, 32, 5)
    out = model(x)
    assert out.shape == (4, 3)


def test_patchtst_is_module():
    model = PatchTSTModel(n_features=5, n_targets=3)
    assert isinstance(model, nn.Module)


def test_patchtst_different_params():
    model = PatchTSTModel(
        n_features=10,
        n_targets=1,
        patch_len=4,
        d_model=128,
        nhead=8,
        num_encoder_layers=2,
        dim_feedforward=256,
        dropout=0.2,
    )
    x = torch.randn(2, 20, 10)
    out = model(x)
    assert out.shape == (2, 1)


def test_patchtst_gradient_flows():
    model = PatchTSTModel(n_features=3, n_targets=2, d_model=32, patch_len=4)
    x = torch.randn(4, 16, 3)
    out = model(x)
    loss = out.sum()
    loss.backward()
    for p in model.parameters():
        assert p.grad is not None


def test_patchtst_partial_patches():
    model = PatchTSTModel(n_features=3, n_targets=2, patch_len=8, d_model=32)
    x = torch.randn(2, 30, 3)
    out = model(x)
    assert out.shape == (2, 2)
