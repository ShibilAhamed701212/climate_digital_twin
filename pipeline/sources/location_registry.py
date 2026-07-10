from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_logger = logging.getLogger(__name__)

_DEFAULT_LOCATIONS: list[dict[str, Any]] = [
    {
        "location_id": "KA-BLR-001",
        "name": "Bengaluru",
        "latitude": 12.97,
        "longitude": 77.59,
        "district": "Bengaluru Urban",
        "elevation_m": 920.0,
        "state": "Karnataka",
    },
    {
        "location_id": "KA-MYS-001",
        "name": "Mysuru",
        "latitude": 12.30,
        "longitude": 76.64,
        "district": "Mysuru",
        "elevation_m": 770.0,
        "state": "Karnataka",
    },
    {
        "location_id": "KA-BEL-001",
        "name": "Belagavi",
        "latitude": 15.85,
        "longitude": 74.50,
        "district": "Belagavi",
        "elevation_m": 760.0,
        "state": "Karnataka",
    },
    {
        "location_id": "KA-HUB-001",
        "name": "Hubballi",
        "latitude": 15.36,
        "longitude": 75.12,
        "district": "Dharwad",
        "elevation_m": 640.0,
        "state": "Karnataka",
    },
    {
        "location_id": "KA-MNG-001",
        "name": "Mangaluru",
        "latitude": 12.91,
        "longitude": 74.86,
        "district": "Dakshina Kannada",
        "elevation_m": 20.0,
        "state": "Karnataka",
    },
    {
        "location_id": "KA-KOL-001",
        "name": "Kolar",
        "latitude": 13.14,
        "longitude": 78.13,
        "district": "Kolar",
        "elevation_m": 820.0,
        "state": "Karnataka",
    },
    {
        "location_id": "KA-SGR-001",
        "name": "Shivamogga",
        "latitude": 13.93,
        "longitude": 75.57,
        "district": "Shivamogga",
        "elevation_m": 570.0,
        "state": "Karnataka",
    },
    {
        "location_id": "KA-TUM-001",
        "name": "Tumakuru",
        "latitude": 13.34,
        "longitude": 77.10,
        "district": "Tumakuru",
        "elevation_m": 820.0,
        "state": "Karnataka",
    },
]


@dataclass
class Location:
    location_id: str
    name: str
    latitude: float
    longitude: float
    district: str
    elevation_m: float | None = None
    state: str = "Karnataka"
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {self.longitude}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Location:
        return cls(
            location_id=data["location_id"],
            name=data["name"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            district=data["district"],
            elevation_m=data.get("elevation_m"),
            state=data.get("state", "Karnataka"),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district": self.district,
            "elevation_m": self.elevation_m,
            "state": self.state,
            "metadata": self.metadata,
        }


class LocationRegistry:
    def __init__(self, locations: list[Location] | None = None) -> None:
        self._locations: dict[str, Location] = {}
        self._lock = __import__("threading").Lock()
        if locations is None:
            self._load_defaults()
        else:
            for loc in locations:
                self._locations[loc.location_id] = loc
        _logger.info("LocationRegistry initialized with %d locations", len(self._locations))

    def _load_defaults(self) -> None:
        for data in _DEFAULT_LOCATIONS:
            loc = Location.from_dict(data)
            self._locations[loc.location_id] = loc

    def get_location(self, location_id: str) -> Location | None:
        return self._locations.get(location_id)

    def get_coordinates(self, location_id: str) -> tuple[float, float, str] | None:
        loc = self.get_location(location_id)
        if loc is None:
            return None
        return (loc.latitude, loc.longitude, loc.location_id)

    def add_location(self, location: Location) -> None:
        with self._lock:
            if location.location_id not in self._locations:
                self._locations[location.location_id] = location
                _logger.debug("Added location: %s (%s)", location.location_id, location.name)

    def add_locations(self, locations: list[Location]) -> None:
        for loc in locations:
            self.add_location(loc)

    def list_locations(
        self, district: str | None = None, state: str | None = None
    ) -> list[Location]:
        results = list(self._locations.values())
        if district:
            results = [loc for loc in results if loc.district == district]
        if state:
            results = [loc for loc in results if loc.state == state]
        return results

    def count(self) -> int:
        return len(self._locations)

    def clear(self) -> None:
        with self._lock:
            self._locations.clear()
        _logger.info("LocationRegistry cleared")
