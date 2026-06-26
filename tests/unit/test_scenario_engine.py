"""Unit tests for the Scenario Simulation Engine."""

from __future__ import annotations

import pytest


class TestScenarioEngine:
    """Test the core scenario simulation engine."""

    @pytest.fixture
    def engine(self):
        from simulator.engine.scenario_engine import ScenarioEngine

        return ScenarioEngine()

    @pytest.fixture
    def baseline_data(self):
        return [
            {
                "location_id": "KA-BLR-001",
                "rainfall": 100.0,
                "max_temp": 32.0,
                "min_temp": 20.0,
                "risk_score": 25.0,
                "prediction_confidence": 0.85,
            },
            {
                "location_id": "KA-MYS-001",
                "rainfall": 80.0,
                "max_temp": 30.0,
                "min_temp": 18.0,
                "risk_score": 30.0,
                "prediction_confidence": 0.80,
            },
        ]

    @pytest.fixture
    def temp_scenario(self):
        from simulator.models.scenario_models import ScenarioDefinition

        return ScenarioDefinition(
            scenario_id="temp_test",
            name="Temp Test",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )

    @pytest.fixture
    def rain_scenario(self):
        from simulator.models.scenario_models import ScenarioDefinition

        return ScenarioDefinition(
            scenario_id="rain_test",
            name="Rain Test",
            description="",
            scenario_type="rainfall",
            parameters={"rainfall_change_pct": 50.0},
        )

    def test_run_temperature_simulation(self, engine, temp_scenario, baseline_data):
        run = engine.run_simulation(temp_scenario, baseline_data)
        assert run.status == "completed"
        assert run.location_count == 2
        assert len(run.results) == 2

        for i, result in enumerate(run.results):
            assert result.success
            base = baseline_data[i]
            expected_max = float(base["max_temp"]) + 2.0
            assert abs(float(result.simulated["max_temp"]) - expected_max) < 0.1
            assert "max_temp" in result.deltas
            assert abs(result.deltas["max_temp"] - 2.0) < 0.1

    def test_run_rainfall_simulation(self, engine, rain_scenario, baseline_data):
        run = engine.run_simulation(rain_scenario, baseline_data)
        for i, result in enumerate(run.results):
            assert result.success
            base = baseline_data[i]
            expected_rain = float(base["rainfall"]) * 1.5
            assert abs(float(result.simulated["rainfall"]) - expected_rain) < 0.1

    def test_run_combined_scenario(self, engine, baseline_data):
        from simulator.models.scenario_models import ScenarioDefinition

        scenario = ScenarioDefinition(
            scenario_id="combined_test",
            name="Combined",
            description="",
            scenario_type="combined",
            parameters={
                "scenarios": [
                    {"scenario_type": "temperature", "parameters": {"temperature_delta": 2.0}},
                    {"scenario_type": "rainfall", "parameters": {"rainfall_change_pct": -20.0}},
                ],
            },
        )
        run = engine.run_simulation(scenario, baseline_data)
        for i, result in enumerate(run.results):
            assert result.success
            base = baseline_data[i]
            expected_max = float(base["max_temp"]) + 2.0
            expected_rain = float(base["rainfall"]) * 0.8
            assert abs(float(result.simulated["max_temp"]) - expected_max) < 0.1
            assert abs(float(result.simulated["rainfall"]) - expected_rain) < 0.1

    def test_run_heatwave_scenario(self, engine, baseline_data):
        from simulator.models.scenario_models import ScenarioDefinition

        scenario = ScenarioDefinition(
            scenario_id="heatwave_test",
            name="Heatwave",
            description="",
            scenario_type="extreme_event",
            parameters={"event_type": "heatwave", "temperature_delta": 5.0},
        )
        run = engine.run_simulation(scenario, baseline_data)
        for i, result in enumerate(run.results):
            assert result.success
            base = baseline_data[i]
            expected_max = float(base["max_temp"]) + 5.0
            assert abs(float(result.simulated["max_temp"]) - expected_max) < 0.1

    def test_run_drought_scenario(self, engine, baseline_data):
        from simulator.models.scenario_models import ScenarioDefinition

        scenario = ScenarioDefinition(
            scenario_id="drought_test",
            name="Drought",
            description="",
            scenario_type="extreme_event",
            parameters={"event_type": "drought", "rainfall_change_pct": -80.0},
        )
        run = engine.run_simulation(scenario, baseline_data)
        for i, result in enumerate(run.results):
            assert result.success
            base = baseline_data[i]
            expected_rain = float(base["rainfall"]) * 0.2
            assert abs(float(result.simulated["rainfall"]) - expected_rain) < 0.1

    def test_run_flood_scenario(self, engine, baseline_data):
        from simulator.models.scenario_models import ScenarioDefinition

        scenario = ScenarioDefinition(
            scenario_id="flood_test",
            name="Flood",
            description="",
            scenario_type="extreme_event",
            parameters={"event_type": "flood", "rainfall_change_pct": 200.0},
        )
        run = engine.run_simulation(scenario, baseline_data)
        for i, result in enumerate(run.results):
            assert result.success
            base = baseline_data[i]
            expected_rain = float(base["rainfall"]) * 3.0
            assert abs(float(result.simulated["rainfall"]) - expected_rain) < 0.1

    def test_compare_with_baseline(self, engine, temp_scenario, baseline_data):
        run = engine.run_simulation(temp_scenario, baseline_data)
        comparisons = engine.compare_with_baseline(run)
        assert len(comparisons) == 2
        for comp in comparisons:
            assert "delta_max_temp" in comp
            assert abs(comp["delta_max_temp"] - 2.0) < 0.1

    def test_simulation_speed(self, engine, temp_scenario, baseline_data):
        run = engine.run_simulation(temp_scenario, baseline_data)
        assert run.total_duration_ms < 3000

    def test_deterministic_output(self, engine, temp_scenario, baseline_data):
        run1 = engine.run_simulation(temp_scenario, baseline_data)
        run2 = engine.run_simulation(temp_scenario, baseline_data)
        for r1, r2 in zip(run1.results, run2.results, strict=True):
            assert r1.success == r2.success
            assert r1.simulated == r2.simulated

    def test_rainfall_never_negative(self, engine, baseline_data):
        from simulator.models.scenario_models import ScenarioDefinition

        scenario = ScenarioDefinition(
            scenario_id="extreme_drought",
            name="Extreme Drought",
            description="",
            scenario_type="rainfall",
            parameters={"rainfall_change_pct": -200.0},
        )
        run = engine.run_simulation(scenario, baseline_data)
        for result in run.results:
            assert float(result.simulated["rainfall"]) >= 0

    def test_monsoon_scenario(self, engine, baseline_data):
        from simulator.models.scenario_models import ScenarioDefinition

        scenario = ScenarioDefinition(
            scenario_id="monsoon_test",
            name="Monsoon",
            description="",
            scenario_type="monsoon",
            parameters={"delay_days": 15, "intensity_reduction_pct": 20.0},
        )
        run = engine.run_simulation(scenario, baseline_data)
        for result in run.results:
            assert result.success
            assert result.simulated.get("monsoon_delay_days") == 15


class TestDeltaComputation:
    """Test delta calculation logic."""

    def test_compute_deltas_all_fields(self):
        from simulator.engine.scenario_engine import ScenarioEngine

        baseline = {"rainfall": 100, "max_temp": 30, "min_temp": 20, "risk_score": 25}
        simulated = {"rainfall": 150, "max_temp": 32, "min_temp": 22, "risk_score": 35}
        deltas = ScenarioEngine._compute_deltas(baseline, simulated)
        assert deltas["rainfall"] == 50.0
        assert deltas["max_temp"] == 2.0
        assert deltas["min_temp"] == 2.0
        assert deltas["risk_score"] == 10.0

    def test_compute_deltas_partial(self):
        from simulator.engine.scenario_engine import ScenarioEngine

        baseline = {"rainfall": 100}
        simulated = {"rainfall": 150, "max_temp": 32}
        deltas = ScenarioEngine._compute_deltas(baseline, simulated)
        assert "rainfall" in deltas
        assert "max_temp" not in deltas

    def test_compute_deltas_empty(self):
        from simulator.engine.scenario_engine import ScenarioEngine

        deltas = ScenarioEngine._compute_deltas({}, {})
        assert deltas == {}
