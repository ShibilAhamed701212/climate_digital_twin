from __future__ import annotations

from typing import Any

from copilot.tools.base import BaseTool


class ScenarioSimulatorTool(BaseTool):
    def __init__(self) -> None:
        self._name = "scenario_simulator"
        self._description = "Run a what-if climate scenario simulation (temperature change, rainfall change, etc.)"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        scenario_type = kwargs.get("scenario_type", "temperature")
        value = kwargs.get("value", 1.0)
        location = kwargs.get("location", "Karnataka")
        return {
            "tool": self._name,
            "scenario_type": scenario_type,
            "value": value,
            "location": location,
            "result": _synthetic_scenario(location, scenario_type, value),
        }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        valid_types = ["temperature", "rainfall", "monsoon", "extreme_event"]
        if "scenario_type" in kwargs and kwargs["scenario_type"] not in valid_types:
            return False, f"scenario_type must be one of {valid_types}"
        if "value" in kwargs and not isinstance(kwargs["value"], (int, float)):
            return False, "value must be a number"
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "parameters": {"scenario_type": "str", "value": "float", "location": "str"},
        }

    def health_check(self) -> tuple[bool, str]:
        return True, "scenario_simulator healthy"


def _synthetic_scenario(location: str, scenario_type: str, value: float) -> dict[str, Any]:
    import hashlib
    import random
    seed = int(hashlib.md5(f"{location}:{scenario_type}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    if scenario_type == "temperature":
        return {"max_temp_delta": round(value, 1), "rainfall_delta": 0, "description": f"Temperature changes by {value}°C"}
    if scenario_type == "rainfall":
        return {"max_temp_delta": 0, "rainfall_delta_pct": round(value, 1), "description": f"Rainfall changes by {value}%"}
    if scenario_type == "monsoon":
        return {"monsoon_shift_days": int(value), "max_temp_delta": round(rng.uniform(-1, 1), 1), "rainfall_delta_pct": round(rng.uniform(-20, 20), 1)}
    return {"max_temp_delta": round(rng.uniform(-5, 5), 1), "rainfall_delta_pct": round(rng.uniform(-50, 50), 1)}
