from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PerformanceBudget:
    operation: str
    max_ms: float
    description: str


BUDGETS = [
    PerformanceBudget("blackboard.publish", 1.0, "Publish should take <1ms"),
    PerformanceBudget("blackboard.get", 0.5, "Read should take <0.5ms"),
    PerformanceBudget("event_bus.publish", 1.0, "Event publish should take <1ms"),
    PerformanceBudget(
        "provider_registry.register", 1.0, "Register provider should take <1ms"
    ),
    PerformanceBudget("plugin.load", 50.0, "Load minimal plugin should take <50ms"),
    PerformanceBudget("runtime.initialize", 100.0, "Runtime init should take <100ms"),
    PerformanceBudget("runtime.shutdown", 100.0, "Runtime shutdown should take <100ms"),
]


def check_budget(operation: str, elapsed: float) -> tuple[bool, float, str]:
    for b in BUDGETS:
        if b.operation == operation:
            ok = elapsed <= b.max_ms
            return (
                ok,
                elapsed,
                f"{'OK' if ok else 'EXCEEDED'} {operation}: {elapsed:.3f}ms (max: {b.max_ms}ms)",
            )
    return True, elapsed, f"UNKNOWN {operation}: {elapsed:.3f}ms"
