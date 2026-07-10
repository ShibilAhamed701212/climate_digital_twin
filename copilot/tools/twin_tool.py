from __future__ import annotations

import logging
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.twin_client import TwinClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _synthetic_twin_state(location: str) -> dict[str, Any]:
    """Generate plausible synthetic twin state when the service is unavailable."""
    return {
        "location": location,
        "max_temp": 34.2,
        "min_temp": 21.5,
        "rainfall_mm": 12.8,
        "humidity_pct": 62.0,
        "soil_moisture": 0.45,
        "wind_speed_kmh": 14.3,
        "timestamp": "2025-01-15T10:30:00",
    }


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
            fallback = _synthetic_twin_state(location)
            return {
                "tool": self._name,
                "location": location,
                "state": fallback,
                "available": False,
                "fallback": True,
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
