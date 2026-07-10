"""Evaluation metrics and reporting.

Computes RMSE, MAE, R², SMAPE. Generates plots: predictions vs actuals,
error distribution, residuals. Compares across model architectures.
Exports evaluation reports to models/evaluation/.

SMAPE (Symmetric Mean Absolute Percentage Error) is used instead of MAPE
because MAPE is undefined when actual values are zero, which commonly occurs
with rainfall data. SMAPE is bounded between 0%% and 200%%, symmetric, and
handles zero actual values correctly.
"""

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


def compute_rmse(y_true: torch.Tensor, y_pred: torch.Tensor) -> float:
    """Compute Root Mean Squared Error."""
    return float(torch.sqrt(torch.mean((y_true - y_pred) ** 2)))


def compute_mae(y_true: torch.Tensor, y_pred: torch.Tensor) -> float:
    """Compute Mean Absolute Error."""
    return float(torch.mean(torch.abs(y_true - y_pred)))


def compute_r2(y_true: torch.Tensor, y_pred: torch.Tensor) -> float:
    """Compute R² score."""
    ss_res = torch.sum((y_true - y_pred) ** 2)
    ss_tot = torch.sum((y_true - torch.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


def compute_mape(y_true: torch.Tensor, y_pred: torch.Tensor) -> float:
    """Compute Mean Absolute Percentage Error.

    Note: MAPE is undefined when y_true contains zeros (common in rainfall data).
    Prefer :func:`compute_smape` for climate prediction tasks.
    """
    epsilon = 1e-8
    abs_pct = torch.abs((y_true - y_pred) / (torch.abs(y_true) + epsilon))
    return float(torch.mean(abs_pct) * 100)


def compute_smape(y_true: torch.Tensor, y_pred: torch.Tensor) -> float:
    """Compute Symmetric Mean Absolute Percentage Error.

    SMAPE is bounded between 0%% and 200%%, symmetric, and handles zero
    actual values correctly — unlike MAPE which diverges when actual is zero.

    Formula: 100%% * (2 * |y_true - y_pred|) / (|y_true| + |y_pred| + epsilon)
    """
    epsilon = 1e-8
    numerator = 2.0 * torch.abs(y_true - y_pred)
    denominator = torch.abs(y_true) + torch.abs(y_pred) + epsilon
    return float(torch.mean(numerator / denominator) * 100)


def compute_metrics(y_true: torch.Tensor, y_pred: torch.Tensor) -> dict[str, float]:
    """Compute all evaluation metrics.

    Returns dict with keys: rmse, mae, r2, smape.
    SMAPE is preferred over MAPE for climate data as it handles zero rainfall.
    """
    return {
        "rmse": round(compute_rmse(y_true, y_pred), 4),
        "mae": round(compute_mae(y_true, y_pred), 4),
        "r2": round(compute_r2(y_true, y_pred), 4),
        "smape": round(compute_smape(y_true, y_pred), 4),
    }


def evaluate_model(
    model: nn.Module,
    data_loader: DataLoader,
    device: torch.device,
) -> dict[str, Any]:
    """Evaluate model on a DataLoader and return metrics + predictions."""
    model.eval()
    all_preds: list[torch.Tensor] = []
    all_targets: list[torch.Tensor] = []
    with torch.no_grad():
        for x, y in data_loader:
            x = x.to(device)
            output = model(x)
            all_preds.append(output.cpu())
            all_targets.append(y)
    y_pred = torch.cat(all_preds, dim=0)
    y_true = torch.cat(all_targets, dim=0)
    metrics = compute_metrics(y_true, y_pred)
    return {
        "metrics": metrics,
        "predictions": y_pred,
        "targets": y_true,
    }


def generate_plots(
    eval_results: dict[str, Any],
    output_dir: str = "models/evaluation",
    model_name: str = "model",
    target_names: list[str] | None = None,
) -> list[str]:
    """Generate evaluation plots: predictions vs actuals, error distribution, residuals.

    Returns list of saved plot file paths.
    """
    if target_names is None:
        target_names = ["Rainfall", "MaxTemp", "MinTemp"]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    saved_files: list[str] = []
    y_pred = eval_results["predictions"]
    y_true = eval_results["targets"]
    for i, name in enumerate(target_names):
        if i >= y_pred.size(1):
            break
        pred_i = y_pred[:, i].numpy()
        true_i = y_true[:, i].numpy()
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        ax1, ax2, ax3 = axes
        ax1.scatter(true_i, pred_i, alpha=0.5, s=2)
        ax1.plot([true_i.min(), true_i.max()], [true_i.min(), true_i.max()], "r--", lw=1)
        ax1.set_xlabel("Actual")
        ax1.set_ylabel("Predicted")
        ax1.set_title(f"{name}: Predictions vs Actuals")
        errors = pred_i - true_i
        ax2.hist(errors, bins=50, alpha=0.7, edgecolor="black")
        ax2.set_xlabel("Error")
        ax2.set_ylabel("Frequency")
        ax2.set_title(f"{name}: Error Distribution")
        ax3.scatter(pred_i, errors, alpha=0.5, s=2)
        ax3.axhline(y=0, color="r", linestyle="--", lw=1)
        ax3.set_xlabel("Predicted")
        ax3.set_ylabel("Residual")
        ax3.set_title(f"{name}: Residuals")
        plt.tight_layout()
        plot_path = output_path / f"{model_name}_{name.lower()}_eval.png"
        plt.savefig(plot_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        saved_files.append(str(plot_path))
        logger.info("Saved plot: %s", plot_path)
    return saved_files


def save_evaluation_report(
    all_metrics: dict[str, dict[str, float]],
    output_dir: str = "models/evaluation",
) -> str:
    """Save comparison report across all models."""
    output_path = Path(output_dir) / "model_comparison.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    logger.info("Model comparison saved to %s", output_path)
    return str(output_path)
