"""LSTM Model: Deep-learning sequence baseline.

An LSTM-based sequence model with configurable layers,
hidden dimensions, and dropout for climate time-series forecasting.
"""

import torch
import torch.nn as nn


class LSTMModel(nn.Module):
    """LSTM-based model for climate forecasting.

    Processes (batch, seq_len, n_features) through stacked LSTM layers,
    then a final linear projection to n_targets.
    """

    def __init__(
        self,
        n_features: int,
        n_targets: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = False,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
            bidirectional=bidirectional,
        )
        lstm_output_dim = hidden_dim * (2 if bidirectional else 1)
        self.fc = nn.Linear(lstm_output_dim, n_targets)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, _ = self.lstm(x)
        last_out = lstm_out[:, -1, :]
        return self.fc(last_out)
