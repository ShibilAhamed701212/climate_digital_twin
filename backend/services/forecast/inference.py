"""Forecast engine inference — REAL data and REAL+VALIDATED models only.

Phase 6: the synthetic-input fallback is removed. If REAL input or a
REAL+VALIDATED model is unavailable, a DatasetNotFoundError is raised
instead of fabricating a prediction from random data.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import yaml

from models.data_loader import (
    DatasetNotFoundError,
    Scaler,
    load_scalers,
    needs_scaling,
    verify_dataset_manifest,
)
from models.physics import PhysicsValidator
from models.predictor import load_model, predict
from models.registry import ModelRegistry

logger = logging.getLogger(__name__)

CONFIG_PATH = "models/configs/model_config.yaml"
REAL_DATA_DIR = "data/real"

_ARCH_TO_MODEL = {
    "BaselineModel": "baseline",
    "LSTMModel": "lstm",
    "TransformerModel": "transformer",
}


def load_config() -> dict[str, Any]:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class ForecastInference:
    def __init__(self, model_name: str | None = None) -> None:
        self.registry = ModelRegistry()
        self.entry = self._select_model(model_name)
        self.model_name = self.entry["name"]
        self.config = self.entry.get("config") or load_config()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.n_features = len(self.config["data"]["feature_columns"])
        self.n_targets = len(self.config["data"]["target_columns"])
        self.seq_len = self.config["data"]["sequence_length"]
        model_type = _ARCH_TO_MODEL.get(self.entry.get("architecture", ""))
        if model_type is None:
            raise ValueError(f"Unknown architecture '{self.entry.get('architecture')}'")
        self.model_type: str = model_type
        self.model = self._load_model()
        self.feat_scaler, self.scaler = self._load_scalers()
        self.validator = PhysicsValidator()

    def _select_model(self, model_name: str | None) -> dict[str, Any]:
        """Choose a REAL + VALIDATED model, or a named model if it qualifies."""
        if model_name:
            try:
                entry = self.registry.get(model_name)
            except KeyError:
                entry = None
            if entry and entry.get("authenticity") == "REAL" and entry.get("status") == "VALIDATED":
                logger.info("Using named model '%s' (REAL+VALIDATED)", model_name)
                return entry
            logger.warning(
                "Model '%s' is not REAL+VALIDATED (auth=%s status=%s); selecting best production model",
                model_name,
                entry.get("authenticity", "UNKNOWN") if entry else "UNKNOWN",
                entry.get("status", "?") if entry else "?",
            )
        try:
            entry = self.registry.get_best(
                metric="rmse", ascending=True, require_validated=True, require_real=True
            )
        except KeyError as exc:
            raise DatasetNotFoundError(
                "No REAL + VALIDATED model in registry. Train one with "
                "'python -m models.forecast_cli train' first."
            ) from exc
        logger.info("Selected production model '%s'", entry["name"])
        return entry

    def _load_model(self) -> nn.Module:
        ckpt_path = Path(self.entry["checkpoint_path"])
        if not ckpt_path.exists():
            raise DatasetNotFoundError(f"Checkpoint not found: {ckpt_path}")
        return load_model(
            self.model_type,
            str(ckpt_path),
            self.n_features,
            self.n_targets,
            self.config,
        )

    def _load_scalers(self) -> tuple["Scaler | None", "Scaler | None"]:
        if not needs_scaling(self.model_type):
            return None, None
        feat_scaler, tgt_scaler = load_scalers(self.model_name)
        if feat_scaler is None or tgt_scaler is None:
            raise DatasetNotFoundError(
                f"Scalers missing for model '{self.model_name}' — cannot run scaled inference"
            )
        return feat_scaler, tgt_scaler

    def _load_latest_data(self) -> torch.Tensor:
        """Load the last seq_len rows of the REAL testing split.

        Raises DatasetNotFoundError if REAL data is missing or fails
        manifest verification. Never falls back to synthetic input.
        """
        verify_dataset_manifest(REAL_DATA_DIR)
        import pandas as pd

        df = pd.read_csv(f"{REAL_DATA_DIR}/testing.csv")
        available = len(df)
        if available < self.seq_len:
            raise DatasetNotFoundError(
                f"REAL testing split has {available} rows, need at least {self.seq_len}"
            )
        feature_cols = self.config["data"]["feature_columns"]
        latest = df.iloc[-self.seq_len :][feature_cols].copy()
        # Encode categorical feature columns exactly as training does
        # (data_loader.load_datasets: pd.Categorical().codes). All splits
        # share the same category set, so codes are deterministic.
        for c in feature_cols:
            if pd.api.types.is_string_dtype(latest[c]) or latest[c].dtype == "object":
                latest[c] = pd.Categorical(latest[c]).codes
        logger.info("Loaded last %d rows from %s/testing.csv", self.seq_len, REAL_DATA_DIR)
        return torch.tensor(latest.values, dtype=torch.float32).unsqueeze(0)

    def predict(self, input_data: torch.Tensor | None = None) -> dict[str, Any]:
        if input_data is None:
            input_data = self._load_latest_data()
        if self.feat_scaler is not None:
            input_data = self.feat_scaler.transform(input_data)
        return predict(self.model, input_data, self.scaler)

    def get_available_models(self) -> list[str]:
        return [
            m["name"]
            for m in self.registry.list_models()
            if m.get("authenticity") == "REAL" and m.get("status") == "VALIDATED"
        ]

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "architecture": self.entry.get("architecture", ""),
            "device": str(self.device),
            "n_features": self.n_features,
            "n_targets": self.n_targets,
            "checkpoint_path": self.entry.get("checkpoint_path", ""),
            "authenticity": self.entry.get("authenticity", ""),
            "status": self.entry.get("status", ""),
        }
