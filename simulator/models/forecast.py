from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ForecastPoint:
    location_id: str
    latitude: float
    longitude: float
    forecast_timestamp: datetime
    issue_timestamp: datetime
    temperature_2m: float
    precipitation_mm: float
    humidity_pct: float
    pressure_hpa: float
    wind_speed_10m: float
    wind_direction_10m: float
    cloud_cover_pct: float | None = None
    solar_radiation: float | None = None
    model_name: str = "unknown"
    ensemble_member: int = 0
    confidence_interval_lower: float | None = None
    confidence_interval_upper: float | None = None
    point_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {self.longitude}")
        if not 0.0 <= self.humidity_pct <= 100.0:
            raise ValueError(f"Humidity must be in [0, 100], got {self.humidity_pct}")
        if not 0.0 <= self.wind_direction_10m < 360.0:
            raise ValueError(f"Wind direction must be in [0, 360), got {self.wind_direction_10m}")


@dataclass
class ForecastSeries:
    location_id: str
    latitude: float
    longitude: float
    points: list[ForecastPoint]
    model_name: str
    issue_timestamp: datetime
    horizon_hours: int
    series_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("Forecast series must contain at least one point")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {self.longitude}")
        if self.horizon_hours <= 0:
            raise ValueError(f"Horizon hours must be positive, got {self.horizon_hours}")

    @property
    def variable_names(self) -> list[str]:
        return [
            "temperature_2m",
            "precipitation_mm",
            "humidity_pct",
            "pressure_hpa",
            "wind_speed_10m",
            "wind_direction_10m",
        ]


@dataclass
class ForecastValidation:
    location_id: str
    forecast_issue_timestamp: datetime
    forecast_horizon_hours: int
    model_name: str
    variable: str
    mae: float
    rmse: float
    mape: float | None = None
    bias: float = 0.0
    correlation: float | None = None
    num_samples: int = 0
    observation_start: datetime | None = None
    observation_end: datetime | None = None
    validation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def __post_init__(self) -> None:
        if self.mae < 0:
            raise ValueError(f"MAE must be non-negative, got {self.mae}")
        if self.rmse < 0:
            raise ValueError(f"RMSE must be non-negative, got {self.rmse}")
        if self.mape is not None and self.mape < 0:
            raise ValueError(f"MAPE must be non-negative, got {self.mape}")
        if self.num_samples < 0:
            raise ValueError(f"Number of samples must be non-negative, got {self.num_samples}")


__all__ = [
    "ForecastPoint",
    "ForecastSeries",
    "ForecastValidation",
]
