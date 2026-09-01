"""Phase 4 — Hazard data models.

Canonical HazardAssessment, provenanced evidence, freshness/severity
enums, and Alert/AlertPolicy models.  Builds on the existing scoring
dataclasses in risk_models.py without replacing them.
"""

from __future__ import annotations

import contextlib
import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar


class AssessmentType(enum.StrEnum):
    OBSERVED = "OBSERVED"
    FORECAST = "FORECAST"
    HISTORICAL_BACKTEST = "HISTORICAL_BACKTEST"
    SCENARIO = "SCENARIO"


class Severity(enum.StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class Freshness(enum.StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    VERY_STALE = "VERY_STALE"
    UNAVAILABLE = "UNAVAILABLE"


class DataQuality(enum.StrEnum):
    GOOD = "GOOD"
    SUSPECT = "SUSPECT"
    REJECTED = "REJECTED"
    INSUFFICIENT_FRESH_DATA = "INSUFFICIENT_FRESH_DATA"


class AlertStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    ESCALATED = "ESCALATED"
    DOWNGRADED = "DOWNGRADED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"


class HazardType(enum.StrEnum):
    HEAVY_RAIN = "heavy_rain"
    HEAT = "heat"
    DRYNESS = "dryness"
    HEATWAVE = "heatwave"
    FLOOD = "flood"
    DROUGHT = "drought"
    STORM = "storm"
    WILDFIRE = "wildfire"
    COMPOSITE = "composite"
    AGRICULTURE = "agriculture"


UNSUPPORTED_HAZARDS: frozenset[str] = frozenset(
    {
        "heatwave",
        "flood",
        "drought",
        "storm",
        "wildfire",
    }
)
"""Hazards declared in the enum but lacking operational implementation."""


@dataclass
class EvidenceFactor:
    factor: str
    value: float
    unit: str
    threshold: float | None
    effect: str  # "increases_hazard" | "decreases_hazard" | "neutral"


@dataclass
class HistoricalContext:
    reference_period: str
    location_id: str
    variable: str
    current_value: float
    percentile: float | None
    mean: float | None
    p50: float | None
    p95: float | None
    p99: float | None
    anomaly: float | None
    anomaly_unit: str = ""
    method: str = ""
    dataset_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v.value if isinstance(v, enum.Enum) else v for k, v in self.__dict__.items()}


@dataclass
class DeterministicAttribution:
    primary_driver: str
    factors: list[EvidenceFactor]
    method: str
    method_version: str


@dataclass
class HazardAssessment:
    assessment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    hazard_type: str = ""
    assessment_type: AssessmentType = AssessmentType.OBSERVED
    location_id: str = ""
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    valid_from: str | None = None
    valid_until: str | None = None
    severity: Severity = Severity.NONE
    hazard_score: float = 0.0
    assessment_confidence: float = 0.0
    source_twin_version: str | None = None
    source_observation_ids: list[str] = field(default_factory=list)
    source_forecast_ids: list[str] = field(default_factory=list)
    evidence: list[EvidenceFactor] = field(default_factory=list)
    thresholds_triggered: list[str] = field(default_factory=list)
    historical_context: HistoricalContext | None = None
    data_quality: DataQuality = DataQuality.GOOD
    data_freshness: Freshness = Freshness.FRESH
    method: str = ""
    method_version: str = ""
    config_version: str = ""
    attribution: DeterministicAttribution | None = None
    provenance: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _serialize(obj: Any) -> Any:
            if obj is None:
                return None
            if isinstance(obj, enum.Enum):
                return obj.value
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, "__dataclass_fields__"):
                return {k: _serialize(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, list):
                return [_serialize(v) for v in obj]
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            return obj

        return {k: _serialize(v) for k, v in self.__dict__.items()}

    # Enum fields that need string → enum conversion on deserialization
    _ENUM_FIELDS: ClassVar[dict[str, type[enum.Enum]]] = {
        "assessment_type": AssessmentType,
        "severity": Severity,
        "data_quality": DataQuality,
        "data_freshness": Freshness,
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HazardAssessment:
        converted: dict[str, Any] = {}
        for k, v in data.items():
            if k not in cls.__dataclass_fields__:
                continue
            enum_cls = cls._ENUM_FIELDS.get(k)
            if enum_cls is not None and isinstance(v, str):
                with contextlib.suppress(ValueError):
                    v = enum_cls(v)
            converted[k] = v
        return cls(**converted)


@dataclass
class Alert:
    alert_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    assessment_id: str = ""
    location_id: str = ""
    hazard_type: str = ""
    severity: str = ""
    status: AlertStatus = AlertStatus.ACTIVE
    issued_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v.value if isinstance(v, enum.Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Alert:
        data["status"] = AlertStatus(data.get("status", "ACTIVE"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
