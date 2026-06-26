"""Module 5: Prediction API.

Standardized prediction interface that hides model complexities.
Loads best-performing model from checkpoint and makes predictions.
"""

import logging
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from models.baseline.model import BaselineModel
from models.data_loader import (
    PredictionError,
    Scaler,
)
from models.lstm.model import LSTMModel
from models.trainer import (
    ModelNotFoundError,
)
from models.transformer.model import TransformerModel

logger = logging.getLogger(__name__)

MODEL_REGISTRY: dict[str, Any] = {
    "baseline": BaselineModel,
    "lstm": LSTMModel,
    "transformer": TransformerModel,
}


def create_model(
    model_name: str,
    n_features: int,
    n_targets: int,
    config: dict[str, Any],
) -> nn.Module:
    """Create a model instance by name with the given configuration."""
    if model_name == "baseline":
        cfg = config.get("baseline", {})
        return BaselineModel(
            n_features=n_features,
            n_targets=n_targets,
            sequence_length=config["data"]["sequence_length"],
            hidden_layers=cfg.get("hidden_layers", [64, 32]),
            dropout=cfg.get("dropout", 0.1),
        )
    elif model_name == "lstm":
        cfg = config.get("lstm", {})
        return LSTMModel(
            n_features=n_features,
            n_targets=n_targets,
            hidden_dim=cfg.get("hidden_dim", 128),
            num_layers=cfg.get("num_layers", 2),
            dropout=cfg.get("dropout", 0.2),
            bidirectional=cfg.get("bidirectional", False),
        )
    elif model_name == "transformer":
        cfg = config.get("transformer", {})
        return TransformerModel(
            n_features=n_features,
            n_targets=n_targets,
            d_model=cfg.get("d_model", 128),
            nhead=cfg.get("nhead", 4),
            num_encoder_layers=cfg.get("num_encoder_layers", 3),
            dim_feedforward=cfg.get("dim_feedforward", 512),
            dropout=cfg.get("dropout", 0.1),
        )
    else:
        raise ModelNotFoundError(f"Unknown model: {model_name}")


def load_model(
    model_name: str,
    checkpoint_path: str,
    n_features: int,
    n_targets: int,
    config: dict[str, Any],
) -> nn.Module:
    """Load a model from a checkpoint file."""
    model = create_model(model_name, n_features, n_targets, config)
    ckpt = Path(checkpoint_path)
    if not ckpt.exists():
        raise ModelNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    state_dict = torch.load(ckpt, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    logger.info("Loaded %s model from %s", model_name, checkpoint_path)
    return model


def predict(
    model: nn.Module,
    input_data: torch.Tensor,
    target_scaler: Scaler | None = None,
) -> dict[str, Any]:
    """Make predictions and return structured output with confidence intervals.

    Args:
        model: Trained PyTorch model.
        input_data: Tensor of shape (batch, seq_len, n_features).
        target_scaler: Optional scaler to inverse-transform predictions.

    Returns:
        Dict with keys: 'predictions', 'timestamps', 'confidence_intervals', 'metadata'.
    """
    try:
        model.eval()
        with torch.no_grad():
            raw_preds = model(input_data).cpu()
        if target_scaler is not None:
            raw_preds = target_scaler.inverse_transform(raw_preds)
        pred_list = raw_preds.tolist()
        if not isinstance(pred_list[0], list):
            pred_list = [pred_list]
        std_per_sample = raw_preds.std(dim=1, keepdim=True).expand_as(raw_preds)
        ci_lower = (raw_preds - 1.96 * std_per_sample).tolist()
        ci_upper = (raw_preds + 1.96 * std_per_sample).tolist()
        return {
            "predictions": pred_list,
            "confidence_intervals": {
                "lower": ci_lower,
                "upper": ci_upper,
            },
            "metadata": {
                "model_type": type(model).__name__,
                "n_predictions": len(pred_list),
                "n_variables": len(pred_list[0]) if pred_list else 0,
            },
        }
    except Exception as e:
        raise PredictionError(f"Prediction failed: {e}") from e


def export_model(model: nn.Module, path: str) -> None:
    """Export model in TorchScript format."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    scripted_model = torch.jit.script(model)
    scripted_model.save(output_path)
    logger.info("Model exported to %s", output_path)
