"""Weather observation data models.

These models represent real weather observations from any source
(IMD, ERA5, Open-Meteo, weather stations).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class DataSource(StrEnum):
    IMD = "imd"
    ERA5 = "era5"
    NOAA = "noaa"
    NASA_POWER = "nasa_power"
    OPEN_METEO = "open_meteo"
    WEATHER_STATION = "weather_station"
    SYNTHETIC = "synthetic"


class QualityFlag(StrEnum):
    RAW = "raw"
    VALIDATED = "validated"
    SUSPICIOUS = "suspicious"
    CORRECTED = "corrected"
    MISSING = "missing"
    ESTIMATED = "estimated"


@dataclass
class WeatherObservation:
    location_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    temperature_2m: float
    precipitation_mm: float
    humidity_pct: float
    pressure_hpa: float
    wind_speed_10m: float
    wind_direction_10m: float
    solar_radiation: float | None = None
    cloud_cover_pct: float | None = None
    soil_moisture: float | None = None
    data_source: DataSource = DataSource.OPEN_METEO
    quality_flag: QualityFlag = QualityFlag.RAW
    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    ingestion_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self._validate_coordinates()
        self._validate_percentages()
        self._validate_wind_direction()

    def _validate_coordinates(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {self.longitude}")

    def _validate_percentages(self) -> None:
        if not 0.0 <= self.humidity_pct <= 100.0:
            raise ValueError(f"Humidity must be in [0, 100], got {self.humidity_pct}")
        if self.cloud_cover_pct is not None and not 0.0 <= self.cloud_cover_pct <= 100.0:
            raise ValueError(f"Cloud cover must be in [0, 100], got {self.cloud_cover_pct}")

    def _validate_wind_direction(self) -> None:
        if not 0.0 <= self.wind_direction_10m < 360.0:
            raise ValueError(f"Wind direction must be in [0, 360), got {self.wind_direction_10m}")


__all__ = [
    "DataSource",
    "QualityFlag",
    "WeatherObservation",
]
