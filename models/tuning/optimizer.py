from __future__ import annotations

import itertools
import logging
import time
from typing import Any

import numpy as np
import pandas as pd

_logger = logging.getLogger(__name__)


class HyperparameterOptimizer:
    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed
        self._trials: list[dict[str, Any]] = []
        self._best_params: dict[str, Any] = {}
        self._best_metrics: dict[str, float] = {}

    def grid_search(  # noqa: N803
        self,
        model_class: type,
        param_grid: dict[str, list[Any]],
        X_train: np.ndarray,  # noqa: N803
        y_train: np.ndarray,
        X_val: np.ndarray,  # noqa: N803
        y_val: np.ndarray,
        metric: str = "rmse",
        maximize: bool = False,
        fit_params: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, float]]:
        if not param_grid:
            raise ValueError("param_grid must not be empty")
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        n_combos = len(combinations)
        if n_combos > 1000:
            _logger.warning(
                "Grid search has %d combinations; consider using random_search instead",
                n_combos,
            )
        fit_params = fit_params or {}
        best_score = -float("inf") if maximize else float("inf")
        best_config: dict[str, Any] = {}
        for i, combo in enumerate(combinations):
            params = dict(zip(keys, combo, strict=False))
            _logger.info("Trial %d/%d: %s", i + 1, n_combos, params)
            start_time = time.monotonic()
            try:
                result = self._evaluate_params(
                    model_class=model_class,
                    params=params,
                    X_train=X_train,
                    y_train=y_train,
                    X_val=X_val,
                    y_val=y_val,
                    fit_params=fit_params,
                )
                trial_metrics = result["metrics"]
                score = trial_metrics.get(metric, float("inf"))
                duration = time.monotonic() - start_time
                trial = {
                    "params": params,
                    "metrics": trial_metrics,
                    "duration": duration,
                    "trial_number": i + 1,
                }
                self._trials.append(trial)
                is_better = score > best_score if maximize else score < best_score
                if is_better or not best_config:
                    best_score = score
                    best_config = params
                    self._best_params = params
                    self._best_metrics = trial_metrics
                _logger.info(
                    "Trial %d: %s=%.4f (duration=%.2fs)",
                    i + 1,
                    metric,
                    score,
                    duration,
                )
            except Exception as exc:
                _logger.warning("Trial %d failed: %s", i + 1, exc)
                self._trials.append(
                    {
                        "params": params,
                        "error": str(exc),
                        "trial_number": i + 1,
                    }
                )
        _logger.info(
            "Grid search completed. Best %s: %.4f with params: %s",
            metric,
            best_score,
            best_config,
        )
        return self._best_params, self._best_metrics

    def random_search(  # noqa: N803
        self,
        model_class: type,
        param_distributions: dict[str, list[Any]],
        n_iter: int,
        X_train: np.ndarray,  # noqa: N803
        y_train: np.ndarray,
        X_val: np.ndarray,  # noqa: N803
        y_val: np.ndarray,
        metric: str = "rmse",
        maximize: bool = False,
        fit_params: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, float]]:
        if not param_distributions:
            raise ValueError("param_distributions must not be empty")
        rng = np.random.default_rng(self.random_seed)
        keys = list(param_distributions.keys())
        fit_params = fit_params or {}
        best_score = -float("inf") if maximize else float("inf")
        best_config: dict[str, Any] = {}
        for i in range(n_iter):
            params = {}
            for key in keys:
                values = param_distributions[key]
                params[key] = values[int(rng.integers(len(values)))]
            _logger.info("Random trial %d/%d: %s", i + 1, n_iter, params)
            start_time = time.monotonic()
            try:
                result = self._evaluate_params(
                    model_class=model_class,
                    params=params,
                    X_train=X_train,
                    y_train=y_train,
                    X_val=X_val,
                    y_val=y_val,
                    fit_params=fit_params,
                )
                trial_metrics = result["metrics"]
                score = trial_metrics.get(metric, float("inf"))
                duration = time.monotonic() - start_time
                trial = {
                    "params": params,
                    "metrics": trial_metrics,
                    "duration": duration,
                    "trial_number": i + 1,
                }
                self._trials.append(trial)
                is_better = score > best_score if maximize else score < best_score
                if is_better or not best_config:
                    best_score = score
                    best_config = params
                    self._best_params = params
                    self._best_metrics = trial_metrics
                _logger.info(
                    "Random trial %d: %s=%.4f (duration=%.2fs)",
                    i + 1,
                    n_iter,
                    metric,
                    score,
                    duration,
                )
            except Exception as exc:
                _logger.warning("Random trial %d failed: %s", i + 1, exc)
                self._trials.append(
                    {
                        "params": params,
                        "error": str(exc),
                        "trial_number": i + 1,
                    }
                )
        _logger.info(
            "Random search completed. Best %s: %.4f with params: %s",
            metric,
            best_score,
            best_config,
        )
        return self._best_params, self._best_metrics

    def _evaluate_params(  # noqa: N803
        self,
        model_class: type,
        params: dict[str, Any],
        X_train: np.ndarray | None,  # noqa: N803
        y_train: np.ndarray | None,
        X_val: np.ndarray | None,  # noqa: N803
        y_val: np.ndarray | None,
        fit_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        model = model_class(**params)
        X_train_df = self._to_dataframe(X_train) if X_train is not None else None  # noqa: N806
        y_train_s = self._to_series(y_train) if y_train is not None else None
        X_val_df = self._to_dataframe(X_val) if X_val is not None else None  # noqa: N806
        y_val_s = self._to_series(y_val) if y_val is not None else None
        history = model.train(
            X_train=X_train_df,
            y_train=y_train_s,
            X_val=X_val_df,
            y_val=y_val_s,
            **(fit_params or {}),
        )
        if X_val is not None and y_val is not None:
            val_pred = model.predict(X_val_df)
            y_val_flat = np.asarray(y_val).ravel()
            val_pred_flat = np.asarray(val_pred).ravel()
            rmse = float(np.sqrt(np.mean((val_pred_flat - y_val_flat) ** 2)))
            mae = float(np.mean(np.abs(val_pred_flat - y_val_flat)))
            epsilon = 1e-10
            y_var = max(np.sum((y_val_flat - np.mean(y_val_flat)) ** 2), epsilon)
            r2 = float(1 - np.sum((val_pred_flat - y_val_flat) ** 2) / y_var)
            metrics = {"rmse": rmse, "mae": mae, "r2": r2}
        else:
            metrics = {"train_loss": history.best_val_loss}
        return {"model": model, "history": history, "metrics": metrics}

    @staticmethod
    def _to_dataframe(X: np.ndarray) -> pd.DataFrame:  # noqa: N803
        if isinstance(X, pd.DataFrame):
            return X
        if X.ndim == 1:
            X = X.reshape(-1, 1)  # noqa: N806
        return pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])

    @staticmethod
    def _to_series(y: np.ndarray) -> pd.Series:
        if isinstance(y, pd.Series):
            return y
        return pd.Series(np.asarray(y).ravel(), name="target")

    def get_trial_history(self) -> list[dict[str, Any]]:
        return list(self._trials)

    def plot_optimization(self) -> dict[str, Any]:
        scores = []
        params_history = []
        for trial in self._trials:
            if "error" not in trial and trial.get("metrics"):
                metrics = trial["metrics"]
                score = metrics.get("rmse", metrics.get("train_loss", float("nan")))
                scores.append(score)
                params_history.append(trial["params"])
        return {
            "param_names": list(self._best_params.keys()) if self._best_params else [],
            "scores": scores,
            "params_history": params_history,
            "best_params": self._best_params,
            "best_metrics": self._best_metrics,
            "n_trials": len(self._trials),
        }

    @property
    def best_params(self) -> dict[str, Any]:
        return dict(self._best_params)

    @property
    def best_metrics(self) -> dict[str, float]:
        return dict(self._best_metrics)


__all__ = [
    "HyperparameterOptimizer",
]
