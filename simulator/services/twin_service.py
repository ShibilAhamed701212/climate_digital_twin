"""Service layer — business logic for the Digital Twin.

Connects the API layer to the engine, state manager, repository, and event bus.
"""

import logging
from typing import Any

import yaml

from simulator.entities.climate_entity import ClimateEntity
from simulator.entities.state import StateType
from simulator.events.event_bus import EventBus
from simulator.events.events import TwinEvent
from simulator.repository.base import TwinRepository
from simulator.state_manager.manager import StateManager

logger = logging.getLogger(__name__)


class TwinService:
    """High-level service for Digital Twin operations.

    Coordinates between the StateManager, Repository, and EventBus.
    """

    def __init__(
        self,
        state_manager: StateManager,
        repository: TwinRepository,
        event_bus: EventBus,
        config_path: str = "simulator/configs/twin_config.yaml",
    ) -> None:
        self.state_manager = state_manager
        self.repository = repository
        self.event_bus = event_bus
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def _validate_entity(self, entity: ClimateEntity) -> list[str]:
        errors = entity.validate()
        cfg = self.config.get("state", {})
        if cfg.get("validate_coordinates", True):
            bounds = {"lat": (11.5, 18.5), "lon": (74.0, 78.5)}
            if not (bounds["lat"][0] <= entity.latitude <= bounds["lat"][1]):
                errors.append(f"Latitude outside Karnataka bounds: {entity.latitude}")
            if not (bounds["lon"][0] <= entity.longitude <= bounds["lon"][1]):
                errors.append(f"Longitude outside Karnataka bounds: {entity.longitude}")
        return errors

    def update_observation(self, entity: ClimateEntity) -> dict[str, Any]:
        """Ingest a new observation from authoritative data sources."""
        entity.state_type = StateType.CURRENT.value
        entity.data_source = "IMD"
        errors = self._validate_entity(entity)
        if errors:
            raise ValueError(f"Invalid observation: {errors}")
        version = self.state_manager.create_version(entity)
        self.repository.save_version(version)
        self.event_bus.publish(
            TwinEvent(
                event_type="ObservationUpdated",
                location_id=entity.location_id,
                timestamp=entity.timestamp,
                version_id=version.version_id,
                data={"state_type": "current"},
            )
        )
        logger.info(
            "Observation updated for %s (v%d)",
            entity.location_id,
            version.version_id,
        )
        return {"version_id": version.version_id, "location_id": entity.location_id}

    def apply_forecast(self, entity: ClimateEntity) -> dict[str, Any]:
        """Apply a forecast from Phase 3 to the twin state."""
        entity.state_type = StateType.FORECAST.value
        entity.data_source = "forecast"
        errors = self._validate_entity(entity)
        if errors:
            raise ValueError(f"Invalid forecast: {errors}")
        version = self.state_manager.create_version(entity)
        self.repository.save_version(version)
        self.event_bus.publish(
            TwinEvent(
                event_type="ForecastGenerated",
                location_id=entity.location_id,
                timestamp=entity.timestamp,
                version_id=version.version_id,
                data={
                    "state_type": "forecast",
                    "confidence": entity.prediction_confidence,
                },
            )
        )
        return {"version_id": version.version_id, "location_id": entity.location_id}

    def apply_scenario(self, entity: ClimateEntity, scenario_id: str) -> dict[str, Any]:
        """Apply a what-if scenario to the twin state.

        Isolation guard: scenario/synthetic/demo state must never be persisted
        into the twin repository.  Entities explicitly marked with a non-REAL
        authenticity are hard-rejected.  (Bare entities without an authenticity
        marker keep legacy behavior.)
        """
        entity.state_type = StateType.SCENARIO.value
        entity.data_source = "scenario"
        entity.scenario_id = scenario_id
        errors = self._validate_entity(entity)
        if errors:
            raise ValueError(f"Invalid scenario: {errors}")
        authenticity = getattr(entity, "authenticity", "") or ""
        if authenticity.upper() in ("SCENARIO", "SYNTHETIC", "DEMO"):
            raise ValueError(
                f"Refusing to persist non-REAL '{authenticity}' scenario state "
                f"into the twin repository"
            )
        version = self.state_manager.create_version(entity)
        self.repository.save_version(version)
        self.event_bus.publish(
            TwinEvent(
                event_type="ScenarioApplied",
                location_id=entity.location_id,
                timestamp=entity.timestamp,
                version_id=version.version_id,
                data={"scenario_id": scenario_id},
            )
        )
        return {"version_id": version.version_id, "location_id": entity.location_id}

    def update_risk_score(self, location_id: str, risk_score: float) -> dict[str, Any]:
        """Update the climate risk score for a location."""
        current_data = self.get_current_state(location_id)
        if current_data is None:
            raise ValueError(f"No current state for {location_id}")
        entity = ClimateEntity.deserialize(current_data)
        entity.risk_score = risk_score
        entity.state_type = StateType.CURRENT.value
        entity.data_source = "risk_analysis"
        version = self.state_manager.create_version(entity)
        self.repository.save_version(version)
        self.event_bus.publish(
            TwinEvent(
                event_type="RiskUpdated",
                location_id=location_id,
                timestamp=entity.timestamp,
                version_id=version.version_id,
                data={"risk_score": risk_score},
            )
        )
        return {"version_id": version.version_id, "location_id": location_id}

    def get_current_state(self, location_id: str) -> dict[str, Any] | None:
        """Get the current (latest observation) state for a location."""
        versions = self.repository.load_versions(location_id)
        current = [v for v in versions if v.state_type == StateType.CURRENT.value]
        if not current:
            return None
        return max(current, key=lambda v: v.version_id).entity_data

    def get_historical_state(
        self,
        location_id: str,
        time_range: str | None = None,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Get historical states for a location."""
        versions = self.repository.load_versions(location_id)
        return [v.entity_data for v in versions]

    def get_forecast_state(
        self,
        location_id: str,
        horizon: str | None = None,  # noqa: ARG002
    ) -> dict[str, Any] | None:
        """Get the latest forecast state for a location."""
        versions = self.repository.load_versions(location_id)
        forecast_versions = [v for v in versions if v.state_type == StateType.FORECAST.value]
        if not forecast_versions:
            return None
        return max(forecast_versions, key=lambda v: v.version_id).entity_data

    def rollback(self, location_id: str, version_id: int) -> dict[str, Any]:
        """Rollback to a specific version."""
        new_version = self.state_manager.rollback(location_id, version_id)
        self.repository.save_version(new_version)
        return {"version_id": new_version.version_id, "location_id": location_id}

    def get_state_history(self, location_id: str) -> list[dict[str, Any]]:
        """Get the complete state history for a location."""
        versions = self.repository.load_versions(location_id)
        return [
            {
                "version_id": v.version_id,
                "timestamp": v.timestamp,
                "state_type": v.state_type,
            }
            for v in versions
        ]
