from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimeoutPolicy:
    """Timeout configuration for a capability."""

    default_ms: int = 30000
    max_ms: int = 120000
    hard_limit_ms: int = 300000


@dataclass
class RetryPolicy:
    """Retry configuration for a capability."""

    max_retries: int = 2
    backoff_ms: int = 1000
    backoff_multiplier: float = 2.0
    max_backoff_ms: int = 30000


@dataclass
class CachePolicy:
    """Cache configuration for a capability."""

    ttl_seconds: int = 60
    max_size: int = 1000
    stale_on_error: bool = True


@dataclass
class CapabilityType:
    """Contract definition for a capability.

    Every capability publishes input/output/error schemas (JSON Schema),
    timeout/retry/cache policies, and required permissions.
    The Runtime validates all provider implementations against these contracts.
    """

    name: str
    description: str
    version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    error_schema: dict[str, Any] | None = None
    timeout_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    cache_policy: CachePolicy = field(default_factory=CachePolicy)
    required_permissions: list[str] = field(default_factory=list)
    deterministic_possible: bool = True
    dependencies: list[str] = field(default_factory=list)
    execution_cost: float = 1.0
    expected_latency_ms: int = 5000
    confidence_weight: float = 1.0
    parallelizable: bool = True
    streaming_support: bool = False
    failure_policy: str = "abort"
