from __future__ import annotations

import logging
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.orchestrator import IngestionOrchestrator
from pipeline.sources.base import DataConnector
from simulator.models.weather import DataSource, QualityFlag, WeatherObservation


def _obs(
    temperature_2m: float = 25.0,
    precipitation_mm: float = 0.0,
    humidity_pct: float = 50.0,
    timestamp: datetime | None = None,
    location_id: str = "loc1",
) -> WeatherObservation:
    return WeatherObservation(
        location_id=location_id,
        latitude=15.0,
        longitude=75.0,
        timestamp=timestamp or datetime(2024, 1, 1, 0, 0),
        temperature_2m=temperature_2m,
        precipitation_mm=precipitation_mm,
        humidity_pct=humidity_pct,
        pressure_hpa=1013.0,
        wind_speed_10m=5.0,
        wind_direction_10m=90.0,
        data_source=DataSource.OPEN_METEO,
        quality_flag=QualityFlag.RAW,
    )


@pytest.fixture
def connector():
    c = MagicMock(spec=DataConnector)
    c.source_id = "test_source"
    c.source_name = "Test Source"
    c.fetch_historical = AsyncMock(return_value=[])
    c.fetch_forecast = AsyncMock(return_value=[])
    return c


@pytest.fixture
def orch():
    return IngestionOrchestrator()


class TestInit:
    def test_no_connectors(self):
        assert IngestionOrchestrator().connectors == {}

    def test_with_connectors(self, connector):
        o = IngestionOrchestrator(connectors=[connector])
        assert o.connectors == {"test_source": connector}


class TestRegisterConnector:
    def test_registers_and_logs(self, orch, connector, caplog):
        caplog.set_level(logging.INFO)
        orch.register_connector(connector)
        assert orch.connectors["test_source"] is connector
        assert "Registered connector: test_source (Test Source)" in caplog.text


class TestGetConnector:
    def test_found(self, orch, connector):
        orch.register_connector(connector)
        assert orch.get_connector("test_source") is connector

    def test_not_found(self, orch):
        assert orch.get_connector("missing") is None


class TestIngestAllSources:
    @pytest.mark.asyncio
    async def test_empty_connectors(self, orch):
        assert await orch.ingest_all_sources((15.0, 75.0, "loc1"), date(2024, 1, 1)) == []

    @pytest.mark.asyncio
    async def test_defaults_end_date_to_start_date(self, orch, connector):
        orch.register_connector(connector)
        await orch.ingest_all_sources((15.0, 75.0, "loc1"), date(2024, 1, 1))
        connector.fetch_historical.assert_awaited_once_with(
            location=(15.0, 75.0, "loc1"), start_date=date(2024, 1, 1), end_date=date(2024, 1, 1)
        )

    @pytest.mark.asyncio
    async def test_historical_path(self, orch, connector):
        orch.register_connector(connector)
        r = await orch.ingest_all_sources(
            (15.0, 75.0, "loc1"), date(2024, 1, 1), end_date=date(2024, 1, 3)
        )
        assert len(r) == 1
        assert r[0].success and r[0].source_name == "Test Source"

    @pytest.mark.asyncio
    async def test_forecast_path(self, orch, connector):
        orch.register_connector(connector)
        r = await orch.ingest_all_sources((15.0, 75.0, "loc1"), date(2024, 1, 1), horizon_days=5)
        assert len(r) == 1 and r[0].success

    @pytest.mark.asyncio
    async def test_multiple_connectors(self, orch):
        c1 = MagicMock(spec=DataConnector)
        c1.source_id = "a"
        c1.source_name = "A"
        c1.fetch_historical = AsyncMock(return_value=[])
        c1.fetch_forecast = AsyncMock(return_value=[])
        c2 = MagicMock(spec=DataConnector)
        c2.source_id = "b"
        c2.source_name = "B"
        c2.fetch_historical = AsyncMock(return_value=[])
        c2.fetch_forecast = AsyncMock(return_value=[])
        orch.register_connector(c1)
        orch.register_connector(c2)
        r = await orch.ingest_all_sources(
            (15.0, 75.0, "loc1"), date(2024, 1, 1), end_date=date(2024, 1, 2)
        )
        assert len(r) == 2


class TestIngestSingleSource:
    @pytest.mark.asyncio
    async def test_forecast(self, orch, connector):
        connector.fetch_forecast = AsyncMock(return_value=[_obs()])
        r = await orch._ingest_single_source(
            connector, (15.0, 75.0, "loc1"), date(2024, 1, 1), date(2024, 1, 1), horizon_days=7
        )
        connector.fetch_forecast.assert_awaited_once_with(
            location=(15.0, 75.0, "loc1"), horizon_days=7
        )
        assert r.success and r.records_ingested == 1

    @pytest.mark.asyncio
    async def test_historical(self, orch, connector):
        connector.fetch_historical = AsyncMock(return_value=[_obs(), _obs()])
        r = await orch._ingest_single_source(
            connector, (15.0, 75.0, "loc1"), date(2024, 1, 1), date(2024, 1, 2)
        )
        connector.fetch_historical.assert_awaited_once_with(
            location=(15.0, 75.0, "loc1"), start_date=date(2024, 1, 1), end_date=date(2024, 1, 2)
        )
        assert r.success and r.records_ingested == 2

    @pytest.mark.asyncio
    async def test_error(self, orch, connector, caplog):
        caplog.set_level(logging.ERROR)
        connector.fetch_historical = AsyncMock(side_effect=ValueError("boom"))
        r = await orch._ingest_single_source(
            connector, (15.0, 75.0, "loc1"), date(2024, 1, 1), date(2024, 1, 2)
        )
        assert not r.success and r.records_ingested == 0 and r.error_message == "boom"
        assert "Ingestion failed for test_source at loc1: boom" in caplog.text


class TestDeduplicateAndMerge:
    def test_deduplicates(self, orch):
        ts = datetime(2024, 1, 1, 0, 0)
        dupe = _obs(timestamp=ts)
        result = orch.deduplicate_and_merge([_obs(timestamp=ts), dupe, _obs(timestamp=ts)])
        assert len(result) == 1


class TestQualityCheck:
    def test_all_valid(self, orch):
        obs = [_obs(temperature_2m=22.0, precipitation_mm=10.0, humidity_pct=55.0)]
        r = orch.quality_check(obs, location_id="loc1")
        assert r.location_id == "loc1"
        assert r.total_observations == 1
        assert r.passed_checks == 4
        assert r.failed_checks == 0
        assert r.coverage_fraction == 1.0

    def test_invalid_values(self, orch):
        obs = [_obs(temperature_2m=999.0, precipitation_mm=-5.0, humidity_pct=50.0)]
        r = orch.quality_check(obs)
        assert r.failed_checks >= 2
        assert r.passed_checks == 2
        assert any("Temperature" in e for e in r.errors)
        assert any("Precipitation" in e for e in r.errors)

    def test_humidity_failure(self, orch, monkeypatch):
        monkeypatch.setattr(
            "pipeline.orchestrator.validate_humidity_range",
            lambda v: ["Humidity out of range"],
        )
        obs = [_obs(humidity_pct=50.0)]
        r = orch.quality_check(obs)
        assert r.failed_checks > 0
        assert any("Humidity out of range" in e for e in r.errors)

    def test_empty_list(self, orch):
        r = orch.quality_check([], location_id="")
        assert r.total_observations == 0
        assert r.coverage_fraction == 0.0
        assert r.location_id == "unknown"
        assert r.passed_checks == 1
        assert r.failed_checks == 0

    def test_timestamp_order_mismatch(self, orch):
        obs = [
            _obs(timestamp=datetime(2024, 1, 1, 2, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 1, 0)),
        ]
        r = orch.quality_check(obs)
        assert r.failed_checks > 0
        assert any("Timestamp out of order" in e for e in r.errors)


class TestPublishIngestionEvent:
    def test_with_bus(self, orch, caplog):
        caplog.set_level(logging.DEBUG)
        bus = MagicMock()
        orch.publish_ingestion_event({"key": "val"}, bus)
        bus.publish.assert_called_once_with({"key": "val"})
        assert "Published ingestion event" in caplog.text

    def test_without_bus(self, orch, caplog):
        caplog.set_level(logging.INFO)
        orch.publish_ingestion_event({"key": "val"})
        assert "Ingestion event (no bus)" in caplog.text

    def test_bus_missing_publish(self, orch, caplog):
        caplog.set_level(logging.INFO)
        orch.publish_ingestion_event({"key": "val"}, object())
        assert "Ingestion event (no bus)" in caplog.text
