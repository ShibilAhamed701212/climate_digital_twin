"""Unit tests for simulator/scenarios/api.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
def client(mock_service):
    with patch("simulator.scenarios.api._get_service", return_value=mock_service):
        from simulator.scenarios.api import app

        with TestClient(app) as c:
            yield c


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "scenario-engine"


class TestCreateScenario:
    def test_create_scenario(self, client, mock_service):
        mock_service.create_scenario.return_value.to_dict.return_value = {
            "scenario_id": "sc_abc123",
            "name": "test",
        }
        resp = client.post(
            "/scenarios/create",
            json={
                "scenario_id": "my_sc",
                "name": "Test",
                "description": "desc",
                "scenario_type": "temperature",
                "parameters": {"delta": 2.0},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["scenario_id"] == "sc_abc123"
        mock_service.create_scenario.assert_called_once_with(
            scenario_id="my_sc",
            name="Test",
            description="desc",
            scenario_type="temperature",
            parameters={"delta": 2.0},
        )


class TestSimulateScenario:
    def test_simulate_success(self, client, mock_service):
        mock_service.run_simulation.return_value.to_dict.return_value = {
            "run_id": "run_001",
            "scenario": {},
            "results": [],
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:00:01",
            "total_duration_ms": 1.0,
            "location_count": 0,
            "status": "completed",
        }
        resp = client.post(
            "/scenarios/simulate",
            json={"scenario_id": "sc_001", "location_ids": ["loc1"]},
        )
        assert resp.status_code == 200
        assert resp.json()["run_id"] == "run_001"

    def test_simulate_not_found(self, client, mock_service):
        mock_service.run_simulation.side_effect = ValueError("Scenario not found")
        resp = client.post(
            "/scenarios/simulate",
            json={"scenario_id": "missing", "location_ids": None},
        )
        assert resp.status_code == 404
        assert "Scenario not found" in resp.json()["detail"]


class TestListScenarios:
    def test_list_scenarios(self, client, mock_service):
        mock_service.list_scenarios.return_value = [
            {"scenario_id": "sc_001"},
            {"scenario_id": "sc_002"},
        ]
        resp = client.get("/scenarios")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCompareWithBaseline:
    def test_compare_success(self, client, mock_service):
        mock_run = MagicMock()
        mock_service.run_simulation.return_value = mock_run
        mock_service.compare_with_baseline.return_value = [
            {"variable": "temperature", "delta": 1.5}
        ]
        resp = client.get("/scenarios/sc_001/compare")
        assert resp.status_code == 200
        assert resp.json()[0]["delta"] == 1.5

    def test_compare_not_found(self, client, mock_service):
        mock_service.run_simulation.side_effect = ValueError("Missing")
        resp = client.get("/scenarios/missing/compare")
        assert resp.status_code == 404


class TestValidateScenario:
    def test_validate_valid(self, client, mock_service):
        mock_service.validate_scenario.return_value = []
        resp = client.post(
            "/scenarios/validate",
            json={"scenario_type": "temperature", "parameters": {"delta": 2.0}},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_validate_invalid(self, client, mock_service):
        mock_service.validate_scenario.return_value = ["Bad param"]
        resp = client.post(
            "/scenarios/validate",
            json={"scenario_type": "rainfall", "parameters": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
        assert resp.json()["errors"] == ["Bad param"]


class TestDeleteScenario:
    def test_delete_success(self, client, mock_service):
        mock_service.delete_scenario.return_value = True
        resp = client.delete("/scenarios/sc_001")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_not_found(self, client, mock_service):
        mock_service.delete_scenario.return_value = False
        resp = client.delete("/scenarios/missing")
        assert resp.status_code == 404


class TestGetService:
    def test_raises_when_not_initialized(self):
        from simulator.scenarios.api import _get_service

        with (
            patch("simulator.scenarios.api._service", None),
            pytest.raises(RuntimeError, match="Service not initialized"),
        ):
            _get_service()

    def test_returns_service_when_initialized(self):
        from simulator.scenarios.api import _get_service

        mock_svc = MagicMock()
        with patch("simulator.scenarios.api._service", mock_svc):
            assert _get_service() == mock_svc
