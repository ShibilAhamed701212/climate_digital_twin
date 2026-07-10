"""Risk data models for Climate Risk Assessment.

Defines dataclasses for risk scores, explanations, reports, and insights.
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class HazardType(StrEnum):
    HEAT = "heat"
    FLOOD = "flood"
    DROUGHT = "drought"
    STORM = "storm"
    WILDFIRE = "wildfire"
    COMPOSITE = "composite"
    AGRICULTURE = "agriculture"


class RiskCategory(StrEnum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    SEVERE = "Severe"


def categorize_risk(score: float) -> RiskCategory:
    if score <= 20:
        return RiskCategory.VERY_LOW
    elif score <= 40:
        return RiskCategory.LOW
    elif score <= 60:
        return RiskCategory.MODERATE
    elif score <= 80:
        return RiskCategory.HIGH
    else:
        return RiskCategory.SEVERE


@dataclass
class RiskScore:
    hazard_type: HazardType
    score: float
    category: RiskCategory
    probability: float | None = None
    severity: float | None = None
    confidence: float | None = None
    description: str = ""


@dataclass(frozen=True)
class HeatRiskScore:
    score: float
    max_temperature_contribution: float
    consecutive_hot_days_contribution: float
    seasonal_anomaly_contribution: float
    consecutive_hot_days: int
    seasonal_anomaly: float


@dataclass(frozen=True)
class FloodRiskScore:
    score: float
    rainfall_intensity_contribution: float
    multi_day_accumulation_contribution: float
    forecast_uncertainty_contribution: float
    multi_day_accumulation: float
    rainfall_intensity: float


@dataclass(frozen=True)
class DroughtRiskScore:
    score: float
    rainfall_deficit_contribution: float
    temperature_increase_contribution: float
    dry_period_days_contribution: float
    rainfall_deficit_percent: float
    temperature_anomaly: float


@dataclass(frozen=True)
class CompositeRiskScore:
    score: float
    heat_score: float
    flood_score: float
    drought_score: float
    weights: dict[str, float]


@dataclass(frozen=True)
class FeatureAttribution:
    feature_name: str
    shap_value: float
    feature_value: float
    contribution_type: str  # "positive" or "negative"


@dataclass(frozen=True)
class SHAPExplanation:
    prediction: float
    base_value: float
    feature_attributions: list[FeatureAttribution]
    top_features: list[str]
    positive_contributors: list[FeatureAttribution]
    negative_contributors: list[FeatureAttribution]
    confidence: float
    risk_interpretation: str


@dataclass(frozen=True)
class GlobalFeatureImportance:
    feature_name: str
    mean_abs_shap: float
    importance_percent: float


@dataclass(frozen=True)
class ClimateInsight:
    variable: str
    direction: str
    magnitude: float
    description: str
    risk_implication: str


@dataclass
class RiskReport:
    location_id: str
    district: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    heat_risk: HeatRiskScore | None = None
    flood_risk: FloodRiskScore | None = None
    drought_risk: DroughtRiskScore | None = None
    composite_risk: CompositeRiskScore | None = None
    agriculture_risk: RiskScore | None = None
    explanation: SHAPExplanation | None = None
    insights: list[ClimateInsight] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _serialize(obj: Any) -> Any:
            if hasattr(obj, "_asdict"):
                return obj._asdict()
            if isinstance(obj, enum.Enum):
                return obj.value
            if isinstance(obj, list):
                return [_serialize(v) for v in obj]
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if hasattr(obj, "__dict__"):
                return {k: _serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
            return obj

        return _serialize(self)
