from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest

from pipeline.sources.base import DataConnector, DataSourceHealth, IngestionResult
from simulator.models.forecast import ForecastPoint
from simulator.models.weather import WeatherObservation


class _ConcreteConnector(DataConnector):
    source_id = "test_source"
    source_name = "Test Source"

    def __init__(self, fail_fetch: bool = False, fail_forecast: bool = False) -> None:
        self.fail_fetch = fail_fetch
        self.fail_forecast = fail_forecast

    async def fetch_historical(
        self, location: tuple[float, float, str], start_date: date, end_date: date, **kwargs: Any
    ) -> list[WeatherObservation]:
        if self.fail_fetch:
            raise RuntimeError("Fetch failed")
        return [
            WeatherObservation(
                location_id=location[2],
                latitude=location[0],
                longitude=location[1],
                timestamp=datetime.combine(start_date, datetime.min.time()),
                temperature_2m=25.0,
                precipitation_mm=0.0,
                humidity_pct=60.0,
                pressure_hpa=1013.0,
                wind_speed_10m=5.0,
                wind_direction_10m=180.0,
            )
        ]

    async def fetch_forecast(
        self, location: tuple[float, float, str], horizon_days: int, **kwargs: Any
    ) -> list[ForecastPoint]:
        if self.fail_forecast:
            raise RuntimeError("Forecast failed")
        return [
            ForecastPoint(
                location_id=location[2],
                latitude=location[0],
                longitude=location[1],
                forecast_timestamp=datetime(2020, 1, 1),
                issue_timestamp=datetime(2020, 1, 1),
                temperature_2m=25.0,
                precipitation_mm=0.0,
                humidity_pct=60.0,
                pressure_hpa=1013.0,
                wind_speed_10m=5.0,
                wind_direction_10m=180.0,
            )
        ]

    async def validate(self, **kwargs: Any) -> DataSourceHealth:
        return DataSourceHealth(source_id=self.source_id, reachable=True, status_code=200)


class _MockStore:
    def __init__(self) -> None:
        self.observations: list[WeatherObservation] = []
        self.forecasts: list[ForecastPoint] = []

    def write_observations(self, obs: list[WeatherObservation]) -> None:
        self.observations.extend(obs)

    def write_forecast(self, fcst: list[ForecastPoint]) -> None:
        self.forecasts.extend(fcst)


@pytest.mark.asyncio
class TestIngestHistorical:
    async def test_success_without_store(self) -> None:
        conn = _ConcreteConnector()
        result = await conn.ingest_historical(
            (12.0, 77.0, "LOC-001"), date(2020, 1, 1), date(2020, 1, 10)
        )
        assert result.success is True
        assert result.records_ingested == 1
        assert result.location_id == "LOC-001"
        assert result.source_name == "Test Source"

    async def test_success_with_store(self) -> None:
        conn = _ConcreteConnector()
        store = _MockStore()
        result = await conn.ingest_historical(
            (12.0, 77.0, "LOC-001"), date(2020, 1, 1), date(2020, 1, 10), store=store
        )
        assert result.success is True
        assert len(store.observations) == 1

    async def test_failure(self) -> None:
        conn = _ConcreteConnector(fail_fetch=True)
        result = await conn.ingest_historical(
            (12.0, 77.0, "LOC-001"), date(2020, 1, 1), date(2020, 1, 10)
        )
        assert result.success is False
        assert result.records_ingested == 0
        assert result.error_message is not None
        assert "Fetch failed" in result.error_message


@pytest.mark.asyncio
class TestIngestForecast:
    async def test_success_without_store(self) -> None:
        conn = _ConcreteConnector()
        result = await conn.ingest_forecast((12.0, 77.0, "LOC-001"), horizon_days=7)
        assert result.success is True
        assert result.records_ingested == 1

    async def test_success_with_store(self) -> None:
        conn = _ConcreteConnector()
        store = _MockStore()
        result = await conn.ingest_forecast((12.0, 77.0, "LOC-001"), horizon_days=7, store=store)
        assert result.success is True
        assert len(store.forecasts) == 1

    async def test_failure(self) -> None:
        conn = _ConcreteConnector(fail_forecast=True)
        result = await conn.ingest_forecast((12.0, 77.0, "LOC-001"), horizon_days=7)
        assert result.success is False
        assert result.records_ingested == 0
        assert result.error_message is not None
        assert "Forecast failed" in result.error_message


class TestIngestionResult:
    def test_default_ingested_at(self) -> None:
        result = IngestionResult(
            source_name="Test", location_id="LOC-001", records_ingested=0, success=False
        )
        assert result.ingested_at is not None

    def test_error_message(self) -> None:
        result = IngestionResult(
            source_name="Test",
            location_id="LOC-001",
            records_ingested=0,
            success=False,
            error_message="Something went wrong",
        )
        assert result.error_message == "Something went wrong"
