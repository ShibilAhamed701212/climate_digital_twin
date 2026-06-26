from __future__ import annotations

from typing import Any

from copilot.tools.base import BaseTool


class DigitalTwinTool(BaseTool):
    def __init__(self) -> None:
        self._name = "digital_twin_tool"
        self._description = "Query the current state of the digital twin for a location"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        location = kwargs.get("location", "Karnataka")
        return {"tool": self._name, "location": location, "state": _synthetic_twin_state(location)}

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {"name": self._name, "description": self._description, "parameters": {"location": "str"}}

    def health_check(self) -> tuple[bool, str]:
        return True, "digital_twin_tool healthy"


def _synthetic_twin_state(location: str) -> dict[str, Any]:
    import hashlib
    import random
    seed = int(hashlib.md5(location.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return {
        "location": location,
        "max_temp": round(32 + rng.uniform(-3, 3), 1),
        "min_temp": round(22 + rng.uniform(-2, 2), 1),
        "rainfall_mm": round(max(0, rng.gauss(15, 10)), 1),
        "humidity_pct": round(60 + rng.uniform(-10, 10), 1),
        "timestamp": "2026-06-26T12:00:00",
    }
