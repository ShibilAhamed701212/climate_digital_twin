"""Tests for all API route endpoints with mocked dependencies.

Uses FastAPI's dependency_overrides to properly mock DI at the framework level.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.dependencies import (
    get_feedback_analyzer,
    get_feedback_capture,
    get_forecast_pipeline,
    get_rag_service,
    get_risk_service,
    get_scenario_service,
    get_twin_manager,
)
from backend.api.routes import feedback, forecast, health, rag, risk, scenario, twin


@pytest.fixture
def mock_services() -> dict[str, Any]:
    svc: dict[str, Any] = {}

    svc["risk"] = AsyncMock()
    svc["risk"].assess_location = AsyncMock()
    svc["risk"].assess_batch = AsyncMock()
    svc["risk"].get_risk_trend = AsyncMock()

    svc["scenario"] = AsyncMock()
    svc["scenario"].save_scenario = AsyncMock()
    svc["scenario"].load_scenario = AsyncMock()
    svc["scenario"].run_scenario = AsyncMock()
    svc["scenario"].compare_scenarios = AsyncMock()
    svc["scenario"].run_monte_carlo_scenario = AsyncMock()
    svc["scenario"].generator = MagicMock()

    svc["rag"] = AsyncMock()
    svc["rag"].ask = AsyncMock()
    svc["rag"].ingest = AsyncMock()
    svc["rag"].ingest_batch = AsyncMock()
    svc["rag"].get_context = AsyncMock()
    svc["rag"].knowledge_base = MagicMock()

    svc["feedback_capture"] = AsyncMock()
    svc["feedback_analyzer"] = AsyncMock()

    svc["twin"] = AsyncMock()
    svc["twin"].get_current_state = AsyncMock()
    svc["twin"].update_state = AsyncMock()
    svc["twin"].get_version_history = AsyncMock()
    svc["twin"].rollback = AsyncMock()

    svc["forecast"] = AsyncMock()
    svc["forecast"].predict_with_best = AsyncMock()
    svc["forecast"].train_forecast_model = AsyncMock()
    svc["forecast"].model_registry = MagicMock()

    return svc


@pytest.fixture
def app(mock_services: dict[str, Any]) -> FastAPI:
    app = FastAPI()
    app.include_router(health.router)
    app.include_router(risk.router)
    app.include_router(scenario.router)
    app.include_router(rag.router)
    app.include_router(feedback.router)
    app.include_router(twin.router)
    app.include_router(forecast.router)

    app.dependency_overrides[get_risk_service] = lambda: mock_services["risk"]
    app.dependency_overrides[get_scenario_service] = lambda: mock_services["scenario"]
    app.dependency_overrides[get_rag_service] = lambda: mock_services["rag"]
    app.dependency_overrides[get_feedback_capture] = lambda: mock_services["feedback_capture"]
    app.dependency_overrides[get_feedback_analyzer] = lambda: mock_services["feedback_analyzer"]
    app.dependency_overrides[get_twin_manager] = lambda: mock_services["twin"]
    app.dependency_overrides[get_forecast_pipeline] = lambda: mock_services["forecast"]

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestHealthRoutes:
    def test_get_health_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "services" in data

    def test_get_readiness_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True
        assert "services" in data

    def test_get_liveness_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


class TestRiskRoutes:
    def test_assess_risk_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        mock_services["risk"].assess_location.return_value = MagicMock(
            assessment_id="risk-001",
            location_id="loc-001",
            composite_score=0.45,
            composite_category="moderate",
            scores=[
                MagicMock(
                    hazard_type="heat",
                    score=0.6,
                    category="high",
                    description="High heat risk",
                )
            ],
            timestamp=datetime.now(UTC),
            metadata={"source": "test"},
        )
        resp = client.post(
            "/risk/assess",
            json={
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"] == "risk-001"
        assert data["composite_score"] == 0.45
        assert data["composite_category"] == "moderate"

    def test_assess_risk_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["risk"].assess_location.side_effect = ValueError("Invalid location")
        resp = client.post(
            "/risk/assess",
            json={
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 400

    def test_assess_risk_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["risk"].assess_location.side_effect = RuntimeError("DB down")
        resp = client.post(
            "/risk/assess",
            json={
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 500

    def test_assess_risk_batch_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["risk"].assess_batch.return_value = {
            "loc-001": MagicMock(
                assessment_id="a1",
                location_id="loc-001",
                composite_score=0.3,
                composite_category="low",
                scores=[],
                timestamp=datetime.now(UTC),
                metadata={},
            ),
        }
        resp = client.post(
            "/risk/assess/batch",
            json={
                "locations": [{"location_id": "loc-001", "latitude": 12.97, "longitude": 77.59}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_locations"] == 1
        assert "loc-001" in data["assessments"]

    def test_assess_risk_batch_validation_error(self, client: TestClient) -> None:
        resp = client.post("/risk/assess/batch", json={"locations": []})
        assert resp.status_code == 422

    def test_get_risk_trend_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["risk"].get_risk_trend.return_value = [
            MagicMock(
                assessment_id="a1",
                location_id="loc-001",
                composite_score=0.4,
                composite_category="moderate",
                scores=[],
                timestamp=datetime.now(UTC),
                metadata={},
            )
        ]
        resp = client.get("/risk/trend/loc-001?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_id"] == "loc-001"
        assert data["days_analysed"] == 30
        assert len(data["assessments"]) == 1

    def test_explain_risk_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        explainer = MagicMock()
        explainer.factor_contribution.return_value = {"temperature": 0.6, "humidity": 0.3}
        mock_services["risk"]._explainer = explainer
        mock_services["risk"].assess_location.return_value = MagicMock(
            assessment_id="a1",
            location_id="unknown",
            composite_score=0.0,
            composite_category="unknown",
            scores=[],
            timestamp=datetime.now(UTC),
            metadata={},
        )
        resp = client.post("/risk/explain", json={"assessment_id": "a1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"] == "a1"
        assert "top_factors" in data

    def test_explain_risk_no_explainer(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["risk"]._explainer = None
        resp = client.post("/risk/explain", json={"assessment_id": "a1"})
        assert resp.status_code == 501


class TestScenarioRoutes:
    def test_create_scenario_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].save_scenario.return_value = "scenario-001"
        resp = client.post(
            "/scenario/create",
            json={
                "name": "Test Scenario",
                "description": "A test",
                "scenario_type": "temperature",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 30,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["scenario_id"] == "scenario-001"
        assert data["name"] == "Test Scenario"

    def test_create_scenario_validation_error(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/create",
            json={
                "name": "Test",
                "description": "",
                "scenario_type": "invalid",
                "location_id": "",
                "latitude": 200,
                "longitude": 0,
                "duration_days": 0,
            },
        )
        assert resp.status_code == 422

    def test_run_scenario_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        scenario_mock = MagicMock(
            scenario_id="s1",
            name="Test",
            description="Test scenario",
            location_id="loc-001",
            latitude=12.97,
            longitude=77.59,
            duration_days=30,
            created_at=datetime.now(UTC),
            temperature_delta=None,
            rainfall_multiplier=None,
            humidity_delta=None,
            wind_speed_delta=None,
            pressure_delta=None,
            parameters={},
        )
        mock_services["scenario"].load_scenario.return_value = scenario_mock

        result = MagicMock()
        result.result_id = "r1"
        result.scenario_id = "s1"
        result.location_id = "loc-001"
        result.summary_statistics = {"temp": {"mean": 25.0}}
        result.time_steps = [datetime.now(UTC)]
        result.execution_time_ms = 100.0
        result.authenticity = "SCENARIO"
        result.mode = "REAL"
        result.baseline_state = {"temperature_2m": 22.1}
        result.scenario_state = {"temperature_2m": 25.1}
        result.deltas = {"temperature_2m": 3.0}
        result.baseline_hazard = None
        result.scenario_hazard = None
        result.hazard_deltas = {}
        mock_services["scenario"].run_scenario.return_value = result

        resp = client.post("/scenario/run", json={"scenario_id": "s1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_id"] == "s1"
        assert data["result_id"] == "r1"
        assert data["authenticity"] == "SCENARIO"
        assert data["deltas"] == {"temperature_2m": 3.0}

    def test_run_scenario_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = None
        resp = client.post("/scenario/run", json={"scenario_id": "nonexistent"})
        assert resp.status_code == 404

    def test_compare_scenarios_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(
            scenario_id="s1", created_at=datetime.now(UTC)
        )
        mock_services["scenario"].compare_scenarios.return_value = [
            MagicMock(
                comparison_id="c1",
                baseline_result_id="b1",
                scenario_result_id="s1",
                variable_deltas={"temp": 0.5},
                percentage_changes={"temp": 2.0},
                significant_variables=["temp"],
                summary="Slight warming",
            )
        ]
        resp = client.post("/scenario/compare", json={"scenario_ids": ["s1", "s2"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_comparisons"] == 1

    def test_compare_scenarios_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = None
        resp = client.post("/scenario/compare", json={"scenario_ids": ["s1", "s2"]})
        assert resp.status_code == 404

    def test_list_templates_success(self, client: TestClient) -> None:
        resp = client.get("/scenario/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert len(data["templates"]) == 9

    def test_get_scenario_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        scenario = MagicMock()
        scenario.scenario_id = "s1"
        scenario.name = "Test"
        scenario.description = "Desc"
        scenario.location_id = "loc-001"
        scenario.duration_days = 30
        scenario.parameters = {}
        scenario.scenario_type = "temperature"
        mock_services["scenario"].load_scenario.return_value = scenario
        resp = client.get("/scenario/s1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_id"] == "s1"
        assert data["name"] == "Test"

    def test_get_scenario_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = None
        resp = client.get("/scenario/nonexistent")
        assert resp.status_code == 404


class TestRAGRoutes:
    def test_ask_question_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        mock_services["rag"].ask.return_value = [
            MagicMock(
                chunk=MagicMock(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    text="Climate data content",
                    metadata={"source": "test"},
                ),
                score=0.95,
                rank=1,
            )
        ]
        resp = client.post("/rag/ask", json={"query": "What is climate change?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_results"] == 1
        assert data["query"] == "What is climate change?"

    def test_ask_question_empty_query(self, client: TestClient) -> None:
        resp = client.post("/rag/ask", json={"query": ""})
        assert resp.status_code == 422

    def test_ingest_document_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].ingest.return_value = [MagicMock()]
        resp = client.post(
            "/rag/ingest",
            json={
                "title": "Test Doc",
                "source": "test",
                "content": "Some content here",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "document_id" in data
        assert data["chunks_created"] == 1

    def test_ingest_document_empty_content(self, client: TestClient) -> None:
        resp = client.post(
            "/rag/ingest",
            json={
                "title": "Test",
                "source": "test",
                "content": "",
            },
        )
        assert resp.status_code == 422

    def test_ingest_batch_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        mock_services["rag"].ingest_batch.return_value = {}
        resp = client.post(
            "/rag/ingest/batch",
            json={
                "documents": [
                    {"title": "Doc1", "source": "test", "content": "Content 1"},
                    {"title": "Doc2", "source": "test", "content": "Content 2"},
                ],
            },
        )
        assert resp.status_code == 201

    def test_get_context_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        mock_services["rag"].get_context.return_value = "Context content --- Source2"
        resp = client.post("/rag/context", json={"query": "test query"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == 2

    def test_list_collections_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].knowledge_base.list_collections.return_value = [
            MagicMock(collection_id="c1", name="Collection 1"),
        ]
        resp = client.get("/rag/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["collections"]) == 1

    def test_create_collection_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        kb.create_collection = MagicMock(return_value="new-collection-id")
        resp = client.post("/rag/collections", json={"name": "New Collection"})
        assert resp.status_code == 201
        assert resp.json()["collection_id"] == "new-collection-id"

    def test_get_collection_stats_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        kb.get_collection_stats = AsyncMock(
            return_value={
                "name": "Coll",
                "document_count": 10,
                "chunk_count": 50,
            }
        )
        resp = client.get("/rag/collections/test-coll/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_count"] == 10

    def test_search_collection_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        kb.search = AsyncMock(
            return_value=[
                MagicMock(
                    chunk=MagicMock(chunk_id="c1", text="Result text", metadata={}),
                    score=0.9,
                )
            ]
        )
        resp = client.post("/rag/search/test-coll", json={"query": "search term"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1


class TestFeedbackRoutes:
    def test_submit_risk_feedback_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_risk_feedback.return_value = MagicMock(
            record_id="fb-001",
            status="recorded",
        )
        resp = client.post(
            "/feedback/risk",
            json={
                "assessment_id": "a1",
                "rating": 4,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["record_id"] == "fb-001"
        assert data["message"] == "Risk feedback captured successfully"

    def test_submit_risk_feedback_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_risk_feedback.side_effect = ValueError("Bad data")
        resp = client.post(
            "/feedback/risk",
            json={
                "assessment_id": "a1",
                "rating": 4,
            },
        )
        assert resp.status_code == 400

    def test_submit_forecast_feedback_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_forecast_feedback.return_value = MagicMock(
            record_id="fb-002",
            status="recorded",
        )
        resp = client.post(
            "/feedback/forecast",
            json={
                "forecast_id": "f1",
                "rating": 5,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["message"] == "Forecast feedback captured successfully"

    def test_submit_general_feedback_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_general_feedback.return_value = MagicMock(
            record_id="fb-003",
            status="recorded",
        )
        resp = client.post(
            "/feedback/general",
            json={
                "location_id": "loc-001",
                "rating": 3,
                "feedback_type": "general",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["record_id"] == "fb-003"

    def test_submit_general_feedback_validation_error(self, client: TestClient) -> None:
        resp = client.post(
            "/feedback/general",
            json={
                "location_id": "loc-001",
                "rating": 3,
                "feedback_type": "invalid_type",
            },
        )
        assert resp.status_code == 422

    def test_get_feedback_stats_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_analyzer"].get_overview_stats.return_value = {
            "total_feedback": 100,
            "avg_rating": 4.2,
            "rating_std": 0.8,
            "rating_counts": {"5": 50, "4": 30},
            "feedback_types": {"risk": 60, "forecast": 40},
        }
        resp = client.get("/feedback/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_feedback"] == 100
        assert data["avg_rating"] == 4.2

    def test_get_feedback_trend_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_analyzer"].get_improvement_trend.return_value = {
            "overall_trend": 0.05,
            "first_period_avg": 4.0,
            "second_period_avg": 4.2,
            "trend_direction": "improving",
            "improvement_pct": 5.0,
        }
        resp = client.get("/feedback/trend?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trend_direction"] == "improving"
        assert data["improvement_pct"] == 5.0

    def test_get_location_feedback_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_analyzer"].get_location_performance.return_value = {
            "total_feedback": 20,
            "avg_rating": 4.0,
            "trend": "stable",
            "recent_avg": 4.1,
        }
        resp = client.get("/feedback/location/loc-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_id"] == "loc-001"
        assert data["total_feedback"] == 20

    def test_submit_risk_feedback_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_risk_feedback.side_effect = RuntimeError(
            "DB error"
        )
        resp = client.post(
            "/feedback/risk",
            json={"assessment_id": "a1", "rating": 4},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Risk feedback submission failed"

    def test_submit_forecast_feedback_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_forecast_feedback.side_effect = ValueError(
            "Invalid"
        )
        resp = client.post(
            "/feedback/forecast",
            json={"forecast_id": "f1", "rating": 5},
        )
        assert resp.status_code == 400

    def test_submit_forecast_feedback_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_forecast_feedback.side_effect = RuntimeError(
            "fail"
        )
        resp = client.post(
            "/feedback/forecast",
            json={"forecast_id": "f1", "rating": 5},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Forecast feedback submission failed"

    def test_submit_general_feedback_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_capture"].capture_general_feedback.side_effect = RuntimeError(
            "fail"
        )
        resp = client.post(
            "/feedback/general",
            json={"location_id": "loc-001", "rating": 3, "feedback_type": "general"},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "General feedback submission failed"

    def test_get_feedback_stats_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_analyzer"].get_overview_stats.side_effect = RuntimeError("fail")
        resp = client.get("/feedback/stats")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Feedback statistics retrieval failed"

    def test_get_feedback_trend_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_analyzer"].get_improvement_trend.side_effect = RuntimeError("fail")
        resp = client.get("/feedback/trend?days=30")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Feedback trend retrieval failed"

    def test_get_location_feedback_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["feedback_analyzer"].get_location_performance.side_effect = RuntimeError(
            "fail"
        )
        resp = client.get("/feedback/location/loc-001")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Location feedback retrieval failed"


class TestTwinRoutes:
    def test_get_twin_state_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        state = MagicMock()
        state.entity_id = "entity-001"
        state.timestamp = datetime.now(UTC)
        state.temperature_2m = 25.0
        state.precipitation_mm = 10.0
        state.humidity_pct = 60.0
        state.pressure_hpa = 1013.0
        state.wind_speed_10m = 5.0
        state.data_source = "obs"
        state.quality_flag = "good"
        mock_services["twin"].get_current_state.return_value = state
        resp = client.get("/twin/state/entity-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == "entity-001"
        assert data["temperature_2m"] == 25.0

    def test_get_twin_state_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].get_current_state.side_effect = ValueError("Not found")
        resp = client.get("/twin/state/nonexistent")
        assert resp.status_code == 404

    def test_update_twin_state_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].update_state.return_value = MagicMock(
            version_id="v1",
            version_number=2,
        )
        resp = client.post(
            "/twin/state",
            json={
                "entity_id": "entity-001",
                "delta_temperature": 1.0,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["version_id"] == "v1"
        assert data["version_number"] == 2

    def test_get_entity_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        mock_services["twin"].get_current_state.return_value = {
            "name": "Entity 001",
            "location_id": "entity-001",
            "latitude": 12.97,
            "longitude": 77.59,
        }
        resp = client.get("/twin/entity/entity-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == "entity-001"

    def test_get_state_history_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        v = MagicMock()
        v.version_id = "v1"
        v.version_number = 1
        v.created_at = datetime.now(UTC)
        v.created_by = "test"
        v.description = "Initial state"
        mock_services["twin"].get_version_history.return_value = [v]
        resp = client.get("/twin/history/entity-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_versions"] == 1
        assert len(data["versions"]) == 1

    def test_rollback_state_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].rollback = AsyncMock()
        resp = client.post(
            "/twin/rollback",
            json={
                "entity_id": "entity-001",
                "version_number": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back_to_version"] == 1

    def test_get_twin_state_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].get_current_state.side_effect = RuntimeError("fail")
        resp = client.get("/twin/state/entity-001")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Twin state retrieval failed"

    def test_update_twin_state_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].update_state.side_effect = ValueError("Invalid delta")
        resp = client.post(
            "/twin/state",
            json={"entity_id": "entity-001", "delta_temperature": 999},
        )
        assert resp.status_code == 400

    def test_update_twin_state_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].update_state.side_effect = RuntimeError("fail")
        resp = client.post(
            "/twin/state",
            json={"entity_id": "entity-001", "delta_temperature": 1.0},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Twin state update failed"

    def test_get_entity_not_found(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        mock_services["twin"].get_current_state.side_effect = ValueError("Not found")
        resp = client.get("/twin/entity/nonexistent")
        assert resp.status_code == 404

    def test_get_entity_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].get_current_state.side_effect = RuntimeError("fail")
        resp = client.get("/twin/entity/entity-001")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Entity retrieval failed"

    def test_get_state_history_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].get_version_history.side_effect = ValueError("Not found")
        resp = client.get("/twin/history/nonexistent")
        assert resp.status_code == 404

    def test_get_state_history_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].get_version_history.side_effect = RuntimeError("fail")
        resp = client.get("/twin/history/entity-001")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Version history retrieval failed"

    def test_rollback_bad_request(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        mock_services["twin"].rollback.side_effect = ValueError("Invalid version")
        resp = client.post(
            "/twin/rollback",
            json={"entity_id": "entity-001", "version_number": 1},
        )
        assert resp.status_code == 400

    def test_rollback_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["twin"].rollback.side_effect = RuntimeError("fail")
        resp = client.post(
            "/twin/rollback",
            json={"entity_id": "entity-001", "version_number": 1},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "State rollback failed"


class TestForecastRoutes:
    def test_predict_forecast_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        series = MagicMock()
        series.location_id = "loc-001"
        series.target_variable = "temperature_2m"
        series.timestamps = [datetime.now(UTC), datetime.now(UTC)]
        series.values = MagicMock()
        series.values.tolist.return_value = [25.0, 26.0]
        series.model_id = "model-001"
        series.confidence = 0.95
        series.forecast_id = "fc-001"
        series.authenticity = "REAL"
        mock_services["forecast"].predict_with_best.return_value = series
        resp = client.post(
            "/forecast/predict",
            json={
                "location_id": "loc-001",
                "target_variable": "temperature_2m",
                "horizon_hours": 48,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_id"] == "loc-001"
        assert len(data["values"]) == 2

    def test_predict_forecast_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].predict_with_best.side_effect = ValueError("Bad request")
        resp = client.post(
            "/forecast/predict",
            json={
                "location_id": "loc-001",
                "target_variable": "temperature_2m",
                "horizon_hours": 48,
            },
        )
        assert resp.status_code == 400

    def test_list_forecast_models_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        m = MagicMock()
        m.model_id = "m1"
        m.model_type = "xgboost"
        m.target_variable = "temperature_2m"
        m.status = "trained"
        m.training_date = datetime.now(UTC)
        mock_services["forecast"].model_registry.list_models.return_value = [m]
        resp = client.get("/forecast/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_retrain_model_success(self, client: TestClient, mock_services: dict[str, Any]) -> None:
        report = MagicMock()
        report.model_id = "m1"
        report.status = "success"
        report.metrics = {"rmse": 0.5}
        mock_services["forecast"].train_forecast_model.return_value = report
        resp = client.post("/forecast/retrain?target_variable=temperature_2m&model_type=xgboost")
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "success"

    def test_get_model_performance_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        metadata = MagicMock()
        metadata.metrics = {"rmse": 0.5, "mae": 0.3}
        metadata.target_variable = "temperature_2m"
        mock_services["forecast"].model_registry.get.return_value = metadata
        resp = client.get("/forecast/performance/model-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "model-001"
        assert "rmse" in data["metrics"]

    def test_get_model_performance_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].model_registry.get.return_value = None
        resp = client.get("/forecast/performance/nonexistent")
        assert resp.status_code == 404

    def test_predict_forecast_runtime_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].predict_with_best.side_effect = RuntimeError("Runtime error")
        resp = client.post(
            "/forecast/predict",
            json={
                "location_id": "loc-001",
                "target_variable": "temperature_2m",
                "horizon_hours": 48,
            },
        )
        assert resp.status_code == 400

    def test_predict_forecast_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].predict_with_best.side_effect = Exception("Unexpected")
        resp = client.post(
            "/forecast/predict",
            json={
                "location_id": "loc-001",
                "target_variable": "temperature_2m",
                "horizon_hours": 48,
            },
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Forecast prediction failed"

    def test_list_forecast_models_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].model_registry.list_models.side_effect = RuntimeError("fail")
        resp = client.get("/forecast/models")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Failed to list forecast models"

    def test_retrain_model_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].train_forecast_model.side_effect = ValueError("Bad data")
        resp = client.post("/forecast/retrain")
        assert resp.status_code == 400

    def test_retrain_model_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].train_forecast_model.side_effect = KeyError("fail")
        resp = client.post("/forecast/retrain")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Model retraining failed"

    def test_get_model_performance_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["forecast"].model_registry.get.side_effect = RuntimeError("fail")
        resp = client.get("/forecast/performance/model-001")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Model performance retrieval failed"


class TestRAGErrorPaths:
    def test_ask_question_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].ask.side_effect = RuntimeError("fail")
        resp = client.post("/rag/ask", json={"query": "test"})
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Knowledge base query failed"

    def test_ingest_document_validation_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].ingest.side_effect = ValueError("Invalid content")
        resp = client.post(
            "/rag/ingest",
            json={"title": "Test", "source": "test", "content": "content"},
        )
        assert resp.status_code == 400

    def test_ingest_document_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].ingest.side_effect = RuntimeError("fail")
        resp = client.post(
            "/rag/ingest",
            json={"title": "Test", "source": "test", "content": "content"},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Document ingestion failed"

    def test_ingest_batch_validation_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].ingest_batch.side_effect = ValueError("Invalid batch")
        resp = client.post(
            "/rag/ingest/batch",
            json={"documents": [{"title": "Doc1", "source": "test", "content": "Content 1"}]},
        )
        assert resp.status_code == 400

    def test_ingest_batch_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].ingest_batch.side_effect = RuntimeError("fail")
        resp = client.post(
            "/rag/ingest/batch",
            json={"documents": [{"title": "Doc1", "source": "test", "content": "Content 1"}]},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Batch ingestion failed"

    def test_get_context_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].get_context.side_effect = RuntimeError("fail")
        resp = client.post("/rag/context", json={"query": "test"})
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Context retrieval failed"

    def test_list_collections_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["rag"].knowledge_base.list_collections.side_effect = RuntimeError("fail")
        resp = client.get("/rag/collections")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Failed to list collections"

    def test_create_collection_not_implemented(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        if hasattr(kb, "create_collection"):
            del kb.create_collection
        resp = client.post("/rag/collections", json={"name": "New"})
        assert resp.status_code == 501

    def test_create_collection_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        kb.create_collection = MagicMock(side_effect=RuntimeError("fail"))
        resp = client.post("/rag/collections", json={"name": "New"})
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Failed to create collection"

    def test_get_collection_stats_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        kb.get_collection_stats = AsyncMock(side_effect=ValueError("Not found"))
        resp = client.get("/rag/collections/test-coll/stats")
        assert resp.status_code == 404

    def test_get_collection_stats_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        kb.get_collection_stats = AsyncMock(side_effect=RuntimeError("fail"))
        resp = client.get("/rag/collections/test-coll/stats")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Failed to get collection stats"

    def test_search_collection_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        kb = mock_services["rag"].knowledge_base
        kb.search = AsyncMock(side_effect=RuntimeError("fail"))
        resp = client.post("/rag/search/test-coll", json={"query": "search term"})
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Collection search failed"


class TestScenarioErrorPaths:
    def test_create_scenario_validation_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].save_scenario.side_effect = ValueError("Invalid params")
        resp = client.post(
            "/scenario/create",
            json={
                "name": "Test",
                "description": "test",
                "scenario_type": "temperature",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 30,
            },
        )
        assert resp.status_code == 400

    def test_create_scenario_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].save_scenario.side_effect = RuntimeError("fail")
        resp = client.post(
            "/scenario/create",
            json={
                "name": "Test",
                "description": "test",
                "scenario_type": "temperature",
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
                "duration_days": 30,
            },
        )
        assert resp.status_code == 500

    def test_run_scenario_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(scenario_id="s1")
        mock_services["scenario"].run_scenario.side_effect = ValueError("Simulation error")
        resp = client.post("/scenario/run", json={"scenario_id": "s1"})
        assert resp.status_code == 400

    def test_run_scenario_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(scenario_id="s1")
        mock_services["scenario"].run_scenario.side_effect = RuntimeError("fail")
        resp = client.post("/scenario/run", json={"scenario_id": "s1"})
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Scenario simulation failed"

    def test_compare_scenarios_bad_request(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(scenario_id="s1")
        mock_services["scenario"].compare_scenarios.side_effect = ValueError("Compare error")
        resp = client.post("/scenario/compare", json={"scenario_ids": ["s1", "s2"]})
        assert resp.status_code == 400

    def test_compare_scenarios_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(scenario_id="s1")
        mock_services["scenario"].compare_scenarios.side_effect = RuntimeError("fail")
        resp = client.post("/scenario/compare", json={"scenario_ids": ["s1", "s2"]})
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Scenario comparison failed"

    def test_get_scenario_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.side_effect = RuntimeError("fail")
        resp = client.get("/scenario/s1")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Scenario retrieval failed"

    def test_monte_carlo_service_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(scenario_id="s1")
        mc_result = MagicMock()
        mc_result.num_samples = 1000
        mc_result.statistics = {"temperature_2m": {"mean": 25.5}}
        mock_services["scenario"].run_monte_carlo_scenario.return_value = mc_result
        resp = client.post(
            "/scenario/monte-carlo",
            json={
                "scenario_id": "s1",
                "distributions": {"temp": {"mean": 0, "std": 1}},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_id"] == "s1"
        assert data["num_samples"] == 1000

    def test_monte_carlo_service_not_found(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = None
        resp = client.post(
            "/scenario/monte-carlo",
            json={
                "scenario_id": "nonexistent",
                "distributions": {"temp": {"mean": 0, "std": 1}},
            },
        )
        assert resp.status_code == 404

    def test_monte_carlo_service_runtime_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(scenario_id="s1")
        mock_services["scenario"].run_monte_carlo_scenario.side_effect = RuntimeError("MC error")
        resp = client.post(
            "/scenario/monte-carlo",
            json={
                "scenario_id": "s1",
                "distributions": {"temp": {"mean": 0, "std": 1}},
            },
        )
        assert resp.status_code == 501

    def test_monte_carlo_service_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        mock_services["scenario"].load_scenario.return_value = MagicMock(scenario_id="s1")
        mock_services["scenario"].run_monte_carlo_scenario.side_effect = Exception("fail")
        resp = client.post(
            "/scenario/monte-carlo",
            json={
                "scenario_id": "s1",
                "distributions": {"temp": {"mean": 0, "std": 1}},
            },
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Monte Carlo simulation failed"

    def test_generate_from_template_success(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        generator = mock_services["scenario"].generator
        generator.warming_scenario.return_value = MagicMock(
            scenario_id="gen-001",
            name="+1.5C Warming",
            description="Test",
            scenario_type="temperature",
            created_at=datetime.now(UTC),
        )
        mock_services["scenario"].save_scenario.return_value = "gen-001"
        resp = client.post(
            "/scenario/generate/warming_1_5",
            json={
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["scenario_id"] == "gen-001"
        assert data["template"] == "warming_1_5"

    def test_generate_from_template_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/scenario/generate/invalid_template",
            json={
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 404

    def test_generate_from_template_internal_error(
        self, client: TestClient, mock_services: dict[str, Any]
    ) -> None:
        generator = mock_services["scenario"].generator
        generator.warming_scenario.side_effect = RuntimeError("fail")
        resp = client.post(
            "/scenario/generate/warming_1_5",
            json={
                "location_id": "loc-001",
                "latitude": 12.97,
                "longitude": 77.59,
            },
        )
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Template generation failed"
