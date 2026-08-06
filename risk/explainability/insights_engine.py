"""Climate Insights Engine — generates readable summaries from risk scores.

Converts numerical risk assessments into natural language insights
for dashboard, copilot, and reports.
"""

import logging

from risk.models.risk_models import (
    ClimateInsight,
    CompositeRiskScore,
    DroughtRiskScore,
    FloodRiskScore,
    HeatRiskScore,
)

logger = logging.getLogger(__name__)


def generate_insights(
    heat: HeatRiskScore,
    flood: FloodRiskScore,
    drought: DroughtRiskScore,
    composite: CompositeRiskScore,
) -> list[ClimateInsight]:
    """Generate climate insights from risk assessment results.

    Args:
        heat: Heat risk assessment result.
        flood: Flood risk assessment result.
        drought: Drought risk assessment result.
        composite: Composite risk index result.

    Returns:
        List of ClimateInsight objects with readable descriptions.
    """
    insights: list[ClimateInsight] = []

    insights.extend(_heat_insights(heat))
    insights.extend(_flood_insights(flood))
    insights.extend(_drought_insights(drought))
    insights.extend(_composite_insights(composite, heat, flood, drought))

    return insights


def _heat_insights(heat: HeatRiskScore) -> list[ClimateInsight]:
    insights: list[ClimateInsight] = []

    if heat.seasonal_anomaly > 2.0:
        insights.append(
            ClimateInsight(
                variable="max_temp",
                direction="increasing",
                magnitude=heat.seasonal_anomaly,
                description=f"Temperature is {heat.seasonal_anomaly:.1f}°C above seasonal average.",
                risk_implication="Increased heat stress risk for vulnerable populations.",
            )
        )

    if heat.consecutive_hot_days >= 3:
        insights.append(
            ClimateInsight(
                variable="consecutive_hot_days",
                direction="elevated",
                magnitude=float(heat.consecutive_hot_days),
                description=f"{heat.consecutive_hot_days} consecutive hot days recorded.",
                risk_implication="Prolonged heat exposure increases health risks and energy demand.",
            )
        )

    return insights


def _flood_insights(flood: FloodRiskScore) -> list[ClimateInsight]:
    insights: list[ClimateInsight] = []

    if flood.rainfall_intensity > 100:
        insights.append(
            ClimateInsight(
                variable="rainfall",
                direction="heavy",
                magnitude=flood.rainfall_intensity,
                description=f"Rainfall intensity at {flood.rainfall_intensity:.1f}mm — above heavy rain threshold.",
                risk_implication="Elevated surface water accumulation risk — localized pooling possible in low-lying areas.",
            )
        )

    if flood.multi_day_accumulation > 200:
        insights.append(
            ClimateInsight(
                variable="multi_day_accumulation",
                direction="high",
                magnitude=flood.multi_day_accumulation,
                description=f"Multi-day accumulation of {flood.multi_day_accumulation:.1f}mm.",
                risk_implication="Sustained rainfall increases surface water accumulation — may cause waterlogging in poor drainage areas.",
            )
        )

    return insights


def _drought_insights(drought: DroughtRiskScore) -> list[ClimateInsight]:
    insights: list[ClimateInsight] = []

    if drought.rainfall_deficit_percent < -25:
        insights.append(
            ClimateInsight(
                variable="rainfall",
                direction="deficit",
                magnitude=abs(drought.rainfall_deficit_percent),
                description=f"Rainfall deficit of {abs(drought.rainfall_deficit_percent):.1f}% below historical mean.",
                risk_implication="Below-normal rainfall — drier-than-usual conditions may affect local soil moisture.",
            )
        )

    if drought.temperature_anomaly > 1.5:
        insights.append(
            ClimateInsight(
                variable="max_temp",
                direction="increasing",
                magnitude=drought.temperature_anomaly,
                description=f"Temperature {drought.temperature_anomaly:.1f}°C above normal.",
                risk_implication="Higher temperatures accelerate evaporation, worsening drought conditions.",
            )
        )

    return insights


def _composite_insights(
    composite: CompositeRiskScore,
    heat: HeatRiskScore,
    flood: FloodRiskScore,
    drought: DroughtRiskScore,
) -> list[ClimateInsight]:
    insights: list[ClimateInsight] = []

    max_risk = max(heat.score, flood.score, drought.score)
    if max_risk == heat.score:
        primary = "Heat"
    elif max_risk == flood.score:
        primary = "Flood"
    else:
        primary = "Drought"

    insights.append(
        ClimateInsight(
            variable="composite",
            direction=primary.lower(),
            magnitude=composite.score,
            description=f"Composite climate risk index is {composite.score:.1f}. Primary driver: {primary} Risk.",
            risk_implication=f"{primary} is the dominant climate hazard for this location.",
        )
    )

    if composite.score > 60:
        insights.append(
            ClimateInsight(
                variable="composite",
                direction="critical",
                magnitude=composite.score,
                description=f"Composite risk is {composite.score:.1f} — classified as {_risk_label(composite.score)}.",
                risk_implication="Proactive monitoring and mitigation measures recommended.",
            )
        )

    return insights


def _risk_label(score: float) -> str:
    if score <= 20:
        return "Very Low"
    if score <= 40:
        return "Low"
    if score <= 60:
        return "Moderate"
    if score <= 80:
        return "High"
    return "Severe"
