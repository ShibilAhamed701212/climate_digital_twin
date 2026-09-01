"""Deterministic factor attribution — replaces fake SHAP.

Every explanation derives from the actual scoring inputs and rules.
No AI, no heuristics pretending to be SHAP.
"""

from __future__ import annotations

from risk.models.hazard import DeterministicAttribution, EvidenceFactor


def build_heat_attribution(
    max_temp: float,
    consecutive_hot_days: int,
    seasonal_anomaly: float,
    _heat_score: float,
    hot_day_threshold: float = 35.0,
) -> DeterministicAttribution:
    factors: list[EvidenceFactor] = []

    if max_temp > 0:
        effect = "increases_hazard" if max_temp > hot_day_threshold else "decreases_hazard"
        factors.append(
            EvidenceFactor(
                factor="max_temp",
                value=max_temp,
                unit="°C",
                threshold=hot_day_threshold,
                effect=effect,
            )
        )

    if consecutive_hot_days > 0:
        factors.append(
            EvidenceFactor(
                factor="consecutive_hot_days",
                value=float(consecutive_hot_days),
                unit="days",
                threshold=3.0,
                effect="increases_hazard",
            )
        )

    if seasonal_anomaly != 0:
        effect = "increases_hazard" if seasonal_anomaly > 0 else "decreases_hazard"
        factors.append(
            EvidenceFactor(
                factor="seasonal_anomaly",
                value=round(seasonal_anomaly, 2),
                unit="°C",
                threshold=2.0,
                effect=effect,
            )
        )

    factors.sort(
        key=lambda f: abs(f.value * (1 if f.effect == "increases_hazard" else -1)), reverse=True
    )
    primary = factors[0].factor if factors else "none"

    return DeterministicAttribution(
        primary_driver=primary,
        factors=factors,
        method="HEAT_V1",
        method_version="1.0.0",
    )


def build_heavy_rain_attribution(
    rainfall: float,
    multi_day_accumulation: float | None,
    heavy_rain_threshold: float,
    _flood_score: float,
) -> DeterministicAttribution:
    factors: list[EvidenceFactor] = []
    threshold_24h = heavy_rain_threshold

    if rainfall > 0:
        effect = "increases_hazard" if rainfall >= threshold_24h * 0.5 else "neutral"
        factors.append(
            EvidenceFactor(
                factor="rainfall_24h",
                value=round(rainfall, 1),
                unit="mm",
                threshold=threshold_24h,
                effect=effect,
            )
        )

    accum = multi_day_accumulation if multi_day_accumulation is not None else rainfall
    if accum > 0:
        accum_threshold = threshold_24h * 3 * 0.5
        effect = "increases_hazard" if accum >= accum_threshold else "neutral"
        factors.append(
            EvidenceFactor(
                factor="rainfall_3d_accumulation",
                value=round(accum, 1),
                unit="mm",
                threshold=round(accum_threshold, 1),
                effect=effect,
            )
        )

    factors.sort(key=lambda f: abs(f.value), reverse=True)
    primary = factors[0].factor if factors else "none"

    return DeterministicAttribution(
        primary_driver=primary,
        factors=factors,
        method="HEAVY_RAIN_V1",
        method_version="1.0.0",
    )


def build_dryness_attribution(
    rainfall: float,
    historical_mean_rainfall: float,
    dry_period_days: int,
    temperature_anomaly: float,
) -> DeterministicAttribution:
    factors: list[EvidenceFactor] = []
    deficit_pct = (
        (rainfall - historical_mean_rainfall) / max(historical_mean_rainfall, 0.1)
    ) * 100.0

    effect = "increases_hazard" if deficit_pct < -25 else "neutral"
    factors.append(
        EvidenceFactor(
            factor="rainfall_deficit_pct",
            value=round(deficit_pct, 1),
            unit="%",
            threshold=-25.0,
            effect=effect,
        )
    )

    if dry_period_days > 0:
        factors.append(
            EvidenceFactor(
                factor="dry_period_days",
                value=float(dry_period_days),
                unit="days",
                threshold=15.0,
                effect="increases_hazard" if dry_period_days >= 15 else "neutral",
            )
        )

    if temperature_anomaly != 0:
        effect = "increases_hazard" if temperature_anomaly > 1.5 else "neutral"
        factors.append(
            EvidenceFactor(
                factor="temperature_anomaly",
                value=round(temperature_anomaly, 2),
                unit="°C",
                threshold=1.5,
                effect=effect,
            )
        )

    factors.sort(key=lambda f: abs(f.value), reverse=True)
    primary = factors[0].factor if factors else "none"

    return DeterministicAttribution(
        primary_driver=primary,
        factors=factors,
        method="DRYNESS_V1",
        method_version="1.0.0",
    )
