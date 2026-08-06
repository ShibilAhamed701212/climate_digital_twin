from __future__ import annotations

import logging
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.twin_client import TwinClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DigitalTwinTool(BaseTool):
    def __init__(self) -> None:
        self._name = "digital_twin_tool"
        self._description = "Query the current state of the digital twin for a location"
        self._client = TwinClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        location = kwargs.get("location", "Karnataka")
        try:
            state = self._client.get_current_state(location)
            return {
                "tool": self._name,
                "location": location,
                "state": state,
                "available": True,
                "fallback": False,
            }
        except (ConnectionError, Timeout, HTTPError) as e:
            logger.warning("Twin service unavailable: %s", e)
            from pipeline.providers.manager import DataSourceManager, ObservationStatus
            dsm = DataSourceManager()
            obs = dsm.get_observation(location.lower(), "temperature_2m")
            if obs.status != ObservationStatus.UNAVAILABLE:
                return {
                    "tool": self._name,
                    "location": location,
                    "state": {
                        "location": location,
                        "max_temp": obs.values.get("temperature_2m", 0),
                        "min_temp": obs.values.get("temperature_2m_min", 0),
                        "rainfall_mm": obs.values.get("precipitation_mm", 0),
                    },
                    "available": True,
                    "data_source": obs.status.value,
                    "provider": obs.provider,
                }
            return {
                "tool": self._name,
                "location": location,
                "state": {},
                "available": False,
                "error": "No verified climate observation is available.",
            }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "parameters": {"location": "str"},
        }

    def health_check(self) -> tuple[bool, str]:
        return True, "digital_twin_tool healthy"
