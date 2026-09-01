"""Flood Risk scoring module.

Computes flood risk based on rainfall intensity, multi-day accumulation,
and forecast uncertainty.
"""

import logging

from risk.models.risk_models import FloodRiskScore

logger = logging.getLogger(__name__)


def calculate_flood_risk(
    rainfall: float,
    multi_day_accumulation: float | None = None,
    forecast_uncertainty: float = 0.0,
    weights: dict[str, float] | None = None,
    heavy_rain_threshold: float = 100.0,
    accumulation_window_days: int = 3,
) -> FloodRiskScore:
    """Compute flood risk score (0-100) from rainfall data.

    Args:
        rainfall: Current/forecast rainfall in mm.
        multi_day_accumulation: Accumulated rainfall over window (mm).
        forecast_uncertainty: Uncertainty level (0-1, higher = more uncertain).
        weights: Configurable weights dict with keys:
            rainfall_intensity, multi_day_accumulation, forecast_uncertainty.
        heavy_rain_threshold: Threshold for heavy rainfall (mm).
        accumulation_window_days: Lookback window for accumulation.

    Returns:
        FloodRiskScore with score and factor contributions.
    """
    w = weights or {
        "rainfall_intensity": 0.4,
        "multi_day_accumulation": 0.35,
        "forecast_uncertainty": 0.25,
    }

    if multi_day_accumulation is None:
        # Honest 1-day window: same-day rainfall, not a fabricated fraction.
        multi_day_accumulation = rainfall

    intensity_score = _intensity_score(rainfall, heavy_rain_threshold)
    accumulation_score = _accumulation_score(
        multi_day_accumulation, heavy_rain_threshold, accumulation_window_days
    )
    uncertainty_score = _uncertainty_score(forecast_uncertainty)

    score = (
        w.get("rainfall_intensity", 0.4) * intensity_score
        + w.get("multi_day_accumulation", 0.35) * accumulation_score
        + w.get("forecast_uncertainty", 0.25) * uncertainty_score
    )

    score = max(0.0, min(100.0, score))

    return FloodRiskScore(
        score=round(score, 2),
        rainfall_intensity_contribution=round(intensity_score, 2),
        multi_day_accumulation_contribution=round(accumulation_score, 2),
        forecast_uncertainty_contribution=round(uncertainty_score, 2),
        multi_day_accumulation=round(multi_day_accumulation, 2),
        rainfall_intensity=round(rainfall, 2),
    )


def _intensity_score(rainfall: float, threshold: float) -> float:
    """Score rainfall intensity contribution (0-100)."""
    if rainfall <= 0:
        return 0.0
    if rainfall <= threshold:
        return (rainfall / threshold) * 50.0
    excess = rainfall - threshold
    return min(100.0, 50.0 + (excess / threshold) * 50.0)


def _accumulation_score(accumulation: float, threshold: float, window: int) -> float:
    """Score multi-day accumulation contribution (0-100)."""
    effective_threshold = threshold * (window * 0.5)
    if accumulation <= 0:
        return 0.0
    if accumulation <= effective_threshold:
        return (accumulation / effective_threshold) * 60.0
    return min(100.0, 60.0 + ((accumulation - effective_threshold) / effective_threshold) * 40.0)


def _uncertainty_score(uncertainty: float) -> float:
    """Score forecast uncertainty contribution (0-100).

    Higher uncertainty amplifies flood risk (precautionary principle).
    """
    if uncertainty <= 0:
        return 0.0
    return min(100.0, uncertainty * 100.0 * 0.5)
