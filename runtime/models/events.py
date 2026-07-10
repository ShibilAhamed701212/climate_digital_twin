from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """An event published through the Event Bus.

    Every event carries a trace_id for distributed tracing.
    Events are the primary communication mechanism between Runtime components.
    """

    type: str
    data: dict[str, Any]
    source: str
    trace_id: str
    timestamp: float = field(default_factory=time.time)
