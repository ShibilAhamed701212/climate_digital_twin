"""Digital Twin state data models.

These models represent the state of a digital twin entity (a geographic
location or district) at a point in time, along with versioned snapshots
and state deltas for change tracking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class TwinEntity:
    """A digital twin entity representing a geographic location/district.

    Attributes:
        entity_id: Unique identifier for the entity.
        name: Human-readable name (e.g., 'Bangalore Urban').
        location_id: Short code (e.g., 'KA-BLR-001').
        latitude: Centroid latitude in decimal degrees.
        longitude: Centroid longitude in decimal degrees.
        district: Administrative district name.
        state: State or region name.
        country: Country code (ISO 3166-1 alpha-2).
        elevation_m: Mean elevation in meters (optional).
        area_km2: Area in square kilometers (optional).
        metadata: Additional key-value metadata.
        created_at: When this entity was created.
    """

    entity_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    location_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    district: str = ""
    state: str = ""
    country: str = "IN"
    elevation_m: float | None = None
    area_km2: float | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.location_id and not self.name:
            raise ValueError("Either location_id or name must be provided")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {self.longitude}")


@dataclass
class TwinState:
    """The complete state of a twin entity at a point in time.

    Attributes:
        entity_id: The entity this state belongs to.
        timestamp: UTC timestamp of this state snapshot.
        temperature_2m: Current temperature at 2m in °C.
        precipitation_mm: Current precipitation in mm.
        humidity_pct: Current relative humidity in %.
        pressure_hpa: Current atmospheric pressure in hPa.
        wind_speed_10m: Current wind speed at 10m in m/s.
        wind_direction_10m: Current wind direction in degrees.
        solar_radiation: Current solar radiation in W/m² (optional).
        cloud_cover_pct: Current cloud cover in % (optional).
        soil_moisture: Current soil moisture in m³/m³ (optional).
        data_source: Source of the current state data.
        quality_flag: Quality flag for this state snapshot.
        metadata: Additional state metadata.
    """

    entity_id: str
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
    data_source: str = "open_meteo"
    quality_flag: str = "raw"
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.humidity_pct <= 100.0:
            raise ValueError(f"Humidity must be in [0, 100], got {self.humidity_pct}")
        if not 0.0 <= self.wind_direction_10m < 360.0:
            raise ValueError(f"Wind direction must be in [0, 360), got {self.wind_direction_10m}")
        if self.cloud_cover_pct is not None and not 0.0 <= self.cloud_cover_pct <= 100.0:
            raise ValueError(f"Cloud cover must be in [0, 100], got {self.cloud_cover_pct}")


@dataclass
class TwinStateVersion:
    """A versioned snapshot of twin state with metadata.

    Attributes:
        version_id: Unique identifier for this version.
        entity_id: The entity this version belongs to.
        version_number: Monotonically increasing version number.
        state: The actual state data.
        created_at: When this version was created.
        created_by: Identifier for what created this version.
        parent_version_id: Previous version ID for lineage tracking (optional).
        description: Human-readable description of changes in this version.
    """

    version_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    entity_id: str = ""
    version_number: int = 0
    state: TwinState | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "system"
    parent_version_id: str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.version_number < 0:
            raise ValueError(f"Version number must be non-negative, got {self.version_number}")


@dataclass
class StateDelta:
    """Difference between two twin states.

    Attributes:
        entity_id: The entity this delta applies to.
        from_version_id: The source version ID.
        to_version_id: The target version ID.
        delta_temperature: Change in temperature in °C.
        delta_precipitation: Change in precipitation in mm.
        delta_humidity: Change in humidity in %.
        delta_pressure: Change in pressure in hPa.
        delta_wind_speed: Change in wind speed in m/s.
        delta_wind_direction: Change in wind direction in degrees.
        delta_solar_radiation: Change in solar radiation in W/m² (optional).
        delta_cloud_cover: Change in cloud cover in % (optional).
        delta_soil_moisture: Change in soil moisture in m³/m³ (optional).
        computed_at: When this delta was computed.
    """

    entity_id: str
    from_version_id: str
    to_version_id: str
    delta_temperature: float = 0.0
    delta_precipitation: float = 0.0
    delta_humidity: float = 0.0
    delta_pressure: float = 0.0
    delta_wind_speed: float = 0.0
    delta_wind_direction: float = 0.0
    delta_solar_radiation: float | None = None
    delta_cloud_cover: float | None = None
    delta_soil_moisture: float | None = None
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    delta_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])


__all__ = [
    "TwinEntity",
    "TwinState",
    "TwinStateVersion",
    "StateDelta",
]
