"""Climate Entity — the base domain model for the Digital Twin.

Every monitored location (grid cell or district) is a ClimateEntity
with attributes, state management, and lifecycle methods.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from simulator.entities.state import StateType

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class ClimateEntity:
    """Base domain model for a climate-monitored location.

    Attributes:
        location_id: Unique identifier (e.g., \"KA-BLR-001\").
        latitude: Decimal latitude.
        longitude: Decimal longitude.
        district: District name.
        timestamp: ISO timestamp of the current state.
        rainfall: Current rainfall value in mm.
        max_temp: Current maximum temperature in Celsius.
        min_temp: Current minimum temperature in Celsius.
        risk_score: Climate risk score (0-100).
        prediction_confidence: Confidence score (0-1) of the forecast.
        scenario_id: ID of the active scenario, if any.
        data_source: Source of the current data (\"IMD\", \"INSAT\", \"forecast\", \"scenario\").
        state_type: Type of the current state.
    """

    location_id: str
    latitude: float
    longitude: float
    district: str = ""
    timestamp: str = field(default_factory=_now_iso)
    rainfall: float = 0.0
    max_temp: float = 25.0
    min_temp: float = 18.0
    risk_score: float = 0.0
    prediction_confidence: float = 0.0
    scenario_id: str = ""
    data_source: str = "IMD"
    state_type: str = StateType.CURRENT.value

    def update_state(self, **kwargs: Any) -> "ClimateEntity":
        """Create a new entity with updated fields (immutable pattern).

        Returns a *new* ClimateEntity — the original is never modified.
        """
        new_data = {
            "location_id": self.location_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district": self.district,
            "timestamp": kwargs.pop("timestamp", _now_iso()),
            "rainfall": kwargs.pop("rainfall", self.rainfall),
            "max_temp": kwargs.pop("max_temp", self.max_temp),
            "min_temp": kwargs.pop("min_temp", self.min_temp),
            "risk_score": kwargs.pop("risk_score", self.risk_score),
            "prediction_confidence": kwargs.pop(
                "prediction_confidence", self.prediction_confidence
            ),
            "scenario_id": kwargs.pop("scenario_id", self.scenario_id),
            "data_source": kwargs.pop("data_source", self.data_source),
            "state_type": kwargs.pop("state_type", self.state_type),
        }
        return ClimateEntity(**new_data)

    def serialize(self) -> dict[str, Any]:
        """Serialize entity to a dictionary for storage."""
        return {
            "location_id": self.location_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district": self.district,
            "timestamp": self.timestamp,
            "rainfall": self.rainfall,
            "max_temp": self.max_temp,
            "min_temp": self.min_temp,
            "risk_score": self.risk_score,
            "prediction_confidence": self.prediction_confidence,
            "scenario_id": self.scenario_id,
            "data_source": self.data_source,
            "state_type": self.state_type,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "ClimateEntity":
        """Create an entity from a dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> list[str]:
        """Validate entity data and return a list of error messages."""
        errors: list[str] = []
        if not self.location_id:
            errors.append("location_id is required")
        if not (-90 <= self.latitude <= 90):
            errors.append(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            errors.append(f"Invalid longitude: {self.longitude}")
        if self.rainfall < 0 or self.rainfall > 2000:
            errors.append(f"Invalid rainfall: {self.rainfall}")
        if self.max_temp < -10 or self.max_temp > 55:
            errors.append(f"Invalid max_temp: {self.max_temp}")
        if self.min_temp < -10 or self.min_temp > 55:
            errors.append(f"Invalid min_temp: {self.min_temp}")
        if self.state_type not in {s.value for s in StateType}:
            errors.append(f"Invalid state_type: {self.state_type}")
        return errors
