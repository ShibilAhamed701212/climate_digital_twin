try:
    import torch
    import torch.nn as nn
except ImportError:
    import types as _types

    torch = _types.ModuleType("torch")
    torch.Tensor = type("Tensor", (), {})
    nn = _types.ModuleType("nn")
    nn.Module = type("Module", (), {})


class ITransformerModel(nn.Module):
    def __init__(
        self,
        n_features: int,  # noqa: ARG002
        n_targets: int,
        d_model: int = 128,
        nhead: int = 4,
        num_encoder_layers: int = 3,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.time_proj = nn.Linear(1, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)
        self.fc = nn.Linear(d_model, n_targets)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = x.unsqueeze(-1)
        x = self.time_proj(x)
        x = x.mean(dim=2)
        x = self.encoder(x)
        x = x.mean(dim=1)
        return self.fc(x)
