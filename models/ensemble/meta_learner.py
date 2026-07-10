from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class EnsembleMetaLearner:
    def __init__(
        self,
        alpha: float = 1.0,
        fit_intercept: bool = True,
        use_scaler: bool = True,
    ) -> None:
        self.alpha = alpha
        self.fit_intercept = fit_intercept
        self.use_scaler = use_scaler
        self._meta_models: dict[str, Ridge] = {}
        self._scalers: dict[str, StandardScaler] = {}
        self._base_model_names: list[str] = []
        self._fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def fit(
        self,
        base_predictions: dict[str, np.ndarray],
        targets: np.ndarray,
    ) -> dict[str, Any]:
        self._base_model_names = list(base_predictions.keys())
        n_models = len(self._base_model_names)
        self._target_ndim = targets.ndim
        n_targets = targets.shape[1] if targets.ndim > 1 else 1

        if n_models < 2:
            raise ValueError(f"Need at least 2 base models, got {n_models}")

        meta_features = self._build_meta_features(base_predictions)

        for t in range(n_targets):
            y = targets[:, t] if n_targets > 1 else targets
            if self.use_scaler:
                scaler = StandardScaler()
                x_scaled = scaler.fit_transform(meta_features)
                self._scalers[t] = scaler
            else:
                x_scaled = meta_features
            model = Ridge(alpha=self.alpha, fit_intercept=self.fit_intercept)
            model.fit(x_scaled, y)
            self._meta_models[t] = model

        self._fitted = True
        self._n_targets = n_targets
        return self._compute_fit_metrics(base_predictions, targets)

    def predict(self, base_predictions: dict[str, np.ndarray]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Ensemble must be fitted before predict")

        meta_features = self._build_meta_features(base_predictions)
        n_targets = len(self._meta_models)
        predictions = np.zeros((meta_features.shape[0], n_targets))

        for t, model in self._meta_models.items():
            x = self._scalers[t].transform(meta_features) if self.use_scaler else meta_features
            predictions[:, t] = model.predict(x)

        if self._target_ndim == 1:
            predictions = predictions.squeeze(axis=1)

        return predictions

    def get_weights(self) -> dict[str, dict[int, float]]:
        weights: dict[str, dict[int, float]] = {}
        for t, model in self._meta_models.items():
            for i, name in enumerate(self._base_model_names):
                if name not in weights:
                    weights[name] = {}
                weights[name][t] = round(float(model.coef_[i]), 4)
        return weights

    def _build_meta_features(self, base_predictions: dict[str, np.ndarray]) -> np.ndarray:
        preds_list = []
        for name in self._base_model_names:
            preds = base_predictions[name]
            if preds.ndim == 1:
                preds = preds.reshape(-1, 1)
            preds_list.append(preds)
        return np.concatenate(preds_list, axis=1)

    def _compute_fit_metrics(
        self,
        base_predictions: dict[str, np.ndarray],
        targets: np.ndarray,
    ) -> dict[str, float]:
        train_preds = self.predict(base_predictions)
        errors = targets - train_preds
        rmse = float(np.sqrt(np.mean(errors**2)))
        mae = float(np.mean(np.abs(errors)))
        ss_res = np.sum(errors**2)
        ss_tot = np.sum((targets - np.mean(targets, axis=0)) ** 2)
        r2 = float(1 - ss_res / (ss_tot + 1e-10))
        return {"rmse": round(rmse, 4), "mae": round(mae, 4), "r2": round(r2, 4)}

    def save(self, path: str) -> None:
        import joblib

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "alpha": self.alpha,
            "fit_intercept": self.fit_intercept,
            "use_scaler": self.use_scaler,
            "base_model_names": self._base_model_names,
            "target_ndim": self._target_ndim,
            "n_targets": self._n_targets,
            "meta_models": self._meta_models,
            "scalers": self._scalers,
            "fitted": self._fitted,
        }
        joblib.dump(state, out)
        logger.info("Ensemble saved to %s", path)

    @classmethod
    def load(cls, path: str) -> EnsembleMetaLearner:
        import joblib

        state = joblib.load(path)
        obj = cls(
            alpha=state["alpha"],
            fit_intercept=state["fit_intercept"],
            use_scaler=state["use_scaler"],
        )
        obj._base_model_names = state["base_model_names"]
        obj._target_ndim = state.get("target_ndim", 2)
        obj._n_targets = state.get("n_targets", len(state["meta_models"]))
        obj._meta_models = state["meta_models"]
        obj._scalers = state["scalers"]
        obj._fitted = state["fitted"]
        logger.info("Ensemble loaded from %s", path)
        return obj
