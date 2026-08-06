from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class SyncResult:
    status: str
    location_id: str = ""
    observation_id: str = ""
    run_id: str = ""
    provider: str = ""
    authenticity: str = ""
    old_version: int = 0
    new_version: int = 0
    changed_variables: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error: str | None = None


CREATED = "CREATED"
UPDATED = "UPDATED"
NO_STATE_CHANGE = "NO_STATE_CHANGE"
SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
OUT_OF_ORDER = "OUT_OF_ORDER"
REJECTED_QUALITY = "REJECTED_QUALITY"
REJECTED_SYNTHETIC = "REJECTED_SYNTHETIC"
LOCATION_MISMATCH = "LOCATION_MISMATCH"
FAILED = "FAILED"
