"""Unit tests for simulator/api/contract.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from simulator.api.contract import TwinAPI
from simulator.entities.climate_entity import ClimateEntity


class TestTwinAPI:
    def test_get_current_state_body(self):
        assert TwinAPI.get_current_state(None, None) is None

    def test_get_historical_state_body(self):
        assert TwinAPI.get_historical_state(None, None) is None

    def test_get_forecast_state_body(self):
        assert TwinAPI.get_forecast_state(None, None) is None

    def test_apply_scenario_body(self):
        assert TwinAPI.apply_scenario(None, None) is None

    def test_rollback_body(self):
        assert TwinAPI.rollback(None, None) is None

    def test_get_state_history_body(self):
        assert TwinAPI.get_state_history(None, None) is None


class TestTwinEngineAdapter:
    @pytest.fixture
    def mock_engine(self):
        return MagicMock()

    @pytest.fixture
    def adapter(self, mock_engine):
        from simulator.api.contract import TwinEngineAdapter

        return TwinEngineAdapter(mock_engine)

    def test_init_stores_engine(self, mock_engine):
        from simulator.api.contract import TwinEngineAdapter

        adapter = TwinEngineAdapter(mock_engine)
        assert adapter._engine is mock_engine

    def test_get_current_state(self, adapter, mock_engine):
        expected = {"location_id": "LOC-001", "rainfall": 10.0}
        mock_engine.get_current_state.return_value = expected

        result = adapter.get_current_state("LOC-001")

        assert result == expected
        mock_engine.get_current_state.assert_called_once_with("LOC-001")

    def test_get_current_state_none(self, adapter, mock_engine):
        mock_engine.get_current_state.return_value = None

        result = adapter.get_current_state("UNKNOWN")

        assert result is None

    def test_get_historical_state(self, adapter, mock_engine):
        expected = [{"location_id": "LOC-001", "rainfall": 10.0}]
        mock_engine.get_historical_state.return_value = expected

        result = adapter.get_historical_state("LOC-001")

        assert result == expected
        mock_engine.get_historical_state.assert_called_once_with("LOC-001", None)

    def test_get_historical_state_with_time_range(self, adapter, mock_engine):
        expected = [{"location_id": "LOC-001"}]
        mock_engine.get_historical_state.return_value = expected

        result = adapter.get_historical_state("LOC-001", "2024-01-01/2024-12-31")

        assert result == expected
        mock_engine.get_historical_state.assert_called_once_with("LOC-001", "2024-01-01/2024-12-31")

    def test_get_historical_state_empty(self, adapter, mock_engine):
        mock_engine.get_historical_state.return_value = []

        result = adapter.get_historical_state("LOC-002")

        assert result == []

    def test_get_forecast_state(self, adapter, mock_engine):
        expected = {"location_id": "LOC-001", "rainfall": 15.0}
        mock_engine.get_forecast_state.return_value = expected

        result = adapter.get_forecast_state("LOC-001")

        assert result == expected
        mock_engine.get_forecast_state.assert_called_once_with("LOC-001", None)

    def test_get_forecast_state_with_horizon(self, adapter, mock_engine):
        expected = {"location_id": "LOC-001"}
        mock_engine.get_forecast_state.return_value = expected

        result = adapter.get_forecast_state("LOC-001", "7d")

        assert result == expected
        mock_engine.get_forecast_state.assert_called_once_with("LOC-001", "7d")

    def test_get_forecast_state_none(self, adapter, mock_engine):
        mock_engine.get_forecast_state.return_value = None

        result = adapter.get_forecast_state("UNKNOWN")

        assert result is None

    def test_apply_scenario(self, adapter, mock_engine):
        scenario_params = {
            "entity": {
                "location_id": "LOC-001",
                "latitude": 12.34,
                "longitude": 56.78,
                "rainfall": 200.0,
                "max_temp": 35.0,
            },
            "scenario_id": "scenario_001",
        }
        expected = {"status": "applied", "scenario_id": "scenario_001"}
        mock_engine.apply_scenario.return_value = expected

        result = adapter.apply_scenario(scenario_params)

        assert result == expected
        call_args = mock_engine.apply_scenario.call_args
        assert call_args is not None
        entity_arg, scenario_id_arg = call_args[0]
        assert isinstance(entity_arg, ClimateEntity)
        assert entity_arg.location_id == "LOC-001"
        assert entity_arg.latitude == 12.34
        assert entity_arg.longitude == 56.78
        assert entity_arg.rainfall == 200.0
        assert entity_arg.max_temp == 35.0
        assert scenario_id_arg == "scenario_001"

    def test_apply_scenario_default_scenario_id(self, adapter, mock_engine):
        scenario_params = {
            "entity": {
                "location_id": "LOC-001",
                "latitude": 12.34,
                "longitude": 56.78,
            },
        }
        mock_engine.apply_scenario.return_value = {}

        adapter.apply_scenario(scenario_params)

        call_args = mock_engine.apply_scenario.call_args
        assert call_args is not None
        _, scenario_id_arg = call_args[0]
        assert scenario_id_arg == "unknown"

    def test_apply_scenario_missing_entity_raises(self, adapter):
        with pytest.raises(TypeError):
            adapter.apply_scenario({"scenario_id": "s1"})

    def test_rollback(self, adapter, mock_engine):
        expected = {"status": "rolled_back", "version": 5}
        mock_engine.rollback.return_value = expected

        result = adapter.rollback(5)

        assert result == expected
        mock_engine.rollback.assert_called_once_with("", 5)

    def test_get_state_history(self, adapter, mock_engine):
        expected = [{"version": 1}, {"version": 2}]
        mock_engine.get_state_history.return_value = expected

        result = adapter.get_state_history("LOC-001")

        assert result == expected
        mock_engine.get_state_history.assert_called_once_with("LOC-001")

    def test_get_state_history_empty(self, adapter, mock_engine):
        mock_engine.get_state_history.return_value = []

        result = adapter.get_state_history("LOC-003")

        assert result == []
