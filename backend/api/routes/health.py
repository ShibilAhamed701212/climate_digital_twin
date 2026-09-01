from __future__ import annotations

import asyncio
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from fastapi import APIRouter

from backend.api.config import get_gateway_config
from backend.api.models import HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])

_PROBE_TIMEOUT_S = 2.0

_SERVICE_ENV = {
    "twin": "TWIN_HEALTH_URL",
    "forecast": "FORECAST_HEALTH_URL",
    "scenario": "SCENARIO_HEALTH_URL",
    "risk": "RISK_HEALTH_URL",
    "rag": "RAG_HEALTH_URL",
    "copilot": "COPILOT_HEALTH_URL",
}

_OPTIONAL_SERVICES = {"disaster"}


def _probe(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=_PROBE_TIMEOUT_S) as resp:
            if 200 <= getattr(resp, "status", 200) < 300:
                return "healthy"
            return "unhealthy"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return "unreachable"


def _collect_service_status() -> dict[str, str]:
    statuses: dict[str, str] = {"gateway": "healthy"}
    # Collect URLs to probe
    to_probe: dict[str, str] = {}
    for name, env_key in _SERVICE_ENV.items():
        url = os.environ.get(env_key)
        if url:
            to_probe[name] = url
        else:
            statuses[name] = "unprobed"
    disaster_url = os.environ.get("DISASTER_HEALTH_URL")
    if disaster_url:
        to_probe["disaster"] = disaster_url
    else:
        statuses["disaster"] = "unprobed"
    # Probe all services in parallel with a shared thread pool
    if to_probe:
        with ThreadPoolExecutor(max_workers=min(len(to_probe), 8)) as pool:
            futures = {pool.submit(_probe, url): name for name, url in to_probe.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    statuses[name] = future.result()
                except Exception:
                    statuses[name] = "unreachable"
    statuses["feedback"] = "healthy"
    return statuses


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Get overall system health",
)
async def get_health() -> HealthResponse:
    services = await asyncio.to_thread(_collect_service_status)
    required = [v for k, v in services.items() if k != "gateway" and k not in _OPTIONAL_SERVICES]
    overall = "healthy" if all(v in {"healthy", "unprobed"} for v in required) else "degraded"
    return HealthResponse(
        status=overall,
        version=get_gateway_config().app_version,
        timestamp=datetime.now(UTC).isoformat(),
        services=services,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
)
async def get_readiness() -> ReadinessResponse:
    services = await asyncio.to_thread(_collect_service_status)
    ready_map = {name: status == "healthy" for name, status in services.items()}
    return ReadinessResponse(
        ready=ready_map.get("gateway", False),
        services=ready_map,
    )


@router.get(
    "/health/live",
    summary="Liveness check",
)
async def get_liveness() -> dict[str, str]:
    return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}
