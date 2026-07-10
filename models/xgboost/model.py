from __future__ import annotations

import json
import logging
import time
import warnings
from typing import Any

import numpy as np
import pandas as pd

try:
    import xgboost as xgb

    _XGB_AVAILABLE = True
except ImportError:
    _XGB_AVAILABLE = False

_logger = logging.getLogger(__name__)


class TrainingHistory:
    def __init__(self, training_duration: float = 0.0) -> None:
        self.training_duration = training_duration
        self.train_losses: list[float] = []
        self.val_losses: list[float] = []
        self.best_epoch: int = 0
        self.best_val_loss: float = float("inf")


def _check_xgboost() -> None:
    if not _XGB_AVAILABLE:
        raise ImportError("XGBoost is required. Install it with: pip install xgboost")


class XGBoostModel:
    def __init__(
        self,
        params: dict[str, Any] | None = None,
        n_estimators: int = 300,
        max_depth: int = 8,
        learning_rate: float = 0.05,
        random_state: int = 42,
    ) -> None:
        _check_xgboost()
        self.params = params or {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "booster": "gbtree",
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "random_state": random_state,
        }
        self.params["n_estimators"] = n_estimators
        self.params["max_depth"] = max_depth
        self.params["learning_rate"] = learning_rate
        self.params["random_state"] = random_state
        self._model: xgb.XGBRegressor | None = None
        self._feature_names: list[str] = []
        self._is_trained = False

    def forward(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        return self.predict(X)

    def train(  # noqa: N803
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,  # noqa: N803
        y_val: pd.Series | None = None,
    ) -> TrainingHistory:
        self._feature_names = list(X_train.columns)
        eval_set = [(X_train.values, y_train.values)]
        eval_metric = self.params.get("eval_metric", "rmse")
        if X_val is not None and y_val is not None:
            eval_set.append((X_val.values, y_val.values))
        self._model = xgb.XGBRegressor(**self.params)
        start_time = time.monotonic()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model.fit(
                X_train.values,
                y_train.values,
                eval_set=eval_set,
                verbose=False,
            )
        duration = time.monotonic() - start_time
        self._is_trained = True
        history = TrainingHistory(training_duration=duration)
        if hasattr(self._model, "evals_result") and self._model.evals_result():
            evals = self._model.evals_result()
            if "validation_0" in evals and eval_metric in evals["validation_0"]:
                history.train_losses = evals["validation_0"][eval_metric]
            if "validation_1" in evals and eval_metric in evals["validation_1"]:
                history.val_losses = evals["validation_1"][eval_metric]
        if history.val_losses:
            min_idx = int(np.argmin(history.val_losses))
            history.best_epoch = min_idx
            history.best_val_loss = float(history.val_losses[min_idx])
        elif history.train_losses:
            history.best_val_loss = float(history.train_losses[-1])
        _logger.info(
            "XGBoost trained: %d estimators, depth=%d, duration=%.2fs",
            self.params.get("n_estimators", 300),
            self.params.get("max_depth", 8),
            duration,
        )
        return history

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        if not self._is_trained or self._model is None:
            raise RuntimeError("Model must be trained before prediction. Call train() first.")
        return self._model.predict(X.values)

    def get_feature_importance(self) -> dict[str, float]:
        if not self._is_trained or self._model is None:
            raise RuntimeError("Model must be trained first. Call train() first.")
        importance_type = self.params.get("importance_type", "weight")
        importance = self._model.get_booster().get_score(importance_type=importance_type)
        result: dict[str, float] = {}
        for i, name in enumerate(self._feature_names):
            key = f"f{i}"
            if key in importance:
                result[name] = float(importance[key])
        return result

    def tune_hyperparameters(  # noqa: N803
        self,
        X_train: pd.DataFrame,  # noqa: N803
        y_train: pd.Series,
        param_grid: dict[str, list[Any]] | None = None,
        cv: int = 3,
        verbose: bool = False,
    ) -> dict[str, Any]:
        _check_xgboost()
        if param_grid is None:
            param_grid = {
                "max_depth": [4, 6, 8],
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.05, 0.1],
                "subsample": [0.7, 0.8],
                "colsample_bytree": [0.7, 0.8],
            }
        from sklearn.model_selection import GridSearchCV

        base_params = dict(self.params)
        for key in param_grid:
            base_params.pop(key, None)
        model = xgb.XGBRegressor(**base_params)
        grid_search = GridSearchCV(
            estimator=model,
            param_grid=param_grid,
            cv=cv,
            scoring="neg_root_mean_squared_error",
            verbose=verbose,
            n_jobs=1,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            grid_search.fit(X_train.values, y_train.values)
        best_params = grid_search.best_params_
        self.params.update(best_params)
        self.params["n_estimators"] = best_params.get(
            "n_estimators", self.params.get("n_estimators", 300)
        )
        self.params["max_depth"] = best_params.get("max_depth", self.params.get("max_depth", 8))
        self.params["learning_rate"] = best_params.get(
            "learning_rate", self.params.get("learning_rate", 0.05)
        )
        _logger.info(
            "Hyperparameter tuning completed. Best params: %s, score: %.4f",
            best_params,
            grid_search.best_score_,
        )
        return best_params

    def save(self, path: str) -> None:
        if not self._is_trained or self._model is None:
            raise RuntimeError("Model must be trained before saving. Call train() first.")
        self._model.save_model(path)
        meta_path = path + ".meta.json"
        metadata = {
            "params": self.params,
            "feature_names": self._feature_names,
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f)
        _logger.info("XGBoost model saved to %s", path)

    def load(self, path: str) -> None:
        _check_xgboost()
        self._model = xgb.XGBRegressor()
        self._model.load_model(path)
        meta_path = path + ".meta.json"
        try:
            with open(meta_path) as f:
                metadata = json.load(f)
            self.params = metadata.get("params", self.params)
            self._feature_names = metadata.get("feature_names", [])
        except FileNotFoundError:
            _logger.warning("Metadata file not found: %s", meta_path)
        self._is_trained = True
        _logger.info("XGBoost model loaded from %s", path)


XGBoostForecastModel = XGBoostModel


__all__ = [
    "XGBoostModel",
    "XGBoostForecastModel",
    "TrainingHistory",
]
