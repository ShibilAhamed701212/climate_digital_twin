from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from backend.services.forecast.inference import ForecastInference

logger = logging.getLogger(__name__)

app = FastAPI(title="Forecast Engine", version="1.0.0")

_inference: ForecastInference | None = None


def _get_inference() -> ForecastInference:
    global _inference
    if _inference is None:
        _inference = ForecastInference()
    return _inference


class PredictRequest(BaseModel):
    location_id: str = "Karnataka"
    horizon: int = 3
    model: str = "transformer"


class PredictResponse(BaseModel):
    location_id: str
    horizon: int
    model: str
    predictions: list[list[float]]
    confidence_intervals: dict[str, list[list[float]]]
    metadata: dict[str, Any]


@app.get("/health")
def health():
    return {"status": "healthy", "service": "forecast-engine", "version": "1.0.0"}


@app.post("/forecast/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    inf = _get_inference()
    result = inf.predict()
    return PredictResponse(
        location_id=req.location_id,
        horizon=req.horizon,
        model=req.model,
        predictions=result["predictions"],
        confidence_intervals=result["confidence_intervals"],
        metadata=result["metadata"],
    )


@app.get("/forecast/models")
def list_models():
    inf = _get_inference()
    return {"models": inf.get_available_models()}


@app.get("/forecast/model-info")
def model_info():
    inf = _get_inference()
    return inf.get_model_info()
