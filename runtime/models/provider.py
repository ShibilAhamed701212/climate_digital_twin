from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.models.runtime import RuntimeContext


@dataclass
class ProviderRequest:
    """Request to execute a provider's capability."""

    capability: str
    params: dict[str, Any]
    context: RuntimeContext
    timeout_ms: int = 30000


@dataclass
class ProviderResult:
    """Result from a provider execution."""

    success: bool
    data: Any = None
    error: str | None = None
    confidence: float = 1.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderHealth:
    """Health status of a provider."""

    ok: bool
    message: str = ""
    latency_ms: float = 0.0
    version: str = "unknown"
