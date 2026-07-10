"""Observability — structured logging + metrics collection for the Runtime.

Phase 4: Production hardening.
Provides a centralized logger with structured fields, and a metrics registry
for counters, gauges, histograms, and timer-based latency tracking.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any

# ── Structured Logger ────────────────────────────────────────────────────


class StructuredLogger:
    """Logger that emits JSON-structured log records.

    Wraps a standard Python logger and adds structured context fields.
    """

    def __init__(self, name: str, level: int = logging.INFO) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self._logger.addHandler(handler)

    def info(self, message: str, **fields: Any) -> None:
        self._logger.info(self._format(message, fields))

    def warning(self, message: str, **fields: Any) -> None:
        self._logger.warning(self._format(message, fields))

    def error(self, message: str, **fields: Any) -> None:
        self._logger.error(self._format(message, fields))

    def debug(self, message: str, **fields: Any) -> None:
        self._logger.debug(self._format(message, fields))

    @staticmethod
    def _format(message: str, fields: dict[str, Any]) -> str:
        if fields:
            meta = json.dumps(fields, default=str)
            return f"{message}  {meta}"
        return message


# Singleton logger for the Runtime
runtime_logger = StructuredLogger("runtime")


# ── Metrics Registry ─────────────────────────────────────────────────────

_MetricValue = int | float


@dataclass
class Counter:
    """Monotonic counter metric."""

    _value: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, amount: int = 1) -> None:
        with self._lock:
            self._value += amount

    @property
    def value(self) -> int:
        with self._lock:
            return self._value


@dataclass
class Gauge:
    """Point-in-time value metric."""

    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value -= amount

    @property
    def value(self) -> float:
        with self._lock:
            return self._value


@dataclass
class Histogram:
    """Distribution metric (min, max, sum, count, p50, p95, p99)."""

    _values: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def observe(self, value: float) -> None:
        with self._lock:
            self._values.append(value)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._values)

    @property
    def sum(self) -> float:
        with self._lock:
            return sum(self._values)

    @property
    def min(self) -> float:
        with self._lock:
            vals = self._values
            return min(vals) if vals else 0.0

    @property
    def max(self) -> float:
        with self._lock:
            vals = self._values
            return max(vals) if vals else 0.0

    @property
    def avg(self) -> float:
        with self._lock:
            vals = self._values
            return sum(vals) / len(vals) if vals else 0.0

    def percentile(self, p: float) -> float:
        """Compute approximate percentile (0 <= p <= 100).

        Uses the nearest-rank method for consistency.
        """
        with self._lock:
            if not self._values:
                return 0.0
            sorted_vals = sorted(self._values)
            rank = max(1, min(len(sorted_vals), int(math.ceil(len(sorted_vals) * p / 100))))
            return sorted_vals[rank - 1]

    def snapshot(self) -> dict[str, float]:
        """Return a dict summary safe for serialization."""
        with self._lock:
            if not self._values:
                return {"count": 0, "sum": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0}
            sorted_vals = sorted(self._values)
            n = len(sorted_vals)

            def _p(pct: float) -> float:
                rank = max(1, min(n, int(math.ceil(n * pct / 100))))
                return sorted_vals[rank - 1]

            return {
                "count": n,
                "sum": sum(sorted_vals),
                "min": sorted_vals[0],
                "max": sorted_vals[-1],
                "avg": sum(sorted_vals) / n,
                "p50": _p(50),
                "p95": _p(95),
                "p99": _p(99),
            }


@dataclass
class Timer:
    """Timer metric — wraps a Histogram for latency."""

    _histogram: Histogram = field(default_factory=Histogram)

    def record(self, seconds: float) -> None:
        """Record a duration in seconds."""
        self._histogram.observe(seconds)

    def record_ms(self, milliseconds: float) -> None:
        """Record a duration in milliseconds."""
        self._histogram.observe(milliseconds)

    @property
    def snapshot(self) -> dict[str, float]:
        return self._histogram.snapshot()


class MetricsRegistry:
    """Thread-safe registry for counters, gauges, histograms, and timers.

    Usage:
        metrics = MetricsRegistry()
        metrics.counter("requests.total").inc()
        metrics.timer("pipeline.latency").record_ms(42.5)
        metrics.gauge("active_sessions").set(10)
        report = metrics.snapshot()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._timers: dict[str, Timer] = {}

    def counter(self, name: str) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter()
            return self._counters[name]

    def gauge(self, name: str) -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge()
            return self._gauges[name]

    def histogram(self, name: str) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram()
            return self._histograms[name]

    def timer(self, name: str) -> Timer:
        with self._lock:
            if name not in self._timers:
                self._timers[name] = Timer()
            return self._timers[name]

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all registered metrics."""
        result: dict[str, dict[str, Any]] = {}
        with self._lock:
            for name, c in self._counters.items():
                result[f"counter.{name}"] = {"type": "counter", "value": c.value}
            for name, g in self._gauges.items():
                result[f"gauge.{name}"] = {"type": "gauge", "value": g.value}
            for name, h in self._histograms.items():
                result[f"histogram.{name}"] = {"type": "histogram", **h.snapshot()}
            for name, t in self._timers.items():
                result[f"timer.{name}"] = {"type": "timer", **t.snapshot}
        return result

    def summary(self) -> str:
        """Human-readable summary of all metrics."""
        snap = self.snapshot()
        lines = ["=== Metrics Summary ==="]
        for key, val in sorted(snap.items()):
            lines.append(f"  {key}: {val}")
        return "\n".join(lines)


# Singleton metrics registry
metrics = MetricsRegistry()


# ── Context-aware timing decorator ────────────────────────────────────────


class TimerContext:
    """Context manager for timing code blocks.

    Usage:
        with TimerContext("pipeline.execute"):
            await pipeline.execute(...)

    Records duration to the metrics registry automatically.
    Pass a custom registry with ``registry=my_registry``, otherwise uses the
    global ``metrics`` singleton.
    """

    def __init__(self, metric_name: str, *, registry: MetricsRegistry | None = None) -> None:
        self._metric_name = metric_name
        self._registry = registry or metrics
        self._start: float = 0.0

    def __enter__(self) -> TimerContext:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed = (time.perf_counter() - self._start) * 1000
        self._registry.timer(self._metric_name).record_ms(elapsed)
