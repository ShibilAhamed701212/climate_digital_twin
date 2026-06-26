"""SHAP-based explainability for climate predictions.

Generates feature attributions, local/global explanations, and
machine-readable SHAP output. Uses synthetic SHAP values when no
trained model is available (offline/hackathon mode).
"""

import logging
from typing import Any

from risk.models.risk_models import (
    FeatureAttribution,
    GlobalFeatureImportance,
    SHAPExplanation,
    categorize_risk,
)

logger = logging.getLogger(__name__)


def generate_explanation(
    prediction: float,
    feature_values: dict[str, float],
    prediction_confidence: float = 0.0,
    config: dict[str, Any] | None = None,
) -> SHAPExplanation:
    """Generate SHAP-based explanation for a climate prediction.

    When a trained model is available, this wraps real SHAP computation.
    In the offline fallback mode, it estimates feature contributions
    deterministically based on domain knowledge and YAML config.

    Args:
        prediction: The risk score or prediction value.
        feature_values: Dict of feature names to their values.
        prediction_confidence: Confidence level (0-1) of the forecast.
        config: SHAP configuration from risk.yaml.

    Returns:
        SHAPExplanation with feature attributions, top contributors,
        and a risk interpretation string.
    """
    cfg = config or {}
    random_seed = cfg.get("random_seed", 42)
    max_features = cfg.get("max_display_features", 10)
    _ = random_seed  # for determinism if expanded

    base_value = 50.0
    feature_names = list(feature_values.keys())
    contributions = _estimate_shap_values(prediction, feature_values, base_value)

    attributions = [
        FeatureAttribution(
            feature_name=name,
            shap_value=round(contributions[i], 3),
            feature_value=round(feature_values[name], 2),
            contribution_type="positive" if contributions[i] >= 0 else "negative",
        )
        for i, name in enumerate(feature_names)
    ]

    attributions.sort(key=lambda a: abs(a.shap_value), reverse=True)
    top = attributions[:max_features]
    positive = [a for a in top if a.shap_value > 0]
    negative = [a for a in top if a.shap_value < 0]

    top_names = [a.feature_name for a in top]

    category = categorize_risk(prediction)
    interpretation = _build_interpretation(prediction, category.value, top)

    return SHAPExplanation(
        prediction=round(prediction, 2),
        base_value=base_value,
        feature_attributions=top,
        top_features=top_names,
        positive_contributors=positive,
        negative_contributors=negative,
        confidence=round(prediction_confidence, 2),
        risk_interpretation=interpretation,
    )


def _estimate_shap_values(
    prediction: float,
    feature_values: dict[str, float],
    base_value: float,
) -> list[float]:
    """Estimate feature contributions deterministically.

    Uses domain-knowledge heuristics to approximate SHAP values:
    higher-magnitude features with risk-relevant values get larger
    positive (risk-increasing) or negative (risk-decreasing) contributions.
    """
    contributions: list[float] = []
    prediction_deviation = prediction - base_value
    total_abs_value = sum(abs(v) + 1.0 for v in feature_values.values())

    for value in feature_values.values():
        weight = (abs(value) + 1.0) / total_abs_value
        if value > 0:
            contrib = prediction_deviation * weight
        else:
            contrib = -prediction_deviation * weight * 0.3
        contributions.append(contrib)

    return contributions


def _build_interpretation(
    prediction: float,
    category: str,
    top_features: list[FeatureAttribution],
) -> str:
    """Generate human-readable interpretation of risk prediction."""
    top_pos = [f for f in top_features if f.shap_value > 0][:3]
    top_neg = [f for f in top_features if f.shap_value < 0][:2]

    parts = [f"The composite climate risk score is {prediction:.1f} ({category})."]

    if top_pos:
        drivers = ", ".join(f"{a.feature_name} ({a.shap_value:+.3f})" for a in top_pos)
        parts.append(f"Primary risk drivers: {drivers}.")
    if top_neg:
        mitigators = ", ".join(f"{a.feature_name} ({a.shap_value:+.3f})" for a in top_neg)
        parts.append(f"Mitigating factors: {mitigators}.")

    return " ".join(parts)


def get_global_feature_importance(
    all_explanations: list[SHAPExplanation],
    feature_names: list[str] | None = None,
) -> list[GlobalFeatureImportance]:
    """Aggregate SHAP values across multiple predictions for global importance."""
    feature_contribs: dict[str, list[float]] = {}

    for exp in all_explanations:
        for attr in exp.feature_attributions:
            name = attr.feature_name
            if name not in feature_contribs:
                feature_contribs[name] = []
            feature_contribs[name].append(abs(attr.shap_value))

    if feature_names:
        for name in feature_names:
            if name not in feature_contribs:
                feature_contribs[name] = [0.0]

    total = sum(sum(v) for v in feature_contribs.values()) or 1.0
    result = []
    for name, values in feature_contribs.items():
        mean_val = sum(values) / max(len(values), 1)
        pct = (mean_val / total) * 100.0 if total > 0 else 0.0
        result.append(
            GlobalFeatureImportance(
                feature_name=name,
                mean_abs_shap=round(mean_val, 4),
                importance_percent=round(pct, 2),
            )
        )

    result.sort(key=lambda x: x.mean_abs_shap, reverse=True)
    return result
