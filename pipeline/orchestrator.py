from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from pipeline.sources.base import DataConnector, IngestionResult
from pipeline.sources.quality import (
    QualityReport,
    remove_duplicates,
    validate_humidity_range,
    validate_precipitation_range,
    validate_temperature_range,
    validate_timestamps,
)
from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    def __init__(self, connectors: list[DataConnector] | None = None) -> None:
        self.connectors: dict[str, DataConnector] = {}
        if connectors:
            for c in connectors:
                self.connectors[c.source_id] = c

    def register_connector(self, connector: DataConnector) -> None:
        self.connectors[connector.source_id] = connector
        _logger.info("Registered connector: %s (%s)", connector.source_id, connector.source_name)

    def get_connector(self, source_id: str) -> DataConnector | None:
        return self.connectors.get(source_id)

    async def ingest_all_sources(
        self,
        location: tuple[float, float, str],
        start_date: date,
        end_date: date | None = None,
        horizon_days: int | None = None,
    ) -> list[IngestionResult]:
        if end_date is None:
            end_date = start_date
        tasks: list[asyncio.Task[IngestionResult]] = []
        for connector in self.connectors.values():
            task = asyncio.ensure_future(
                self._ingest_single_source(connector, location, start_date, end_date, horizon_days)
            )
            tasks.append(task)
        if not tasks:
            return []
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)

    async def _ingest_single_source(
        self,
        connector: DataConnector,
        location: tuple[float, float, str],
        start_date: date,
        end_date: date,
        horizon_days: int | None = None,
    ) -> IngestionResult:
        try:
            if horizon_days is not None:
                records = await connector.fetch_forecast(
                    location=location, horizon_days=horizon_days
                )
                return IngestionResult(
                    source_name=connector.source_name,
                    location_id=location[2],
                    records_ingested=len(records),
                    success=True,
                )
            else:
                records = await connector.fetch_historical(
                    location=location, start_date=start_date, end_date=end_date
                )
                return IngestionResult(
                    source_name=connector.source_name,
                    location_id=location[2],
                    records_ingested=len(records),
                    success=True,
                )
        except Exception as e:
            _logger.error("Ingestion failed for %s at %s: %s", connector.source_id, location[2], e)
            return IngestionResult(
                source_name=connector.source_name,
                location_id=location[2],
                records_ingested=0,
                success=False,
                error_message=str(e),
            )

    def deduplicate_and_merge(
        self, observations: list[WeatherObservation]
    ) -> list[WeatherObservation]:
        return remove_duplicates(observations)

    def quality_check(
        self, observations: list[WeatherObservation], location_id: str = ""
    ) -> QualityReport:
        errors: list[str] = []
        passed = 0
        failed = 0
        for obs in observations:
            temp_errors = validate_temperature_range(obs.temperature_2m)
            if temp_errors:
                errors.extend(temp_errors)
                failed += 1
            else:
                passed += 1
            precip_errors = validate_precipitation_range(obs.precipitation_mm)
            if precip_errors:
                errors.extend(precip_errors)
                failed += 1
            else:
                passed += 1
            humidity_errors = validate_humidity_range(obs.humidity_pct)
            if humidity_errors:
                errors.extend(humidity_errors)
                failed += 1
            else:
                passed += 1
        ts_errors = validate_timestamps(observations)
        if ts_errors:
            errors.extend(ts_errors)
            failed += 1
        else:
            passed += 1
        return QualityReport(
            location_id=location_id or "unknown",
            total_observations=len(observations),
            passed_checks=passed,
            failed_checks=failed,
            errors=errors,
            coverage_fraction=1.0 if observations else 0.0,
        )

    def publish_ingestion_event(self, event: Any, event_bus: Any | None = None) -> None:
        if event_bus is not None and hasattr(event_bus, "publish"):
            event_bus.publish(event)
            _logger.debug("Published ingestion event: %s", event)
        else:
            _logger.info("Ingestion event (no bus): %s", event)
