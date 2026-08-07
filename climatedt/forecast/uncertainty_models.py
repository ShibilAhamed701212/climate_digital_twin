"""Phase 12 — Extended forecast models with prediction intervals.

Extends the forecast result to carry conformal prediction intervals,
coverage guarantees, and calibration metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np


@dataclass
class ForecastWithUncertainty:
    """A forecast with conformal prediction intervals."""

    date: str
    location_id: str
    forecast_id: str
    model_id: str

    # Point predictions
    tmax_pred: float
    tmin_pred: float
    rainfall_pred: float

    # Prediction intervals (90% confidence, alpha=0.1)
    tmax_lower: float
    tmax_upper: float
    tmin_lower: float
    tmin_upper: float
    rainfall_lower: float
    rainfall_upper: float

    # Calibration metadata
    confidence_level: float = 0.9
    coverage_achieved: float | None = None
    calibration_method: str = "SPLIT_CONFORMAL"
    calibration_samples: int = 0
    q_hat_tmax: float = 0.0
    q_hat_tmin: float = 0.0
    q_hat_rainfall: float = 0.0
    interval_width_tmax: float = 0.0
    interval_width_tmin: float = 0.0
    interval_width_rainfall: float = 0.0

    authenticity: str = "REAL"
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    provenance: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "location_id": self.location_id,
            "forecast_id": self.forecast_id,
            "model_id": self.model_id,
            "predictions": {
                "tmax": self.tmax_pred,
                "tmin": self.tmin_pred,
                "rainfall": self.rainfall_pred,
            },
            "prediction_intervals": {
                "tmax": {"lower": self.tmax_lower, "upper": self.tmax_upper},
                "tmin": {"lower": self.tmin_lower, "upper": self.tmin_upper},
                "rainfall": {"lower": self.rainfall_lower, "upper": self.rainfall_upper},
            },
            "calibration": {
                "method": self.calibration_method,
                "confidence_level": self.confidence_level,
                "coverage_achieved": self.coverage_achieved,
                "calibration_samples": self.calibration_samples,
                "q_hat": {
                    "tmax": self.q_hat_tmax,
                    "tmin": self.q_hat_tmin,
                    "rainfall": self.q_hat_rainfall,
                },
                "interval_width": {
                    "tmax": self.interval_width_tmax,
                    "tmin": self.interval_width_tmin,
                    "rainfall": self.interval_width_rainfall,
                },
            },
            "authenticity": self.authenticity,
            "generated_at": self.generated_at,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastWithUncertainty:
        pi = data.get("prediction_intervals", {})
        cal = data.get("calibration", {})
        qh = cal.get("q_hat", {})
        iw = cal.get("interval_width", {})
        preds = data.get("predictions", {})
        return cls(
            date=data["date"],
            location_id=data["location_id"],
            forecast_id=data.get("forecast_id", ""),
            model_id=data.get("model_id", ""),
            tmax_pred=preds.get("tmax", 0.0),
            tmin_pred=preds.get("tmin", 0.0),
            rainfall_pred=preds.get("rainfall", 0.0),
            tmax_lower=pi.get("tmax", {}).get("lower", 0.0),
            tmax_upper=pi.get("tmax", {}).get("upper", 0.0),
            tmin_lower=pi.get("tmin", {}).get("lower", 0.0),
            tmin_upper=pi.get("tmin", {}).get("upper", 0.0),
            rainfall_lower=pi.get("rainfall", {}).get("lower", 0.0),
            rainfall_upper=pi.get("rainfall", {}).get("upper", 0.0),
            confidence_level=cal.get("confidence_level", 0.9),
            coverage_achieved=cal.get("coverage_achieved"),
            calibration_method=cal.get("method", "SPLIT_CONFORMAL"),
            calibration_samples=cal.get("calibration_samples", 0),
            q_hat_tmax=qh.get("tmax", 0.0),
            q_hat_tmin=qh.get("tmin", 0.0),
            q_hat_rainfall=qh.get("rainfall", 0.0),
            interval_width_tmax=iw.get("tmax", 0.0),
            interval_width_tmin=iw.get("tmin", 0.0),
            interval_width_rainfall=iw.get("rainfall", 0.0),
            authenticity=data.get("authenticity", "REAL"),
            generated_at=data.get("generated_at", ""),
            provenance=data.get("provenance", {}),
        )


def compute_conformal_intervals_from_history(
    historical_predictions: list[dict[str, float]],
    historical_observations: list[dict[str, float]],
    current_predictions: dict[str, float],
    alpha: float = 0.1,
) -> ForecastWithUncertainty:
    """Compute conformal prediction intervals from historical performance.

    Uses the empirical distribution of historical residuals to compute
    prediction intervals for current predictions.

    Args:
        historical_predictions: List of {tmax, tmin, rainfall} predictions
        historical_observations: Corresponding observations
        current_predictions: Current forecast {tmax, tmin, rainfall}
        alpha: Significance level (default 0.1 for 90% CI)
    """
    from climatedt.simulation.processes.uncertainty import conformal_prediction_intervals

    y_pred = np.array(
        [[p[k] for p in historical_predictions] for k in ("tmax", "tmin", "rainfall")]
    )
    y_true = np.array(
        [[o[k] for o in historical_observations] for k in ("tmax", "tmin", "rainfall")]
    )
    y_test = np.array([[current_predictions[k]] for k in ("tmax", "tmin", "rainfall")])

    intervals = {}
    q_hats = {}
    for idx, key in enumerate(("tmax", "tmin", "rainfall")):
        result = conformal_prediction_intervals(y_true[idx], y_pred[idx], y_test[idx], alpha)
        intervals[key] = {"lower": float(result["lower"][0]), "upper": float(result["upper"][0])}
        q_hats[key] = float(result["q_hat"])

    n_cal = len(historical_predictions)
    return ForecastWithUncertainty(
        date=current_predictions.get("date", ""),
        location_id=current_predictions.get("location_id", ""),
        forecast_id=current_predictions.get("forecast_id", ""),
        model_id=current_predictions.get("model_id", ""),
        tmax_pred=float(current_predictions.get("tmax", 0)),
        tmin_pred=float(current_predictions.get("tmin", 0)),
        rainfall_pred=float(current_predictions.get("rainfall", 0)),
        tmax_lower=intervals["tmax"]["lower"],
        tmax_upper=intervals["tmax"]["upper"],
        tmin_lower=intervals["tmin"]["lower"],
        tmin_upper=intervals["tmin"]["upper"],
        rainfall_lower=intervals["rainfall"]["lower"],
        rainfall_upper=intervals["rainfall"]["upper"],
        calibration_method="SPLIT_CONFORMAL",
        calibration_samples=n_cal,
        q_hat_tmax=q_hats["tmax"],
        q_hat_tmin=q_hats["tmin"],
        q_hat_rainfall=q_hats["rainfall"],
        interval_width_tmax=round(intervals["tmax"]["upper"] - intervals["tmax"]["lower"], 2),
        interval_width_tmin=round(intervals["tmin"]["upper"] - intervals["tmin"]["lower"], 2),
        interval_width_rainfall=round(
            intervals["rainfall"]["upper"] - intervals["rainfall"]["lower"], 2
        ),
    )
