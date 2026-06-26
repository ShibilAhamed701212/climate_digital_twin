"""Scenario data models and schemas for the Scenario Simulation Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ScenarioDefinition:
    """Immutable definition of a climate scenario."""

    scenario_id: str
    name: str
    description: str
    scenario_type: str
    parameters: dict[str, float | int | str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type,
            "parameters": dict(self.parameters),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SimulationResult:
    """Result of a single scenario simulation."""

    location_id: str
    scenario_id: str
    timestamp: str
    baseline: dict[str, Any]
    simulated: dict[str, Any]
    deltas: dict[str, float]
    duration_ms: float
    success: bool
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
            "baseline": self.baseline,
            "simulated": self.simulated,
            "deltas": self.deltas,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class ScenarioRun:
    """Complete record of a scenario simulation run across locations."""

    run_id: str
    scenario: ScenarioDefinition
    results: list[SimulationResult]
    started_at: str
    completed_at: str
    total_duration_ms: float
    location_count: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario": self.scenario.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "location_count": self.location_count,
            "status": self.status,
        }
