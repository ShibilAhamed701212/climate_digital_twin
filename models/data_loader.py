"""Module 1: Data Loader.

Loads processed train/val/test splits from data/processed/,
creates PyTorch Dataset and DataLoader with configurable batch size
and sequence length. Supports feature scaling and target normalization.
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)

_SCALER_DIR = "models/checkpoints"


def save_scalers(
    feat_scaler: "Scaler",
    tgt_scaler: "Scaler",
    model_name: str,
    scaler_dir: str = _SCALER_DIR,
) -> tuple[str, str]:
    """Persist feature and target scalers alongside checkpoints."""
    import pickle as _pickle

    dir_path = Path(scaler_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    feat_path = str(dir_path / f"{model_name}_feat_scaler.pkl")
    tgt_path = str(dir_path / f"{model_name}_tgt_scaler.pkl")
    with open(feat_path, "wb") as f:
        _pickle.dump(feat_scaler, f)
    with open(tgt_path, "wb") as f:
        _pickle.dump(tgt_scaler, f)
    logger.info("Scalers saved: %s, %s", feat_path, tgt_path)
    return feat_path, tgt_path


def load_scalers(
    model_name: str,
    scaler_dir: str = _SCALER_DIR,
) -> tuple:
    """Load persisted scalers. Returns (None, None) if not found."""
    import pickle as _pickle

    feat_path = Path(scaler_dir) / f"{model_name}_feat_scaler.pkl"
    tgt_path = Path(scaler_dir) / f"{model_name}_tgt_scaler.pkl"
    feat: Scaler | None = None
    tgt: Scaler | None = None
    if feat_path.exists():
        with open(feat_path, "rb") as f:
            feat = _pickle.load(f)
    if tgt_path.exists():
        with open(tgt_path, "rb") as f:
            tgt = _pickle.load(f)
    return feat, tgt


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


class DatasetNotFoundError(Exception):
    """Raised when required dataset files are missing."""


def verify_dataset_manifest(data_dir: str) -> dict[str, Any]:
    manifest_path = Path(data_dir) / "dataset_manifest.json"
    if not manifest_path.exists():
        raise DatasetNotFoundError(f"No dataset manifest found at {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    for fname, expected_cs in manifest.get("checksums", {}).items():
        actual = Path(data_dir) / fname
        if not actual.exists():
            raise DatasetNotFoundError(f"Dataset file missing: {actual}")
        import hashlib

        actual_cs = hashlib.sha256(actual.read_bytes()).hexdigest()[:16]
        if actual_cs != expected_cs:
            raise DatasetNotFoundError(
                f"Checksum mismatch for {fname}: expected {expected_cs}, got {actual_cs}"
            )
    return manifest


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


NEURAL_FAMILIES = {"lstm", "transformer", "patchtst", "itransformer", "timemixer"}


def needs_scaling(model_type: str | None) -> bool:
    if model_type is None:
        return False
    return model_type in NEURAL_FAMILIES


def load_data(
    config: dict[str, Any],
    data_dir: str | None = None,
    require_real: bool = False,
    scale: bool = False,
) -> tuple[DataLoader, DataLoader, DataLoader, Scaler, Scaler]:
    """Load train/val/test splits and create DataLoaders.

    When require_real=True, the data_dir must contain dataset_manifest.json
    with valid checksums — fails instead of falling back to synthetic data.

    When scale=True, features and targets are min-max scaled using TRAIN-only
    statistics.  Neural models (LSTM, Transformer, etc.) require scaling.

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
        if require_real:
            verify_dataset_manifest(data_dir)
            logger.info("Dataset manifest verified for %s", data_dir)
    else:
        if require_real:
            raise DatasetNotFoundError(
                f"Real data required but not found at {data_dir}. "
                "Run 'python -m models.build_dataset' first."
            )
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
    if scale:
        train_feat_scaled = feat_scaler.transform(train_feat)
        train_tgt_scaled = tgt_scaler.transform(train_tgt)
        train_df = train_df.copy()
        train_df[feat_cols] = train_feat_scaled.numpy()
        train_df[tgt_cols] = train_tgt_scaled.numpy()
        val_feat = torch.tensor(val_df[feat_cols].values, dtype=torch.float32)
        val_tgt = torch.tensor(val_df[tgt_cols].values, dtype=torch.float32)
        val_df = val_df.copy()
        val_df[feat_cols] = feat_scaler.transform(val_feat).numpy()
        val_df[tgt_cols] = tgt_scaler.transform(val_tgt).numpy()
        test_feat = torch.tensor(test_df[feat_cols].values, dtype=torch.float32)
        test_tgt = torch.tensor(test_df[tgt_cols].values, dtype=torch.float32)
        test_df = test_df.copy()
        test_df[feat_cols] = feat_scaler.transform(test_feat).numpy()
        test_df[tgt_cols] = tgt_scaler.transform(test_tgt).numpy()
        logger.info("Features and targets scaled using TRAIN statistics")
    train_dataset = ClimateDataset(train_df, feat_cols, tgt_cols, seq_len)
    val_dataset = ClimateDataset(val_df, feat_cols, tgt_cols, seq_len)
    test_dataset = ClimateDataset(test_df, feat_cols, tgt_cols, seq_len)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader, test_loader, feat_scaler, tgt_scaler
