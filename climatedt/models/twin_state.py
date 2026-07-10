"""Twin state model — mirrors BHAI TwinState for backward compatibility."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TwinState:
    """Represents the current state of the digital twin."""

    twin_id: str
    location_id: str
    status: str = "initialized"
    last_sync: datetime | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
