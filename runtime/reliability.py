"""Reliability patterns — retry, circuit breaker for the Runtime.

Phase 4: Production hardening.
Provides circuit breaker (fail-fast when downstream is unhealthy) and
configurable retry with backoff.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from runtime.observability import metrics

logger = logging.getLogger("runtime.reliability")


# ── Circuit Breaker ───────────────────────────────────────────────────────


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation — calls pass through
    OPEN = "open"  # Failing — calls are rejected fast
    HALF_OPEN = "half_open"  # Testing — one call allowed through


class CircuitBreaker:
    """Circuit breaker for protecting downstream dependencies.

    States:
        CLOSED  → normal, calls pass through
        OPEN    → failures threshold exceeded, calls rejected fast
        HALF_OPEN → after timeout, one probe call allowed

    Thread-safe for the async context (single event loop, cooperative).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current state, potentially transitioning from OPEN → HALF_OPEN."""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
        return self._state

    async def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *fn(*args, **kwargs)* through the circuit breaker.

        Raises CircuitBreakerOpenError if the circuit is open.
        """
        state = self.state

        if state == CircuitState.OPEN:
            metrics.counter(f"circuit.{self.name}.rejected").inc()
            raise CircuitBreakerOpenError(self.name)

        if state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                metrics.counter(f"circuit.{self.name}.rejected").inc()
                raise CircuitBreakerOpenError(self.name, "half_open limit")
            self._half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(*args, **kwargs)
            else:
                result = fn(*args, **kwargs)

            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit '%s' recovered (HALF_OPEN → CLOSED)", self.name)
            metrics.counter(f"circuit.{self.name}.recovery").inc()
        self._state = CircuitState.CLOSED
        self._failure_count = 0

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning("Circuit '%s' probe failed (HALF_OPEN → OPEN)", self.name)
            self._state = CircuitState.OPEN
            metrics.counter(f"circuit.{self.name}.open").inc()
        elif self._failure_count >= self.failure_threshold:
            logger.warning(
                "Circuit '%s' opened (%d failures)",
                self.name,
                self._failure_count,
            )
            self._state = CircuitState.OPEN
            metrics.counter(f"circuit.{self.name}.open").inc()

    def reset(self) -> None:
        """Manually reset the circuit to CLOSED."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0

    @property
    def failure_count(self) -> int:
        return self._failure_count


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, name: str, detail: str = "") -> None:
        msg = f"Circuit '{name}' is open"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)
        self.circuit_name = name


# ── Retry ─────────────────────────────────────────────────────────────────

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    metric_name: str = "",
):
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of attempts (including first).
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        backoff_factor: Multiplier per attempt (2.0 = double).
        retryable_exceptions: Tuple of exception types to retry on.
        metric_name: Optional metric name prefix for observability.

    Usage:
        @retry(max_attempts=3, metric_name="provider.call")
        async def call_provider(req):
            return await provider.execute(req)
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    if asyncio.iscoroutinefunction(fn):
                        return await fn(*args, **kwargs)
                    return fn(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                        logger.debug(
                            "Retry %s/%s for %s in %.2fs: %s",
                            attempt,
                            max_attempts,
                            fn.__name__,
                            delay,
                            e,
                        )
                        if metric_name:
                            metrics.counter(f"{metric_name}.retry").inc()
                        await asyncio.sleep(delay)
                    else:
                        if metric_name:
                            metrics.counter(f"{metric_name}.exhausted").inc()
                        logger.error(
                            "Retry exhausted for %s after %d attempts: %s",
                            fn.__name__,
                            max_attempts,
                            e,
                        )
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ── Circuit‑aware provider call ────────────────────────────────────────────


async def call_with_circuit(
    fn: Callable[..., Any],
    *args: Any,
    circuit: CircuitBreaker,
    **kwargs: Any,
) -> Any:
    """Call *fn* through a circuit breaker with retry.

    This is a convenience helper that combines circuit breaker + retry.
    The retry layer only fires on exceptions AFTER the circuit allows the call.

    Usage:
        result = await call_with_circuit(
            provider.execute, request,
            circuit=provider_circuit,
        )
    """

    for attempt in range(1, 4):  # up to 3 attempts through circuit
        try:
            return await circuit.call(fn, *args, **kwargs)
        except CircuitBreakerOpenError:
            # Circuit is open — don't retry, fail fast
            raise
        except Exception as e:
            if attempt < 3:
                delay = 0.5 * (2 ** (attempt - 1))
                logger.debug(
                    "Circuit call %s/%s failed, retry in %.2fs: %s",
                    attempt,
                    3,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
            else:
                raise
