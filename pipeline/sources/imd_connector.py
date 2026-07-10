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
from simulator.models.imd import IMD_FALLBACK_BASE_URL, IMD_GRIDDED_PRODUCTS, IMDGridDefinition
from simulator.models.weather import DataSource, WeatherObservation

_logger = logging.getLogger(__name__)

_DEFAULT_MAX_CONCURRENT = 3
_DEFAULT_CACHE_TTL = 3600
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

IMD_HOURLY_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "shortwave_radiation",
    "cloud_cover",
]


@dataclass
class _CachedResponse:
    data: dict[str, Any]
    timestamp: float


class _RateLimiter:
    def __init__(self, max_concurrent: int = _DEFAULT_MAX_CONCURRENT) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent

    async def acquire(self) -> None:
        await self._semaphore.acquire()

    def release(self) -> None:
        self._semaphore.release()

    @property
    def available(self) -> int:
        return self._max_concurrent


class IMDConnector(DataConnector):
    source_id: str = "imd"
    source_name: str = "India Meteorological Department"

    def __init__(
        self,
        base_url: str = IMD_FALLBACK_BASE_URL,
        max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
        cache_ttl_seconds: int = _DEFAULT_CACHE_TTL,
        available_products: dict[str, IMDGridDefinition] | None = None,
    ) -> None:
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.cache_ttl_seconds = cache_ttl_seconds
        self.data_source = DataSource.IMD
        self._rate_limiter = _RateLimiter(max_concurrent)
        self._cache: dict[str, _CachedResponse] = {}
        self._available_products = (
            available_products if available_products is not None else IMD_GRIDDED_PRODUCTS
        )

    @property
    def available_products(self) -> dict[str, IMDGridDefinition]:
        return dict(self._available_products)

    def get_product(self, product_id: str) -> IMDGridDefinition | None:
        return self._available_products.get(product_id)

    async def fetch_historical(
        self, location: tuple[float, float, str], start_date: date, end_date: date, **kwargs: Any
    ) -> list[WeatherObservation]:
        lat, lon, location_id = location
        session: aiohttp.ClientSession | None = kwargs.get("session")
        product_id: str | None = kwargs.get("product_id")
        if product_id is not None:
            product = self._available_products.get(product_id)
            if product is not None:
                self._validate_location_in_grid(lat, lon, product)
        params = self._build_historical_params(lat, lon, start_date, end_date)
        raw_data = await self._request_with_retry(url=self.base_url, params=params, session=session)
        return self._parse_historical_response(raw_data, location_id, lat, lon)

    async def fetch_forecast(
        self, location: tuple[float, float, str], horizon_days: int, **kwargs: Any
    ) -> list[ForecastPoint]:
        lat, lon, location_id = location
        session: aiohttp.ClientSession | None = kwargs.get("session")
        params = self._build_forecast_params(lat, lon, horizon_days)
        raw_data = await self._request_with_retry(url=self.base_url, params=params, session=session)
        return self._parse_forecast_response(raw_data, location_id, lat, lon)

    async def validate(self, **kwargs: Any) -> DataSourceHealth:
        session: aiohttp.ClientSession | None = kwargs.get("session")
        start_time = time.monotonic()
        try:
            params = {
                "latitude": "20.0",
                "longitude": "78.0",
                "hourly": "temperature_2m",
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "timezone": "auto",
            }
            own_session = False
            if session is None:
                session = aiohttp.ClientSession()
                own_session = True
            try:
                async with session.get(
                    self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=10)
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

    def get_product_metadata(self, product_id: str) -> dict[str, Any]:
        product = self._available_products[product_id]
        return {
            "product_name": product.product_name,
            "resolution_deg": product.resolution_deg,
            "lat_range": product.lat_range,
            "lon_range": product.lon_range,
            "time_range": (product.time_range[0].isoformat(), product.time_range[1].isoformat()),
            "variables": product.variables,
            "grid_shape": (product.lat_count, product.lon_count),
            "total_grid_points": product.total_grid_points,
            "source_id": self.source_id,
            "source_name": self.source_name,
        }

    def supports_location(
        self, latitude: float, longitude: float, product_id: str | None = None
    ) -> bool:
        products_to_check: list[IMDGridDefinition] = (
            [self._available_products[product_id]]
            if product_id and product_id in self._available_products
            else list(self._available_products.values())
        )
        for product in products_to_check:
            if (
                product.lat_range[0] <= latitude <= product.lat_range[1]
                and product.lon_range[0] <= longitude <= product.lon_range[1]
            ):
                return True
        return False

    def _build_historical_params(
        self, latitude: float, longitude: float, start_date: date, end_date: date
    ) -> dict[str, str]:
        return {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": ",".join(IMD_HOURLY_VARIABLES),
            "timezone": "auto",
        }

    def _build_forecast_params(
        self, latitude: float, longitude: float, horizon_days: int
    ) -> dict[str, str]:
        return {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            "hourly": ",".join(IMD_HOURLY_VARIABLES),
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
        for i, time_str in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(time_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue
            obs = WeatherObservation(
                location_id=location_id,
                latitude=latitude,
                longitude=longitude,
                timestamp=timestamp,
                temperature_2m=temps[i] if i < len(temps) else 0.0,
                precipitation_mm=precips[i] if i < len(precips) else 0.0,
                humidity_pct=humidities[i] if i < len(humidities) else 0.0,
                pressure_hpa=pressures[i] if i < len(pressures) else 1013.0,
                wind_speed_10m=wind_speeds[i] if i < len(wind_speeds) else 0.0,
                wind_direction_10m=wind_dirs[i] if i < len(wind_dirs) else 0.0,
                solar_radiation=radiations[i] if i < len(radiations) else None,
                cloud_cover_pct=clouds[i] if i < len(clouds) else None,
                data_source=self.data_source,
            )
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
                temperature_2m=temps[i] if i < len(temps) else 0.0,
                precipitation_mm=precips[i] if i < len(precips) else 0.0,
                humidity_pct=humidities[i] if i < len(humidities) else 0.0,
                pressure_hpa=pressures[i] if i < len(pressures) else 1013.0,
                wind_speed_10m=wind_speeds[i] if i < len(wind_speeds) else 0.0,
                wind_direction_10m=wind_dirs[i] if i < len(wind_dirs) else 0.0,
                cloud_cover_pct=clouds[i] if i < len(clouds) else None,
                solar_radiation=radiations[i] if i < len(radiations) else None,
                model_name="imd_fallback",
            )
            forecast_points.append(fp)
        return forecast_points

    def _validate_location_in_grid(
        self, latitude: float, longitude: float, product: IMDGridDefinition
    ) -> None:
        if not (product.lat_range[0] <= latitude <= product.lat_range[1]):
            raise ValueError(
                f"Latitude {latitude} is outside {product.product_name} grid coverage {product.lat_range}"
            )
        if not (product.lon_range[0] <= longitude <= product.lon_range[1]):
            raise ValueError(
                f"Longitude {longitude} is outside {product.product_name} grid coverage {product.lon_range}"
            )

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
        _logger.debug("IMD cache cleared")


def get_imd_connector(
    base_url: str = IMD_FALLBACK_BASE_URL,
    max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
    cache_ttl_seconds: int = _DEFAULT_CACHE_TTL,
) -> IMDConnector:
    return IMDConnector(
        base_url=base_url, max_concurrent=max_concurrent, cache_ttl_seconds=cache_ttl_seconds
    )
