"""Transformer Model: Advanced temporal forecasting.

A Transformer encoder with positional encoding for climate
time-series forecasting.
"""

import math

try:
    import torch
    import torch.nn as nn
except ImportError:
    import types as _types

    torch = _types.ModuleType("torch")
    torch.Tensor = type("Tensor", (), {})
    nn = _types.ModuleType("nn")
    nn.Module = type("Module", (), {})


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for sequence positions."""

    def __init__(self, d_model: int, max_len: int = 1000) -> None:
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1), :]


class TransformerModel(nn.Module):
    """Transformer encoder for climate forecasting.

    Applies positional encoding, then passes through stacked
    Transformer encoder layers, and projects the output to n_targets.
    """

    def __init__(
        self,
        n_features: int,
        n_targets: int,
        d_model: int = 128,
        nhead: int = 4,
        num_encoder_layers: int = 3,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        max_len: int = 1000,
    ) -> None:
        super().__init__()
        self.input_proj = nn.Linear(n_features, d_model)
        self.pos_encoder = PositionalEncoding(d_model, max_len)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation="relu",
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=num_encoder_layers
        )
        self.fc = nn.Linear(d_model, n_targets)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        x = self.pos_encoder(x)
        x = self.transformer_encoder(x)
        x = x[:, -1, :]
        return self.fc(x)
