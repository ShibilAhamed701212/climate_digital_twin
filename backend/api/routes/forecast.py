from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_forecast_pipeline
from backend.api.models import (
    ForecastModelsResponse,
    ForecastPerformanceResponse,
    ForecastPredictRequest,
    ForecastPredictResponse,
    RetrainResponse,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecast", tags=["Forecasting"])


@router.post(
    "/predict",
    response_model=ForecastPredictResponse,
    summary="Get forecast for location",
)
async def predict_forecast(
    request: ForecastPredictRequest,
    pipeline: Any = Depends(get_forecast_pipeline),  # noqa: B008
) -> ForecastPredictResponse:
    try:
        series = await pipeline.predict_with_best(
            _location_id=request.location_id,
            _target_variable=request.target_variable,
            _horizon=request.horizon_hours,
        )

        return ForecastPredictResponse(
            location_id=request.location_id,
            target_variable=request.target_variable,
            timestamps=[ts.isoformat() for ts in getattr(series, "timestamps", [])],
            values=getattr(series, "values", []).tolist()
            if hasattr(getattr(series, "values", []), "tolist")
            else list(getattr(series, "values", [])),
            model_id=getattr(series, "model_id", ""),
            created_at=datetime.now(UTC).isoformat(),
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Forecast prediction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Forecast prediction failed",
        ) from exc


@router.get(
    "/models",
    response_model=ForecastModelsResponse,
    summary="List available forecast models",
)
async def list_forecast_models(
    pipeline: Any = Depends(get_forecast_pipeline),  # noqa: B008
) -> ForecastModelsResponse:
    try:
        registry = pipeline.model_registry
        models = registry.list_models() if hasattr(registry, "list_models") else []

        model_list: list[dict[str, Any]] = []
        for m in models:
            model_list.append(
                {
                    "model_id": getattr(m, "model_id", ""),
                    "model_type": getattr(m, "model_type", ""),
                    "target_variable": getattr(m, "target_variable", ""),
                    "status": getattr(m, "status", ""),
                    "training_date": (
                        getattr(m, "training_date", datetime.now(UTC)).isoformat()
                        if hasattr(m, "training_date")
                        else ""
                    ),
                }
            )

        return ForecastModelsResponse(
            models=model_list,
            total=len(model_list),
        )
    except Exception as exc:
        _logger.exception("List models failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list forecast models",
        ) from exc


@router.post(
    "/retrain",
    response_model=RetrainResponse,
    summary="Trigger model retraining",
    status_code=status.HTTP_202_ACCEPTED,
)
async def retrain_model(
    target_variable: str = "temperature_2m",
    model_type: str = "xgboost",
    pipeline: Any = Depends(get_forecast_pipeline),  # noqa: B008
) -> RetrainResponse:
    try:
        report = await pipeline.train_forecast_model(
            model_type=model_type,
            target_variable=target_variable,
        )

        return RetrainResponse(
            model_id=getattr(report, "model_id", ""),
            model_type=model_type,
            target_variable=target_variable,
            status=getattr(report, "status", "success"),
            metrics=getattr(report, "metrics", {}),
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Model retraining failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model retraining failed",
        ) from exc


@router.get(
    "/performance/{model_id}",
    response_model=ForecastPerformanceResponse,
    summary="Model performance metrics",
)
async def get_model_performance(
    model_id: str,
    pipeline: Any = Depends(get_forecast_pipeline),  # noqa: B008
) -> ForecastPerformanceResponse:
    try:
        registry = pipeline.model_registry

        metadata = registry.get(model_id) if hasattr(registry, "get") else None

        if metadata is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_id}' not found",
            )
        return ForecastPerformanceResponse(
            model_id=model_id,
            metrics=dict(getattr(metadata, "metrics", {})),
            target_variable=getattr(metadata, "target_variable", ""),
        )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("Model performance retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model performance retrieval failed",
        ) from exc
