from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from backend.api.models import HealthResponse, ReadinessResponse

_logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Get overall system health",
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(UTC).isoformat(),
        services={
            "gateway": "healthy",
            "risk": "available",
            "scenario": "available",
            "rag": "available",
            "feedback": "available",
            "twin": "available",
            "forecast": "available",
        },
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
)
async def get_readiness() -> ReadinessResponse:
    return ReadinessResponse(
        ready=True,
        services={
            "gateway": True,
            "risk": True,
            "scenario": True,
            "rag": True,
            "feedback": True,
            "twin": True,
            "forecast": True,
        },
    )


@router.get(
    "/health/live",
    summary="Liveness check",
)
async def get_liveness() -> dict[str, str]:
    return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}
