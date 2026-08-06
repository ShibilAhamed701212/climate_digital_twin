from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from pipeline.providers.fetch_result import (
    INVALID_RESPONSE,
    REQUEST_FAILED,
    FetchResult,
)
from pipeline.sources.openmeteo_connector import (
    OpenMeteoConnector,
    validate_schema,
)
from simulator.models.weather import DataSource

_logger = logging.getLogger(__name__)


def fetch_open_meteo(
    lat: float,
    lon: float,
    location_id: str = "auto",
    intent: str = "recent",
    horizon_days: int = 7,
) -> FetchResult:
    connector = OpenMeteoConnector()
    now = datetime.now(UTC)
    requested_at = now

    try:
        if intent == "forecast":
            raw = asyncio.run(
                connector._request_with_retry(
                    connector.forecast_base_url,
                    connector._build_forecast_params(lat, lon, horizon_days),
                )
            )
        elif intent == "historical":
            end = now
            start = end - timedelta(days=365)
            raw = asyncio.run(
                connector._request_with_retry(
                    connector.archive_base_url,
                    connector._build_archive_params(lat, lon, start.date(), end.date()),
                )
            )
        else:
            raw = asyncio.run(
                connector._request_with_retry(
                    connector.forecast_base_url,
                    connector._build_forecast_params(lat, lon, 1),
                )
            )
    except Exception as e:
        _logger.error("Open-Meteo request failed: %s", e)
        return FetchResult(
            provider=DataSource.OPEN_METEO,
            status="FAILED",
            observations=[],
            error_code=REQUEST_FAILED,
            error_message=str(e),
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
        )

    issues = validate_schema(raw)
    if issues:
        return FetchResult(
            provider=DataSource.OPEN_METEO,
            status="FAILED",
            observations=[],
            error_code=INVALID_RESPONSE,
            error_message="; ".join(issues),
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
        )

    if intent == "forecast":
        obs = connector._parse_forecast_response(raw, location_id, lat, lon)
    else:
        obs = connector._parse_historical_response(raw, location_id, lat, lon)

    if not obs:
        return FetchResult(
            provider=DataSource.OPEN_METEO,
            status="FAILED",
            observations=[],
            error_code=INVALID_RESPONSE,
            error_message="No observations parsed from response",
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
        )

    return FetchResult(
        provider=DataSource.OPEN_METEO,
        status="SUCCESS",
        observations=obs,
        requested_at=requested_at,
        completed_at=datetime.now(UTC),
        request_metadata={
            "endpoint": connector.forecast_base_url
            if intent != "historical"
            else connector.archive_base_url,
            "latitude": lat,
            "longitude": lon,
            "intent": intent,
        },
    )
