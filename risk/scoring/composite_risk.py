"""Composite Climate Risk Index.

Computes a weighted combination of heat, flood, and drought risks.
"""

import logging

from risk.models.risk_models import CompositeRiskScore

logger = logging.getLogger(__name__)


def calculate_composite_risk(
    heat_score: float,
    flood_score: float,
    drought_score: float,
    weights: dict[str, float] | None = None,
) -> CompositeRiskScore:
    """Compute composite climate risk index (0-100).

    Args:
        heat_score: Heat risk score (0-100).
        flood_score: Flood risk score (0-100).
        drought_score: Drought risk score (0-100).
        weights: Configurable weights dict with keys: heat, flood, drought.
            Defaults to equal weighting.

    Returns:
        CompositeRiskScore with overall score and individual components.
    """
    w = weights or {"heat": 0.33, "flood": 0.33, "drought": 0.34}

    heat_w = w.get("heat", 0.33)
    flood_w = w.get("flood", 0.33)
    drought_w = w.get("drought", 0.34)

    score = heat_w * heat_score + flood_w * flood_score + drought_w * drought_score
    score = max(0.0, min(100.0, score))

    return CompositeRiskScore(
        score=round(score, 2),
        heat_score=round(heat_score, 2),
        flood_score=round(flood_score, 2),
        drought_score=round(drought_score, 2),
        weights={"heat": heat_w, "flood": flood_w, "drought": drought_w},
    )
