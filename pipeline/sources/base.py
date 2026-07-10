from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from simulator.models.forecast import ForecastPoint
from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)


@dataclass
class DataSourceHealth:
    source_id: str
    reachable: bool
    status_code: int
    response_time_ms: float | None = None
    error_message: str | None = None


@dataclass
class IngestionResult:
    source_name: str
    location_id: str
    records_ingested: int
    success: bool
    error_message: str | None = None
    ingested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class DataConnector(ABC):
    source_id: str = ""
    source_name: str = ""

    @abstractmethod
    async def fetch_historical(
        self,
        location: tuple[float, float, str],
        start_date: date,
        end_date: date,
        **kwargs: Any,
    ) -> list[WeatherObservation]: ...

    @abstractmethod
    async def fetch_forecast(
        self,
        location: tuple[float, float, str],
        horizon_days: int,
        **kwargs: Any,
    ) -> list[ForecastPoint]: ...

    @abstractmethod
    async def validate(self, **kwargs: Any) -> DataSourceHealth: ...

    async def ingest_historical(
        self,
        location: tuple[float, float, str],
        start_date: date,
        end_date: date,
        store: object | None = None,
        **kwargs: Any,
    ) -> IngestionResult:
        location_id = location[2]
        _logger.info(
            "Ingesting historical %s for %s [%s to %s]",
            self.source_id,
            location_id,
            start_date,
            end_date,
        )
        try:
            observations = await self.fetch_historical(
                location=location, start_date=start_date, end_date=end_date, **kwargs
            )
            if store is not None and observations:
                store.write_observations(observations)
            return IngestionResult(
                source_name=self.source_name,
                location_id=location_id,
                records_ingested=len(observations),
                success=True,
            )
        except Exception as e:
            _logger.error(
                "Historical ingestion failed for %s at %s: %s", self.source_id, location_id, e
            )
            return IngestionResult(
                source_name=self.source_name,
                location_id=location_id,
                records_ingested=0,
                success=False,
                error_message=str(e),
            )

    async def ingest_forecast(
        self,
        location: tuple[float, float, str],
        horizon_days: int,
        store: object | None = None,
        **kwargs: Any,
    ) -> IngestionResult:
        location_id = location[2]
        _logger.info(
            "Ingesting forecast %s for %s (%d days)", self.source_id, location_id, horizon_days
        )
        try:
            forecasts = await self.fetch_forecast(
                location=location, horizon_days=horizon_days, **kwargs
            )
            if store is not None and forecasts and hasattr(store, "write_forecast"):
                store.write_forecast(forecasts)
            return IngestionResult(
                source_name=self.source_name,
                location_id=location_id,
                records_ingested=len(forecasts),
                success=True,
            )
        except Exception as e:
            _logger.error(
                "Forecast ingestion failed for %s at %s: %s", self.source_id, location_id, e
            )
            return IngestionResult(
                source_name=self.source_name,
                location_id=location_id,
                records_ingested=0,
                success=False,
                error_message=str(e),
            )
