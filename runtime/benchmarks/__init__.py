"""Benchmark infrastructure for the Runtime.

Phase 4: Final validation and release candidate.
Provides measurement, statistics, and reporting utilities.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    name: str
    samples: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record(self, latency_ms: float) -> None:
        self.samples.append(latency_ms)

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def min(self) -> float:
        return min(self.samples) if self.samples else 0.0

    @property
    def max(self) -> float:
        return max(self.samples) if self.samples else 0.0

    @property
    def avg(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.samples) if len(self.samples) >= 2 else 0.0

    def percentile(self, p: float) -> float:
        """Nearest-rank percentile."""
        if not self.samples:
            return 0.0
        sorted_vals = sorted(self.samples)
        import math

        rank = max(1, min(len(sorted_vals), int(math.ceil(len(sorted_vals) * p / 100))))
        return sorted_vals[rank - 1]

    def summary(self) -> dict[str, float]:
        return {
            "count": self.count,
            "min_ms": round(self.min, 2),
            "max_ms": round(self.max, 2),
            "avg_ms": round(self.avg, 2),
            "median_ms": round(self.median, 2),
            "p50_ms": round(self.percentile(50), 2),
            "p95_ms": round(self.percentile(95), 2),
            "p99_ms": round(self.percentile(99), 2),
            "stdev_ms": round(self.stdev, 2),
        }

    def throughput(self, duration_sec: float) -> float:
        """Requests per second."""
        return self.count / duration_sec if duration_sec > 0 else 0.0

    def __str__(self) -> str:
        s = self.summary()
        return (
            f"Benchmark[{self.name}]: "
            f"count={s['count']}, avg={s['avg_ms']}ms, "
            f"p50={s['p50_ms']}ms, p95={s['p95_ms']}ms, p99={s['p99_ms']}ms, "
            f"min={s['min_ms']}ms, max={s['max_ms']}ms"
        )


async def benchmark(
    name: str,
    fn: Callable[..., Any] | Awaitable[Any],
    *,
    iterations: int = 100,
    warmup: int = 10,
    **metadata: Any,
) -> BenchmarkResult:
    """Benchmark an async function.

    Args:
        name: Benchmark name for reporting.
        fn: Async callable to benchmark.
        iterations: Number of measured iterations.
        warmup: Number of warmup iterations (discarded).
        **metadata: Extra metadata to attach.

    Returns:
        BenchmarkResult with latency samples in milliseconds.
    """
    result = BenchmarkResult(name=name, metadata=metadata)

    for i in range(iterations + warmup):
        start = time.perf_counter()
        if asyncio.iscoroutinefunction(fn):
            await fn()
        else:
            maybe_coro = fn()
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro
        elapsed = (time.perf_counter() - start) * 1000

        if i >= warmup:
            result.record(elapsed)

    return result


async def benchmark_concurrent(
    name: str,
    fn: Callable[..., Any] | Awaitable[Any],
    *,
    concurrency: int = 10,
    requests_per_worker: int = 10,
    warmup: int = 5,
    **metadata: Any,
) -> BenchmarkResult:
    """Benchmark with concurrent execution.

    Args:
        name: Benchmark name.
        fn: Async callable.
        concurrency: Number of concurrent workers.
        requests_per_worker: Iterations per worker.
        warmup: Warmup iterations per worker.
        **metadata: Extra metadata.

    Returns:
        BenchmarkResult with all latency samples.
    """
    result = BenchmarkResult(name=name, metadata={**metadata, "concurrency": concurrency})

    async def worker(_worker_id: int):
        for i in range(requests_per_worker + warmup):
            start = time.perf_counter()
            await fn()
            elapsed = (time.perf_counter() - start) * 1000
            if i >= warmup:
                result.record(elapsed)

    start_time = time.perf_counter()
    await asyncio.gather(*[worker(i) for i in range(concurrency)])
    duration = time.perf_counter() - start_time

    result.metadata["duration_sec"] = round(duration, 2)
    result.metadata["throughput_rps"] = round(result.count / duration, 2)
    return result
