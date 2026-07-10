"""Unit tests for simulator/services/scenario_service.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from simulator.models.scenario_models import ScenarioDefinition, ScenarioRun, SimulationResult


class TestScenarioService:
    @pytest.fixture
    def mock_twin_engine(self):
        engine = MagicMock()
        engine.event_bus = MagicMock()
        engine.service.state_manager.get_all_location_ids.return_value = {"KA-BLR-001"}
        engine.get_current_state.return_value = {
            "location_id": "KA-BLR-001",
            "rainfall": 100.0,
            "max_temp": 32.0,
            "min_temp": 20.0,
        }
        return engine

    @pytest.fixture
    def mock_scenario_engine(self):
        engine = MagicMock()
        return engine

    @pytest.fixture
    def service(self, mock_twin_engine, mock_scenario_engine):
        from simulator.services.scenario_service import ScenarioService

        return ScenarioService(mock_twin_engine, mock_scenario_engine)

    def test_init(self, mock_twin_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine)
        assert svc.twin is mock_twin_engine
        assert svc.scenario_engine is not None

    def test_create_scenario(self, service):
        s = service.create_scenario(
            scenario_id="test_001",
            name="Test",
            description="A test scenario",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        assert s.scenario_id == "test_001"
        assert s.name == "Test"
        assert s.scenario_type == "temperature"
        assert s.parameters["temperature_delta"] == 2.0
        assert "test_001" in service._scenarios

    def test_create_scenario_auto_id(self, service):
        s = service.create_scenario(
            name="Auto ID",
            scenario_type="rainfall",
            parameters={"rainfall_change_pct": 30.0},
        )
        assert s.scenario_id is not None
        assert s.scenario_type == "rainfall"

    def test_create_scenario_triggers_event(self, mock_twin_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine)
        svc.create_scenario(
            scenario_id="evt_001",
            scenario_type="temperature",
            parameters={"temperature_delta": 1.0},
        )
        assert mock_twin_engine.event_bus.publish.called

    def test_validate_scenario(self, service):
        errors = service.validate_scenario("temperature", {"temperature_delta": 2.0})
        assert isinstance(errors, list)

    def test_run_simulation_custom(self, mock_twin_engine, mock_scenario_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine, mock_scenario_engine)
        result = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="custom_001",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={
                "location_id": "KA-BLR-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
            deltas={},
            duration_ms=10.0,
            success=True,
        )
        run = ScenarioRun(
            run_id="run_001",
            scenario=MagicMock(),
            results=[result],
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=100.0,
            location_count=1,
            status="completed",
        )
        mock_scenario_engine.run_simulation.return_value = run

        svc.create_scenario(
            scenario_id="custom_001",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        result_run = svc.run_simulation("custom_001", location_ids=["KA-BLR-001"])
        assert result_run == run
        mock_twin_engine.event_bus.publish.assert_called()

    def test_run_simulation_preset(self, mock_twin_engine, mock_scenario_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine, mock_scenario_engine)
        result = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="temp_plus_2",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={
                "location_id": "KA-BLR-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
            deltas={},
            duration_ms=10.0,
            success=True,
        )
        run = ScenarioRun(
            run_id="run_002",
            scenario=MagicMock(),
            results=[result],
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=50.0,
            location_count=1,
            status="completed",
        )
        mock_scenario_engine.run_simulation.return_value = run

        with patch("simulator.services.scenario_service.get_preset_scenario") as mock_get:
            mock_get.return_value = ScenarioDefinition(
                scenario_id="temp_plus_2",
                name="Temp +2°C",
                description="",
                scenario_type="temperature",
                parameters={"temperature_delta": 2.0},
            )
            result_run = svc.run_simulation("temp_plus_2", location_ids=["KA-BLR-001"])
            assert result_run == run

    def test_run_simulation_not_found(self, mock_twin_engine, mock_scenario_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine, mock_scenario_engine)
        with (
            patch("simulator.services.scenario_service.get_preset_scenario", return_value=None),
            pytest.raises(ValueError, match="Scenario not found: nonexistent"),
        ):
            svc.run_simulation("nonexistent")

    def test_compare_with_baseline(self, mock_twin_engine, mock_scenario_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine, mock_scenario_engine)
        run = MagicMock(spec=ScenarioRun)
        mock_scenario_engine.compare_with_baseline.return_value = [{"var": "temp", "delta": 2.0}]

        result = svc.compare_with_baseline(run)
        assert result == [{"var": "temp", "delta": 2.0}]
        mock_scenario_engine.compare_with_baseline.assert_called_once_with(run)

    def test_list_scenarios(self, service):
        service.create_scenario(
            scenario_id="s1", scenario_type="temperature", parameters={"temperature_delta": 1.0}
        )
        service.create_scenario(
            scenario_id="s2", scenario_type="rainfall", parameters={"rainfall_change_pct": 10.0}
        )

        with patch(
            "simulator.services.scenario_service.list_preset_scenarios",
            return_value=[{"id": "preset1"}],
        ):
            all_scenarios = service.list_scenarios()
            assert len(all_scenarios) == 3
            scenario_ids = {s.get("scenario_id", s.get("id")) for s in all_scenarios}
            assert "preset1" in scenario_ids
            assert "s1" in scenario_ids
            assert "s2" in scenario_ids

    def test_delete_scenario_exists(self, service):
        service.create_scenario(
            scenario_id="to_delete",
            scenario_type="temperature",
            parameters={"temperature_delta": 1.0},
        )
        assert service.delete_scenario("to_delete") is True
        assert "to_delete" not in service._scenarios

    def test_delete_scenario_not_exists(self, service):
        assert service.delete_scenario("nonexistent") is False

    def test_delete_scenario_triggers_event(self, mock_twin_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine)
        svc.create_scenario(
            scenario_id="del_evt",
            scenario_type="temperature",
            parameters={"temperature_delta": 1.0},
        )
        svc.delete_scenario("del_evt")
        assert mock_twin_engine.event_bus.publish.called

    def test_validate_scenario_delegates(self, service):
        with patch("simulator.services.scenario_service.validate_scenario_parameters") as mock_val:
            mock_val.return_value = ["error1"]
            errors = service.validate_scenario("temperature", {"temperature_delta": 100.0})
            assert errors == ["error1"]
            mock_val.assert_called_once_with("temperature", {"temperature_delta": 100.0})

    def test_collect_baseline_no_locations(self, mock_twin_engine):
        mock_twin_engine.service.state_manager.get_all_location_ids.return_value = set()
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine)
        with pytest.raises(ValueError, match="No locations available"):
            svc.run_simulation("temp_plus_2")

    def test_run_simulation_apply_scenario_raises(self, mock_twin_engine, mock_scenario_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine, mock_scenario_engine)
        mock_twin_engine.apply_scenario.side_effect = ValueError("bad state")

        result = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="custom_001",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={
                "location_id": "KA-BLR-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
            deltas={},
            duration_ms=10.0,
            success=True,
        )
        run = ScenarioRun(
            run_id="run_001",
            scenario=MagicMock(),
            results=[result],
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=100.0,
            location_count=1,
            status="completed",
        )
        mock_scenario_engine.run_simulation.return_value = run

        svc.create_scenario(
            scenario_id="custom_001",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        result_run = svc.run_simulation("custom_001")
        assert result_run == run

    def test_run_simulation_location_state_missing(self, mock_twin_engine, mock_scenario_engine):
        from simulator.services.scenario_service import ScenarioService

        svc = ScenarioService(mock_twin_engine, mock_scenario_engine)
        mock_twin_engine.service.state_manager.get_all_location_ids.return_value = {
            "KA-BLR-001",
            "KA-BLR-002",
        }
        mock_twin_engine.get_current_state.side_effect = lambda loc_id: {
            "KA-BLR-001": {"location_id": "KA-BLR-001"},
        }.get(loc_id)

        result = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="custom_001",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={
                "location_id": "KA-BLR-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
            deltas={},
            duration_ms=10.0,
            success=True,
        )
        run = ScenarioRun(
            run_id="run_001",
            scenario=MagicMock(),
            results=[result],
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=100.0,
            location_count=1,
            status="completed",
        )
        mock_scenario_engine.run_simulation.return_value = run

        svc.create_scenario(
            scenario_id="custom_001",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        result_run = svc.run_simulation("custom_001")
        assert result_run == run
