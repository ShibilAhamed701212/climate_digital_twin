"""Event type definitions for the Digital Twin event system."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TwinEvent:
    """Immutable event payload for the Digital Twin event system."""

    event_type: str
    location_id: str
    timestamp: str
    version_id: int
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        valid_types = {
            "ObservationUpdated",
            "ForecastGenerated",
            "ScenarioApplied",
            "ScenarioCreated",
            "ScenarioUpdated",
            "SimulationStarted",
            "SimulationCompleted",
            "SimulationFailed",
            "ScenarioDeleted",
            "RiskUpdated",
            "TwinRefreshed",
        }
        if self.event_type not in valid_types:
            raise ValueError(
                f"Invalid event type: {self.event_type}. "
                f"Must be one of: {valid_types}"
            )
