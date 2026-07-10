from __future__ import annotations

import logging
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.risk_client import RiskClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _synthetic_risk(location: str) -> dict[str, Any]:
    """Generate plausible synthetic risk scores when the service is unavailable."""
    return {
        "location": location,
        "heat_risk": 32.0,
        "flood_risk": 18.0,
        "drought_risk": 14.0,
        "composite_risk": 22.0,
        "category": "LOW",
    }


class RiskAssessorTool(BaseTool):
    def __init__(self) -> None:
        self._name = "risk_assessor"
        self._description = (
            "Assess climate risk scores (heat, flood, drought, composite) for a location"
        )
        self._client = RiskClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        location = kwargs.get("location", "Karnataka")
        try:
            scores = self._client.assess(location)
            return {
                "tool": self._name,
                "location": location,
                "risk_assessment": {
                    "location": location,
                    "heat_risk": scores["heat"],
                    "flood_risk": scores["flood"],
                    "drought_risk": scores["drought"],
                    "composite_risk": scores["composite"],
                    "category": scores["category"],
                },
                "available": True,
                "fallback": False,
            }
        except (ConnectionError, Timeout, HTTPError) as e:
            logger.warning("Risk service unavailable: %s", e)
            fallback = _synthetic_risk(location)
            return {
                "tool": self._name,
                "location": location,
                "risk_assessment": fallback,
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
        return True, "risk_assessor healthy"
