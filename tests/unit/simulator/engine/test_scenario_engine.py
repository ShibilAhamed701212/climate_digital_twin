"""Unit tests for simulator/engine/scenario_engine.py."""

from __future__ import annotations

from unittest.mock import patch

from simulator.models.scenario_models import ScenarioDefinition


class TestScenarioEngine:
    def test_init(self):
        from simulator.engine.scenario_engine import ScenarioEngine

        engine = ScenarioEngine(random_seed=42)
        assert engine.random_seed == 42

    def test_simulate_single_exception(self):
        from simulator.engine.scenario_engine import ScenarioEngine

        engine = ScenarioEngine()
        scenario = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="desc",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        baseline = {"max_temp": "not-a-number", "min_temp": "not-a-number"}
        with patch.object(engine, "_apply_modifications", side_effect=ValueError("bad data")):
            result = engine._simulate_single(scenario, baseline)
        assert result.success is False
        assert "bad data" in result.error_message
        assert result.simulated == {}
        assert result.deltas == {}

    def test_run_simulation(self):
        from simulator.engine.scenario_engine import ScenarioEngine

        engine = ScenarioEngine()
        scenario = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="desc",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        baseline_data = [
            {"location_id": "loc1", "max_temp": 30.0, "min_temp": 20.0, "rainfall": 100.0},
        ]
        run = engine.run_simulation(scenario, baseline_data)
        assert run.status == "completed"
        assert run.location_count == 1
        assert len(run.results) == 1
        assert run.results[0].success is True
