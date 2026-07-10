"""Unit tests for simulator/scenarios/ensemble.py."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import numpy as np
import pytest

from simulator.models.scenario_models import ScenarioDefinition, SimulationResult
from simulator.models.weather import WeatherObservation


@pytest.fixture
def sample_observations():
    return [
        WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC),
            temperature_2m=25.0,
            precipitation_mm=0.0,
            humidity_pct=70.0,
            pressure_hpa=1013.0,
            wind_speed_10m=3.0,
            wind_direction_10m=180.0,
        ),
        WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=32.0,
            precipitation_mm=5.0,
            humidity_pct=55.0,
            pressure_hpa=1011.0,
            wind_speed_10m=4.0,
            wind_direction_10m=200.0,
        ),
    ]


@pytest.fixture
def base_scenario():
    return ScenarioDefinition(
        scenario_id="ensemble_test",
        name="Ensemble Test",
        description="Base scenario for ensemble",
        scenario_type="temperature",
        parameters={"temperature_delta": 2.0, "rainfall_multiplier": 1.1},
    )


@pytest.fixture
def mock_perturbation():
    def _apply(base_data, _scenario):
        return base_data

    pert = MagicMock()
    pert.apply_perturbation.side_effect = _apply
    return pert


class TestEnsembleResult:
    def test_valid_result(self):
        from simulator.scenarios.ensemble import EnsembleResult

        result = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="test",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        er = EnsembleResult(n_members=1, members=[result])
        assert er.n_members == 1
        assert len(er.members) == 1

    def test_invalid_n_members_zero(self):
        from simulator.scenarios.ensemble import EnsembleResult

        with pytest.raises(ValueError, match="n_members must be positive"):
            EnsembleResult(n_members=0, members=[])

    def test_invalid_n_members_negative(self):
        from simulator.scenarios.ensemble import EnsembleResult

        with pytest.raises(ValueError, match="n_members must be positive"):
            EnsembleResult(n_members=-1, members=[])

    def test_member_count_mismatch(self):
        from simulator.scenarios.ensemble import EnsembleResult

        result = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="test",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        with pytest.raises(ValueError, match="Number of members"):
            EnsembleResult(n_members=2, members=[result])


class TestEnsembleSimulator:
    def test_init_invalid_n_members(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        with pytest.raises(ValueError, match="n_members must be positive"):
            EnsembleSimulator(perturbation_engine=mock_perturbation, n_members=0)

    def test_init_default(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        assert sim.n_members == 10

    def test_init_custom(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation, n_members=5)
        assert sim.n_members == 5

    @pytest.mark.asyncio
    async def test_run_ensemble_empty_data(self, mock_perturbation, base_scenario):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation, n_members=3)
        with pytest.raises(ValueError, match="Cannot run ensemble on empty base data"):
            await sim.run_ensemble([], base_scenario)

    @pytest.mark.asyncio
    async def test_run_ensemble(self, mock_perturbation, sample_observations, base_scenario):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation, n_members=3)
        result = await sim.run_ensemble(sample_observations, base_scenario)

        assert result.n_members == 3
        assert len(result.members) == 3
        assert len(result.ensemble_mean) > 0
        assert len(result.ensemble_spread) > 0
        assert len(result.summary) > 0

        for member in result.members:
            assert member.success
            assert member.simulated["data_source"] == "ensemble"

    def test_compute_ensemble_stats_empty(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        assert sim.compute_ensemble_stats([]) == {}

    def test_compute_ensemble_stats(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 30.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 32.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        stats = sim.compute_ensemble_stats(results)
        assert stats["n_members"] == 2
        assert stats["variable_means"]["temperature_2m"] == 31.0
        assert stats["variable_stds"]["temperature_2m"] == 1.0

    def test_probability_of_exceedance_empty(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        assert sim.probability_of_exceedance([], "temperature_2m", 35.0) == 0.0

    def test_probability_of_exceedance(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [36.0, 37.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [34.0, 33.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        prob = sim.probability_of_exceedance(results, "temperature_2m", 35.0)
        assert prob == 0.5

    def test_rank_members(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [30.0, 31.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [35.0, 36.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        rankings = sim.rank_members(results, "temperature_2m")
        assert len(rankings) == 2
        assert rankings[0][0] == "m2"
        assert rankings[1][0] == "m1"

    def test_rank_members_empty(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        result = SimulationResult(
            location_id="KA-BLR-001",
            scenario_id="m1",
            timestamp="2024-01-01T00:00:00",
            baseline={},
            simulated={},
            deltas={},
            duration_ms=1.0,
            success=True,
        )
        rankings = sim.rank_members([result], "temperature_2m")
        assert rankings == []

    def test_compute_ensemble_mean_empty(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        assert sim.compute_ensemble_mean([]) == {}

    def test_compute_ensemble_mean(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [30.0, 32.0, 34.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [32.0, 34.0, 36.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        mean = sim.compute_ensemble_mean(results)
        assert "temperature_2m" in mean
        np.testing.assert_array_almost_equal(mean["temperature_2m"], [31.0, 33.0, 35.0])

    def test_compute_ensemble_spread_empty(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        assert sim.compute_ensemble_spread([]) == {}

    def test_compute_ensemble_spread(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [30.0, 32.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"time_series": {"temperature_2m": [34.0, 36.0]}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        spread = sim.compute_ensemble_spread(results)
        assert "temperature_2m" in spread
        np.testing.assert_array_almost_equal(spread["temperature_2m"], [2.0, 2.0])

    def test_build_member_scenario(self, mock_perturbation, base_scenario):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        member = sim._build_member_scenario(base_scenario, 0)
        assert member.scenario_id == base_scenario.scenario_id
        assert "member 0" in member.name
        assert "temperature_delta" in member.parameters

    def test_compute_summary(self):
        from simulator.scenarios.ensemble import EnsembleSimulator

        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 30.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="m2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 34.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        summary = EnsembleSimulator._compute_summary(results)
        assert "temperature_2m" in summary
        assert summary["temperature_2m"]["ensemble_mean"] == 32.0
        assert summary["temperature_2m"]["ensemble_min"] == 30.0
        assert summary["temperature_2m"]["ensemble_max"] == 34.0

    def test_compute_rankings_empty(self, mock_perturbation):
        from simulator.scenarios.ensemble import EnsembleSimulator

        sim = EnsembleSimulator(perturbation_engine=mock_perturbation)
        assert sim._compute_rankings([]) == {}

    def test_compute_summary_empty(self, mock_perturbation):  # noqa: ARG002
        from simulator.scenarios.ensemble import EnsembleSimulator

        assert EnsembleSimulator._compute_summary([]) == {}
