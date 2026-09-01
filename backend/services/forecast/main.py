from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.services.forecast.inference import ForecastInference
from models.data_loader import DatasetNotFoundError

logger = logging.getLogger(__name__)

app = FastAPI(title="Forecast Engine", version="2.1.0")

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
    return {"status": "healthy", "service": "forecast-engine", "version": "2.1.0"}


@app.post("/forecast/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    try:
        inf = _get_inference()
        result = inf.predict()
        info = inf.get_model_info()
    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "error_code": "MODEL_UNAVAILABLE"},
        ) from exc
    return PredictResponse(
        location_id=req.location_id,
        horizon=req.horizon,
        model=str(info.get("model_name") or info.get("architecture") or "unknown"),
        predictions=result["predictions"],
        confidence_intervals=result["confidence_intervals"],
        metadata={**result.get("metadata", {}), **info},
    )


@app.get("/forecast/models")
def list_models():
    try:
        inf = _get_inference()
    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "error_code": "MODEL_UNAVAILABLE"},
        ) from exc
    return {"models": inf.get_available_models()}


@app.get("/forecast/model-info")
def model_info():
    try:
        inf = _get_inference()
    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "error_code": "MODEL_UNAVAILABLE"},
        ) from exc
    return inf.get_model_info()
