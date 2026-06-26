"""Heat Risk scoring module.

Computes heat risk based on max temperature, consecutive hot days,
and seasonal temperature anomalies.
"""

import logging

from risk.models.risk_models import HeatRiskScore

logger = logging.getLogger(__name__)


def calculate_heat_risk(
    max_temp: float,
    _min_temp: float | None = None,
    consecutive_hot_days: int = 0,
    seasonal_anomaly: float = 0.0,
    weights: dict[str, float] | None = None,
    hot_day_threshold: float = 35.0,
    consecutive_days_threshold: int = 3,
) -> HeatRiskScore:
    """Compute heat risk score (0-100) from temperature data.

    Args:
        max_temp: Maximum temperature in Celsius.
        min_temp: Minimum temperature in Celsius (optional, for average).
        consecutive_hot_days: Number of consecutive days above threshold.
        seasonal_anomaly: Temperature anomaly from seasonal norm (Celsius).
        weights: Configurable weights dict with keys:
            max_temperature, consecutive_hot_days, seasonal_anomaly.
        hot_day_threshold: Temperature threshold for hot day classification.
        consecutive_days_threshold: Days threshold for elevated risk.

    Returns:
        HeatRiskScore with score and factor contributions.
    """
    w = weights or {"max_temperature": 0.4, "consecutive_hot_days": 0.35, "seasonal_anomaly": 0.25}

    temp_score = _temperature_score(max_temp, hot_day_threshold)
    consecutive_score = _consecutive_days_score(consecutive_hot_days, consecutive_days_threshold)
    anomaly_score = _anomaly_score(seasonal_anomaly)

    score = (
        w.get("max_temperature", 0.4) * temp_score
        + w.get("consecutive_hot_days", 0.35) * consecutive_score
        + w.get("seasonal_anomaly", 0.25) * anomaly_score
    )

    score = max(0.0, min(100.0, score))

    return HeatRiskScore(
        score=round(score, 2),
        max_temperature_contribution=round(temp_score, 2),
        consecutive_hot_days_contribution=round(consecutive_score, 2),
        seasonal_anomaly_contribution=round(anomaly_score, 2),
        consecutive_hot_days=consecutive_hot_days,
        seasonal_anomaly=round(seasonal_anomaly, 2),
    )


def _temperature_score(max_temp: float, threshold: float) -> float:
    """Score temperature contribution (0-100)."""
    if max_temp <= threshold:
        return 0.0
    excess = max_temp - threshold
    return min(100.0, excess * 4.0)


def _consecutive_days_score(days: int, threshold: int) -> float:
    """Score consecutive hot days contribution (0-100)."""
    if days <= 0:
        return 0.0
    if days <= threshold:
        return days * 10.0
    return min(100.0, threshold * 10.0 + (days - threshold) * 15.0)


def _anomaly_score(anomaly: float) -> float:
    """Score seasonal anomaly contribution (0-100)."""
    if anomaly <= 0:
        return 0.0
    return min(100.0, anomaly * 15.0)
