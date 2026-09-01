from __future__ import annotations

import logging
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.report_client import ReportClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ReportGeneratorTool(BaseTool):
    def __init__(self) -> None:
        self._name = "report_generator"
        self._description = (
            "Generate a structured climate report combining forecast, risk, and twin state data"
        )
        self._client = ReportClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        report_type = kwargs.get("report_type", "summary")
        location = kwargs.get("location", "Karnataka")
        try:
            report = self._client.generate_report(location, report_type)
            return {
                "tool": self._name,
                "report_type": report_type,
                "location": location,
                "report": report,
                "fallback": False,
            }
        except (ConnectionError, Timeout, HTTPError) as e:
            logger.warning("Report service unavailable: %s", e)
            return {
                "tool": self._name,
                "report_type": report_type,
                "location": location,
                "report": "",
                "error": "Report service unavailable. No synthetic fallback available.",
                "fallback": True,
            }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        valid_types = ["summary", "detailed", "risk", "forecast", "disaster"]
        if "report_type" in kwargs and kwargs["report_type"] not in valid_types:
            return False, f"report_type must be one of {valid_types}"
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "parameters": {
                "report_type": "str (summary/detailed/risk/forecast)",
                "location": "str",
            },
        }

    def health_check(self) -> tuple[bool, str]:
        return True, "report_generator healthy"
