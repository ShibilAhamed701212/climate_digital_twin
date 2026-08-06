"""Quality and freshness gates for operational hazard assessments.

Rejects SYNTHETIC/UNKNOWN data, checks timestamp freshness, and
produces deterministic quality/confidence scores.

All thresholds are driven by a single runtime configuration (risk_config.yaml).
The HazardEvaluator wires the loaded config into these functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from risk.models.hazard import DataQuality, Freshness, Severity

CONFIG_VERSION = "2026-07-30"

DEFAULT_FRESH_MINUTES = {"fresh": 60, "stale": 360, "very_stale": 1440}
DEFAULT_CONFIDENCE = {
    "base": 0.85,
    "stale_penalty": 0.15,
    "very_stale_penalty": 0.40,
    "suspect_penalty": 0.20,
    "incomplete_penalty": 0.10,
}
DEFAULT_SEVERITY_THRESHOLDS = {"low": 20, "moderate": 40, "high": 60, "severe": 80}


@dataclass
class QualityGateConfig:
    fresh_max_minutes: int = 60
    stale_max_minutes: int = 360
    very_stale_max_minutes: int = 1440
    confidence_base: float = 0.85
    stale_penalty: float = 0.15
    very_stale_penalty: float = 0.40
    suspect_penalty: float = 0.20
    incomplete_penalty: float = 0.10
    forecast_validation_bonus: float = 0.10
    severity_low: float = 20.0
    severity_moderate: float = 40.0
    severity_high: float = 60.0
    severity_severe: float = 80.0
    allowed_authenticity: frozenset[str] = field(default_factory=lambda: frozenset({"REAL"}))
    allowed_quality: frozenset[str] = field(default_factory=lambda: frozenset({"validated", "raw"}))

    @classmethod
    def from_yaml_config(cls, config: dict[str, Any] | None) -> "QualityGateConfig":
        if not config:
            return cls()
        freshness = config.get("freshness", {})
        conf = config.get("confidence", {})
        quality = config.get("quality", {})
        severity_vals = DEFAULT_SEVERITY_THRESHOLDS.copy()
        hazards_cfg = config.get("hazards", {})
        for hazard_name in ("heavy_rain", "heat", "dryness"):
            h_sev = hazards_cfg.get(hazard_name, {}).get("severity_thresholds", {})
            if h_sev:
                severity_vals.update(h_sev)
        return cls(
            fresh_max_minutes=freshness.get("fresh_max_minutes", 60),
            stale_max_minutes=freshness.get("stale_max_minutes", 360),
            very_stale_max_minutes=freshness.get("very_stale_max_minutes", 1440),
            confidence_base=conf.get("base_confidence", 0.85),
            stale_penalty=conf.get("freshness_penalty_stale", 0.15),
            very_stale_penalty=conf.get("freshness_penalty_very_stale", 0.40),
            suspect_penalty=conf.get("quality_penalty_suspect", 0.20),
            incomplete_penalty=conf.get("incomplete_inputs_penalty", 0.10),
            forecast_validation_bonus=conf.get("forecast_validation_bonus", 0.10),
            severity_low=severity_vals.get("low", 20.0),
            severity_moderate=severity_vals.get("moderate", 40.0),
            severity_high=severity_vals.get("high", 60.0),
            severity_severe=severity_vals.get("severe", 80.0),
            allowed_authenticity=frozenset(quality.get("allowed_authenticity", ["REAL"])),
            allowed_quality=frozenset(quality.get("allowed_quality_flags", ["validated", "raw"])),
        )


_default_config = QualityGateConfig()


def check_freshness(
    timestamp: datetime | str | None,
    fresh_max_minutes: int | None = None,
    stale_max_minutes: int | None = None,
    config: QualityGateConfig | None = None,
) -> Freshness:
    cfg = config or _default_config
    f_max = fresh_max_minutes if fresh_max_minutes is not None else cfg.fresh_max_minutes
    s_max = stale_max_minutes if stale_max_minutes is not None else cfg.stale_max_minutes
    if timestamp is None:
        return Freshness.UNAVAILABLE
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except ValueError:
            return Freshness.UNAVAILABLE
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - timestamp).total_seconds() / 60.0
    if age < 0:
        return Freshness.FRESH
    if age <= f_max:
        return Freshness.FRESH
    if age <= s_max:
        return Freshness.STALE
    return Freshness.VERY_STALE


def check_quality(
    authenticity: str | None,
    quality_flag: str | None,
    allowed_authenticity: frozenset[str] | None = None,
    allowed_quality: frozenset[str] | None = None,
    config: QualityGateConfig | None = None,
) -> tuple[DataQuality, str]:
    cfg = config or _default_config
    allowed_auth = allowed_authenticity or cfg.allowed_authenticity
    allowed_q = allowed_quality or cfg.allowed_quality

    if authenticity is None or authenticity.upper() not in allowed_auth:
        return DataQuality.REJECTED, f"authenticity={authenticity} not in allowed set"
    if quality_flag is None or quality_flag.lower() not in allowed_q:
        return DataQuality.REJECTED, f"quality_flag={quality_flag} not in allowed set"
    if authenticity.upper() in ("SYNTHETIC", "UNKNOWN", "SCENARIO"):
        return DataQuality.REJECTED, f"operational mode rejects authenticity={authenticity}"

    if quality_flag.lower() == "raw":
        return DataQuality.SUSPECT, "unvalidated raw data"
    return DataQuality.GOOD, ""


def compute_confidence(
    data_quality: DataQuality,
    freshness: Freshness,
    input_count: int,
    expected_inputs: int,
    forecast_validated: bool = False,
    config: QualityGateConfig | None = None,
) -> float:
    cfg = config or _default_config
    conf = cfg.confidence_base
    if data_quality == DataQuality.SUSPECT:
        conf -= cfg.suspect_penalty
    if freshness == Freshness.STALE:
        conf -= cfg.stale_penalty
    elif freshness == Freshness.VERY_STALE:
        conf -= cfg.very_stale_penalty
    if input_count < expected_inputs:
        conf -= cfg.incomplete_penalty
    if forecast_validated:
        conf += cfg.forecast_validation_bonus
    return max(0.1, min(1.0, conf))


def severity_from_score(
    score: float,
    thresholds: QualityGateConfig | None = None,
) -> Severity:
    cfg = thresholds or _default_config
    if score <= 0:
        return Severity.NONE
    if score <= cfg.severity_low:
        return Severity.LOW
    if score <= cfg.severity_moderate:
        return Severity.MODERATE
    if score <= cfg.severity_high:
        return Severity.HIGH
    return Severity.SEVERE
