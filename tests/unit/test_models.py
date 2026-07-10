"""Unit tests for model architectures (baseline, LSTM, transformer)."""

import pytest

try:
    import torch
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.baseline.model import BaselineModel
from models.lstm.model import LSTMModel
from models.transformer.model import PositionalEncoding, TransformerModel


@pytest.fixture
def sample_batch():
    batch_size, seq_len, n_features = 4, 10, 5
    return torch.randn(batch_size, seq_len, n_features)


class TestBaselineModel:
    def test_forward_shape(self, sample_batch):
        model = BaselineModel(n_features=5, n_targets=3, sequence_length=10)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch):
        model = BaselineModel(n_features=5, n_targets=3, sequence_length=10)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_different_hidden_layers(self, sample_batch):
        model = BaselineModel(
            n_features=5,
            n_targets=3,
            sequence_length=10,
            hidden_layers=[128, 64, 32],
        )
        output = model(sample_batch)
        assert output.shape == (4, 3)


class TestLSTMModel:
    def test_forward_shape(self, sample_batch):
        model = LSTMModel(n_features=5, n_targets=3, hidden_dim=64)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch):
        model = LSTMModel(n_features=5, n_targets=3, hidden_dim=64)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_bidirectional(self, sample_batch):
        model = LSTMModel(n_features=5, n_targets=3, hidden_dim=64, bidirectional=True)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_multiple_layers(self, sample_batch):
        model = LSTMModel(n_features=5, n_targets=3, hidden_dim=64, num_layers=3)
        output = model(sample_batch)
        assert output.shape == (4, 3)


class TestTransformerModel:
    def test_forward_shape(self, sample_batch):
        model = TransformerModel(n_features=5, n_targets=3, d_model=32, nhead=2)
        output = model(sample_batch)
        assert output.shape == (4, 3)

    def test_forward_no_nan(self, sample_batch):
        model = TransformerModel(n_features=5, n_targets=3, d_model=32, nhead=2)
        output = model(sample_batch)
        assert not torch.isnan(output).any()

    def test_larger_model(self, sample_batch):
        model = TransformerModel(
            n_features=5,
            n_targets=3,
            d_model=64,
            nhead=4,
            num_encoder_layers=2,
            dim_feedforward=256,
        )
        output = model(sample_batch)
        assert output.shape == (4, 3)


class TestPositionalEncoding:
    def test_output_shape(self):
        pe = PositionalEncoding(d_model=16, max_len=50)
        x = torch.randn(2, 10, 16)
        out = pe(x)
        assert out.shape == x.shape

    def test_adds_position_info(self):
        pe = PositionalEncoding(d_model=16, max_len=50)
        x = torch.zeros(1, 10, 16)
        out = pe(x)
        assert not torch.allclose(out, x)
