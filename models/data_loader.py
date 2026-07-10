"""Module 1: Data Loader.

Loads processed train/val/test splits from data/processed/,
creates PyTorch Dataset and DataLoader with configurable batch size
and sequence length. Supports feature scaling and target normalization.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)


class ClimateDataset(Dataset):
    """PyTorch Dataset for climate time-series forecasting.

    Creates sliding windows of sequence_length from the input data.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        feature_columns: list[str],
        target_columns: list[str],
        sequence_length: int = 30,
    ) -> None:
        self.sequence_length = sequence_length
        self.feature_columns = feature_columns
        self.target_columns = target_columns
        self.features = torch.tensor(data[feature_columns].values, dtype=torch.float32)
        self.targets = torch.tensor(data[target_columns].values, dtype=torch.float32)
        if len(self.features) <= sequence_length:
            raise DataShapeError(
                f"Data length ({len(self.features)}) must exceed "
                f"sequence_length ({sequence_length})"
            )

    def __len__(self) -> int:
        return len(self.features) - self.sequence_length

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.features[idx : idx + self.sequence_length]
        y = self.targets[idx + self.sequence_length]
        return x, y


class DataShapeError(Exception):
    """Raised when input data has invalid shape."""


class PredictionError(Exception):
    """Raised when prediction fails."""


class Scaler:
    """Min-max scaler for feature/target normalization."""

    def __init__(self) -> None:
        self.min_vals: torch.Tensor | None = None
        self.max_vals: torch.Tensor | None = None

    def fit(self, data: torch.Tensor) -> None:
        self.min_vals = data.min(dim=0).values
        self.max_vals = data.max(dim=0).values
        range_vals = self.max_vals - self.min_vals
        range_vals[range_vals == 0] = 1.0
        self.max_vals = self.min_vals + range_vals

    def transform(self, data: torch.Tensor) -> torch.Tensor:
        if self.min_vals is None or self.max_vals is None:
            return data
        range_vals = self.max_vals - self.min_vals
        range_vals[range_vals == 0] = 1.0
        return (data - self.min_vals) / range_vals

    def inverse_transform(self, data: torch.Tensor) -> torch.Tensor:
        if self.min_vals is None or self.max_vals is None:
            return data
        range_vals = self.max_vals - self.min_vals
        range_vals[range_vals == 0] = 1.0
        return data * range_vals + self.min_vals


def load_config(config_path: str = "models/configs/model_config.yaml") -> dict[str, Any]:
    """Load model configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def _generate_synthetic_training_data(
    num_samples: int = 5000,
    sequence_length: int = 30,
) -> pd.DataFrame:
    """Generate synthetic training data for testing/demo."""
    rng = np.random.default_rng(42)
    n = num_samples + sequence_length
    data = pd.DataFrame(
        {
            "Rainfall": np.maximum(0, rng.exponential(5, n)),
            "MaxTemp": rng.uniform(25, 38, n),
            "MinTemp": rng.uniform(15, 22, n),
            "Month": rng.integers(1, 13, n),
            "Week": rng.integers(1, 53, n),
            "Season": rng.choice(["Winter", "Summer", "Monsoon", "Post-Monsoon"], n),
            "Monsoon": rng.integers(0, 2, n),
            "RollingRain7": np.maximum(0, rng.exponential(4, n)),
            "RollingRain30": np.maximum(0, rng.exponential(4, n)),
            "RollingTemp7": rng.uniform(20, 35, n),
            "RollingTemp30": rng.uniform(20, 35, n),
        }
    )
    return data


def load_data(
    config: dict[str, Any],
    data_dir: str | None = None,
) -> tuple[DataLoader, DataLoader, DataLoader, Scaler, Scaler]:
    """Load train/val/test splits and create DataLoaders.

    Returns (train_loader, val_loader, test_loader, feature_scaler, target_scaler).
    """
    if data_dir is None:
        data_dir = "data/processed"
    seq_len = config["data"]["sequence_length"]
    batch_size = config["data"]["batch_size"]
    feat_cols = config["data"]["feature_columns"]
    tgt_cols = config["data"]["target_columns"]
    data_dir_path = Path(data_dir)
    train_path = data_dir_path / "training.csv"
    val_path = data_dir_path / "validation.csv"
    test_path = data_dir_path / "testing.csv"
    if all(p.exists() for p in [train_path, val_path, test_path]):
        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)
        test_df = pd.read_csv(test_path)
        logger.info("Loaded data from %s", data_dir)
    else:
        logger.warning("Processed data not found, generating synthetic data")
        syn = _generate_synthetic_training_data(5000, seq_len)
        train_df = syn.iloc[:3500].copy()
        val_df = syn.iloc[3500:4250].copy()
        test_df = syn.iloc[4250:].copy()
    train_df = train_df.reset_index(drop=True)
    val_df = val_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)
    logger.info(
        "Train: %d, Val: %d, Test: %d samples",
        len(train_df),
        len(val_df),
        len(test_df),
    )
    cat_cols = [
        c
        for c in feat_cols
        if pd.api.types.is_string_dtype(train_df[c]) or train_df[c].dtype == "object"
    ]
    for df in [train_df, val_df, test_df]:
        for c in cat_cols:
            df[c] = pd.Categorical(df[c]).codes
    if "Month" in feat_cols:
        for df in [train_df, val_df, test_df]:
            df["Month"] = df["Month"].astype(int)
    if "Week" in feat_cols:
        for df in [train_df, val_df, test_df]:
            df["Week"] = df["Week"].astype(float)
    feat_scaler = Scaler()
    tgt_scaler = Scaler()
    train_feat = torch.tensor(train_df[feat_cols].values, dtype=torch.float32)
    train_tgt = torch.tensor(train_df[tgt_cols].values, dtype=torch.float32)
    feat_scaler.fit(train_feat)
    tgt_scaler.fit(train_tgt)
    train_dataset = ClimateDataset(train_df, feat_cols, tgt_cols, seq_len)
    val_dataset = ClimateDataset(val_df, feat_cols, tgt_cols, seq_len)
    test_dataset = ClimateDataset(test_df, feat_cols, tgt_cols, seq_len)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader, test_loader, feat_scaler, tgt_scaler
