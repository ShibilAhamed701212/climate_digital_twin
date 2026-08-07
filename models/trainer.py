"""Module 3: Training Engine.

Supports GPU/CPU training, configurable loss functions, optimizers,
schedulers, early stopping, model checkpointing, and training metrics logging.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


def get_device(device_pref: str = "auto") -> torch.device:
    """Get the compute device (GPU if available, else CPU)."""
    if device_pref == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_pref)


def set_random_seed(seed: int = 42) -> None:
    """Set random seeds for reproducibility."""
    import random

    import numpy as np

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class ModelNotFoundError(Exception):
    """Raised when a model file is not found."""


class EarlyStopping:
    """Stop training when validation loss stops improving."""

    def __init__(self, patience: int = 10, min_delta: float = 1e-6) -> None:
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss: float | None = None
        self.early_stop = False

    def __call__(self, val_loss: float) -> None:
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0


def get_loss_fn(name: str) -> nn.Module:
    """Get loss function by name."""
    if name == "mse":
        return nn.MSELoss()
    elif name == "mae":
        return nn.L1Loss()
    else:
        raise ValueError(f"Unknown loss function: {name}")


def get_optimizer(name: str, params, lr: float) -> torch.optim.Optimizer:
    """Get optimizer by name."""
    if name == "adam":
        return torch.optim.Adam(params, lr=lr)
    elif name == "sgd":
        return torch.optim.SGD(params, lr=lr)
    else:
        raise ValueError(f"Unknown optimizer: {name}")


def train_one_epoch(
    model: nn.Module,
    train_loader: DataLoader,
    loss_fn: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    """Train for one epoch and return average loss."""
    model.train()
    total_loss = 0.0
    num_batches = 0
    for x, y in train_loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        output = model(x)
        loss = loss_fn(output, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        num_batches += 1
    return total_loss / max(num_batches, 1)


def validate_one_epoch(
    model: nn.Module,
    val_loader: DataLoader,
    loss_fn: nn.Module,
    device: torch.device,
) -> float:
    """Validate for one epoch and return average loss."""
    model.eval()
    total_loss = 0.0
    num_batches = 0
    with torch.no_grad():
        for x, y in val_loader:
            x, y = x.to(device), y.to(device)
            output = model(x)
            loss = loss_fn(output, y)
            total_loss += loss.item()
            num_batches += 1
    return total_loss / max(num_batches, 1)


_ARCH_TO_CONFIG = {
    "baseline": "baseline",
    "lstm": "lstm",
    "transformer": "transformer",
}


def _resolve_model_config(model_type: str, config: dict[str, Any]) -> dict[str, Any]:
    section = _ARCH_TO_CONFIG.get(model_type)
    if section is None:
        raise ValueError(
            f"Unknown model type '{model_type}'. Valid types: {list(_ARCH_TO_CONFIG.keys())}"
        )
    cfg = config.get(section)
    if cfg is None:
        raise ValueError(
            f"Model type '{model_type}' maps to config section '{section}' "
            f"but that section is missing from model_config.yaml"
        )
    return cfg


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: dict[str, Any],
    checkpoint_dir: str = "models/checkpoints",
    model_name: str = "model",
    model_type: str | None = None,
) -> dict[str, Any]:
    """Full training loop with early stopping and checkpointing.

    Args:
        model_type: Maps to config section (baseline/lstm/transformer).
                    Required — raises ValueError if None.
    Returns training history dict.
    """
    if model_type is None:
        if model_name:
            candidate = model_name.split("_")[0].lower()
            if candidate in (
                "baseline",
                "lstm",
                "transformer",
                "patchtst",
                "itransformer",
                "timemixer",
                "xgboost",
                "prophet",
            ):
                model_type = candidate
        if model_type is None:
            raise ValueError(
                "model_type is required — must be 'baseline', 'lstm', or 'transformer'"
            )
    device_name = config["training"].get("device", "auto")
    device = get_device(device_name)
    seed = config["training"].get("random_seed", 42)
    set_random_seed(seed)
    model = model.to(device)
    loss_name = config["training"].get("loss", "mse")
    loss_fn = get_loss_fn(loss_name)
    opt_name = config["training"].get("optimizer", "adam")
    model_cfg = _resolve_model_config(model_type, config)
    lr = model_cfg.get("learning_rate", 0.001)
    optimizer = get_optimizer(opt_name, model.parameters(), lr)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)
    patience = config["training"].get("early_stopping_patience", 10)
    early_stopping = EarlyStopping(patience=patience)
    epochs = model_cfg.get("epochs", 50)
    checkpoint_dir_path = Path(checkpoint_dir)
    checkpoint_dir_path.mkdir(parents=True, exist_ok=True)
    history = {
        "train_loss": [],
        "val_loss": [],
        "best_epoch": 0,
        "best_val_loss": float("inf"),
        "epochs_trained": 0,
        "model_name": model_name,
    }
    logger.info("Training %s on %s for up to %d epochs", model_name, device, epochs)
    start_time = time.time()
    for epoch in range(1, epochs + 1):
        train_loss = train_one_epoch(model, train_loader, loss_fn, optimizer, device)
        val_loss = validate_one_epoch(model, val_loader, loss_fn, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        scheduler.step(val_loss)
        if val_loss < history["best_val_loss"]:
            history["best_val_loss"] = val_loss
            history["best_epoch"] = epoch
            checkpoint_path = checkpoint_dir_path / f"{model_name}_best.pt"
            torch.save(model.state_dict(), checkpoint_path)
        if epoch % 5 == 0 or epoch == 1:
            logger.info(
                "Epoch %d/%d | Train Loss: %.6f | Val Loss: %.6f",
                epoch,
                epochs,
                train_loss,
                val_loss,
            )
        early_stopping(val_loss)
        if early_stopping.early_stop:
            logger.info("Early stopping triggered at epoch %d", epoch)
            break
    elapsed = time.time() - start_time
    history["epochs_trained"] = epoch
    history["elapsed_seconds"] = round(elapsed, 2)
    logger.info(
        "Training complete: %d epochs in %.2fs | Best val loss: %.6f",
        epoch,
        elapsed,
        history["best_val_loss"],
    )
    return history


def save_training_history(
    history: dict[str, Any],
    output_dir: str = "models/evaluation",
    model_name: str = "model",
) -> str:
    """Save training history as JSON."""
    output_path = Path(output_dir) / f"{model_name}_history.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {}
    for k, v in history.items():
        if isinstance(v, list):
            serializable[k] = [float(x) if hasattr(x, "item") else x for x in v]
        else:
            serializable[k] = v
    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)
    logger.info("Training history saved to %s", output_path)
    return str(output_path)
