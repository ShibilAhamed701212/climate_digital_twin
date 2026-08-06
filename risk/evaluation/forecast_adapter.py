"""ForecastAdapter — maps persisted ForecastResult to risk-engine inputs.

Preserves forecast provenance: forecast_id, model_id, training_run_id,
dataset_id, authenticity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ForecastInputs:
    rainfall: float | None
    max_temp: float | None
    min_temp: float | None
    confidence: float
    forecast_id: str
    model_id: str
    training_run_id: str
    dataset_id: str
    authenticity: str
    source_twin_version: int
    created_at: str | None
    physics_validated: bool


def extract_forecast_inputs(forecast_result: Any) -> ForecastInputs:
    if forecast_result is None:
        return ForecastInputs(
            rainfall=None,
            max_temp=None,
            min_temp=None,
            confidence=0.0,
            forecast_id="",
            model_id="",
            training_run_id="",
            dataset_id="",
            authenticity="UNKNOWN",
            source_twin_version=0,
            created_at=None,
            physics_validated=False,
        )
    return ForecastInputs(
        rainfall=getattr(forecast_result, "rainfall", None),
        max_temp=getattr(forecast_result, "max_temp", None),
        min_temp=getattr(forecast_result, "min_temp", None),
        confidence=getattr(forecast_result, "confidence", 0.0) or 0.0,
        forecast_id=getattr(forecast_result, "forecast_id", ""),
        model_id=getattr(forecast_result, "model_id", ""),
        training_run_id=getattr(forecast_result, "training_run_id", ""),
        dataset_id=getattr(forecast_result, "dataset_id", ""),
        authenticity=getattr(forecast_result, "authenticity", "UNKNOWN"),
        source_twin_version=getattr(forecast_result, "source_twin_version", 0) or 0,
        created_at=getattr(forecast_result, "created_at", None),
        physics_validated=getattr(forecast_result, "physics_validated", False),
    )
