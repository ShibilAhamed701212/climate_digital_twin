from __future__ import annotations

from typing import Any

from copilot.tools.base import BaseTool


class ForecastTool(BaseTool):
    def __init__(self) -> None:
        self._name = "forecast_tool"
        self._description = "Retrieve climate forecasts for temperature and rainfall up to 7 days ahead"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        location = kwargs.get("location", "Karnataka")
        days = kwargs.get("days", 3)
        return {"tool": self._name, "location": location, "days": days, "forecast": _synthetic_forecast(location, days)}

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        if "days" in kwargs and (not isinstance(kwargs["days"], int) or kwargs["days"] < 1 or kwargs["days"] > 7):
            return False, "days must be an integer between 1 and 7"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {"name": self._name, "description": self._description, "parameters": {"location": "str", "days": "int (1-7)"}}

    def health_check(self) -> tuple[bool, str]:
        return True, "forecast_tool healthy"


def _synthetic_forecast(location: str, days: int) -> list[dict[str, Any]]:
    import hashlib
    import random
    seed = int(hashlib.md5(location.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    results = []
    for d in range(1, days + 1):
        results.append({
            "day": d,
            "date": f"2026-06-{26 + d:02d}",
            "location": location,
            "max_temp": round(32 + rng.uniform(-3, 3), 1),
            "min_temp": round(22 + rng.uniform(-2, 2), 1),
            "rainfall_mm": round(max(0, rng.gauss(15, 10)), 1),
            "humidity_pct": round(60 + rng.uniform(-10, 10), 1),
        })
    return results
