from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

MAX_TRACE_LOG = 1_000


@dataclass
class RuntimeContext:
    """Execution context carried through every stage of processing.

    Every request gets a unique trace_id.
    All events, provider calls, and workflow steps log to trace_log.
    Bounded trace_log: limited to MAX_TRACE_LOG (1,000) entries.
    """

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    conversation_id: str | None = None
    user_id: str | None = None
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    _trace_log: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=MAX_TRACE_LOG))

    @property
    def trace_log(self) -> list[dict[str, Any]]:
        return list(self._trace_log)

    def log_stage(self, stage: str, details: dict[str, Any] | None = None) -> None:
        """Log a stage of execution for tracing."""
        self._trace_log.append(
            {
                "stage": stage,
                "timestamp": time.time(),
                "elapsed_ms": round((time.time() - self.start_time) * 1000, 2),
                "details": details or {},
            }
        )

    def elapsed_ms(self) -> float:
        """Milliseconds since context creation."""
        return round((time.time() - self.start_time) * 1000, 2)


@dataclass
class RuntimeResult:
    """Result from a full Runtime execution cycle."""

    success: bool
    response: Any = None
    error: str | None = None
    latency_ms: float = 0.0
    trace_id: str = ""
    trace_log: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
