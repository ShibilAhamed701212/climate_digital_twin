"""Tests for enhanced scenario route endpoints with mocked engine modules."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.dependencies import get_scenario_service
from backend.api.routes import scenario


@pytest.fixture
def mock_services() -> dict[str, Any]:
    svc: dict[str, Any] = {}

    svc["scenario"] = AsyncMock()
    svc["scenario"].save_scenario = AsyncMock()
    svc["scenario"].load_scenario = AsyncMock(
        return_value=MagicMock(
            scenario_id="s1",
            name="Test",
            description="Test",
            location_id="loc-001",
            duration_days=30,
            parameters={},
            scenario_type="temperature",
            created_at=datetime.now(UTC),
        )
    )
    svc["scenario"].run_scenario = AsyncMock()
    svc["scenario"].compare_scenarios = AsyncMock()
    svc["scenario"].run_monte_carlo_scenario = AsyncMock()
    svc["scenario"].generator = MagicMock()

    return svc


@pytest.fixture
def app(mock_services: dict[str, Any]) -> FastAPI:
    app = FastAPI()
    app.include_router(scenario.router)
    app.dependency_overrides[get_scenario_service] = lambda: mock_services["scenario"]
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestMonteCarloSim:
    def test_monte_carlo_sim_success(self, client: TestClient) -> None:
        mock_result = MagicMock()
        mock_result.n_samples = 100
        mock_result.summary = {"temperature_2m": {"mean": 25.5, "std": 0.5}}
        mock_result.confidence_intervals = {
            "temperature_2m": {"lower": 24.5, "upper": 26.5, "mean": 25.5}
        }
        mock_result.sensitivity = {"temperature_delta": 1.0}

        with patch(
            "simulator.engine.monte_carlo.MonteCarloEngine.run_monte_carlo",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = client.post(
                "/scenario/monte-carlo-sim",
                json={
                    "scenario_type": "temperature",
                    "base_params": {"location_id": "loc-001", "temperature_2m": 25.0},
                    "num_simulations": 100,
                    "confidence_level": 0.95,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["n_samples"] == 100
            assert "summary" in data
            assert "confidence_intervals" in data
            assert data["config"]["num_simulations"] == 100

    def test_monte_carlo_sim_validation_error(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/monte-carlo-sim",
            json={
                "scenario_type": "temperature",
                "base_params": {},
                "num_simulations": -1,
            },
        )
        assert resp.status_code == 422

    def test_monte_carlo_sim_internal_error(self, client: TestClient) -> None:
        with patch(
            "simulator.engine.monte_carlo.MonteCarloEngine.run_monte_carlo",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Engine failure"),
        ):
            resp = client.post(
                "/scenario/monte-carlo-sim",
                json={
                    "scenario_type": "temperature",
                    "base_params": {"location_id": "loc-001"},
                    "num_simulations": 100,
                },
            )
            assert resp.status_code == 500


class TestCompareScenarios:
    def test_compare_scenarios_success(self, client: TestClient) -> None:
        mock_comparison = MagicMock()
        mock_comparison.comparison_id = "comp-001"
        mock_comparison.variable_deltas = {
            "temperature_2m": {"mean": 2.0, "max": 3.0, "min": 1.0, "std": 0.5}
        }
        mock_comparison.percentage_changes = {"temperature_2m": 8.0}
        mock_comparison.significant_variables = ["temperature_2m"]
        mock_comparison.summary = "Test summary"

        with patch(
            "simulator.scenarios.comparison.ScenarioComparison.compare_baseline_scenario",
            return_value=mock_comparison,
        ):
            resp = client.post(
                "/scenario/compare-scenarios",
                json={
                    "scenarios": [
                        {
                            "name": "Baseline",
                            "scenario_type": "temperature",
                            "parameters": {"temperature_delta": 0},
                            "location_id": "loc-001",
                        },
                        {
                            "name": "Warming",
                            "scenario_type": "temperature",
                            "parameters": {"temperature_delta": 2.0},
                            "location_id": "loc-001",
                        },
                    ],
                    "baseline_index": 0,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_comparisons"] >= 1
            assert "comparisons" in data

    def test_compare_scenarios_single_fails(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/compare-scenarios",
            json={
                "scenarios": [
                    {
                        "name": "Only One",
                        "scenario_type": "temperature",
                        "parameters": {},
                    }
                ],
            },
        )
        assert resp.status_code == 422

    def test_compare_scenarios_baseline_out_of_range(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/compare-scenarios",
            json={
                "scenarios": [
                    {
                        "name": "A",
                        "scenario_type": "temperature",
                        "parameters": {},
                        "location_id": "loc-001",
                    },
                    {
                        "name": "B",
                        "scenario_type": "temperature",
                        "parameters": {"temperature_delta": 1.0},
                        "location_id": "loc-001",
                    },
                ],
                "baseline_index": 5,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["total_comparisons"] >= 1

    def test_compare_scenarios_internal_error(self, client: TestClient) -> None:
        with patch(
            "simulator.scenarios.comparison.ScenarioComparison.compare_baseline_scenario",
            side_effect=RuntimeError("Comparison engine error"),
        ):
            resp = client.post(
                "/scenario/compare-scenarios",
                json={
                    "scenarios": [
                        {
                            "name": "A",
                            "scenario_type": "temperature",
                            "parameters": {},
                            "location_id": "loc-001",
                        },
                        {
                            "name": "B",
                            "scenario_type": "temperature",
                            "parameters": {"temperature_delta": 1.0},
                            "location_id": "loc-001",
                        },
                    ],
                },
            )
            assert resp.status_code == 500


class TestEnsemble:
    def test_ensemble_success(self, client: TestClient) -> None:
        mock_result = MagicMock()
        mock_result.n_members = 5
        mock_result.ensemble_mean = {"temperature_2m": [25.0, 26.0, 27.0]}
        mock_result.ensemble_spread = {"temperature_2m": [0.5, 0.6, 0.7]}
        mock_result.member_rankings = {"temperature_2m": [("m1", 27.0), ("m2", 26.0)]}
        mock_result.summary = {
            "temperature_2m": {
                "ensemble_mean": 26.0,
                "ensemble_std": 1.0,
                "ensemble_p50": 26.0,
            }
        }

        with patch(
            "simulator.scenarios.ensemble.EnsembleSimulator.run_ensemble",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = client.post(
                "/scenario/ensemble",
                json={
                    "members": [
                        {
                            "config": {
                                "name": "Member 1",
                                "scenario_type": "temperature",
                                "parameters": {"temperature_delta": 1.0},
                            },
                            "weight": 1.0,
                        }
                    ],
                    "location_id": "loc-001",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["n_members"] == 5
            assert "ensemble_mean" in data
            assert "ensemble_spread" in data

    def test_ensemble_internal_error(self, client: TestClient) -> None:
        with patch(
            "simulator.scenarios.ensemble.EnsembleSimulator.run_ensemble",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Ensemble error"),
        ):
            resp = client.post(
                "/scenario/ensemble",
                json={
                    "members": [
                        {
                            "config": {
                                "name": "M1",
                                "scenario_type": "temperature",
                                "parameters": {},
                            },
                            "weight": 1.0,
                        }
                    ],
                    "location_id": "loc-001",
                },
            )
            assert resp.status_code == 500


class TestGenerateScenario:
    def test_generate_temperature_scenario(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "temperature",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 30,
                "parameters": {"temperature_delta": 2.0},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["scenario_type"] == "temperature"
        assert data["name"] == "+2.0C Warming"
        assert "scenario_id" in data

    def test_generate_rainfall_scenario(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "rainfall",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 30,
                "parameters": {"rainfall_multiplier": 1.2},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "Rainfall" in data["name"]

    def test_generate_extreme_scenario(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "extreme",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 14,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "Extreme" in data["name"]

    def test_generate_drought_scenario(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "drought",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "Drought" in data["name"]

    def test_generate_ipcc_scenario(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "ipcc",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "parameters": {"pathway": "ssp585", "target_year": 2050},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "IPCC" in data["name"]

    def test_generate_ipcc_invalid_pathway(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "ipcc",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "parameters": {"pathway": "invalid", "target_year": 2050},
            },
        )
        assert resp.status_code == 500

    def test_generate_custom_scenario(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "custom",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 60,
                "parameters": {
                    "name": "My Custom",
                    "description": "A custom scenario",
                    "temperature_delta": 1.5,
                },
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "scenario_id" in data

    def test_generate_validation_error(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/scenario-generator",
            json={
                "scenario_type": "temperature",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 0,
            },
        )
        assert resp.status_code == 422
