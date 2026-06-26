from __future__ import annotations

from typing import Any

from copilot.tools.base import BaseTool


class RiskAssessorTool(BaseTool):
    def __init__(self) -> None:
        self._name = "risk_assessor"
        self._description = "Assess climate risk scores (heat, flood, drought, composite) for a location"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        location = kwargs.get("location", "Karnataka")
        return {"tool": self._name, "location": location, "risk_assessment": _synthetic_risk(location)}

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {"name": self._name, "description": self._description, "parameters": {"location": "str"}}

    def health_check(self) -> tuple[bool, str]:
        return True, "risk_assessor healthy"


def _synthetic_risk(location: str) -> dict[str, Any]:
    import hashlib
    import random
    seed = int(hashlib.md5(location.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    heat = rng.randint(10, 80)
    flood = rng.randint(10, 80)
    drought = rng.randint(10, 80)
    composite = round(heat * 0.3 + flood * 0.35 + drought * 0.35, 1)
    return {
        "location": location,
        "heat_risk": heat,
        "flood_risk": flood,
        "drought_risk": drought,
        "composite_risk": composite,
        "category": "Low" if composite < 25 else "Moderate" if composite < 50 else "High" if composite < 75 else "Severe",
    }
