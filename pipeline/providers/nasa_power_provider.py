from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from pipeline.providers.fetch_result import (
    INVALID_RESPONSE,
    NO_DATA,
    REQUEST_FAILED,
    FetchResult,
)
from pipeline.sources.nasa_power import (
    NASA_PARAM_MAP,
    fetch_point,
    parse_response,
)
from simulator.models.weather import DataSource, WeatherObservation

_logger = logging.getLogger(__name__)


def _nasa_to_weather_observations(
    records: dict[str, Any],
    lat: float,
    lon: float,
    location_id: str,
) -> list[WeatherObservation]:
    obs_list: list[WeatherObservation] = []
    df = next(iter(records.values()))
    if df is None or df.empty:
        return obs_list
    for _, row in df.iterrows():
        obs_list.append(
            WeatherObservation(
                location_id=location_id,
                latitude=lat,
                longitude=lon,
                timestamp=row.get("Date", datetime.now(UTC)),
                temperature_2m=float(row.get("MaxTemp", row.get("temperature_2m", 0))),
                precipitation_mm=float(row.get("Rainfall", row.get("precipitation_mm", 0))),
                humidity_pct=50.0,
                pressure_hpa=1013.0,
                wind_speed_10m=5.0,
                wind_direction_10m=180.0,
                data_source=DataSource.NASA_POWER,
            )
        )
    return obs_list


def fetch_nasa_power(
    lat: float,
    lon: float,
    location_id: str = "auto",
    start_date: str | None = None,
    end_date: str | None = None,
) -> FetchResult:
    now = datetime.now(UTC)
    requested_at = now
    s = start_date or (now - timedelta(days=30)).strftime("%Y%m%d")
    e = end_date or now.strftime("%Y%m%d")
    source_config: dict[str, Any] = {
        "parameters": NASA_PARAM_MAP,
        "community": "RE",
        "format": "JSON",
        "endpoint": "https://power.larc.nasa.gov/api/temporal/daily/point",
    }

    try:
        raw = fetch_point(lat, lon, s, e, source_config)
    except Exception as ex:
        _logger.error("NASA POWER fetch exception: %s", ex)
        return FetchResult(
            provider=DataSource.NASA_POWER,
            status="FAILED",
            observations=[],
            error_code=REQUEST_FAILED,
            error_message=str(ex),
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
        )

    if raw is None:
        return FetchResult(
            provider=DataSource.NASA_POWER,
            status="FAILED",
            observations=[],
            error_code=NO_DATA,
            error_message="No data returned from NASA POWER",
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
        )

    parsed = parse_response(raw, lat, lon, source_config)
    if not parsed:
        return FetchResult(
            provider=DataSource.NASA_POWER,
            status="FAILED",
            observations=[],
            error_code=INVALID_RESPONSE,
            error_message="Failed to parse NASA POWER response",
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
        )

    obs = _nasa_to_weather_observations(parsed, lat, lon, location_id)
    return FetchResult(
        provider=DataSource.NASA_POWER,
        status="SUCCESS",
        observations=obs,
        requested_at=requested_at,
        completed_at=datetime.now(UTC),
        request_metadata={
            "endpoint": source_config["endpoint"],
            "latitude": lat,
            "longitude": lon,
            "start": s,
            "end": e,
        },
    )
