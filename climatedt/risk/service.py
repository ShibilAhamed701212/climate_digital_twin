import logging
from datetime import UTC, datetime
from typing import Any

from risk.engine.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class _Assessment:
    def __init__(self, report) -> None:
        cr = getattr(report, "composite_risk", None)
        self.assessment_id = ""
        self.location_id = getattr(report, "location_id", "")
        self.composite_score = getattr(cr, "score", 0.0) if cr else 0.0
        self.composite_category = getattr(cr, "category", "unknown") if cr else "unknown"
        self.timestamp = datetime.now(UTC)
        self.metadata = {}
        scores = []
        for hazard_type, attr_name in [
            ("heat", "heat_risk"),
            ("flood", "flood_risk"),
            ("drought", "drought_risk"),
        ]:
            score_obj = getattr(report, attr_name, None)
            if score_obj:
                scores.append(
                    type(
                        "Score",
                        (),
                        {
                            "hazard_type": hazard_type,
                            "score": getattr(score_obj, "score", 0.0),
                            "category": getattr(score_obj, "category", "unknown"),
                            "description": getattr(score_obj, "description", ""),
                        },
                    )()
                )
        self.scores = scores


class RiskService:
    def __init__(self) -> None:
        self._engine = RiskEngine()
        self._explainer = _Explainer()

    async def assess_location(
        self,
        location_id: str,
        _latitude: float = 0.0,
        _longitude: float = 0.0,
        _include_explainability: bool = False,
    ) -> _Assessment:
        report = self._engine.assess_all(
            location_id=location_id,
            district="unknown",
            max_temp=0.0,
            min_temp=0.0,
            rainfall=0.0,
        )
        return _Assessment(report)

    async def assess_batch(
        self,
        location_ids: list[str],
        latitudes: list[float] | None = None,
        longitudes: list[float] | None = None,
    ) -> dict[str, _Assessment]:
        results: dict[str, _Assessment] = {}
        for i, loc_id in enumerate(location_ids):
            lat = latitudes[i] if latitudes else 0.0
            lon = longitudes[i] if longitudes else 0.0
            results[loc_id] = await self.assess_location(loc_id, lat, lon)
        return results

    async def get_risk_trend(
        self,
        location_id: str,
        latitude: float = 0.0,
        longitude: float = 0.0,
        _observations: list[Any] | None = None,
        _days: int = 90,
    ) -> list[_Assessment]:
        return [await self.assess_location(location_id, latitude, longitude)]


class _Explainer:
    def factor_contribution(self, _assessment: Any) -> dict[str, float]:
        return {}
