from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.dependencies import get_risk_service
from backend.api.routes.risk import router


def _make_mock_assessment(**overrides: object) -> MagicMock:
    score = MagicMock(
        hazard_type="flood",
        score=0.8,
        category="high",
        description="Flood risk",
    )
    defaults: dict[str, object] = {
        "assessment_id": "test-001",
        "location_id": "loc-001",
        "composite_score": 0.75,
        "composite_category": "high",
        "scores": [score],
        "timestamp": datetime(2025, 1, 1, tzinfo=UTC),
        "metadata": {},
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


@pytest.fixture
def mock_service() -> AsyncMock:
    assessment = _make_mock_assessment()
    service = AsyncMock()
    service.assess_location.return_value = assessment
    service.assess_batch.return_value = {"loc-001": assessment}
    service.get_risk_trend.return_value = [assessment]
    return service


def _build_client(mock_service: AsyncMock) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[get_risk_service] = lambda: mock_service
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestAssessRisk:
    def test_success(self, mock_service: AsyncMock) -> None:
        client = _build_client(mock_service)
        resp = client.post(
            "/risk/assess",
            json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_id"] == "loc-001"
        assert data["composite_score"] == 0.75
        assert data["composite_category"] == "high"

    def test_value_error(self, mock_service: AsyncMock) -> None:
        mock_service.assess_location.side_effect = ValueError("bad data")
        client = _build_client(mock_service)
        resp = client.post(
            "/risk/assess",
            json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "bad data"

    def test_server_error(self, mock_service: AsyncMock) -> None:
        mock_service.assess_location.side_effect = RuntimeError("crash")
        client = _build_client(mock_service)
        resp = client.post(
            "/risk/assess",
            json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Risk assessment failed"


class TestAssessRiskBatch:
    def test_success(self, mock_service: AsyncMock) -> None:
        client = _build_client(mock_service)
        resp = client.post(
            "/risk/assess/batch",
            json={
                "locations": [
                    {"location_id": "loc-001", "latitude": 0, "longitude": 0},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "loc-001" in data["assessments"]
        assert data["total_locations"] == 1

    def test_value_error(self, mock_service: AsyncMock) -> None:
        mock_service.assess_batch.side_effect = ValueError("bad batch")
        client = _build_client(mock_service)
        resp = client.post(
            "/risk/assess/batch",
            json={
                "locations": [
                    {"location_id": "loc-001", "latitude": 0, "longitude": 0},
                ]
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "bad batch"

    def test_server_error(self, mock_service: AsyncMock) -> None:
        mock_service.assess_batch.side_effect = RuntimeError("crash")
        client = _build_client(mock_service)
        resp = client.post(
            "/risk/assess/batch",
            json={
                "locations": [
                    {"location_id": "loc-001", "latitude": 0, "longitude": 0},
                ]
            },
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Batch risk assessment failed"


class TestGetRiskTrend:
    def test_success(self, mock_service: AsyncMock) -> None:
        client = _build_client(mock_service)
        resp = client.get("/risk/trend/loc-001?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_id"] == "loc-001"
        assert data["days_analysed"] == 30
        assert len(data["assessments"]) == 1

    def test_value_error(self, mock_service: AsyncMock) -> None:
        mock_service.get_risk_trend.side_effect = ValueError("bad trend")
        client = _build_client(mock_service)
        resp = client.get("/risk/trend/loc-001")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "bad trend"

    def test_server_error(self, mock_service: AsyncMock) -> None:
        mock_service.get_risk_trend.side_effect = RuntimeError("crash")
        client = _build_client(mock_service)
        resp = client.get("/risk/trend/loc-001")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Risk trend retrieval failed"


class TestExplainRisk:
    def test_not_implemented(self, mock_service: AsyncMock) -> None:
        service = mock_service
        service._explainer = None
        client = _build_client(service)
        resp = client.post(
            "/risk/explain",
            json={"assessment_id": "test-001"},
        )
        assert resp.status_code == 501
        assert resp.json()["detail"] == "Explainer not available"

    def test_server_error(self, mock_service: AsyncMock) -> None:
        service = mock_service
        service._explainer = MagicMock()
        service.assess_location.side_effect = RuntimeError("explain crash")
        client = _build_client(service)
        resp = client.post(
            "/risk/explain",
            json={"assessment_id": "test-001"},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Risk explanation failed"

    def test_success(self, mock_service: AsyncMock) -> None:
        service = mock_service
        service._explainer = MagicMock()
        service._explainer.factor_contribution.return_value = {
            "temperature": 0.5,
            "humidity": -0.3,
        }
        client = _build_client(service)
        resp = client.post(
            "/risk/explain",
            json={"assessment_id": "test-001"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"] == "test-001"
        assert "composite" in data["hazard_contributions"]
        assert data["top_factors"] == ["temperature", "humidity"]
