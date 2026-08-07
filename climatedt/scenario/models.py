"""Phase 5 — canonical Counterfactual / What-If Scenario models.

Every scenario-derived artifact carries ``authenticity = SCENARIO``.  The baseline
may be REAL, but scenario output never inherits REAL.  Identity is a content hash
of the canonical inputs (location, twin version, baseline timestamp, ordered
interventions, method, config) — NOT just ``scenario_id``.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

SCENARIO_AUTHENTICITY = "SCENARIO"
REAL_AUTHENTICITY = "REAL"

METHOD = "counterfactual"
METHOD_VERSION = "1.0.0"
CONFIG_VERSION = "2026-07-31"

SUPPORTED_OPERATIONS = ("ADD", "SUBTRACT", "MULTIPLY", "SET", "PERCENT_CHANGE")

# Canonical variable → unit.
VARIABLE_UNITS: dict[str, str] = {
    "temperature_2m": "°C",
    "precipitation_mm": "mm",
    "humidity_pct": "%",
    "pressure_hpa": "hPa",
    "wind_speed_10m": "m/s",
    "wind_direction_10m": "deg",
    "cloud_cover_pct": "%",
    "soil_moisture": "m³/m³",
    "solar_radiation": "W/m²",
}

# Physical bounds per variable; None = unbounded.  Post-application values must
# stay within bounds or the intervention is rejected (never silently clamped).
VARIABLE_BOUNDS: dict[str, tuple[float | None, float | None]] = {
    "temperature_2m": (None, None),
    "precipitation_mm": (0.0, None),
    "humidity_pct": (0.0, 100.0),
    "pressure_hpa": (850.0, 1080.0),
    "wind_speed_10m": (0.0, None),
    "wind_direction_10m": (0.0, 360.0),
    "cloud_cover_pct": (0.0, 100.0),
    "soil_moisture": (0.0, None),
    "solar_radiation": (0.0, None),
}


@dataclass(frozen=True)
class ScenarioIntervention:
    """A single deterministic hypothetical alteration of one twin variable."""

    variable: str
    operation: str
    value: float
    unit: str | None = None

    def __post_init__(self) -> None:
        if self.variable not in VARIABLE_UNITS:
            raise ValueError(
                f"Unknown scenario variable '{self.variable}'. Supported: {sorted(VARIABLE_UNITS)}"
            )
        if self.operation not in SUPPORTED_OPERATIONS:
            raise ValueError(
                f"Unknown operation '{self.operation}'. Supported: {SUPPORTED_OPERATIONS}"
            )
        if (
            self.value is None
            or self.value != self.value
            or self.value in (float("inf"), float("-inf"))
        ):
            raise ValueError(f"Intervention value must be a finite number, got {self.value!r}")
        if self.unit is None:
            object.__setattr__(self, "unit", VARIABLE_UNITS[self.variable])
        elif self.unit != VARIABLE_UNITS[self.variable]:
            raise ValueError(
                f"Unit '{self.unit}' does not match canonical unit "
                f"'{VARIABLE_UNITS[self.variable]}' for '{self.variable}'"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "operation": self.operation,
            "value": self.value,
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioIntervention:
        return cls(
            variable=data["variable"],
            operation=data["operation"],
            value=float(data["value"]),
            unit=data.get("unit"),
        )


@dataclass(frozen=True)
class ScenarioDefinition:
    """Canonical scenario definition.  ``duration_days`` is metadata only."""

    scenario_id: str
    name: str
    description: str
    scenario_type: str
    location_id: str
    interventions: list[ScenarioIntervention]
    duration_days: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    parameters: dict[str, Any] = field(default_factory=dict)
    method: str = METHOD
    method_version: str = METHOD_VERSION
    config_version: str = CONFIG_VERSION
    authenticity: str = SCENARIO_AUTHENTICITY
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type,
            "location_id": self.location_id,
            "interventions": [i.to_dict() for i in self.interventions],
            "duration_days": self.duration_days,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "parameters": dict(self.parameters),
            "method": self.method,
            "method_version": self.method_version,
            "config_version": self.config_version,
            "authenticity": self.authenticity,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioDefinition:
        return cls(
            scenario_id=data["scenario_id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            scenario_type=data.get("scenario_type", "custom"),
            location_id=data.get("location_id", ""),
            interventions=[
                ScenarioIntervention.from_dict(i) for i in data.get("interventions", [])
            ],
            duration_days=data.get("duration_days", 0),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            parameters=data.get("parameters", {}),
            method=data.get("method", METHOD),
            method_version=data.get("method_version", METHOD_VERSION),
            config_version=data.get("config_version", CONFIG_VERSION),
            authenticity=data.get("authenticity", SCENARIO_AUTHENTICITY),
            created_at=data.get("created_at", ""),
        )

    def canonical_identity(self) -> dict[str, Any]:
        """Content-hash identity payload — NOT just ``scenario_id``."""
        return {
            "location_id": self.location_id,
            "interventions": [i.to_dict() for i in self.interventions],
            "method": self.method,
            "method_version": self.method_version,
            "config_version": self.config_version,
        }


def compute_result_id(
    definition: ScenarioDefinition,
    baseline_twin_version: str,
    baseline_timestamp: str,
) -> str:
    payload = {
        **definition.canonical_identity(),
        "baseline_twin_version": baseline_twin_version,
        "baseline_timestamp": baseline_timestamp,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"scn_{digest[:16]}"


def new_scenario_id() -> str:
    return f"scenario_{uuid.uuid4().hex[:8]}"


@dataclass
class ScenarioResult:
    """Deterministic single-timestamp counterfactual result."""

    result_id: str
    scenario_id: str
    definition: ScenarioDefinition
    location_id: str
    baseline_twin_version: str
    baseline_timestamp: str
    baseline_state: dict[str, float]
    scenario_state: dict[str, float]
    deltas: dict[str, float]
    baseline_hazard: dict[str, Any] | None
    scenario_hazard: dict[str, Any] | None
    hazard_deltas: dict[str, Any]
    authenticity: str = SCENARIO_AUTHENTICITY
    mode: str = "REAL"
    execution_time_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Route-compat attributes (existing /scenario/run handler reads these directly).
    @property
    def summary_statistics(self) -> dict[str, dict[str, float]]:
        return {
            "baseline": dict(self.baseline_state),
            "scenario": dict(self.scenario_state),
            "deltas": dict(self.deltas),
        }

    @property
    def time_steps(self) -> list[datetime]:
        try:
            return [datetime.fromisoformat(self.baseline_timestamp)]
        except ValueError:
            return [datetime.now(UTC)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "scenario_id": self.scenario_id,
            "definition": self.definition.to_dict(),
            "location_id": self.location_id,
            "baseline_twin_version": self.baseline_twin_version,
            "baseline_timestamp": self.baseline_timestamp,
            "baseline_state": self.baseline_state,
            "scenario_state": self.scenario_state,
            "deltas": self.deltas,
            "baseline_hazard": self.baseline_hazard,
            "scenario_hazard": self.scenario_hazard,
            "hazard_deltas": self.hazard_deltas,
            "authenticity": self.authenticity,
            "mode": self.mode,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioResult:
        return cls(
            result_id=data["result_id"],
            scenario_id=data["scenario_id"],
            definition=ScenarioDefinition.from_dict(data["definition"]),
            location_id=data["location_id"],
            baseline_twin_version=data.get("baseline_twin_version", ""),
            baseline_timestamp=data.get("baseline_timestamp", ""),
            baseline_state=data.get("baseline_state", {}),
            scenario_state=data.get("scenario_state", {}),
            deltas=data.get("deltas", {}),
            baseline_hazard=data.get("baseline_hazard"),
            scenario_hazard=data.get("scenario_hazard"),
            hazard_deltas=data.get("hazard_deltas", {}),
            authenticity=data.get("authenticity", SCENARIO_AUTHENTICITY),
            mode=data.get("mode", "REAL"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            created_at=data.get("created_at", ""),
        )


@dataclass(frozen=True)
class ScenarioComparison:
    """Comparison of a baseline result vs one scenario result."""

    comparison_id: str
    baseline_result_id: str
    scenario_result_id: str
    variable_deltas: dict[str, float]
    percentage_changes: dict[str, float]
    significant_variables: list[str]
    summary: str
    hazard_deltas: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "baseline_result_id": self.baseline_result_id,
            "scenario_result_id": self.scenario_result_id,
            "variable_deltas": self.variable_deltas,
            "percentage_changes": self.percentage_changes,
            "significant_variables": self.significant_variables,
            "summary": self.summary,
            "hazard_deltas": self.hazard_deltas,
        }


def compute_comparison_id(a_result_id: str, b_result_id: str) -> str:
    payload = {"baseline": a_result_id, "scenario": b_result_id}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"comp_{digest[:16]}"


def serialize_hazard(assessment: Any) -> dict[str, Any] | None:
    """Serialize a HazardAssessment to a JSON-safe dict (or None)."""
    if assessment is None:
        return None
    ha = assessment
    return {
        "assessment_id": getattr(ha, "assessment_id", ""),
        "location_id": getattr(ha, "location_id", ""),
        "hazard_type": getattr(ha, "hazard_type", "unknown"),
        "assessment_type": getattr(getattr(ha, "assessment_type", None), "value", "SCENARIO"),
        "severity": getattr(getattr(ha, "severity", None), "value", "NONE"),
        "hazard_score": getattr(ha, "hazard_score", 0.0),
        "assessment_confidence": getattr(ha, "assessment_confidence", 0.0),
        "data_quality": getattr(getattr(ha, "data_quality", None), "value", ""),
        "data_freshness": getattr(getattr(ha, "data_freshness", None), "value", ""),
        "method": getattr(ha, "method", ""),
        "method_version": getattr(ha, "method_version", ""),
        "config_version": getattr(ha, "config_version", ""),
        "source_twin_version": getattr(ha, "source_twin_version", ""),
        "thresholds_triggered": getattr(ha, "thresholds_triggered", []),
        "evidence": [
            {
                "factor": getattr(e, "factor", ""),
                "value": getattr(e, "value", 0.0),
                "unit": getattr(e, "unit", ""),
                "effect": getattr(e, "effect", 0.0),
            }
            for e in getattr(ha, "evidence", []) or []
        ],
        "provenance": getattr(ha, "provenance", {}),
    }
