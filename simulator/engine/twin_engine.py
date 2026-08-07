"""Digital Twin Engine — central orchestration for the Digital Twin.

Coordinates entity lifecycle, state management, persistence,
event publishing, and downstream API exposure.
"""

import logging
from typing import Any

import yaml

from simulator.entities.climate_entity import ClimateEntity
from simulator.events.event_bus import EventBus
from simulator.events.events import TwinEvent
from simulator.repository.base import TwinRepository
from simulator.repository.parquet_repository import ParquetRepository
from simulator.services.twin_service import TwinService
from simulator.state_manager.manager import StateManager

logger = logging.getLogger(__name__)


class DigitalTwinEngine:
    """Central orchestrator for the Digital Twin.

    Wires together StateManager, Repository, EventBus, and TwinService.
    Exposes a unified interface for all Digital Twin operations.
    """

    def __init__(
        self,
        config_path: str = "simulator/configs/twin_config.yaml",
        store_dir: str = "data/twin_store",
    ) -> None:
        self.config_path = config_path
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.repository: TwinRepository = ParquetRepository(store_dir)
        self.service = TwinService(self.state_manager, self.repository, self.event_bus, config_path)
        self._load_from_repository()

    def _load_from_repository(self) -> None:
        """Rehydrate state manager from persistent storage."""
        location_ids = self.repository.load_all_location_ids()
        for loc_id in location_ids:
            latest = self.repository.load_latest_version(loc_id)
            if latest is not None:
                self.state_manager._versions[loc_id] = self.repository.load_versions(loc_id)
                self.state_manager._current[loc_id] = latest
        if location_ids:
            logger.info("Loaded %d locations from repository", len(location_ids))

    def create_entity(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        district: str = "",
    ) -> ClimateEntity:
        """Create a new ClimateEntity instance."""
        return ClimateEntity(
            location_id=location_id,
            latitude=latitude,
            longitude=longitude,
            district=district,
        )

    def ingest_observation(self, entity: ClimateEntity) -> dict[str, Any]:
        """Ingest a new observation (Current State)."""
        return self.service.update_observation(entity)

    def apply_forecast(self, entity: ClimateEntity) -> dict[str, Any]:
        """Apply a forecast prediction (Forecast State)."""
        return self.service.apply_forecast(entity)

    def apply_scenario(self, entity: ClimateEntity, scenario_id: str) -> dict[str, Any]:
        """Apply a scenario simulation (Scenario State)."""
        return self.service.apply_scenario(entity, scenario_id)

    def update_risk(self, location_id: str, risk_score: float) -> dict[str, Any]:
        """Update the risk score for a location."""
        return self.service.update_risk_score(location_id, risk_score)

    def get_current_state(self, location_id: str) -> dict[str, Any] | None:
        """Get current state for a location."""
        return self.service.get_current_state(location_id)

    def get_historical_state(
        self, location_id: str, time_range: str | None = None
    ) -> list[dict[str, Any]]:
        """Get historical states for a location."""
        return self.service.get_historical_state(location_id, time_range)

    def get_forecast_state(
        self, location_id: str, horizon: str | None = None
    ) -> dict[str, Any] | None:
        """Get forecast state for a location."""
        return self.service.get_forecast_state(location_id, horizon)

    def rollback(self, location_id: str, version_id: int) -> dict[str, Any]:
        """Rollback to a specific version."""
        return self.service.rollback(location_id, version_id)

    def get_state_history(self, location_id: str) -> list[dict[str, Any]]:
        """Get state history for a location."""
        return self.service.get_state_history(location_id)

    def refresh_twin(self) -> None:
        """Publish a TwinRefreshed event to all subscribers."""
        self.event_bus.publish(
            TwinEvent(
                event_type="TwinRefreshed",
                location_id="*",
                timestamp=__import__("datetime").datetime.now().isoformat(),
                version_id=0,
                data={"locations": self.state_manager.get_all_location_ids()},
            )
        )
        logger.info("Twin refresh event published")
