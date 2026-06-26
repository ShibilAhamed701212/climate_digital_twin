"""Unit tests for scenario data models."""

from __future__ import annotations

import pytest


class TestScenarioDefinition:
    """Test the ScenarioDefinition model."""

    def test_create_scenario_definition(self):
        from simulator.models.scenario_models import ScenarioDefinition

        s = ScenarioDefinition(
            scenario_id="test_001",
            name="Test Scenario",
            description="A test",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        assert s.scenario_id == "test_001"
        assert s.scenario_type == "temperature"
        assert s.parameters["temperature_delta"] == 2.0
        assert s.created_at is not None

    def test_immutable(self):
        from simulator.models.scenario_models import ScenarioDefinition

        s = ScenarioDefinition(
            scenario_id="test_001",
            name="Test",
            description="",
            scenario_type="rainfall",
            parameters={"rainfall_change_pct": 10},
        )
        with pytest.raises(AttributeError):
            s.name = "Changed"  # type: ignore[misc]

    def test_to_dict(self):
        from simulator.models.scenario_models import ScenarioDefinition

        s = ScenarioDefinition(
            scenario_id="test_001",
            name="Test",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 1.0},
        )
        d = s.to_dict()
        assert d["scenario_id"] == "test_001"
        assert d["scenario_type"] == "temperature"
        assert d["parameters"]["temperature_delta"] == 1.0
        assert "created_at" in d

    def test_frozen_dataclass(self):
        from dataclasses import FrozenInstanceError

        from simulator.models.scenario_models import ScenarioDefinition

        s = ScenarioDefinition(
            scenario_id="id", name="n", description="d",
            scenario_type="t", parameters={},
        )
        with pytest.raises(FrozenInstanceError):
            s.scenario_id = "id2"  # type: ignore[misc]


class TestSimulationResult:
    """Test the SimulationResult model."""

    def test_create_result(self):
        from simulator.models.scenario_models import SimulationResult

        r = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="test_001",
            timestamp="2024-01-01T00:00:00",
            baseline={"rainfall": 50},
            simulated={"rainfall": 75},
            deltas={"rainfall": 25.0},
            duration_ms=10.5,
            success=True,
        )
        assert r.location_id == "KA-BLR-001"
        assert r.success
        assert r.deltas["rainfall"] == 25.0

    def test_result_failure(self):
        from simulator.models.scenario_models import SimulationResult

        r = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="test_001",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={},
            deltas={},
            duration_ms=0.5,
            success=False,
            error_message="Something went wrong",
        )
        assert not r.success
        assert r.error_message == "Something went wrong"

    def test_to_dict(self):
        from simulator.models.scenario_models import SimulationResult

        r = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="test_001",
            timestamp="2024-01-01T00:00:00",
            baseline={"rainfall": 50},
            simulated={"rainfall": 75},
            deltas={"rainfall": 25.0},
            duration_ms=10.5,
            success=True,
        )
        d = r.to_dict()
        assert d["location_id"] == "KA-BLR-001"
        assert d["duration_ms"] == 10.5


class TestScenarioRun:
    """Test the ScenarioRun model."""

    @pytest.fixture
    def sample_scenario(self):
        from simulator.models.scenario_models import ScenarioDefinition

        return ScenarioDefinition(
            scenario_id="test_001",
            name="Test",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )

    @pytest.fixture
    def sample_results(self):
        from simulator.models.scenario_models import SimulationResult

        return [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="test_001",
                timestamp="2024-01-01T00:00:00",
                baseline={"rainfall": 50},
                simulated={"rainfall": 75},
                deltas={"rainfall": 25.0},
                duration_ms=10.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-MYS-001",
                scenario_id="test_001",
                timestamp="2024-01-01T00:00:00",
                baseline={"rainfall": 40},
                simulated={"rainfall": 60},
                deltas={"rainfall": 20.0},
                duration_ms=8.0,
                success=True,
            ),
        ]

    def test_create_run(self, sample_scenario, sample_results):
        from simulator.models.scenario_models import ScenarioRun

        run = ScenarioRun(
            run_id="run_001",
            scenario=sample_scenario,
            results=sample_results,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=100.0,
            location_count=2,
            status="completed",
        )
        assert run.run_id == "run_001"
        assert run.location_count == 2
        assert len(run.results) == 2

    def test_to_dict(self, sample_scenario, sample_results):
        from simulator.models.scenario_models import ScenarioRun

        run = ScenarioRun(
            run_id="run_001",
            scenario=sample_scenario,
            results=sample_results,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            total_duration_ms=100.0,
            location_count=2,
            status="completed",
        )
        d = run.to_dict()
        assert d["run_id"] == "run_001"
        assert d["status"] == "completed"
        assert "scenario" in d
        assert "results" in d
        assert len(d["results"]) == 2
