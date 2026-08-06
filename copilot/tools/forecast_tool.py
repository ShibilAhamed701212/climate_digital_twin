from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.forecast_client import ForecastClient, ForecastUnavailableError
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _raw_to_forecast(raw: list[list[float]], days: int) -> list[dict[str, Any]]:
    """Convert raw model output to labeled forecast.

    Gateway predicts the target variable (temperature_2m), so single-value rows
    are treated as temperature. Legacy 3-tuples [[rainfall, max_temp, min_temp]]
    are still tolerated.
    """
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    forecast: list[dict[str, Any]] = []
    for d in range(days):
        vals = raw[d] if d < len(raw) else (raw[-1] if raw else [0.0])
        if len(vals) >= 3:
            rainfall, max_temp, min_temp = vals[0], vals[1], vals[2]
        else:
            max_temp = min_temp = vals[0]
            rainfall = 0.0
        forecast.append(
            {
                "day": d + 1,
                "date": (today + timedelta(days=d)).strftime("%Y-%m-%d"),
                "max_temp": round(max_temp, 1),
                "min_temp": round(min_temp, 1),
                "rainfall_mm": round(max(0.0, rainfall), 1),
                # ponytail: model doesn't predict humidity, rough proxy from rainfall
                "humidity_pct": round(min(95, 50 + rainfall * 10), 1),
            }
        )
    return forecast


class ForecastTool(BaseTool):
    def __init__(self) -> None:
        self._name = "forecast_tool"
        self._description = (
            "Retrieve climate forecasts for temperature and rainfall up to 7 days ahead"
        )
        self._client = ForecastClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        location = kwargs.get("location", "Karnataka")
        days = kwargs.get("days", 3)
        try:
            raw_preds = self._client.predict(location, days)
            return {
                "tool": self._name,
                "location": location,
                "days": days,
                "forecast": _raw_to_forecast(raw_preds, days),
                "available": True,
            }
        except ForecastUnavailableError as e:
            logger.warning("Forecast unavailable: %s", e)
            return {
                "tool": self._name,
                "location": location,
                "days": days,
                "forecast": [],
                "available": False,
                "error": str(e),
                "error_code": e.error_code,
            }
        except (ConnectionError, Timeout, HTTPError) as e:
            logger.warning("Forecast service unavailable: %s", e)
            return {
                "tool": self._name,
                "location": location,
                "days": days,
                "forecast": [],
                "available": False,
                "error": str(e),
            }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        if "days" in kwargs and (
            not isinstance(kwargs["days"], int) or kwargs["days"] < 1 or kwargs["days"] > 7
        ):
            return False, "days must be an integer between 1 and 7"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "parameters": {"location": "str", "days": "int (1-7)"},
        }

    def health_check(self) -> tuple[bool, str]:
        return True, "forecast_tool healthy"
