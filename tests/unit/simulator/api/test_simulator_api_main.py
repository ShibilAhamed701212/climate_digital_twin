"""Unit tests for simulator/api/main.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from simulator.api.main import app

# ── Test Data ──

SAMPLE_STATE = {
    "location_id": "KA-BLR-001",
    "latitude": 12.97,
    "longitude": 77.59,
    "timestamp": "2024-01-01T00:00:00",
    "rainfall": 10.5,
    "max_temp": 32.0,
    "min_temp": 18.0,
    "risk_score": 0.3,
    "prediction_confidence": 0.85,
    "scenario_id": "baseline",
    "data_source": "IMD",
    "state_type": "observed",
}

SAMPLE_SYNC_RESULT = {
    "version_id": 42,
    "location_id": "KA-BLR-001",
}


@pytest.fixture
def mock_engine():
    return MagicMock()


@pytest.fixture
def client(mock_engine):
    with (
        patch("simulator.api.main._get_engine", return_value=mock_engine),
        TestClient(app) as c,
    ):
        yield c


# ── Tests ──


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "twin-state-mgr"
        assert data["version"] == "2.1.0"


class TestGetCurrentState:
    def test_success(self, client, mock_engine):
        mock_engine.get_current_state.return_value = SAMPLE_STATE
        resp = client.get("/state/current?location_id=KA-BLR-001")
        assert resp.status_code == 200
        assert resp.json()["location_id"] == "KA-BLR-001"

    def test_not_found(self, client, mock_engine):
        mock_engine.get_current_state.return_value = None
        resp = client.get("/state/current?location_id=UNKNOWN")
        assert resp.status_code == 404


class TestGetHistoricalState:
    def test_success(self, client, mock_engine):
        mock_engine.get_historical_state.return_value = [SAMPLE_STATE]
        resp = client.get("/state/history?location_id=KA-BLR-001")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["location_id"] == "KA-BLR-001"

    def test_with_time_range(self, client, mock_engine):
        mock_engine.get_historical_state.return_value = [SAMPLE_STATE]
        resp = client.get("/state/history?location_id=KA-BLR-001&time_range=2024-01")
        assert resp.status_code == 200
        mock_engine.get_historical_state.assert_called_once_with("KA-BLR-001", "2024-01")

    def test_empty(self, client, mock_engine):
        mock_engine.get_historical_state.return_value = []
        resp = client.get("/state/history?location_id=KA-BLR-001")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetVersionHistory:
    def test_success(self, client, mock_engine):
        mock_engine.get_state_history.return_value = [
            {"version_id": 1, "timestamp": "2024-01-01T00:00:00", "state_type": "observed"},
        ]
        resp = client.get("/state/version-history?location_id=KA-BLR-001")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["version_id"] == 1

    def test_empty(self, client, mock_engine):
        mock_engine.get_state_history.return_value = []
        resp = client.get("/state/version-history?location_id=KA-BLR-001")
        assert resp.status_code == 200
        assert resp.json() == []


class TestSyncObservation:
    def test_success(self, client, mock_engine):
        mock_engine.ingest_observation.return_value = SAMPLE_SYNC_RESULT
        resp = client.post(
            "/state/sync",
            json={
                "location_id": "KA-BLR-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["version_id"] == 42

    def test_validation_error(self, client, mock_engine):
        mock_engine.ingest_observation.side_effect = ValueError("Invalid data")
        resp = client.post(
            "/state/sync",
            json={
                "location_id": "KA-BLR-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 422
        assert "Invalid data" in resp.json()["detail"]


class TestForecastState:
    def test_success(self, client, mock_engine):
        mock_engine.get_forecast_state.return_value = SAMPLE_STATE
        resp = client.get("/forecast/state?location_id=KA-BLR-001")
        assert resp.status_code == 200
        assert resp.json()["location_id"] == "KA-BLR-001"

    def test_not_found(self, client, mock_engine):
        mock_engine.get_forecast_state.return_value = None
        resp = client.get("/forecast/state?location_id=UNKNOWN")
        assert resp.status_code == 404


class TestSimulateScenario:
    def test_success(self, client, mock_engine):
        mock_engine.get_current_state.return_value = SAMPLE_STATE
        mock_engine.apply_scenario.return_value = SAMPLE_SYNC_RESULT
        resp = client.post(
            "/scenarios/simulate",
            json={"location_id": "KA-BLR-001", "scenario_id": "sc_001"},
        )
        assert resp.status_code == 201
        assert resp.json()["version_id"] == 42

    def test_location_not_found(self, client, mock_engine):
        mock_engine.get_current_state.return_value = None
        resp = client.post(
            "/scenarios/simulate",
            json={"location_id": "UNKNOWN", "scenario_id": "sc_001"},
        )
        assert resp.status_code == 404

    def test_scenario_error(self, client, mock_engine):
        mock_engine.get_current_state.return_value = SAMPLE_STATE
        mock_engine.apply_scenario.side_effect = ValueError("Scenario not found")
        resp = client.post(
            "/scenarios/simulate",
            json={"location_id": "KA-BLR-001", "scenario_id": "invalid"},
        )
        assert resp.status_code == 422
        assert "Scenario not found" in resp.json()["detail"]


class TestGetEngine:
    def test_raises_when_not_initialized(self):
        from simulator.api.main import _get_engine

        with (
            patch("simulator.api.main._engine", None),
            pytest.raises(RuntimeError, match="Engine not initialized"),
        ):
            _get_engine()

    def test_returns_engine(self):
        from unittest.mock import MagicMock

        from simulator.api.main import _get_engine

        mock_engine = MagicMock()
        with patch("simulator.api.main._engine", mock_engine):
            result = _get_engine()
        assert result is mock_engine


class TestRollback:
    def test_success(self, client, mock_engine):
        mock_engine.rollback.return_value = {
            "version_id": 5,
            "location_id": "KA-BLR-001",
        }
        resp = client.post(
            "/rollback",
            json={"location_id": "KA-BLR-001", "version_id": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["version_id"] == 5

    def test_error(self, client, mock_engine):
        mock_engine.rollback.side_effect = ValueError("Invalid version")
        resp = client.post(
            "/rollback",
            json={"location_id": "KA-BLR-001", "version_id": 5},
        )
        assert resp.status_code == 422
        assert "Invalid version" in resp.json()["detail"]


class TestOverlayPointer:
    def test_upsert_and_get(self, client):
        payload = {
            "location_id": "KA-HAS-001",
            "assessment_id": "A1",
            "event_id": "E1",
            "disaster_type": "flood",
            "href_assessment": "/disaster/assessments/A1",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        resp = client.post("/overlay-pointer", json=payload)
        assert resp.status_code == 200
        got = client.get("/overlay-pointer/KA-HAS-001")
        assert got.status_code == 200
        assert got.json()["assessment_id"] == "A1"

    def test_missing(self, client):
        resp = client.get("/overlay-pointer/missing-loc")
        assert resp.status_code == 404
