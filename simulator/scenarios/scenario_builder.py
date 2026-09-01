"""Scenario definitions and builders for the Scenario Simulation Engine."""

from __future__ import annotations

import uuid
from typing import Any

from simulator.models.scenario_models import ScenarioDefinition
from simulator.validators.scenario_validator import validate_scenario_parameters

PRESET_SCENARIOS: dict[str, dict[str, Any]] = {
    "temp_plus_1": {
        "name": "Temperature +1°C",
        "description": "Raises temperature by 1°C across all locations",
        "scenario_type": "temperature",
        "parameters": {"temperature_delta": 1.0},
    },
    "temp_plus_2": {
        "name": "Temperature +2°C",
        "description": "Raises temperature by 2°C across all locations",
        "scenario_type": "temperature",
        "parameters": {"temperature_delta": 2.0},
    },
    "temp_minus_1": {
        "name": "Temperature -1°C",
        "description": "Lowers temperature by 1°C across all locations",
        "scenario_type": "temperature",
        "parameters": {"temperature_delta": -1.0},
    },
    "rain_plus_10": {
        "name": "Rainfall +10%",
        "description": "Increases rainfall by 10% across all locations",
        "scenario_type": "rainfall",
        "parameters": {"rainfall_change_pct": 10.0},
    },
    "rain_plus_40": {
        "name": "Rainfall +40%",
        "description": "Increases rainfall by 40% across all locations",
        "scenario_type": "rainfall",
        "parameters": {"rainfall_change_pct": 40.0},
    },
    "rain_minus_25": {
        "name": "Rainfall -25%",
        "description": "Reduces rainfall by 25% across all locations",
        "scenario_type": "rainfall",
        "parameters": {"rainfall_change_pct": -25.0},
    },
    "monsoon_delayed_15": {
        "name": "Monsoon Delayed 15 Days",
        "description": "Delays monsoon onset by 15 days with 20% intensity reduction",
        "scenario_type": "monsoon",
        "parameters": {"delay_days": 15, "intensity_reduction_pct": 20.0},
    },
    "monsoon_early_7": {
        "name": "Monsoon Early 7 Days",
        "description": "Advances monsoon onset by 7 days",
        "scenario_type": "monsoon",
        "parameters": {"delay_days": -7, "intensity_reduction_pct": 0.0},
    },
    "extreme_heat": {
        "name": "Extreme Heat Day",
        "description": "Simulates a single hot day with temperature 5degC above baseline",
        "scenario_type": "extreme_event",
        "parameters": {"event_type": "heatwave", "temperature_delta": 5.0, "duration_days": 1},
    },
    "extreme_rainfall": {
        "name": "Extreme Rainfall",
        "description": "Simulates a heavy rainfall event with 200% normal precipitation",
        "scenario_type": "extreme_event",
        "parameters": {"event_type": "flood", "rainfall_change_pct": 200.0, "duration_days": 5},
    },
    "dry_spell": {
        "name": "Dry Spell",
        "description": "Simulates a dry spell with 80% reduction in rainfall",
        "scenario_type": "extreme_event",
        "parameters": {"event_type": "drought", "rainfall_change_pct": -80.0, "duration_days": 30},
    },
    "post_disaster_recovery": {
        "name": "Post-disaster recovery",
        "description": "Reads DIE assessment KPIs as exogenous recovery inputs (climate physics unchanged)",
        "scenario_type": "post_disaster_recovery",
        "parameters": {"assessment_id": "pending", "rainfall_change_pct": 0.0},
    },
}


def create_scenario(
    scenario_id: str | None = None,
    name: str = "",
    description: str = "",
    scenario_type: str = "",
    parameters: dict[str, Any] | None = None,
) -> ScenarioDefinition:
    """Create a new scenario definition with validation."""
    if not scenario_id:
        scenario_id = f"scenario_{uuid.uuid4().hex[:8]}"
    params = parameters or {}

    errors = validate_scenario_parameters(scenario_type, params)
    if errors:
        raise ValueError(f"Invalid scenario parameters: {errors}")

    return ScenarioDefinition(
        scenario_id=scenario_id,
        name=name or scenario_id,
        description=description or f"Scenario: {scenario_type}",
        scenario_type=scenario_type,
        parameters=params,
    )


def list_preset_scenarios() -> list[dict[str, Any]]:
    """Return all preset scenario definitions."""
    return [
        {
            "scenario_id": sid,
            **data,
        }
        for sid, data in PRESET_SCENARIOS.items()
    ]


def get_preset_scenario(scenario_id: str) -> ScenarioDefinition | None:
    """Get a preset scenario by ID."""
    data = PRESET_SCENARIOS.get(scenario_id)
    if data is None:
        return None
    return create_scenario(
        scenario_id=scenario_id,
        **data,
    )
