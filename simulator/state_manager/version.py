"""Immutable version model for the Digital Twin state manager.

Each version represents a snapshot of a ClimateEntity at a point in time.
Versions are strictly append-only and never overwritten.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass(frozen=True)
class Version:
    """An immutable version snapshot of a ClimateEntity.

    Attributes:
        version_id: Monotonically increasing version number.
        location_id: The entity this version belongs to.
        entity_data: Serialized entity state.
        timestamp: When this version was created.
        state_type: The type of state (current, historical, forecast, scenario).
    """

    version_id: int
    location_id: str
    entity_data: dict[str, Any]
    timestamp: str = field(default_factory=_now_iso)
    state_type: str = "current"
