from __future__ import annotations

import logging
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.risk_client import RISK_SERVICE_URL, RiskClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


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
            if scores.get("heat") is None and scores.get("composite") is None:
                return {
                    "tool": self._name,
                    "location": location,
                    "risk_assessment": {},
                    "available": False,
                    "error": "Risk service returned no scores.",
                }
            return {
                "tool": self._name,
                "location": location,
                "risk_assessment": {
                    "location": location,
                    "heat_risk": scores.get("heat"),
                    "flood_risk": scores.get("flood"),
                    "drought_risk": scores.get("drought"),
                    "composite_risk": scores.get("composite"),
                    "category": scores.get("category"),
                },
                "available": True,
                "fallback": False,
            }
        except (ConnectionError, Timeout, HTTPError, KeyError, TypeError) as e:
            logger.warning("Risk service unavailable: %s", e)
            return {
                "tool": self._name,
                "location": location,
                "risk_assessment": {},
                "available": False,
                "error": "No verified risk assessment is available.",
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
        try:
            resp = requests.get(f"{RISK_SERVICE_URL}/health", timeout=2)
            if resp.ok:
                return True, "risk_assessor healthy"
            return False, f"risk engine HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
