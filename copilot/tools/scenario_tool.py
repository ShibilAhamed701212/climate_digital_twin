from __future__ import annotations

import logging
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.scenario_client import ScenarioClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _synthetic_scenario(scenario_type: str, value: float, location: str) -> dict[str, Any]:
    """Generate plausible synthetic scenario result when the service is unavailable."""
    return {
        "scenario_id": f"synthetic_{scenario_type}",
        "location": location,
        "max_temp_delta": round(value * 0.8, 1),
        "rainfall_delta": round(value * 2.5 if scenario_type == "rainfall" else 0, 1),
        "confidence": 0.65,
    }


class ScenarioSimulatorTool(BaseTool):
    def __init__(self) -> None:
        self._name = "scenario_simulator"
        self._description = "Run a what-if climate scenario simulation using the scenario engine"
        self._client = ScenarioClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        scenario_type = kwargs.get("scenario_type", "temperature")
        value = kwargs.get("value", 1.0)
        location = kwargs.get("location", "Karnataka")

        try:
            result = self._client.simulate(location, scenario_type, value)
            return {
                "tool": self._name,
                "scenario_type": scenario_type,
                "value": value,
                "location": location,
                "result": result,
                "available": True,
                "fallback": False,
            }
        except (ConnectionError, Timeout, HTTPError) as e:
            logger.warning("Scenario service unavailable: %s", e)
            fallback = _synthetic_scenario(scenario_type, value, location)
            return {
                "tool": self._name,
                "scenario_type": scenario_type,
                "value": value,
                "location": location,
                "result": fallback,
                "available": False,
                "fallback": True,
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
