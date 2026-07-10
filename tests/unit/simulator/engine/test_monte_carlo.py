"""Unit tests for simulator/engine/monte_carlo.py."""

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
def scenario_template():
    return ScenarioDefinition(
        scenario_id="mc_test",
        name="MC Test",
        description="Base scenario for MC",
        scenario_type="temperature",
        parameters={"temperature_delta": 2.0},
    )


@pytest.fixture
def parameter_distributions():
    return {
        "temperature_delta": {"distribution": "normal", "mean": 2.0, "std": 0.5},
        "rainfall_multiplier": {"distribution": "uniform", "low": 0.8, "high": 1.2},
    }


@pytest.fixture
def mock_perturbation():
    def _apply(base_data, _scenario):
        return base_data

    pert = MagicMock()
    pert.apply_perturbation.side_effect = _apply
    return pert


class TestParseDistribution:
    def test_normal(self):
        from simulator.engine.monte_carlo import _parse_distribution

        dist, _ = _parse_distribution("normal", {"mean": 0.0, "std": 1.0})
        assert abs(dist.mean()) < 0.1

    def test_normal_std_zero(self):
        from simulator.engine.monte_carlo import _parse_distribution

        with pytest.raises(ValueError, match="Standard deviation must be positive"):
            _parse_distribution("normal", {"mean": 0.0, "std": 0.0})

    def test_normal_std_negative(self):
        from simulator.engine.monte_carlo import _parse_distribution

        with pytest.raises(ValueError, match="Standard deviation must be positive"):
            _parse_distribution("normal", {"mean": 0.0, "std": -1.0})

    def test_normal_with_loc_scale(self):
        from simulator.engine.monte_carlo import _parse_distribution

        dist, _ = _parse_distribution("normal", {"mean": 5.0, "std": 2.0, "loc": 5.0, "scale": 2.0})
        assert abs(dist.mean() - 5.0) < 0.1

    def test_uniform(self):
        from simulator.engine.monte_carlo import _parse_distribution

        dist, _ = _parse_distribution("uniform", {"low": 0.0, "high": 1.0})
        sample = dist.rvs(random_state=np.random.default_rng(42))
        assert 0.0 <= sample <= 1.0

    def test_uniform_invalid(self):
        from simulator.engine.monte_carlo import _parse_distribution

        with pytest.raises(ValueError, match="Uniform high"):
            _parse_distribution("uniform", {"low": 1.0, "high": 0.0})

    def test_lognormal(self):
        from simulator.engine.monte_carlo import _parse_distribution

        dist, _ = _parse_distribution("lognormal", {"mean": 0.0, "sigma": 0.5})
        sample = dist.rvs(random_state=np.random.default_rng(42))
        assert sample > 0

    def test_lognormal_sigma_zero(self):
        from simulator.engine.monte_carlo import _parse_distribution

        with pytest.raises(ValueError, match="Log-normal sigma must be positive"):
            _parse_distribution("lognormal", {"mean": 0.0, "sigma": 0.0})

    def test_triangular(self):
        from simulator.engine.monte_carlo import _parse_distribution

        dist, _ = _parse_distribution("triangular", {"low": 0.0, "mode": 0.5, "high": 1.0})
        sample = dist.rvs(random_state=np.random.default_rng(42))
        assert 0.0 <= sample <= 1.0

    def test_triangular_invalid(self):
        from simulator.engine.monte_carlo import _parse_distribution

        with pytest.raises(ValueError, match="Triangular must satisfy"):
            _parse_distribution("triangular", {"low": 1.0, "mode": 0.5, "high": 0.0})

    def test_unknown_distribution(self):
        from simulator.engine.monte_carlo import _parse_distribution

        with pytest.raises(ValueError, match="Unknown distribution"):
            _parse_distribution("weird", {})

    def test_name_variations(self):
        from simulator.engine.monte_carlo import _parse_distribution

        dist1, _ = _parse_distribution("log-normal", {"mean": 0.0, "sigma": 0.5})
        dist2, _ = _parse_distribution("log_normal", {"mean": 0.0, "sigma": 0.5})
        assert dist1 is not None
        assert dist2 is not None


class TestMonteCarloResult:
    def test_valid_result(self):
        from simulator.engine.monte_carlo import MonteCarloResult

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
        mc = MonteCarloResult(n_samples=1, parameter_distributions={}, results=[result])
        assert mc.n_samples == 1

    def test_invalid_n_samples_zero(self):
        from simulator.engine.monte_carlo import MonteCarloResult

        with pytest.raises(ValueError, match="n_samples must be positive"):
            MonteCarloResult(n_samples=0, parameter_distributions={}, results=[])

    def test_invalid_n_samples_negative(self):
        from simulator.engine.monte_carlo import MonteCarloResult

        with pytest.raises(ValueError, match="n_samples must be positive"):
            MonteCarloResult(n_samples=-1, parameter_distributions={}, results=[])

    def test_result_count_mismatch(self):
        from simulator.engine.monte_carlo import MonteCarloResult

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
        with pytest.raises(ValueError, match="Number of results"):
            MonteCarloResult(n_samples=2, parameter_distributions={}, results=[result])


class TestMonteCarloEngine:
    def test_init_invalid_n_samples(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        with pytest.raises(ValueError, match="n_samples must be positive"):
            MonteCarloEngine(perturbation_engine=mock_perturbation, n_samples=0)

    def test_init_default(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation)
        assert engine.n_samples == 1000

    def test_init_custom(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(
            perturbation_engine=mock_perturbation, n_samples=50, random_seed=42
        )
        assert engine.n_samples == 50

    def test_sample_parameters(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation, random_seed=42)
        samples = engine.sample_parameters(
            {
                "temperature_delta": {"distribution": "normal", "mean": 2.0, "std": 0.5},
                "rainfall_multiplier": {"distribution": "uniform", "low": 0.8, "high": 1.2},
            }
        )
        assert "temperature_delta" in samples
        assert "rainfall_multiplier" in samples
        assert 0.8 <= samples["rainfall_multiplier"] <= 1.2

    def test_sample_parameters_single(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation, random_seed=42)
        samples = engine.sample_parameters(
            {
                "temp_delta": {"distribution": "normal", "mean": 3.0, "std": 1.0},
            }
        )
        assert len(samples) == 1

    @pytest.mark.asyncio
    async def test_run_monte_carlo_empty_data(self, mock_perturbation, scenario_template):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation, n_samples=5)
        with pytest.raises(ValueError, match="Cannot run Monte Carlo on empty base data"):
            await engine.run_monte_carlo(
                [], scenario_template, {"temp": {"distribution": "normal"}}
            )

    @pytest.mark.asyncio
    async def test_run_monte_carlo_no_distributions(
        self, mock_perturbation, sample_observations, scenario_template
    ):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation, n_samples=5)
        with pytest.raises(ValueError, match="Must provide at least one parameter distribution"):
            await engine.run_monte_carlo(sample_observations, scenario_template, {})

    @pytest.mark.asyncio
    async def test_run_monte_carlo(
        self, mock_perturbation, sample_observations, scenario_template, parameter_distributions
    ):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(
            perturbation_engine=mock_perturbation, n_samples=5, random_seed=42
        )
        result = await engine.run_monte_carlo(
            sample_observations, scenario_template, parameter_distributions
        )
        assert result.n_samples == 5
        assert len(result.results) == 5
        assert len(result.summary) > 0
        assert len(result.confidence_intervals) > 0

    def test_compute_confidence_intervals_empty(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation)
        assert engine.compute_confidence_intervals([]) == {}

    def test_compute_confidence_intervals(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="s1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 30.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="s2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 34.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        cis = engine.compute_confidence_intervals(results, confidence=0.95)
        assert "temperature_2m" in cis
        assert cis["temperature_2m"]["mean"] == 32.0

    def test_sensitivity_analysis_empty(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation)
        assert engine.sensitivity_analysis([], []) == {}
        assert engine.sensitivity_analysis([], ["temp"]) == {}

    def test_sensitivity_analysis(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="s1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 30.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="s2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 34.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        scores = engine.sensitivity_analysis(results, ["temp_delta", "rain_mult"])
        assert len(scores) == 2
        assert scores["temp_delta"] == 0.5

    def test_sensitivity_analysis_no_variance(self, mock_perturbation):
        from simulator.engine.monte_carlo import MonteCarloEngine

        engine = MonteCarloEngine(perturbation_engine=mock_perturbation)
        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="s1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 30.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="s2",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 30.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        scores = engine.sensitivity_analysis(results, ["temp_delta"])
        assert scores["temp_delta"] == 0.0

    def test_build_scenario(self, mock_perturbation, scenario_template):  # noqa: ARG002
        from simulator.engine.monte_carlo import MonteCarloEngine

        scenario = MonteCarloEngine._build_scenario(scenario_template, {"temperature_delta": 3.5})
        assert scenario.parameters["temperature_delta"] == 3.5
        assert "(MC sample)" in scenario.name

    def test_build_scenario_with_unknown_param(self, mock_perturbation, scenario_template):  # noqa: ARG002
        from simulator.engine.monte_carlo import MonteCarloEngine

        scenario = MonteCarloEngine._build_scenario(
            scenario_template, {"temperature_delta": 3.0, "custom_param": 42}
        )
        assert scenario.parameters["temperature_delta"] == 3.0
        assert scenario.parameters["custom_param"] == 42

    def test_build_scenario_humidity_delta(self, mock_perturbation):  # noqa: ARG002
        from simulator.engine.monte_carlo import MonteCarloEngine

        template = ScenarioDefinition(
            scenario_id="t1",
            name="t",
            description="d",
            scenario_type="constant",
            parameters={},
        )
        scenario = MonteCarloEngine._build_scenario(
            template,
            {"humidity_delta": 5.0, "wind_speed_delta": 2.0, "pressure_delta": -1.0},
        )
        assert scenario.parameters["humidity_delta"] == 5.0
        assert scenario.parameters["wind_speed_delta"] == 2.0
        assert scenario.parameters["pressure_delta"] == -1.0

    def test_compute_summary(self, mock_perturbation):  # noqa: ARG002
        from simulator.engine.monte_carlo import MonteCarloEngine

        results = [
            SimulationResult(
                location_id="KA-BLR-001",
                scenario_id="s1",
                timestamp="2024-01-01T00:00:00",
                baseline={},
                simulated={"summary_statistics": {"temperature_2m": {"mean": 30.0}}},
                deltas={},
                duration_ms=1.0,
                success=True,
            ),
        ]
        summary = MonteCarloEngine._compute_summary(results)
        assert summary["temperature_2m"]["mean"] == 30.0
        assert summary["temperature_2m"]["p50"] == 30.0
