"""Agriculture risk assessment model.

Evaluates climate-related risks to agriculture:
- Growing season conditions
- Precipitation deficit/surplus
- Temperature stress
- Soil moisture
- Vegetation health
- Crop stage sensitivity
- Monsoon performance
"""

from __future__ import annotations

import logging
from typing import Any

from risk.models.risk_models import HazardType, RiskCategory, RiskScore

_logger = logging.getLogger(__name__)

_OPTIMAL_TEMP_MIN = 15.0
_OPTIMAL_TEMP_MAX = 32.0
_HEAT_STRESS_TEMP = 35.0
_FROST_TEMP = 0.0
_OPTIMAL_PRECIP_MIN = 50.0
_OPTIMAL_PRECIP_MAX = 200.0
_DROUGHT_PRECIP_THRESHOLD = 20.0

_STAGE_SENSITIVITY: dict[str, float] = {
    "planting": 1.3,
    "vegetative": 1.0,
    "flowering": 1.5,
    "grain_fill": 1.2,
    "maturation": 0.8,
    "fallow": 0.3,
}


class AgricultureRiskModel:
    """Agriculture/climate impact risk model.

    Evaluates risks to agricultural productivity from climate
    conditions, including growing season quality, precipitation
    adequacy, temperature stress, and monsoon performance.
    """

    def __init__(self) -> None:
        pass

    async def assess(
        self,
        _location_id: str = "",
        **features: Any,
    ) -> RiskScore:
        score = self._compute_raw_score(features)
        category = self._score_to_category(score)
        description = self._generate_description(score, features)

        return RiskScore(
            hazard_type=HazardType.DROUGHT,
            score=score / 100.0,
            category=category,
            description=description,
        )

    def _compute_raw_score(self, features: dict[str, Any]) -> float:
        scores: list[float] = []
        weights: list[float] = []

        temp = features.get("growing_season_temp")
        if temp is not None:
            temp_score = self._temperature_stress_score(float(temp))
            scores.append(temp_score)
            weights.append(0.20)

        precip = features.get("growing_season_precip")
        if precip is not None:
            precip_score = self._precipitation_adequacy_score(float(precip))
            scores.append(precip_score)
            weights.append(0.20)

        deficit = features.get("precipitation_deficit")
        if deficit is not None:
            deficit = float(deficit)
            deficit_score = min(100, max(0, deficit * 1.5))
            scores.append(deficit_score)
            weights.append(0.10)

        stress_days = features.get("temperature_stress_days")
        if stress_days is not None:
            stress_score = min(100, int(stress_days) * 10)
            scores.append(stress_score)
            weights.append(0.10)

        moisture = features.get("soil_moisture")
        if moisture is not None:
            moisture = float(moisture)
            if moisture < 0.2:
                moisture_score = (0.2 - moisture) / 0.2 * 100
            elif moisture > 0.4:
                moisture_score = (moisture - 0.4) / 0.3 * 100
            else:
                moisture_score = 0
            moisture_score = min(100, max(0, moisture_score))
            scores.append(moisture_score)
            weights.append(0.10)

        ndvi = features.get("ndvi")
        if ndvi is not None:
            ndvi = float(ndvi)
            ndvi_score = max(0, (0.5 - ndvi) / 0.5 * 100)
            ndvi_score = min(100, ndvi_score)
            scores.append(ndvi_score)
            weights.append(0.10)

        crop_stage = features.get("crop_stage", "vegetative")
        sensitivity = _STAGE_SENSITIVITY.get(str(crop_stage).lower(), 1.0)

        monsoon = features.get("monsoon_performance")
        if monsoon is not None:
            monsoon = float(monsoon)
            monsoon_score = (1.0 - monsoon) * 100
            scores.append(monsoon_score)
            weights.append(0.10)

        if not scores:
            return 50.0

        total = sum(s * w for s, w in zip(scores, weights, strict=False))
        total_weight = sum(weights)

        raw = total / total_weight if total_weight > 0 else 50.0
        raw *= sensitivity

        return max(0.0, min(100.0, raw))

    @staticmethod
    def _temperature_stress_score(temp: float) -> float:
        if _OPTIMAL_TEMP_MIN <= temp <= _OPTIMAL_TEMP_MAX:
            return 0.0
        if temp < _FROST_TEMP:
            return 100.0
        if temp < _OPTIMAL_TEMP_MIN:
            return (_OPTIMAL_TEMP_MIN - temp) / _OPTIMAL_TEMP_MIN * 100
        if temp >= _HEAT_STRESS_TEMP:
            return min(100, (temp - _OPTIMAL_TEMP_MAX) / 10.0 * 100)
        return (temp - _OPTIMAL_TEMP_MAX) / (_HEAT_STRESS_TEMP - _OPTIMAL_TEMP_MAX) * 50

    @staticmethod
    def _precipitation_adequacy_score(precip: float) -> float:
        if _OPTIMAL_PRECIP_MIN <= precip <= _OPTIMAL_PRECIP_MAX:
            return 0.0
        if precip < _DROUGHT_PRECIP_THRESHOLD:
            return 100.0
        if precip < _OPTIMAL_PRECIP_MIN:
            return (_OPTIMAL_PRECIP_MIN - precip) / _OPTIMAL_PRECIP_MIN * 100
        return min(100, (precip - _OPTIMAL_PRECIP_MAX) / _OPTIMAL_PRECIP_MAX * 100)

    @staticmethod
    def _score_to_category(score: float) -> RiskCategory:
        if score <= 25:
            return RiskCategory.LOW
        if score <= 50:
            return RiskCategory.MODERATE
        if score <= 75:
            return RiskCategory.HIGH
        return RiskCategory.SEVERE

    @staticmethod
    def _generate_description(score: float, features: dict[str, Any]) -> str:
        crop_stage = features.get("crop_stage", "unknown")
        if score < 25:
            return f"Low agriculture risk. Growing conditions favorable for {crop_stage} stage."
        if score < 50:
            return (
                f"Moderate agriculture risk. Some stress on crops "
                f"during {crop_stage} stage. Monitor conditions."
            )
        if score < 75:
            return (
                f"High agriculture risk. Significant stress on crops "
                f"during {crop_stage} stage. Consider mitigation measures."
            )
        return (
            f"Extreme agriculture risk. Severe conditions threatening "
            f"crop yield during {crop_stage} stage. "
            "Urgent intervention needed."
        )


__all__ = [
    "AgricultureRiskModel",
]
