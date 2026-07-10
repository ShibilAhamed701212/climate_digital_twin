"""Async-safe provider execution with thread pool support.

Wraps synchronous provider calls in asyncio.to_thread to prevent
event loop blocking. Provides timeout enforcement via asyncio.wait_for.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from runtime.models.provider import ProviderRequest, ProviderResult


async def run_provider_safely(
    execute_func: Callable[..., Any],
    request: ProviderRequest,
    timeout_ms: int = 30000,
    provider_id: str = "unknown",
) -> ProviderResult:
    """Execute a provider call safely with timeout and thread pool isolation.

    If the provider's execute method is synchronous (likely blocking I/O),
    it runs in a thread pool executor to avoid blocking the event loop.
    """
    start = time.time()

    try:
        # Check if the result is already a coroutine
        result_or_coro = execute_func(request)

        if asyncio.iscoroutine(result_or_coro):
            result = await asyncio.wait_for(result_or_coro, timeout=timeout_ms / 1000.0)
        else:
            # Synchronous provider — run in thread pool
            result = await asyncio.wait_for(
                asyncio.to_thread(execute_func, request),
                timeout=timeout_ms / 1000.0,
            )

        elapsed = (time.time() - start) * 1000

        if isinstance(result, ProviderResult):
            if not result.metadata.get("provider_id"):
                result.metadata["provider_id"] = provider_id
            return result
        return ProviderResult(
            success=True,
            data=result if isinstance(result, dict) else {"value": result},
            latency_ms=elapsed,
            metadata={"provider_id": provider_id},
        )

    except TimeoutError:
        return ProviderResult(
            success=False,
            error=f"Provider '{provider_id}' timed out after {timeout_ms}ms",
            latency_ms=(time.time() - start) * 1000,
            metadata={"provider_id": provider_id},
        )
    except Exception as e:
        return ProviderResult(
            success=False,
            error=str(e),
            latency_ms=(time.time() - start) * 1000,
            metadata={"provider_id": provider_id},
        )
