from __future__ import annotations

from pipeline.orchestrator import IngestionOrchestrator
from pipeline.scheduler import IngestionScheduler, ScheduledJob, SchedulerConfig
from pipeline.sources.base import DataConnector, DataSourceHealth, IngestionResult
from pipeline.sources.location_registry import Location, LocationRegistry
from pipeline.sources.openmeteo_connector import OpenMeteoConnector, get_openmeteo_connector
from pipeline.sources.quality import (
    QualityReport,
    check_coverage,
    detect_outliers,
    remove_duplicates,
    validate_humidity_range,
    validate_precipitation_range,
    validate_temperature_range,
    validate_timestamps,
)

__all__ = [
    "DataConnector",
    "DataSourceHealth",
    "IngestionResult",
    "Location",
    "LocationRegistry",
    "OpenMeteoConnector",
    "get_openmeteo_connector",
    "IngestionOrchestrator",
    "QualityReport",
    "check_coverage",
    "detect_outliers",
    "remove_duplicates",
    "validate_temperature_range",
    "validate_precipitation_range",
    "validate_humidity_range",
    "validate_timestamps",
    "IngestionScheduler",
    "SchedulerConfig",
    "ScheduledJob",
]
