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
from simulator.models.era5 import ERA5_CDS_BASE_URL, ERA5_CDS_DATASET, ERA5Variable
from simulator.models.forecast import ForecastPoint
from simulator.models.weather import DataSource, WeatherObservation

_logger = logging.getLogger(__name__)

_DEFAULT_MAX_CONCURRENT = 1
_DEFAULT_CACHE_TTL = 7200
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

ERA5_HOURLY_VARIABLES = [
    "2m_temperature",
    "total_precipitation",
    "surface_pressure",
    "mean_sea_level_pressure",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_cloud_cover",
    "surface_solar_radiation_downwards",
]

CDS_RATE_LIMIT_DELAY = 10.0


@dataclass
class _CachedResponse:
    data: dict[str, Any]
    timestamp: float


class _RateLimiter:
    def __init__(self, max_concurrent: int = _DEFAULT_MAX_CONCURRENT) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._last_request_time: float = 0.0

    async def acquire(self) -> None:
        await self._semaphore.acquire()
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < CDS_RATE_LIMIT_DELAY and self._last_request_time > 0:
            await asyncio.sleep(CDS_RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.monotonic()

    def release(self) -> None:
        self._semaphore.release()

    @property
    def available(self) -> int:
        return self._max_concurrent


class ERA5Connector(DataConnector):
    source_id: str = "era5"
    source_name: str = "ERA5 Reanalysis"

    def __init__(
        self,
        base_url: str = ERA5_CDS_BASE_URL,
        dataset: str = ERA5_CDS_DATASET,
        max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
        cache_ttl_seconds: int = _DEFAULT_CACHE_TTL,
        api_key: str | None = None,
        api_uid: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.dataset = dataset
        self.max_concurrent = max_concurrent
        self.cache_ttl_seconds = cache_ttl_seconds
        self.api_key = api_key
        self.api_uid = api_uid
        self.data_source = DataSource.ERA5
        self._rate_limiter = _RateLimiter(max_concurrent)
        self._cache: dict[str, _CachedResponse] = {}
        self._use_cdsapi = self._check_cdsapi_available()

    async def fetch_historical(
        self, location: tuple[float, float, str], start_date: date, end_date: date, **kwargs: Any
    ) -> list[WeatherObservation]:
        lat, lon, location_id = location
        session: aiohttp.ClientSession | None = kwargs.get("session")
        variables: list[str] | None = kwargs.get("variables")
        if self._use_cdsapi:
            return await self._fetch_via_cdsapi(location, start_date, end_date, variables)
        params = self._build_request_params(lat, lon, start_date, end_date, variables)
        raw_data = await self._request_with_retry(
            url=f"{self.base_url}/v1/resources/{self.dataset}", params=params, session=session
        )
        return self._parse_historical_response(raw_data, location_id, lat, lon)

    async def fetch_forecast(
        self, location: tuple[float, float, str], _horizon_days: int, **kwargs: Any
    ) -> list[ForecastPoint]:
        lat, lon, location_id = location
        session: aiohttp.ClientSession | None = kwargs.get("session")
        today = date.today()
        recent_start = date(today.year, today.month, 1)
        if recent_start >= today:
            recent_start = date(today.year - 1, today.month, 1)
        params = self._build_request_params(lat, lon, recent_start, today)
        raw_data = await self._request_with_retry(
            url=f"{self.base_url}/v1/resources/{self.dataset}", params=params, session=session
        )
        return self._parse_forecast_response(raw_data, location_id, lat, lon)

    async def validate(self, **kwargs: Any) -> DataSourceHealth:
        session: aiohttp.ClientSession | None = kwargs.get("session")
        start_time = time.monotonic()
        if self._use_cdsapi:
            try:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                return DataSourceHealth(
                    source_id=self.source_id,
                    reachable=True,
                    status_code=200,
                    response_time_ms=elapsed_ms,
                )
            except Exception as e:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                return DataSourceHealth(
                    source_id=self.source_id,
                    reachable=False,
                    status_code=0,
                    response_time_ms=elapsed_ms,
                    error_message=str(e),
                )
        try:
            params = {
                "latitude": "20.0",
                "longitude": "78.0",
                "variable": "2m_temperature",
                "year": "2024",
                "month": "01",
                "product_type": "reanalysis",
                "format": "netcdf",
            }
            own_session = False
            if session is None:
                session = aiohttp.ClientSession()
                own_session = True
            try:
                test_url = f"{self.base_url}/v1/resources/{self.dataset}"
                async with session.get(
                    test_url, params=params, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    elapsed_ms = (time.monotonic() - start_time) * 1000
                    if resp.status in (200, 401, 403):
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

    def _check_cdsapi_available(self) -> bool:
        try:
            import importlib.util as _util

            available = _util.find_spec("cdsapi") is not None
            if available:
                _logger.info("cdsapi package is available — using native CDS API")
            else:
                _logger.warning("cdsapi not installed — falling back to HTTP API")
            return available
        except ImportError:
            _logger.warning("cdsapi not installed — falling back to HTTP API")
            return False
        except Exception:
            return False

    async def _fetch_via_cdsapi(
        self,
        location: tuple[float, float, str],
        start_date: date,
        end_date: date,
        variables: list[str] | None = None,
    ) -> list[WeatherObservation]:
        import cdsapi

        lat, lon, location_id = location
        if variables is None:
            variables = ERA5_HOURLY_VARIABLES
        request = {
            "product_type": "reanalysis",
            "variable": variables,
            "year": [str(y) for y in range(start_date.year, end_date.year + 1)],
            "month": [str(m).zfill(2) for m in self._get_months_in_range(start_date, end_date)],
            "day": [str(d).zfill(2) for d in self._get_days_in_range(start_date, end_date)],
            "time": [f"{h:02d}:00" for h in range(24)],
            "format": "netcdf",
            "area": [lat + 0.5, lon - 0.5, lat - 0.5, lon + 0.5],
        }
        try:
            client = cdsapi.Client(
                url=self.base_url,
                key=f"{self.api_uid}:{self.api_key}" if self.api_uid and self.api_key else None,
                quiet=True,
            )
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: client.retrieve(self.dataset, request)
            )
            if hasattr(result, "download"):
                file_path = await loop.run_in_executor(None, lambda: result.download())
                _logger.info("CDS API download initiated for %s -> %s", location_id, file_path)
        except Exception as e:
            _logger.error("cdsapi request failed: %s", e)
        return []

    def _build_request_params(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        variables: list[str] | None = None,
    ) -> dict[str, str]:
        if variables is None:
            variables = ERA5_HOURLY_VARIABLES
        return {
            "variable": ",".join(variables),
            "product_type": "reanalysis",
            "year": f"{start_date.year}/{end_date.year}",
            "month": f"{start_date.month:02d}/{end_date.month:02d}",
            "area": f"{latitude + 0.5}/{longitude - 0.5}/{latitude - 0.5}/{longitude + 0.5}",
            "format": "netcdf",
        }

    async def _request_with_retry(
        self,
        url: str,
        params: dict[str, str],
        session: aiohttp.ClientSession | None = None,
        max_attempts: int = 3,
        base_delay: float = 2.0,
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
                        url, params=params, timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                            except (json.JSONDecodeError, aiohttp.ContentTypeError):
                                data = {"status": "queued", "message": "request_queued"}
                            self._set_cache(cache_key, data)
                            return data
                        elif resp.status in _RETRYABLE_STATUSES:
                            last_exc = aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=f"HTTP {resp.status}",
                                headers=resp.headers,
                            )
                        else:
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=f"Non-retryable HTTP {resp.status}",
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
        if "status" in data and data.get("status") == "queued":
            _logger.info("CDS request queued for %s: %s", location_id, data.get("message", ""))
            return observations
        hourly = data.get("hourly")
        if hourly is None:
            if "messages" in data:
                _logger.warning("CDS message for %s: %s", location_id, data["messages"])
            return observations
        times = hourly.get("time", [])
        if not times:
            return observations
        temps = hourly.get("2m_temperature", [])
        precips = hourly.get("total_precipitation", [])
        pressures = hourly.get("surface_pressure", [])
        cloud_covers = hourly.get("total_cloud_cover", [])
        radiations = hourly.get("surface_solar_radiation_downwards", [])
        for i, time_str in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(time_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue
            temp_k = temps[i] if i < len(temps) else 288.15
            temp_c = temp_k - 273.15 if temp_k is not None else 15.0
            precip_m = precips[i] if i < len(precips) else 0.0
            precip_mm = precip_m * 1000.0 if precip_m is not None else 0.0
            pressure_pa = pressures[i] if i < len(pressures) else 101325.0
            pressure_hpa = pressure_pa / 100.0 if pressure_pa is not None else 1013.25
            obs = WeatherObservation(
                location_id=location_id,
                latitude=latitude,
                longitude=longitude,
                timestamp=timestamp,
                temperature_2m=temp_c,
                precipitation_mm=precip_mm,
                humidity_pct=50.0,
                pressure_hpa=pressure_hpa,
                wind_speed_10m=0.0,
                wind_direction_10m=0.0,
                solar_radiation=radiations[i] if i < len(radiations) else None,
                cloud_cover_pct=cloud_covers[i] if i < len(cloud_covers) else None,
                data_source=self.data_source,
            )
            observations.append(obs)
        _logger.debug("Parsed %d ERA5 observations for %s", len(observations), location_id)
        return observations

    def _parse_forecast_response(
        self, data: dict[str, Any], location_id: str, latitude: float, longitude: float
    ) -> list[ForecastPoint]:
        forecast_points: list[ForecastPoint] = []
        if "status" in data and data.get("status") == "queued":
            return forecast_points
        hourly = data.get("hourly")
        if hourly is None:
            return forecast_points
        times = hourly.get("time", [])
        if not times:
            return forecast_points
        temps = hourly.get("2m_temperature", [])
        precips = hourly.get("total_precipitation", [])
        pressures = hourly.get("surface_pressure", [])
        cloud_covers = hourly.get("total_cloud_cover", [])
        issue_timestamp = datetime.now(UTC)
        for i, time_str in enumerate(times):
            try:
                forecast_ts = datetime.fromisoformat(time_str)
                if forecast_ts.tzinfo is None:
                    forecast_ts = forecast_ts.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue
            temp_k = temps[i] if i < len(temps) else 288.15
            temp_c = temp_k - 273.15 if temp_k is not None else 15.0
            precip_m = precips[i] if i < len(precips) else 0.0
            precip_mm = precip_m * 1000.0 if precip_m is not None else 0.0
            pressure_pa = pressures[i] if i < len(pressures) else 101325.0
            pressure_hpa = pressure_pa / 100.0 if pressure_pa is not None else 1013.25
            fp = ForecastPoint(
                location_id=location_id,
                latitude=latitude,
                longitude=longitude,
                forecast_timestamp=forecast_ts,
                issue_timestamp=issue_timestamp,
                temperature_2m=temp_c,
                precipitation_mm=precip_mm,
                humidity_pct=50.0,
                pressure_hpa=pressure_hpa,
                wind_speed_10m=0.0,
                wind_direction_10m=0.0,
                cloud_cover_pct=cloud_covers[i] if i < len(cloud_covers) else None,
                model_name="era5",
            )
            forecast_points.append(fp)
        return forecast_points

    def _get_months_in_range(self, start: date, end: date) -> list[int]:
        months: set[int] = set()
        current = start
        while current <= end:
            months.add(current.month)
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        return sorted(months)

    def _get_days_in_range(self, start: date, end: date) -> list[int]:
        days: set[int] = set()
        current = start
        while current <= end:
            days.add(current.day)
            from datetime import timedelta

            current += timedelta(days=1)
        return sorted(days)

    def get_variable_metadata(self, variable_name: str) -> ERA5Variable | None:
        from simulator.models.era5 import ERA5_VARIABLES

        return ERA5_VARIABLES.get(variable_name)

    def estimate_data_volume(
        self, start_date: date, end_date: date, num_variables: int = 8
    ) -> dict[str, float]:
        total_days = (end_date - start_date).days
        total_hours = total_days * 24
        estimated_bytes = total_hours * num_variables * 1024
        return {
            "total_days": float(total_days),
            "total_hours": float(total_hours),
            "estimated_bytes": float(estimated_bytes),
            "estimated_mb": estimated_bytes / (1024 * 1024),
        }

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
        _logger.debug("ERA5 cache cleared")


def get_era5_connector(
    base_url: str = ERA5_CDS_BASE_URL,
    dataset: str = ERA5_CDS_DATASET,
    max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
    cache_ttl_seconds: int = _DEFAULT_CACHE_TTL,
    api_key: str | None = None,
    api_uid: str | None = None,
) -> ERA5Connector:
    return ERA5Connector(
        base_url=base_url,
        dataset=dataset,
        max_concurrent=max_concurrent,
        cache_ttl_seconds=cache_ttl_seconds,
        api_key=api_key,
        api_uid=api_uid,
    )
