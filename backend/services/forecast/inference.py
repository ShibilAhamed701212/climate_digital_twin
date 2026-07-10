from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml

from models.data_loader import Scaler
from models.physics import PhysicsValidator
from models.predictor import load_model, predict
from models.registry import ModelRegistry

logger = logging.getLogger(__name__)

CONFIG_PATH = "models/configs/model_config.yaml"
CHECKPOINT_DIR = Path("models/checkpoints")
EXPORTED_DIR = Path("models/exported")
PROCESSED_DIR = Path("data/processed")


def load_config() -> dict[str, Any]:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class ForecastInference:
    def __init__(self, model_name: str = "transformer") -> None:
        self.model_name = model_name
        self.config = load_config()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        n_features = len(self.config["data"]["feature_columns"])
        n_targets = len(self.config["data"]["target_columns"])
        self.n_features = n_features
        self.n_targets = n_targets
        self.seq_len = self.config["data"]["sequence_length"]
        self.model = self._load_best_model()
        self.scaler = self._load_scaler()
        self.validator = PhysicsValidator()
        self.registry = ModelRegistry()
        if self.registry.contains(model_name):
            logger.info("Model '%s' found in registry", model_name)

    def _load_best_model(self) -> nn.Module:
        ckpt_path = CHECKPOINT_DIR / f"{self.model_name}_best.pt"
        export_path = EXPORTED_DIR / f"{self.model_name}_best.pt"
        if export_path.exists():
            model = torch.jit.load(export_path, map_location=self.device)
            model.eval()
            logger.info("Loaded TorchScript model from %s", export_path)
            return model
        if ckpt_path.exists():
            return load_model(
                self.model_name,
                str(ckpt_path),
                self.n_features,
                self.n_targets,
                self.config,
            )
        raise FileNotFoundError(
            f"No checkpoint found for model '{self.model_name}' "
            f"(checked {ckpt_path} and {export_path})"
        )

    def _load_scaler(self) -> Scaler | None:
        scaler_path = EXPORTED_DIR / "target_scaler.pkl"
        if not scaler_path.exists():
            logger.warning(
                "Target scaler not found at %s, predictions will be un-scaled", scaler_path
            )
            return None
        try:
            return joblib.load(scaler_path)
        except Exception as e:
            logger.warning("Failed to load scaler from %s: %s", scaler_path, e)
            return None

    def _load_latest_data(self) -> torch.Tensor:
        """Load latest seq_len rows from processed data as input tensor.

        Returns tensor of shape (1, seq_len, n_features).
        Falls back to synthetic data if no processed data is found.
        """
        feature_cols = self.config["data"]["feature_columns"]
        seq_len = self.seq_len
        fallback_used = True

        for csv_name in ["testing.csv", "validation.csv", "training.csv"]:
            csv_path = PROCESSED_DIR / csv_name
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path)
                    available = len(df)
                    if available >= seq_len:
                        latest = df.iloc[-seq_len:][feature_cols]
                        fallback_used = False
                        logger.info("Loaded last %d rows from %s", seq_len, csv_path)
                        break
                except Exception as e:
                    logger.warning("Failed to load %s: %s", csv_path, e)
                    continue
        else:
            logger.warning("No processed data found, using synthetic input")
            latest = pd.DataFrame(
                {col: np.random.default_rng(42).uniform(0, 1, seq_len) for col in feature_cols}
            )

        tensor = torch.tensor(latest.values, dtype=torch.float32).unsqueeze(0)
        if fallback_used:
            logger.warning("Fallback synthetic data used for input")
        return tensor

    def predict(self, input_data: torch.Tensor | None = None) -> dict[str, Any]:
        if input_data is None:
            input_data = self._load_latest_data()
        return predict(self.model, input_data, self.scaler)

    def get_available_models(self) -> list[str]:
        models = []
        for p in CHECKPOINT_DIR.glob("*_best.pt"):
            models.append(p.stem.replace("_best", ""))
        for p in EXPORTED_DIR.glob("*_best.pt"):
            name = p.stem.replace("_best", "")
            if name not in models:
                models.append(name)
        return sorted(models)

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "architecture": type(self.model).__name__,
            "device": str(self.device),
            "n_features": self.n_features,
            "n_targets": self.n_targets,
            "checkpoint_path": str(CHECKPOINT_DIR / f"{self.model_name}_best.pt"),
        }
