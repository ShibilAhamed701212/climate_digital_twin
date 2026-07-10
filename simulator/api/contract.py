"""Internal API contracts/interfaces for the Digital Twin.

Defines the standardized API contract that all downstream modules use.
"""

from abc import ABC, abstractmethod
from typing import Any


class TwinAPI(ABC):
    """Standardized API contract for the Digital Twin.

    All downstream modules (dashboard, scenario engine, risk, copilot)
    interact with the twin exclusively through this interface.
    """

    @abstractmethod
    def get_current_state(self, location_id: str) -> dict[str, Any] | None:
        """Get the current (latest observed) state for a location."""
        ...

    @abstractmethod
    def get_historical_state(
        self, location_id: str, time_range: str | None = None
    ) -> list[dict[str, Any]]:
        """Get historical states for a location within an optional time range."""
        ...

    @abstractmethod
    def get_forecast_state(
        self, location_id: str, horizon: str | None = None
    ) -> dict[str, Any] | None:
        """Get the forecast state for a location with an optional horizon."""
        ...

    @abstractmethod
    def apply_scenario(
        self, scenario_parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply a scenario simulation and return the result."""
        ...

    @abstractmethod
    def rollback(self, version_id: int) -> dict[str, Any]:
        """Rollback the twin to a specific version."""
        ...

    @abstractmethod
    def get_state_history(
        self, location_id: str
    ) -> list[dict[str, Any]]:
        """Get the complete version history for a location."""
        ...


class TwinEngineAdapter(TwinAPI):
    """Adapter that wraps DigitalTwinEngine to satisfy the TwinAPI contract.

    Used by dashboard, scenario engine, risk, and copilot modules
    to interact with the digital twin.
    """

    def __init__(self, engine: Any) -> None:
        from simulator.engine.twin_engine import DigitalTwinEngine
        self._engine: DigitalTwinEngine = engine

    def get_current_state(self, location_id: str) -> dict[str, Any] | None:
        return self._engine.get_current_state(location_id)

    def get_historical_state(
        self, location_id: str, time_range: str | None = None
    ) -> list[dict[str, Any]]:
        return self._engine.get_historical_state(location_id, time_range)

    def get_forecast_state(
        self, location_id: str, horizon: str | None = None
    ) -> dict[str, Any] | None:
        return self._engine.get_forecast_state(location_id, horizon)

    def apply_scenario(
        self, scenario_parameters: dict[str, Any]
    ) -> dict[str, Any]:
        entity_data = scenario_parameters.get("entity", {})
        scenario_id = scenario_parameters.get("scenario_id", "unknown")
        from simulator.entities.climate_entity import ClimateEntity
        entity = ClimateEntity.deserialize(entity_data)
        return self._engine.apply_scenario(entity, scenario_id)

    def rollback(self, version_id: int) -> dict[str, Any]:
        return self._engine.rollback("", version_id)

    def get_state_history(
        self, location_id: str
    ) -> list[dict[str, Any]]:
        return self._engine.get_state_history(location_id)
