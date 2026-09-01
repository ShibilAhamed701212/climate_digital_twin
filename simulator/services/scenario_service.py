"""Integration service connecting the Scenario Engine with the Digital Twin."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from simulator.engine.scenario_engine import ScenarioEngine
from simulator.engine.twin_engine import DigitalTwinEngine
from simulator.events.event_bus import EventBus
from simulator.events.events import TwinEvent
from simulator.models.scenario_models import ScenarioDefinition, ScenarioRun
from simulator.scenarios.scenario_builder import (
    create_scenario,
    get_preset_scenario,
    list_preset_scenarios,
)
from simulator.validators.scenario_validator import validate_scenario_parameters

logger = logging.getLogger(__name__)


class ScenarioService:
    """High-level service for scenario creation, simulation, and integration."""

    def __init__(
        self,
        twin_engine: DigitalTwinEngine,
        scenario_engine: ScenarioEngine | None = None,
    ) -> None:
        self.twin = twin_engine
        self.scenario_engine = scenario_engine or ScenarioEngine()
        self.event_bus: EventBus = twin_engine.event_bus
        self._scenarios: dict[str, ScenarioDefinition] = {}

    def create_scenario(
        self,
        scenario_id: str | None = None,
        name: str = "",
        description: str = "",
        scenario_type: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> ScenarioDefinition:
        """Create a new scenario, validate it, and store it."""
        existing = [s for s in self._scenarios.values() if s.scenario_id == scenario_id]
        event_type = "ScenarioUpdated" if existing else "ScenarioCreated"

        scenario = create_scenario(
            scenario_id=scenario_id,
            name=name,
            description=description,
            scenario_type=scenario_type,
            parameters=parameters,
        )
        self._scenarios[scenario.scenario_id] = scenario

        self.event_bus.publish(
            TwinEvent(
                event_type=event_type,
                location_id="*",
                timestamp=datetime.now().isoformat(),
                version_id=0,
                data={"scenario_id": scenario.scenario_id, "name": scenario.name},
            )
        )
        logger.info("Scenario %s: %s", event_type, scenario.scenario_id)
        return scenario

    def validate_scenario(self, scenario_type: str, parameters: dict[str, Any]) -> list[str]:
        """Validate scenario parameters without creating a scenario."""
        return validate_scenario_parameters(scenario_type, parameters)

    def run_simulation(
        self,
        scenario_id: str,
        location_ids: list[str] | None = None,
    ) -> ScenarioRun:
        """Run a scenario simulation across twin locations."""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            scenario = get_preset_scenario(scenario_id)
        if scenario is None:
            raise ValueError(f"Scenario not found: {scenario_id}")

        self.event_bus.publish(
            TwinEvent(
                event_type="SimulationStarted",
                location_id="*",
                timestamp=datetime.now().isoformat(),
                version_id=0,
                data={"scenario_id": scenario_id},
            )
        )

        baseline_data = self._collect_baseline(location_ids)
        run = self.scenario_engine.run_simulation(scenario, baseline_data)
        if scenario.scenario_type == "post_disaster_recovery":
            import json

            from climatedt.disaster.client import DisasterHttpClient

            assessment_id = str(scenario.parameters.get("assessment_id") or "")
            payload: dict[str, Any] = {"available": False}
            if assessment_id and assessment_id != "pending":
                fetched = DisasterHttpClient().assessment(assessment_id)
                if fetched:
                    payload = {"available": True, "assessment": fetched}
            merged = {**dict(scenario.parameters), "disaster_assessment_json": json.dumps(payload)}
            object.__setattr__(run.scenario, "parameters", merged)

        # Isolation: simulated scenario states are NEVER persisted into the
        # twin repository.  Results stay in-memory in the ScenarioRun; the
        # authoritative REAL twin (and the demo twin store) are untouched.
        logger.info(
            "Scenario %s simulated in-memory for %d locations; no twin writes",
            scenario_id,
            run.location_count,
        )

        self.event_bus.publish(
            TwinEvent(
                event_type="SimulationCompleted",
                location_id="*",
                timestamp=datetime.now().isoformat(),
                version_id=0,
                data={
                    "scenario_id": scenario_id,
                    "run_id": run.run_id,
                    "locations": run.location_count,
                    "duration_ms": run.total_duration_ms,
                },
            )
        )

        logger.info(
            "Simulation %s completed: %d locations in %.2fms",
            run.run_id,
            run.location_count,
            run.total_duration_ms,
        )
        return run

    def compare_with_baseline(self, run: ScenarioRun) -> list[dict[str, Any]]:
        """Generate comparison summaries for a simulation run."""
        return self.scenario_engine.compare_with_baseline(run)

    def list_scenarios(self) -> list[dict[str, Any]]:
        """List all available scenarios (preset + custom)."""
        custom = [s.to_dict() for s in self._scenarios.values()]
        preset = list_preset_scenarios()
        return preset + custom

    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete a custom scenario by ID."""
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            self.event_bus.publish(
                TwinEvent(
                    event_type="ScenarioDeleted",
                    location_id="*",
                    timestamp=datetime.now().isoformat(),
                    version_id=0,
                    data={"scenario_id": scenario_id},
                )
            )
            logger.info("Scenario deleted: %s", scenario_id)
            return True
        return False

    def _collect_baseline(self, location_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Collect baseline current states from the twin."""
        if hasattr(self.twin, "reload_from_repository"):
            self.twin.reload_from_repository()
        all_locations = self.twin.service.state_manager.get_all_location_ids()
        if location_ids:
            ids = [lid for lid in location_ids if lid in all_locations]
        else:
            ids = list(all_locations)

        if not ids:
            raise ValueError("No locations available in the digital twin. Seed the twin first.")

        baseline: list[dict[str, Any]] = []
        for loc_id in ids:
            state = self.twin.get_current_state(loc_id)
            if state:
                baseline.append(state)
            else:
                logger.warning("No current state found for %s, skipping", loc_id)
        return baseline
