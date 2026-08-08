from __future__ import annotations

import logging
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.scenario_client import ScenarioClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


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
            from pipeline.providers.manager import DataSourceManager, ObservationStatus

            dsm = DataSourceManager()
            obs = dsm.get_observation(location.lower(), "temperature_2m")
            if obs.status != ObservationStatus.UNAVAILABLE:
                return {
                    "tool": self._name,
                    "scenario_type": scenario_type,
                    "value": value,
                    "location": location,
                    "result": {
                        "scenario_id": f"historical_{scenario_type}",
                        "location": location,
                        "max_temp_delta": obs.values.get("temperature_2m", 0),
                        "rainfall_delta": obs.values.get("precipitation_mm", 0),
                        "confidence": obs.confidence,
                    },
                    "available": True,
                    "data_source": obs.status.value,
                    "provider": obs.provider,
                }
            return {
                "tool": self._name,
                "scenario_type": scenario_type,
                "value": value,
                "location": location,
                "result": {},
                "available": False,
                "error": "No verified climate observation is available.",
            }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        valid_types = ["temperature", "rainfall", "monsoon", "extreme_event"]
        if "scenario_type" in kwargs and kwargs["scenario_type"] not in valid_types:
            return False, f"scenario_type must be one of {valid_types}"
        if "value" in kwargs and not isinstance(kwargs["value"], int | float):
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
