from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import aiohttp

from pipeline.sources.base import DataConnector, DataSourceHealth
from simulator.models.forecast import ForecastPoint
from simulator.models.weather import DataSource, WeatherObservation

_logger = logging.getLogger(__name__)

ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_BASE_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "shortwave_radiation",
    "cloud_cover",
    "soil_moisture_0_to_7cm",
]

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_hours",
]

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_DEFAULT_MAX_CONCURRENT = 5
_DEFAULT_CACHE_TTL = 3600


def _get(arr: list[Any] | None, idx: int, default: float = 0.0) -> float:
    if arr is None or idx >= len(arr) or arr[idx] is None:
        return float("nan")
    try:
        return float(arr[idx])
    except (ValueError, TypeError):
        return float("nan")


def _get_opt(arr: list[Any] | None, idx: int) -> float | None:
    if arr is None or idx >= len(arr) or arr[idx] is None:
        return None
    try:
        return float(arr[idx])
    except (ValueError, TypeError):
        return None


@dataclass
class _CachedResponse:
    data: dict[str, Any]
    timestamp: float


class _RateLimiter:
    def __init__(self, max_concurrent: int = _DEFAULT_MAX_CONCURRENT) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._request_times: list[float] = []
        self._max_concurrent = max_concurrent

    async def acquire(self) -> None:
        await self._semaphore.acquire()

    def release(self) -> None:
        self._semaphore.release()

    @property
    def available(self) -> int:
        return self._max_concurrent - len(self._request_times)


class OpenMeteoConnector(DataConnector):
    source_id: str = "open_meteo"
    source_name: str = "Open-Meteo"

    def __init__(
        self,
        max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
        cache_ttl_seconds: int = _DEFAULT_CACHE_TTL,
    ) -> None:
        self.archive_base_url = ARCHIVE_BASE_URL
        self.forecast_base_url = FORECAST_BASE_URL
        self.max_concurrent = max_concurrent
        self.cache_ttl_seconds = cache_ttl_seconds
        self.data_source = DataSource.OPEN_METEO
        self._rate_limiter = _RateLimiter(max_concurrent)
        self._cache: dict[str, _CachedResponse] = {}
        self._lock = asyncio.Lock()

    async def fetch_historical(
        self, location: tuple[float, float, str], start_date: date, end_date: date, **kwargs: Any
    ) -> list[WeatherObservation]:
        lat, lon, location_id = location
        session: aiohttp.ClientSession | None = kwargs.get("session")
        params = self._build_archive_params(lat, lon, start_date, end_date)
        raw_data = await self._request_with_retry(
            url=self.archive_base_url, params=params, session=session
        )
        return self._parse_historical_response(raw_data, location_id, lat, lon)

    async def fetch_forecast(
        self, location: tuple[float, float, str], horizon_days: int, **kwargs: Any
    ) -> list[ForecastPoint]:
        lat, lon, location_id = location
        session: aiohttp.ClientSession | None = kwargs.get("session")
        params = self._build_forecast_params(lat, lon, horizon_days)
        raw_data = await self._request_with_retry(
            url=self.forecast_base_url, params=params, session=session
        )
        return self._parse_forecast_response(raw_data, location_id, lat, lon)

    async def validate(self, **kwargs: Any) -> DataSourceHealth:
        session: aiohttp.ClientSession | None = kwargs.get("session")
        start_time = time.monotonic()
        try:
            params = {
                "latitude": 12.97,
                "longitude": 77.59,
                "hourly": "temperature_2m",
                "forecast_days": 1,
            }
            own_session = False
            if session is None:
                session = aiohttp.ClientSession()
                own_session = True
            try:
                async with session.get(
                    self.forecast_base_url, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    elapsed_ms = (time.monotonic() - start_time) * 1000
                    if resp.ok:
                        return DataSourceHealth(
                            source_id=self.source_id,
                            reachable=True,
                            status_code=resp.status,
                            response_time_ms=elapsed_ms,
                        )
                    return DataSourceHealth(
                        source_id=self.source_id,
                        reachable=False,
                        status_code=resp.status,
                        response_time_ms=elapsed_ms,
                        error_message=f"HTTP {resp.status}",
                    )
            finally:
                if own_session:
                    await session.close()
        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            return DataSourceHealth(
                source_id=self.source_id,
                reachable=False,
                status_code=0,
                response_time_ms=elapsed_ms,
                error_message=str(e),
            )

    def _build_archive_params(
        self, latitude: float, longitude: float, start_date: date, end_date: date
    ) -> dict[str, str]:
        return {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": ",".join(HOURLY_VARIABLES),
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "auto",
        }

    def _build_forecast_params(
        self, latitude: float, longitude: float, horizon_days: int
    ) -> dict[str, str]:
        return {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            "hourly": ",".join(HOURLY_VARIABLES),
            "forecast_days": str(horizon_days),
            "timezone": "auto",
        }

    async def _request_with_retry(
        self,
        url: str,
        params: dict[str, str],
        session: aiohttp.ClientSession | None = None,
        max_attempts: int = 3,
        base_delay: float = 1.0,
    ) -> dict[str, Any]:
        cache_key = self._make_cache_key(url, params)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        own_session = False
        if session is None:
            session = aiohttp.ClientSession()
            own_session = True
        try:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                await self._rate_limiter.acquire()
                try:
                    async with session.get(
                        url, params=params, timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self._set_cache(cache_key, data)
                            return data
                        elif resp.status in _RETRYABLE_STATUSES:
                            error_text = await resp.text()
                            last_exc = aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=f"HTTP {resp.status}: {error_text[:200]}",
                                headers=resp.headers,
                            )
                        else:
                            error_text = await resp.text()
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=f"Non-retryable HTTP {resp.status}: {error_text[:200]}",
                                headers=resp.headers,
                            )
                except aiohttp.ClientError as e:
                    last_exc = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        _logger.debug(
                            "Retry %d/%d for %s in %.1fs: %s", attempt, max_attempts, url, delay, e
                        )
                        await asyncio.sleep(delay)
                    continue
                finally:
                    self._rate_limiter.release()
            if last_exc is not None:
                raise last_exc
            raise aiohttp.ClientError("Request failed after retries")
        finally:
            if own_session:
                await session.close()

    def _parse_historical_response(
        self, data: dict[str, Any], location_id: str, latitude: float, longitude: float
    ) -> list[WeatherObservation]:
        observations: list[WeatherObservation] = []
        hourly = data.get("hourly")
        if hourly is None:
            return observations
        times = hourly.get("time", [])
        if not times:
            return observations
        temps = hourly.get("temperature_2m", [])
        precips = hourly.get("precipitation", [])
        humidities = hourly.get("relative_humidity_2m", [])
        pressures = hourly.get("surface_pressure", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        wind_dirs = hourly.get("wind_direction_10m", [])
        radiations = hourly.get("shortwave_radiation", [])
        clouds = hourly.get("cloud_cover", [])
        soils = hourly.get("soil_moisture_0_to_7cm", [])
        for i, time_str in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(time_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue
            try:
                obs = WeatherObservation(
                    location_id=location_id,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=timestamp,
                    temperature_2m=_get(temps, i),
                    precipitation_mm=_get(precips, i),
                    humidity_pct=_get(humidities, i),
                    pressure_hpa=_get(pressures, i, default=1013.0),
                    wind_speed_10m=_get(wind_speeds, i),
                    wind_direction_10m=_get(wind_dirs, i),
                    solar_radiation=_get_opt(radiations, i),
                    cloud_cover_pct=_get_opt(clouds, i),
                    soil_moisture=_get_opt(soils, i),
                    data_source=self.data_source,
                )
            except (ValueError, TypeError):
                _logger.debug("Skipping observation at index %d due to invalid values", i)
                continue
            observations.append(obs)
        return observations

    def _parse_forecast_response(
        self, data: dict[str, Any], location_id: str, latitude: float, longitude: float
    ) -> list[ForecastPoint]:
        forecast_points: list[ForecastPoint] = []
        hourly = data.get("hourly")
        if hourly is None:
            return forecast_points
        times = hourly.get("time", [])
        if not times:
            return forecast_points
        temps = hourly.get("temperature_2m", [])
        precips = hourly.get("precipitation", [])
        humidities = hourly.get("relative_humidity_2m", [])
        pressures = hourly.get("surface_pressure", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        wind_dirs = hourly.get("wind_direction_10m", [])
        radiations = hourly.get("shortwave_radiation", [])
        clouds = hourly.get("cloud_cover", [])
        issue_timestamp = datetime.now(UTC)
        for i, time_str in enumerate(times):
            try:
                forecast_ts = datetime.fromisoformat(time_str)
                if forecast_ts.tzinfo is None:
                    forecast_ts = forecast_ts.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue
            fp = ForecastPoint(
                location_id=location_id,
                latitude=latitude,
                longitude=longitude,
                forecast_timestamp=forecast_ts,
                issue_timestamp=issue_timestamp,
                temperature_2m=_get(temps, i),
                precipitation_mm=_get(precips, i),
                humidity_pct=_get(humidities, i),
                pressure_hpa=_get(pressures, i, default=1013.0),
                wind_speed_10m=_get(wind_speeds, i),
                wind_direction_10m=_get(wind_dirs, i),
                cloud_cover_pct=_get_opt(clouds, i),
                solar_radiation=_get_opt(radiations, i),
                model_name="open_meteo",
            )
            forecast_points.append(fp)
        return forecast_points

    def _make_cache_key(self, url: str, params: dict[str, str]) -> str:
        raw = f"{url}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry.timestamp > self.cache_ttl_seconds:
            del self._cache[key]
            return None
        return entry.data

    def _set_cache(self, key: str, data: dict[str, Any]) -> None:
        self._cache[key] = _CachedResponse(data=data, timestamp=time.monotonic())

    def clear_cache(self) -> None:
        self._cache.clear()
        _logger.debug("Cache cleared")


OPEN_METEO_CANONICAL_UNITS: dict[str, str] = {
    "temperature_2m": "°C",
    "precipitation": "mm",
    "relative_humidity_2m": "%",
    "surface_pressure": "hPa",
    "wind_speed_10m": "km/h",
    "wind_direction_10m": "°",
    "shortwave_radiation": "W/m²",
    "cloud_cover": "%",
    "soil_moisture_0_to_7cm": "m³/m³",
}


def normalize_units(data: dict[str, Any]) -> dict[str, Any]:
    return data


def validate_schema(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(data, dict):
        issues.append("response is not a dict")
        return issues
    if "hourly" not in data and "daily" not in data:
        issues.append("response missing hourly and daily keys")
        return issues
    hourly = data.get("hourly", {})
    if not isinstance(hourly, dict):
        issues.append("hourly is not a dict")
        return issues
    time_vals = hourly.get("time")
    if not time_vals or not isinstance(time_vals, list):
        issues.append("hourly.time is missing or not a list")
        return issues
    if len(time_vals) == 0:
        issues.append("hourly.time is empty")
    return issues


def get_openmeteo_connector(
    max_concurrent: int = _DEFAULT_MAX_CONCURRENT, cache_ttl_seconds: int = _DEFAULT_CACHE_TTL
) -> OpenMeteoConnector:
    return OpenMeteoConnector(max_concurrent=max_concurrent, cache_ttl_seconds=cache_ttl_seconds)
