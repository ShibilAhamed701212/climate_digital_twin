"""Unit tests for simulator/services/."""

from pathlib import Path

import pytest
import yaml

from simulator.entities.climate_entity import ClimateEntity
from simulator.events.event_bus import EventBus
from simulator.repository.parquet_repository import ParquetRepository
from simulator.services.twin_service import TwinService
from simulator.state_manager.manager import StateManager


@pytest.fixture
def service(tmp_path: Path) -> TwinService:
    state_manager = StateManager()
    repository = ParquetRepository(store_dir=str(tmp_path / "twin_store"))
    event_bus = EventBus()
    config_path = tmp_path / "twin_config.yaml"
    config = {
        "twin": {"name": "test_twin", "version": "1.0", "region": "Karnataka"},
        "state": {
            "validate_coordinates": False,
            "validate_temperatures": {"min": -10, "max": 55},
            "validate_rainfall": {"min": 0, "max": 2000},
        },
        "events": {"enabled": True, "max_subscribers": 50},
    }
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    return TwinService(state_manager, repository, event_bus, str(config_path))


class TestTwinService:
    def test_update_observation(self, service: TwinService):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=50.0,
            max_temp=32.0,
            min_temp=20.0,
        )
        result = service.update_observation(entity)
        assert result["version_id"] == 1
        assert result["location_id"] == "KA-BLR-001"

    def test_apply_forecast(self, service: TwinService):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=60.0,
            max_temp=30.0,
            min_temp=19.0,
            prediction_confidence=0.85,
        )
        result = service.apply_forecast(entity)
        assert result["version_id"] == 1

    def test_apply_scenario(self, service: TwinService):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=80.0,
            max_temp=35.0,
            min_temp=22.0,
        )
        result = service.apply_scenario(entity, "temp_plus_2")
        assert result["version_id"] == 1

    def test_update_risk_score(self, service: TwinService):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
        )
        service.update_observation(entity)
        result = service.update_risk_score("KA-BLR-001", 75.0)
        assert result["version_id"] == 2

    def test_get_current_state(self, service: TwinService):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=45.0,
        )
        service.update_observation(entity)
        state = service.get_current_state("KA-BLR-001")
        assert state is not None
        assert state["rainfall"] == 45.0

    def test_get_current_state_nonexistent(self, service: TwinService):
        assert service.get_current_state("NONEXISTENT") is None

    def test_get_forecast_state(self, service: TwinService):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=55.0,
            prediction_confidence=0.9,
        )
        service.apply_forecast(entity)
        forecast = service.get_forecast_state("KA-BLR-001")
        assert forecast is not None
        assert forecast["rainfall"] == 55.0

    def test_rollback(self, service: TwinService):
        e = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59, rainfall=10)
        service.update_observation(e)
        e2 = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59, rainfall=50)
        service.update_observation(e2)
        result = service.rollback("KA-BLR-001", 1)
        assert result["version_id"] == 3  # new version created

    def test_get_state_history(self, service: TwinService):
        for r in [10, 20, 30]:
            e = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59, rainfall=r)
            service.update_observation(e)
        history = service.get_state_history("KA-BLR-001")
        assert len(history) == 3

    def test_rejects_invalid_observation(self, service: TwinService):
        invalid = ClimateEntity(
            location_id="KA-BLR-001", latitude=12.97, longitude=77.59, rainfall=-100
        )
        with pytest.raises(ValueError):
            service.update_observation(invalid)

    def test_event_published_on_observation(self, service: TwinService):
        events = []
        service.event_bus.subscribe("ObservationUpdated", lambda e: events.append(e))
        e = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59, rainfall=25)
        service.update_observation(e)
        assert len(events) == 1
        assert events[0].event_type == "ObservationUpdated"
