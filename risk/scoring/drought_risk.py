"""Drought Risk scoring module.

Computes drought risk based on rainfall deficit, temperature increase,
and prolonged dry periods.
"""

import logging

from risk.models.risk_models import DroughtRiskScore

logger = logging.getLogger(__name__)


def calculate_drought_risk(
    rainfall: float,
    historical_mean_rainfall: float = 100.0,
    max_temp: float = 30.0,
    historical_mean_temp: float = 28.0,
    dry_period_days: int = 0,
    weights: dict[str, float] | None = None,
    deficit_threshold_percent: float = -25.0,
    dry_period_threshold_days: int = 15,
) -> DroughtRiskScore:
    """Compute drought risk score (0-100) from rainfall and temperature data.

    Args:
        rainfall: Current/forecast rainfall in mm.
        historical_mean_rainfall: Long-term average rainfall for the period.
        max_temp: Current maximum temperature in Celsius.
        historical_mean_temp: Long-term average max temperature for the period.
        dry_period_days: Number of consecutive dry days.
        weights: Configurable weights dict with keys:
            rainfall_deficit, temperature_increase, dry_period_days.
        deficit_threshold_percent: Deficit percentage to trigger risk.
        dry_period_threshold_days: Days threshold for elevated risk.

    Returns:
        DroughtRiskScore with score and factor contributions.
    """
    w = weights or {"rainfall_deficit": 0.4, "temperature_increase": 0.3, "dry_period_days": 0.3}

    deficit_pct = ((rainfall - historical_mean_rainfall) / max(historical_mean_rainfall, 0.1)) * 100.0
    temp_anomaly = max_temp - historical_mean_temp

    deficit_score = _deficit_score(deficit_pct, deficit_threshold_percent)
    temp_score = _temperature_drought_score(temp_anomaly)
    dry_score = _dry_period_score(dry_period_days, dry_period_threshold_days)

    score = (
        w.get("rainfall_deficit", 0.4) * deficit_score
        + w.get("temperature_increase", 0.3) * temp_score
        + w.get("dry_period_days", 0.3) * dry_score
    )

    score = max(0.0, min(100.0, score))

    return DroughtRiskScore(
        score=round(score, 2),
        rainfall_deficit_contribution=round(deficit_score, 2),
        temperature_increase_contribution=round(temp_score, 2),
        dry_period_days_contribution=round(dry_score, 2),
        rainfall_deficit_percent=round(deficit_pct, 2),
        temperature_anomaly=round(temp_anomaly, 2),
    )


def _deficit_score(deficit_pct: float, threshold: float) -> float:
    """Score rainfall deficit contribution (0-100)."""
    if deficit_pct >= 0:
        return 0.0
    if deficit_pct >= threshold:
        return (abs(deficit_pct) / 100.0) * 40.0
    return min(100.0, 40.0 + (abs(deficit_pct) - abs(threshold)) * 1.5)


def _temperature_drought_score(anomaly: float) -> float:
    """Score temperature increase contribution to drought (0-100)."""
    if anomaly <= 0:
        return 0.0
    return min(100.0, anomaly * 12.0)


def _dry_period_score(days: int, threshold: int) -> float:
    """Score dry period contribution (0-100)."""
    if days <= 0:
        return 0.0
    if days <= threshold:
        return (days / threshold) * 40.0
    return min(100.0, 40.0 + ((days - threshold) / threshold) * 60.0)
