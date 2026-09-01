from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

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


def _row_value(row: Any, *keys: str) -> float | None:
    for key in keys:
        if key not in row.index:
            continue
        raw = row.get(key)
        if raw is None:
            continue
        try:
            if bool(pd.isna(raw)):
                continue
        except (TypeError, ValueError):
            pass
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def _pressure_hpa(raw: float | None) -> float | None:
    """NASA POWER PS is surface pressure in kPa; convert to hPa when needed."""
    if raw is None:
        return None
    if 50.0 <= raw <= 150.0:
        return raw * 10.0
    if 500.0 <= raw <= 1100.0:
        return raw
    return None


def _wind_direction(raw: float | None) -> float | None:
    if raw is None:
        return None
    wrapped = raw % 360.0
    return wrapped


def _nasa_to_weather_observations(
    records: dict[str, Any],
    lat: float,
    lon: float,
    location_id: str,
) -> list[WeatherObservation]:
    frames = [df for df in records.values() if df is not None and not df.empty]
    if not frames:
        return []
    merged = frames[0]
    for extra in frames[1:]:
        merge_on = [c for c in ("Date", "Latitude", "Longitude") if c in merged.columns and c in extra.columns]
        if not merge_on:
            continue
        merged = merged.merge(extra, on=merge_on, how="outer")

    obs_list: list[WeatherObservation] = []
    for _, row in merged.iterrows():
        rainfall = _row_value(row, "Rainfall", "precipitation_mm")
        humidity = _row_value(row, "Humidity", "humidity_pct")
        pressure = _pressure_hpa(_row_value(row, "Pressure", "pressure_hpa"))
        wind = _row_value(row, "WindSpeed", "wind_speed_10m")
        wdir = _wind_direction(_row_value(row, "WindDir", "wind_direction_10m"))
        temp = _row_value(row, "Temperature", "temperature_2m", "MaxTemp")
        if None in (rainfall, humidity, pressure, wind, wdir, temp):
            continue
        ts = row.get("Date", datetime.now(UTC))
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()
        try:
            obs_list.append(
                WeatherObservation(
                    location_id=location_id,
                    latitude=lat,
                    longitude=lon,
                    timestamp=ts,
                    temperature_2m=temp,
                    precipitation_mm=rainfall,
                    humidity_pct=humidity,
                    pressure_hpa=pressure,
                    wind_speed_10m=wind,
                    wind_direction_10m=wdir,
                    data_source=DataSource.NASA_POWER,
                )
            )
        except ValueError:
            continue
    return obs_list


def fetch_nasa_power(
    lat: float,
    lon: float,
    location_id: str = "auto",
    start_date: str | None = None,
    end_date: str | None = None,
    intent: str | None = None,
    **_kwargs: Any,
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
    if not obs:
        return FetchResult(
            provider=DataSource.NASA_POWER,
            status="FAILED",
            observations=[],
            error_code=NO_DATA,
            error_message="NASA POWER returned no complete meteorological records",
            requested_at=requested_at,
            completed_at=datetime.now(UTC),
        )

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
            "intent": intent,
        },
    )
