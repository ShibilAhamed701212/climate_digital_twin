from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class IMDGridDefinition:
    product_name: str
    resolution_deg: float
    lat_range: tuple[float, float]
    lon_range: tuple[float, float]
    time_range: tuple[date, date]
    variables: list[str]
    description: str = ""

    def __post_init__(self) -> None:
        if self.resolution_deg <= 0:
            raise ValueError(f"Grid resolution must be positive, got {self.resolution_deg}")
        if not (-90.0 <= self.lat_range[0] <= 90.0 and -90.0 <= self.lat_range[1] <= 90.0):
            raise ValueError(f"Latitude range must be within [-90, 90], got {self.lat_range}")
        if not (-180.0 <= self.lon_range[0] <= 180.0 and -180.0 <= self.lon_range[1] <= 180.0):
            raise ValueError(f"Longitude range must be within [-180, 180], got {self.lon_range}")
        if self.lat_range[0] >= self.lat_range[1]:
            raise ValueError(f"Latitude range start must be less than end, got {self.lat_range}")
        if self.lon_range[0] >= self.lon_range[1]:
            raise ValueError(f"Longitude range start must be less than end, got {self.lon_range}")
        if self.time_range[0] >= self.time_range[1]:
            raise ValueError(
                f"Time range start ({self.time_range[0]}) must be before end ({self.time_range[1]})"
            )
        if not self.product_name:
            raise ValueError("Product name must not be empty")
        if not self.variables:
            raise ValueError("Variables list must not be empty")

    @property
    def lat_count(self) -> int:
        return int((self.lat_range[1] - self.lat_range[0]) / self.resolution_deg) + 1

    @property
    def lon_count(self) -> int:
        return int((self.lon_range[1] - self.lon_range[0]) / self.resolution_deg) + 1

    @property
    def total_grid_points(self) -> int:
        return self.lat_count * self.lon_count


@dataclass
class IMDDataProduct:
    grid: IMDGridDefinition
    file_url: str
    checksum: str
    last_updated: datetime
    version: str = "1.0"
    license_info: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.file_url:
            raise ValueError("File URL must not be empty")
        if not self.checksum:
            raise ValueError("Checksum must not be empty")
        if not self.version:
            raise ValueError("Version must not be empty")
        self._validate_checksum_format()

    def _validate_checksum_format(self) -> None:
        if not isinstance(self.checksum, str):
            raise TypeError(f"Checksum must be a string, got {type(self.checksum)}")
        if len(self.checksum) != 64:
            raise ValueError(
                f"Checksum must be a 64-character SHA-256 hex string, got {len(self.checksum)} chars"
            )
        try:
            int(self.checksum, 16)
        except ValueError as err:
            raise ValueError(f"Checksum must be a valid hex string, got '{self.checksum}'") from err

    def verify_integrity(self, data: bytes) -> bool:
        computed = hashlib.sha256(data).hexdigest()
        return computed == self.checksum


IMD_DAILY_RAINFALL = IMDGridDefinition(
    product_name="IMD Daily Rainfall",
    resolution_deg=0.25,
    lat_range=(6.5, 38.5),
    lon_range=(66.5, 100.5),
    time_range=(date(1901, 1, 1), date(2024, 12, 31)),
    variables=["precipitation_mm"],
    description="IMD daily gridded rainfall dataset at 0.25° × 0.25° resolution. Covers the Indian landmass from 1901 to present.",
)

IMD_DAILY_TEMPERATURE = IMDGridDefinition(
    product_name="IMD Daily Temperature",
    resolution_deg=1.0,
    lat_range=(7.5, 38.5),
    lon_range=(66.5, 100.5),
    time_range=(date(1951, 1, 1), date(2024, 12, 31)),
    variables=["temperature_max_c", "temperature_min_c"],
    description="IMD daily gridded temperature dataset (max/min) at 1° × 1° resolution. Covers the Indian landmass from 1951 to present.",
)

IMD_FALLBACK_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

IMD_GRIDDED_PRODUCTS: dict[str, IMDGridDefinition] = {
    "imd_daily_rainfall": IMD_DAILY_RAINFALL,
    "imd_daily_temperature": IMD_DAILY_TEMPERATURE,
}

__all__ = [
    "IMDGridDefinition",
    "IMDDataProduct",
    "IMD_DAILY_RAINFALL",
    "IMD_DAILY_TEMPERATURE",
    "IMD_GRIDDED_PRODUCTS",
    "IMD_FALLBACK_BASE_URL",
]
