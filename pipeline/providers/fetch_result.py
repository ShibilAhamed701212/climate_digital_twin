from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from simulator.models.weather import DataSource

SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
REQUEST_FAILED = "REQUEST_FAILED"
AUTH_REQUIRED = "AUTH_REQUIRED"
RATE_LIMITED = "RATE_LIMITED"
INVALID_RESPONSE = "INVALID_RESPONSE"
NO_DATA = "NO_DATA"


@dataclass
class FetchResult:
    provider: DataSource
    status: str
    observations: list[Any]
    error_code: str | None = None
    error_message: str | None = None
    requested_at: datetime | None = None
    completed_at: datetime | None = None
    request_metadata: dict[str, Any] = field(default_factory=dict)
