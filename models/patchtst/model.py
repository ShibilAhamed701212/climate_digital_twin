try:
    import torch
    import torch.nn as nn
except ImportError:
    import types as _types

    torch = _types.ModuleType("torch")
    torch.Tensor = type("Tensor", (), {})
    nn = _types.ModuleType("nn")
    nn.Module = type("Module", (), {})


class PatchEmbedding(nn.Module):
    def __init__(self, patch_len: int, d_model: int, n_features: int) -> None:
        super().__init__()
        self.patch_len = patch_len
        self.proj = nn.Linear(patch_len * n_features, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, seq_len, n_feat = x.shape
        num_patches = seq_len // self.patch_len
        x = x[:, : num_patches * self.patch_len, :]
        x = x.reshape(batch, num_patches, self.patch_len * n_feat)
        return self.proj(x)


class PatchTSTModel(nn.Module):
    def __init__(
        self,
        n_features: int,
        n_targets: int,
        patch_len: int = 8,
        d_model: int = 128,
        nhead: int = 4,
        num_encoder_layers: int = 3,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.patch_embed = PatchEmbedding(patch_len, d_model, n_features)
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
        x = self.patch_embed(x)
        x = self.encoder(x)
        x = x.mean(dim=1)
        return self.fc(x)
