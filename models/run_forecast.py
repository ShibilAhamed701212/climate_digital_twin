#!/usr/bin/env python3
"""Phase 3 — Forecasting Engine Orchestrator.

Runs the complete training pipeline end-to-end:
  Data Load → Preprocessing → Model Selection → Training → Evaluation → Export

Usage:
    python models/run_forecast.py [--config models/configs/model_config.yaml]
"""

import logging
import sys
import time
from pathlib import Path

import torch
import yaml

from models.data_loader import load_data
from models.evaluator import (
    evaluate_model,
    generate_plots,
    save_evaluation_report,
)
from models.predictor import create_model, export_model
from models.trainer import (
    get_device,
    save_training_history,
    train_model,
)

CONFIG_PATH = "models/configs/model_config.yaml"
TARGET_NAMES = ["Rainfall", "MaxTemp", "MinTemp"]


def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """Configure logging to file and console."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "forecast_pipeline.log"
    logger = logging.getLogger("forecast")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(log_file, mode="w")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


def run_forecast(config_path: str = CONFIG_PATH) -> int:
    """Execute the full forecasting pipeline."""
    start_time = time.time()
    with open(config_path) as f:
        config = yaml.safe_load(f)
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("Phase 3 — Forecasting Engine Pipeline Started")
    logger.info("=" * 60)
    model_names = ["baseline", "lstm", "transformer"]
    try:
        logger.info("--- Step 1/4: Data Loading ---")
        train_loader, val_loader, test_loader, feat_scaler, tgt_scaler = load_data(
            config
        )
        n_features = len(config["data"]["feature_columns"])
        n_targets = len(config["data"]["target_columns"])
        logger.info("Features: %d, Targets: %d", n_features, n_targets)
        logger.info("--- Step 2/4: Training ---")
        all_results = {}
        for model_name in model_names:
            logger.info("Training %s ...", model_name)
            model = create_model(model_name, n_features, n_targets, config)
            history = train_model(
                model,
                train_loader,
                val_loader,
                config,
                checkpoint_dir="models/checkpoints",
                model_name=model_name,
            )
            save_training_history(history, model_name=model_name)
            all_results[model_name] = {"history": history}
        logger.info("--- Step 3/4: Evaluation ---")
        device = get_device(config["training"].get("device", "auto"))
        comparison = {}
        for model_name in model_names:
            model = create_model(model_name, n_features, n_targets, config)
            ckpt_path = Path("models/checkpoints") / f"{model_name}_best.pt"
            if ckpt_path.exists():
                model.load_state_dict(
                    torch.load(ckpt_path, map_location="cpu", weights_only=True)
                )
            model = model.to(device)
            eval_result = evaluate_model(model, test_loader, device)
            comparison[model_name] = eval_result["metrics"]
            _ = generate_plots(
                eval_result,
                model_name=model_name,
                target_names=TARGET_NAMES,
            )
            logger.info("%s metrics: %s", model_name, eval_result["metrics"])
        save_evaluation_report(comparison)
        logger.info("--- Step 4/4: Export ---")
        best_model_name = min(comparison, key=lambda k: comparison[k]["rmse"])
        logger.info("Best model: %s (RMSE: %.4f)", best_model_name, comparison[best_model_name]["rmse"])
        best_model = create_model(best_model_name, n_features, n_targets, config)
        best_ckpt = Path("models/checkpoints") / f"{best_model_name}_best.pt"
        if best_ckpt.exists():
            best_model.load_state_dict(
                torch.load(best_ckpt, map_location="cpu", weights_only=True)
            )
            export_path = f"models/exported/{best_model_name}_best.pt"
            export_model(best_model, export_path)
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("Phase 3 Pipeline Complete in %.2f seconds", elapsed)
        logger.info("=" * 60)
        return 0
    except Exception:
        logger.exception("Pipeline failed with unhandled exception")
        elapsed = time.time() - start_time
        logger.info("Pipeline failed after %.2f seconds", elapsed)
        return 1


if __name__ == "__main__":
    sys.exit(run_forecast())
