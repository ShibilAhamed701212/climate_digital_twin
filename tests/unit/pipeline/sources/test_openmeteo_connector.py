"""Tests for OpenMeteoConnector."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from pipeline.sources.base import DataSourceHealth
from pipeline.sources.openmeteo_connector import OpenMeteoConnector
from simulator.models.forecast import ForecastPoint
from simulator.models.weather import DataSource, WeatherObservation


@pytest.fixture
def connector():
    return OpenMeteoConnector(max_concurrent=10, cache_ttl_seconds=60)


def _make_json_data(times, temps=None, precips=None, humidities=None):
    n = len(times)
    return {
        "hourly": {
            "time": times,
            "temperature_2m": temps or [20.0] * n,
            "precipitation": precips or [0.0] * n,
            "relative_humidity_2m": humidities or [50.0] * n,
            "surface_pressure": [1013.0] * n,
            "wind_speed_10m": [5.0] * n,
            "wind_direction_10m": [180.0] * n,
            "shortwave_radiation": [100.0] * n,
            "cloud_cover": [50.0] * n,
            "soil_moisture_0_to_7cm": [0.3] * n,
        }
    }


class TestBuildArchiveParams:
    def test_basic(self, connector):
        params = connector._build_archive_params(12.97, 77.59, date(2023, 1, 1), date(2023, 1, 3))
        assert params["latitude"] == "12.9700"
        assert params["longitude"] == "77.5900"
        assert params["start_date"] == "2023-01-01"
        assert params["end_date"] == "2023-01-03"
        assert "hourly" in params
        assert "daily" in params
        assert params["timezone"] == "auto"

    def test_negative_coordinates(self, connector):
        params = connector._build_archive_params(-33.86, 151.21, date(2023, 6, 1), date(2023, 6, 2))
        assert params["latitude"] == "-33.8600"
        assert params["longitude"] == "151.2100"


class TestBuildForecastParams:
    def test_basic(self, connector):
        params = connector._build_forecast_params(12.97, 77.59, 7)
        assert params["latitude"] == "12.9700"
        assert params["longitude"] == "77.5900"
        assert params["forecast_days"] == "7"
        assert "hourly" in params
        assert params["timezone"] == "auto"

    def test_single_day(self, connector):
        params = connector._build_forecast_params(0.0, 0.0, 1)
        assert params["forecast_days"] == "1"


class TestCache:
    def test_cache_hit(self, connector):
        key = "test_key"
        connector._set_cache(key, {"temp": 25})
        assert connector._get_cached(key) == {"temp": 25}

    def test_cache_miss(self, connector):
        assert connector._get_cached("nonexistent") is None

    def test_cache_expiry(self, connector):
        connector.cache_ttl_seconds = -1
        connector._set_cache("key", {"x": 1})
        assert connector._get_cached("key") is None

    def test_clear_cache(self, connector):
        connector._set_cache("k1", {"a": 1})
        connector._set_cache("k2", {"b": 2})
        connector.clear_cache()
        assert connector._cache == {}

    def test_make_cache_key(self, connector):
        k1 = connector._make_cache_key("http://example.com", {"a": "1"})
        k2 = connector._make_cache_key("http://example.com", {"a": "1"})
        assert k1 == k2
        k3 = connector._make_cache_key("http://example.com", {"a": "2"})
        assert k1 != k3


class TestParseHistorical:
    def test_empty_hourly(self, connector):
        result = connector._parse_historical_response({"hourly": {"time": []}}, "loc1", 0.0, 0.0)
        assert result == []

    def test_no_hourly(self, connector):
        result = connector._parse_historical_response({}, "loc1", 0.0, 0.0)
        assert result == []

    def test_basic_parse(self, connector):
        times = ["2024-01-01T00:00", "2024-01-01T01:00"]
        data = _make_json_data(times)
        result = connector._parse_historical_response(data, "loc1", 12.0, 77.0)
        assert len(result) == 2
        assert all(isinstance(o, WeatherObservation) for o in result)
        assert result[0].location_id == "loc1"
        assert result[0].temperature_2m == 20.0
        assert result[0].data_source == DataSource.OPEN_METEO

    def test_invalid_timestamp_skipped(self, connector):
        data = {
            "hourly": {
                "time": ["not-a-date"],
                "temperature_2m": [20.0],
                "precipitation": [0.0],
                "relative_humidity_2m": [50.0],
                "surface_pressure": [1013.0],
                "wind_speed_10m": [5.0],
                "wind_direction_10m": [180.0],
                "shortwave_radiation": [100.0],
                "cloud_cover": [50.0],
                "soil_moisture_0_to_7cm": [0.3],
            }
        }
        result = connector._parse_historical_response(data, "loc1", 0.0, 0.0)
        assert result == []

    def test_partial_data_skipped(self, connector):
        times = ["2024-01-01T00:00"]
        data = {"hourly": {"time": times, "temperature_2m": [25.0]}}
        result = connector._parse_historical_response(data, "loc1", 0.0, 0.0)
        assert len(result) == 0

    def test_utc_aware(self, connector):
        times = ["2024-01-01T00:00"]
        data = _make_json_data(times)
        result = connector._parse_historical_response(data, "loc1", 0.0, 0.0)
        assert result[0].timestamp.tzinfo is not None


class TestParseForecast:
    def test_empty_hourly(self, connector):
        result = connector._parse_forecast_response({"hourly": {"time": []}}, "loc1", 0.0, 0.0)
        assert result == []

    def test_no_hourly(self, connector):
        result = connector._parse_forecast_response({}, "loc1", 0.0, 0.0)
        assert result == []

    def test_basic_parse(self, connector):
        times = ["2024-01-01T12:00", "2024-01-01T13:00"]
        data = _make_json_data(times)
        result = connector._parse_forecast_response(data, "loc1", 12.0, 77.0)
        assert len(result) == 2
        assert all(isinstance(fp, ForecastPoint) for fp in result)
        assert result[0].location_id == "loc1"
        assert result[0].model_name == "open_meteo"

    def test_invalid_timestamp(self, connector):
        data = {
            "hourly": {
                "time": ["bad"],
                "temperature_2m": [20.0],
                "precipitation": [0.0],
                "relative_humidity_2m": [50.0],
                "surface_pressure": [1013.0],
                "wind_speed_10m": [5.0],
                "wind_direction_10m": [180.0],
                "shortwave_radiation": [100.0],
                "cloud_cover": [50.0],
            }
        }
        result = connector._parse_forecast_response(data, "loc1", 0.0, 0.0)
        assert result == []


class TestRequestWithRetry:
    @pytest.mark.asyncio
    async def test_successful_request(self, connector):
        resp = MagicMock(spec=aiohttp.ClientResponse)
        resp.status = 200
        resp.json = AsyncMock(return_value={"key": "value"})
        cm = AsyncMock()
        cm.__aenter__.return_value = resp
        cm.__aexit__.return_value = None
        with patch.object(connector._rate_limiter, "acquire", AsyncMock()):
            with patch.object(connector._rate_limiter, "release"):
                with patch("aiohttp.ClientSession.get", return_value=cm):
                    result = await connector._request_with_retry("http://example.com", {"p": "1"})
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_non_retryable_status(self, connector):
        resp = MagicMock(spec=aiohttp.ClientResponse)
        resp.status = 400
        resp.text = AsyncMock(return_value="bad request")
        cm = AsyncMock()
        cm.__aenter__.return_value = resp
        cm.__aexit__.return_value = None
        with patch.object(connector._rate_limiter, "acquire", AsyncMock()):
            with patch.object(connector._rate_limiter, "release"):
                with patch("aiohttp.ClientSession.get", return_value=cm):
                    with pytest.raises(aiohttp.ClientResponseError):
                        await connector._request_with_retry(
                            "http://example.com", {"p": "1"}, max_attempts=1
                        )

    @pytest.mark.asyncio
    async def test_network_error_retries(self, connector):
        with patch.object(connector._rate_limiter, "acquire", AsyncMock()):
            with patch.object(connector._rate_limiter, "release"):
                with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ClientError("timeout")):
                    with patch("asyncio.sleep", AsyncMock()):
                        with pytest.raises(aiohttp.ClientError):
                            await connector._request_with_retry(
                                "http://example.com", {"p": "1"}, max_attempts=2, base_delay=0.01
                            )


class TestFetchHistorical:
    @pytest.mark.asyncio
    async def test_integration(self, connector):
        times = ["2024-01-01T00:00", "2024-01-01T01:00"]
        data = _make_json_data(times)
        with patch.object(connector, "_request_with_retry", AsyncMock(return_value=data)):
            result = await connector.fetch_historical(
                (12.0, 77.0, "loc1"), date(2024, 1, 1), date(2024, 1, 1)
            )
        assert len(result) == 2


class TestFetchForecast:
    @pytest.mark.asyncio
    async def test_integration(self, connector):
        times = ["2024-01-02T00:00", "2024-01-02T01:00"]
        data = _make_json_data(times)
        with patch.object(connector, "_request_with_retry", AsyncMock(return_value=data)):
            result = await connector.fetch_forecast((12.0, 77.0, "loc1"), 1)
        assert len(result) == 2


class TestValidate:
    @pytest.mark.asyncio
    async def test_reachable(self, connector):
        resp = MagicMock(spec=aiohttp.ClientResponse)
        resp.ok = True
        resp.status = 200
        cm = AsyncMock()
        cm.__aenter__.return_value = resp
        cm.__aexit__.return_value = None
        with patch("aiohttp.ClientSession.get", return_value=cm):
            health = await connector.validate()
        assert health.reachable is True
        assert isinstance(health, DataSourceHealth)

    @pytest.mark.asyncio
    async def test_unreachable(self, connector):
        with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ClientError("no connection")):
            health = await connector.validate()
        assert health.reachable is False
        assert health.source_id == connector.source_id

    @pytest.mark.asyncio
    async def test_http_error(self, connector):
        resp = MagicMock(spec=aiohttp.ClientResponse)
        resp.ok = False
        resp.status = 500
        cm = AsyncMock()
        cm.__aenter__.return_value = resp
        cm.__aexit__.return_value = None
        with patch("aiohttp.ClientSession.get", return_value=cm):
            health = await connector.validate()
        assert health.reachable is False
        assert health.status_code == 500


class TestGetConnector:
    def test_get_connector(self):
        from pipeline.sources.openmeteo_connector import get_openmeteo_connector

        c = get_openmeteo_connector()
        assert isinstance(c, OpenMeteoConnector)
        assert c.max_concurrent == 5
        assert c.cache_ttl_seconds == 3600

    def test_get_connector_custom(self):
        from pipeline.sources.openmeteo_connector import get_openmeteo_connector

        c = get_openmeteo_connector(max_concurrent=2, cache_ttl_seconds=10)
        assert c.max_concurrent == 2
        assert c.cache_ttl_seconds == 10
