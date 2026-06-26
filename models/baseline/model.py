"""Baseline Model: Simple feed-forward / linear benchmark.

A multi-layer perceptron that flattens the sequence dimension
and predicts all targets at once.
"""

import torch
import torch.nn as nn


class BaselineModel(nn.Module):
    """Feed-forward baseline for climate forecasting.

    Flattens (batch, seq_len, n_features) -> (batch, seq_len * n_features)
    then passes through configurable hidden layers.
    """

    def __init__(
        self,
        n_features: int,
        n_targets: int,
        sequence_length: int = 30,
        hidden_layers: list[int] | None = None,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if hidden_layers is None:
            hidden_layers = [64, 32]
        self.sequence_length = sequence_length
        self.n_features = n_features
        input_dim = sequence_length * n_features
        layers: list[nn.Module] = []
        prev_dim = input_dim
        for h in hidden_layers:
            layers.append(nn.Linear(prev_dim, h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = h
        layers.append(nn.Linear(prev_dim, n_targets))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size(0)
        x = x.reshape(batch_size, -1)
        return self.network(x)
