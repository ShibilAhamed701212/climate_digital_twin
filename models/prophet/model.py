from __future__ import annotations

import logging
import warnings
from typing import Any

import pandas as pd

try:
    from prophet import Prophet
    from prophet.serialize import model_from_json, model_to_json

    _PROPHET_AVAILABLE = True
except ImportError:
    _PROPHET_AVAILABLE = False

_logger = logging.getLogger(__name__)


class ProphetModel:
    def __init__(
        self,
        seasonality_mode: str = "additive",
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        yearly_seasonality: str | bool | int = "auto",
        weekly_seasonality: str | bool | int = "auto",
        daily_seasonality: str | bool | int = "auto",
        uncertainty_samples: int = 1000,
    ) -> None:
        if not _PROPHET_AVAILABLE:
            raise ImportError("Prophet is required. Install it with: pip install prophet")
        self.seasonality_mode = seasonality_mode
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.uncertainty_samples = uncertainty_samples
        self._model: Prophet | None = None
        self._is_trained = False
        self._forecast: pd.DataFrame | None = None
        self._yearly_seasonality = yearly_seasonality
        self._weekly_seasonality = weekly_seasonality
        self._daily_seasonality = daily_seasonality

    def _build_model(self) -> Prophet:
        model = Prophet(
            seasonality_mode=self.seasonality_mode,
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            yearly_seasonality=self._yearly_seasonality,
            weekly_seasonality=self._weekly_seasonality,
            daily_seasonality=self._daily_seasonality,
            uncertainty_samples=self.uncertainty_samples,
        )
        model.add_seasonality(
            name="monsoon",
            period=365.25,
            fourier_order=5,
            condition_name="is_monsoon",
        )
        return model

    def forward(self, df: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
        return self.predict(df=df, periods=periods)

    def train(
        self,
        df: pd.DataFrame,
        date_col: str = "ds",
        target_col: str = "y",
    ) -> None:
        required = [date_col, target_col]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        self._model = self._build_model()
        prophet_df = df[[date_col, target_col]].rename(columns={date_col: "ds", target_col: "y"})
        if "is_monsoon" in df.columns:
            prophet_df["is_monsoon"] = df["is_monsoon"].astype(int)
        else:
            prophet_df["is_monsoon"] = prophet_df["ds"].dt.month.isin([6, 7, 8, 9]).astype(int)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model.fit(prophet_df)
        self._is_trained = True
        _logger.info("Prophet model trained on %d data points", len(prophet_df))

    def predict(
        self,
        periods: int = 30,
        include_history: bool = True,
    ) -> pd.DataFrame:
        if not self._is_trained or self._model is None:
            raise RuntimeError("Model must be trained before prediction. Call train() first.")
        future = self._model.make_future_dataframe(
            periods=periods,
            include_history=include_history,
        )
        future["is_monsoon"] = future["ds"].dt.month.isin([6, 7, 8, 9]).astype(int)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = self._model.predict(future)
        self._forecast = forecast
        return forecast

    def plot_components(self) -> dict[str, Any]:
        if self._forecast is None:
            raise RuntimeError("No forecast available. Call predict() first.")
        components: dict[str, Any] = {"components": self._forecast}
        if "trend" in self._forecast.columns:
            components["trend"] = self._forecast[["ds", "trend"]].copy()
        if "yearly" in self._forecast.columns:
            components["yearly"] = self._forecast[["ds", "yearly"]].copy()
        if "weekly" in self._forecast.columns:
            components["weekly"] = self._forecast[["ds", "weekly"]].copy()
        if "monsoon" in self._forecast.columns:
            components["monsoon"] = self._forecast[["ds", "monsoon"]].copy()
        return components

    def cross_validate(
        self,
        df: pd.DataFrame,
        initial_days: int = 365,
        period_days: int = 90,
        horizon_days: int = 30,
    ) -> dict[str, float]:
        from prophet.diagnostics import cross_validation, performance_metrics

        prophet_df = df.copy()
        if "ds" not in prophet_df.columns:
            prophet_df = prophet_df.rename(columns={df.columns[0]: "ds"})
        if "y" not in prophet_df.columns:
            prophet_df = prophet_df.rename(columns={df.columns[1]: "y"})
        if self._model is None:
            self._model = self._build_model()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._model.fit(prophet_df)
            self._is_trained = True
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cv_results = cross_validation(
                self._model,
                initial=f"{initial_days} days",
                period=f"{period_days} days",
                horizon=f"{horizon_days} days",
            )
            perf = performance_metrics(cv_results)
        return {
            "mse": float(perf["mse"].mean()),
            "rmse": float(perf["rmse"].mean()),
            "mae": float(perf["mae"].mean()),
            "mape": float(perf["mape"].mean()),
            "mdape": float(perf["mdape"].mean()),
            "smape": float(perf["smape"].mean()),
        }

    def save(self, path: str) -> None:
        if not self._is_trained or self._model is None:
            raise RuntimeError("Model must be trained before saving. Call train() first.")
        model_json = model_to_json(self._model)
        with open(path, "w") as f:
            f.write(model_json)
        _logger.info("Prophet model saved to %s", path)

    def load(self, path: str) -> None:
        with open(path) as f:
            model_json = f.read()
        self._model = model_from_json(model_json)
        self._is_trained = True
        _logger.info("Prophet model loaded from %s", path)


ProphetForecastModel = ProphetModel


__all__ = [
    "ProphetModel",
    "ProphetForecastModel",
]
