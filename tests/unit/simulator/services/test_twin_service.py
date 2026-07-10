"""Unit tests for simulator/services/twin_service.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from simulator.entities.climate_entity import ClimateEntity
from simulator.entities.state import StateType


class TestTwinService:
    @pytest.fixture
    def service(self):
        state_manager = MagicMock()
        repository = MagicMock()
        event_bus = MagicMock()
        with (
            patch("builtins.open", MagicMock()),
            patch("simulator.services.twin_service.yaml.safe_load", return_value={}),
        ):
            from simulator.services.twin_service import TwinService

            return TwinService(state_manager, repository, event_bus, config_path="ignored")

    def test_validate_entity_lat_outside_bounds(self, service):
        entity = MagicMock(spec=ClimateEntity)
        entity.validate.return_value = []
        entity.latitude = 20.0
        entity.longitude = 76.0
        errors = service._validate_entity(entity)
        assert any("Latitude outside Karnataka bounds" in e for e in errors)

    def test_validate_entity_lon_outside_bounds(self, service):
        entity = MagicMock(spec=ClimateEntity)
        entity.validate.return_value = []
        entity.latitude = 15.0
        entity.longitude = 80.0
        errors = service._validate_entity(entity)
        assert any("Longitude outside Karnataka bounds" in e for e in errors)

    def test_apply_forecast_invalid(self, service):
        entity = MagicMock(spec=ClimateEntity)
        entity.validate.return_value = ["invalid data"]
        entity.latitude = 12.97
        entity.longitude = 77.59
        with pytest.raises(ValueError, match="Invalid forecast"):
            service.apply_forecast(entity)

    def test_apply_scenario_invalid(self, service):
        entity = MagicMock(spec=ClimateEntity)
        entity.validate.return_value = ["invalid data"]
        entity.latitude = 12.97
        entity.longitude = 77.59
        with pytest.raises(ValueError, match="Invalid scenario"):
            service.apply_scenario(entity, "scenario_1")

    def test_update_risk_score_no_state(self, service):
        with patch.object(service, "get_current_state", return_value=None):
            with pytest.raises(ValueError, match="No current state for loc1"):
                service.update_risk_score("loc1", 0.5)

    def test_get_historical_state(self, service):
        v1 = MagicMock()
        v1.entity_data = {"temp": 25.0}
        v2 = MagicMock()
        v2.entity_data = {"temp": 26.0}
        service.repository.load_versions.return_value = [v1, v2]
        result = service.get_historical_state("loc1")
        assert result == [{"temp": 25.0}, {"temp": 26.0}]

    def test_get_forecast_state_no_forecast(self, service):
        v1 = MagicMock()
        v1.state_type = StateType.CURRENT.value
        service.repository.load_versions.return_value = [v1]
        result = service.get_forecast_state("loc1")
        assert result is None
