from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BBEntry:
    """A single entry on the Blackboard.

    Every entry is versioned, attributed to an agent, and optionally linked
    to a parent version for causal tracing.
    """

    key: str
    value: Any
    agent: str
    version: int
    timestamp: float = field(default_factory=time.time)
    parent_version: int | None = None
    ttl: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def expired(self) -> bool:
        """Check if this entry has expired based on its TTL."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
