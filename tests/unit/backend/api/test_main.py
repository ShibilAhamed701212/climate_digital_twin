from __future__ import annotations

import logging
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.config import GatewayConfig


@pytest.fixture
def gateway_config() -> GatewayConfig:
    return GatewayConfig(
        app_title="Climate Digital Twin API",
        app_description="Test description",
        app_version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        api_key_enabled=False,
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def app(gateway_config: GatewayConfig) -> Any:
    # Import BEFORE patching: importing inside the patch context would bind
    # the mock into backend.api.main permanently (patch would save/restore
    # the mock itself), leaking the test config into later tests.
    from backend.api.main import create_app

    with (
        patch("backend.api.config.get_gateway_config", return_value=gateway_config),
        patch("backend.api.main.get_gateway_config", return_value=gateway_config),
        patch("backend.api.dependencies.get_risk_service", return_value=AsyncMock()),
        patch("backend.api.dependencies.get_scenario_service", return_value=AsyncMock()),
        patch("backend.api.dependencies.get_feedback_capture", return_value=AsyncMock()),
        patch("backend.api.dependencies.get_twin_manager", return_value=AsyncMock()),
    ):
        return create_app()


@pytest.fixture
def client(app: Any) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestMainApp:
    def test_create_app_success(self, app: Any) -> None:
        assert app.title == "Climate Digital Twin API"
        assert app.version == "0.1.0"
        assert app.docs_url == "/docs"
        assert app.openapi_url == "/openapi.json"

    def test_root_endpoint(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Climate Digital Twin API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"
        assert data["openapi"] == "/openapi.json"

    def test_root_endpoint_not_in_openapi(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/" not in paths

    def test_health_endpoint_included(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_openapi_operation_ids_unique(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        ids: list[str] = []
        for path_item in spec["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    ids.append(operation["operationId"])
        assert ids
        assert len(ids) == len(set(ids))

    def test_value_error_handler_returns_400(self, app: Any) -> None:
        @app.get("/trigger-value-error")
        async def trigger():
            raise ValueError("bad input")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/trigger-value-error")
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"] == "bad input"
        assert data["error_code"] == "BAD_REQUEST"
        assert "timestamp" in data

    def test_general_error_handler_returns_500(self, app: Any) -> None:
        @app.get("/trigger-error")
        async def trigger():
            raise RuntimeError("server failure")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/trigger-error")
        assert resp.status_code == 500
        data = resp.json()
        assert data["detail"] == "An internal server error occurred"
        assert data["error_code"] == "INTERNAL_ERROR"
        assert "timestamp" in data

    def test_cors_headers_present(self, client: TestClient) -> None:
        resp = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_feedback_general_value_error(self, app: Any, client: TestClient) -> None:
        from backend.api.routes import feedback as feedback_mod

        svc = AsyncMock()
        svc.capture_general_feedback.side_effect = ValueError("Invalid input")
        app.dependency_overrides[feedback_mod.get_feedback_capture] = lambda: svc
        try:
            resp = client.post(
                "/feedback/general",
                json={"location_id": "loc-001", "rating": 3, "feedback_type": "general"},
            )
            assert resp.status_code == 400
            assert resp.json()["detail"] == "Invalid input"
        finally:
            app.dependency_overrides.pop(feedback_mod.get_feedback_capture, None)

    def test_twin_get_entity_not_found(self, app: Any, client: TestClient) -> None:
        from backend.api.routes import twin as twin_mod

        mgr = AsyncMock()
        mgr.get_current_state.return_value = None
        app.dependency_overrides[twin_mod.get_twin_manager] = lambda: mgr
        try:
            resp = client.get("/twin/entity/nonexistent-id")
            assert resp.status_code == 404
            assert "nonexistent-id" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(twin_mod.get_twin_manager, None)

    def test_routers_included(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/health" in paths
        assert "/risk/assess" in paths
        assert "/scenario/create" in paths
        assert "/rag/ask" in paths
        assert "/feedback/risk" in paths
        assert "/twin/state/{entity_id}" in paths
        assert "/forecast/predict" in paths


class TestMiddleware:
    def test_security_headers_present(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-xss-protection") == "1; mode=block"

    def test_request_timing_header_present(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert "x-request-timing-ms" in resp.headers
        timing = float(resp.headers["x-request-timing-ms"])
        assert timing >= 0

    @staticmethod
    def _patch_get_gateway_config(config: GatewayConfig):
        """Patch get_gateway_config at all import sites."""
        return (
            patch("backend.api.config.get_gateway_config", return_value=config),
            patch("backend.api.middleware.get_gateway_config", return_value=config),
        )

    def test_api_key_auth_blocks_without_key(self) -> None:
        config = GatewayConfig(api_key_enabled=True, api_key="secret-key")
        p1, p2 = self._patch_get_gateway_config(config)
        # Import BEFORE patching so the real function is what patch saves
        # and restores in backend.api.main's namespace.
        from backend.api.main import create_app

        with (
            p1,
            p2,
            patch("backend.api.dependencies.get_risk_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_scenario_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_feedback_capture", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_twin_manager", return_value=AsyncMock()),
        ):
            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/risk/assess",
                json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
            )
        assert resp.status_code == 401, f"Got {resp.status_code}: {resp.text}"

    def test_api_key_auth_accepts_valid_key(self) -> None:
        config = GatewayConfig(api_key_enabled=True, api_key="secret-key")
        p1, p2 = self._patch_get_gateway_config(config)
        # Import BEFORE patching so the real function is what patch saves
        # and restores in backend.api.main's namespace.
        from backend.api.main import create_app

        with (
            p1,
            p2,
            patch("backend.api.dependencies.get_risk_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_scenario_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_feedback_capture", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_twin_manager", return_value=AsyncMock()),
        ):
            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/risk/assess",
                json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
                headers={"Authorization": "Bearer secret-key"},
            )
        assert resp.status_code != 401, f"Got {resp.status_code}: {resp.text}"

    def test_api_key_auth_rejects_invalid_key(self) -> None:
        config = GatewayConfig(api_key_enabled=True, api_key="secret-key")
        p1, p2 = self._patch_get_gateway_config(config)
        # Import BEFORE patching so the real function is what patch saves
        # and restores in backend.api.main's namespace.
        from backend.api.main import create_app

        with (
            p1,
            p2,
            patch("backend.api.dependencies.get_risk_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_scenario_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_feedback_capture", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_twin_manager", return_value=AsyncMock()),
        ):
            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/risk/assess",
                json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
                headers={"Authorization": "Bearer wrong-key"},
            )
        assert resp.status_code == 401, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["detail"] == "Invalid API key"

    def test_slow_request_logs_warning(self, app: Any, caplog: Any) -> None:
        caplog.set_level(logging.WARNING)
        import asyncio

        @app.get("/slow")
        async def slow() -> dict[str, bool]:
            await asyncio.sleep(1.1)
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/slow")
        assert resp.status_code == 200
        assert "Slow request" in caplog.text

    def test_api_key_auth_rejects_wrong_format(self) -> None:
        config = GatewayConfig(api_key_enabled=True, api_key="secret-key")
        p1, p2 = self._patch_get_gateway_config(config)
        # Import BEFORE patching so the real function is what patch saves
        # and restores in backend.api.main's namespace.
        from backend.api.main import create_app

        with (
            p1,
            p2,
            patch("backend.api.dependencies.get_risk_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_scenario_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_feedback_capture", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_twin_manager", return_value=AsyncMock()),
        ):
            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/risk/assess",
                json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
                headers={"Authorization": "no-bearer-prefix"},
            )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"] == "Missing API key. Provide it via Authorization: Bearer <key>"

    def test_rate_limiter_returns_429(self, client: TestClient) -> None:
        with patch("backend.api.middleware._RATE_LIMIT_MAX", 0):
            resp = client.post(
                "/risk/assess",
                json={"location_id": "loc-001", "latitude": 0, "longitude": 0},
            )
        assert resp.status_code == 429
        data = resp.json()
        assert data["detail"] == "Rate limit exceeded. Try again later."
        assert data["error_code"] == "TOO_MANY_REQUESTS"
        assert "retry_after_seconds" in data

    def test_cors_preflight_with_api_key_enabled(self) -> None:
        config = GatewayConfig(
            api_key_enabled=True,
            api_key="secret-key",
            cors_origins=["http://localhost:3000"],
        )
        p1, p2 = self._patch_get_gateway_config(config)
        # Import BEFORE patching so the real function is what patch saves
        # and restores in backend.api.main's namespace.
        from backend.api.main import create_app

        with (
            p1,
            p2,
            patch("backend.api.dependencies.get_risk_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_scenario_service", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_feedback_capture", return_value=AsyncMock()),
            patch("backend.api.dependencies.get_twin_manager", return_value=AsyncMock()),
        ):
            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.options(
                "/health",
                headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
            )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestReportService:
    def test_report_health(self) -> None:
        with patch("backend.api.report.ReportClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            from backend.api import report

            client = TestClient(report.app)
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["service"] == "report-service"

    def test_generate_report_summary(self) -> None:
        with patch("backend.api.report.ReportClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.generate_report.return_value = {"summary": "Climate report data"}
            mock_client_cls.return_value = mock_client
            from backend.api import report

            client = TestClient(report.app)
            resp = client.post("/report", json={"location": "Bangalore", "report_type": "summary"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["location"] == "Bangalore"
            assert data["report_type"] == "summary"
            assert "report" in data

    def test_generate_report_detailed(self) -> None:
        with patch("backend.api.report.ReportClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.generate_report.return_value = {"detail": "Detailed report"}
            mock_client_cls.return_value = mock_client
            from backend.api import report

            client = TestClient(report.app)
            resp = client.post("/report", json={"location": "Mumbai", "report_type": "detailed"})
            assert resp.status_code == 200

    def test_generate_report_risk_type(self) -> None:
        with patch("backend.api.report.ReportClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.generate_report.return_value = {"risk": "High"}
            mock_client_cls.return_value = mock_client
            from backend.api import report

            client = TestClient(report.app)
            resp = client.post("/report", json={"location": "Delhi", "report_type": "risk"})
            assert resp.status_code == 200

    def test_generate_report_forecast_type(self) -> None:
        with patch("backend.api.report.ReportClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.generate_report.return_value = {"forecast": "Sunny"}
            mock_client_cls.return_value = mock_client
            from backend.api import report

            client = TestClient(report.app)
            resp = client.post("/report", json={"location": "Chennai", "report_type": "forecast"})
            assert resp.status_code == 200

    def test_generate_report_invalid_type(self) -> None:
        with patch("backend.api.report.ReportClient"):
            from backend.api import report

            client = TestClient(report.app)
            resp = client.post("/report", json={"location": "Bangalore", "report_type": "invalid"})
            assert resp.status_code == 400
            data = resp.json()
            assert "report_type must be one of" in data["detail"]

    def test_generate_report_missing_location(self) -> None:
        with patch("backend.api.report.ReportClient"):
            from backend.api import report

            client = TestClient(report.app)
            resp = client.post("/report", json={"report_type": "summary"})
            assert resp.status_code == 422


class TestLifespan:
    """Test the lifespan context manager (lines 28-61)."""

    @pytest.fixture(autouse=True)
    def _reset_config(self):
        from backend.api import config as cfg_mod

        saved = cfg_mod._config
        cfg_mod._config = None
        yield
        cfg_mod._config = saved

    @pytest.fixture
    def mock_services(self):
        with (
            patch("backend.api.dependencies.get_risk_service", return_value=MagicMock()),
            patch("backend.api.dependencies.get_scenario_service", return_value=MagicMock()),
            patch("backend.api.dependencies.get_feedback_capture", return_value=MagicMock()),
            patch("backend.api.dependencies.get_twin_manager", return_value=MagicMock()),
        ):
            yield

    async def _run_lifespan(self, app: Any) -> None:
        from backend.api.main import lifespan

        async with lifespan(app):
            pass

    def test_lifespan_initializes_all_services(self, mock_services: Any, caplog: Any) -> None:
        caplog.set_level(logging.INFO)
        import asyncio

        asyncio.run(self._run_lifespan(MagicMock()))
        assert "Climate Digital Twin API v2.1.0 starting up" in caplog.text
        assert "4/4 services initialized" in caplog.text

    def test_lifespan_catches_module_not_found(self, caplog: Any) -> None:
        caplog.set_level(logging.INFO)
        with (
            patch(
                "backend.api.dependencies.get_risk_service",
                side_effect=ModuleNotFoundError("no risk"),
            ),
            patch(
                "backend.api.dependencies.get_scenario_service",
                side_effect=ModuleNotFoundError("no scenario"),
            ),
            patch(
                "backend.api.dependencies.get_feedback_capture",
                side_effect=ModuleNotFoundError("no feedback"),
            ),
            patch(
                "backend.api.dependencies.get_twin_manager",
                side_effect=ModuleNotFoundError("no twin"),
            ),
        ):
            import asyncio

            asyncio.run(self._run_lifespan(MagicMock()))
        assert "0/4 services initialized" in caplog.text
        assert "unavailable (will proxy)" in caplog.text

    def test_lifespan_shutdown_logs(self, mock_services: Any, caplog: Any) -> None:
        caplog.set_level(logging.INFO)
        import asyncio

        asyncio.run(self._run_lifespan(MagicMock()))
        assert "shutting down" in caplog.text


class TestMainFunction:
    def test_main_calls_uvicorn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GATEWAY_HOST", "0.0.0.0")
        monkeypatch.setenv("GATEWAY_PORT", "8001")
        mock_uvicorn = MagicMock()
        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            # Clean module cache to force fresh import with new env vars
            for mod in list(sys.modules):
                if mod.startswith("backend.api"):
                    sys.modules.pop(mod, None)
            from backend.api.main import main

            main()
            mock_uvicorn.run.assert_called_once()
            _call_args, kwargs = mock_uvicorn.run.call_args
            assert kwargs["host"] == "0.0.0.0"
            assert kwargs["port"] == 8001
            assert kwargs["reload"] is False
            assert kwargs["log_level"] == "info"
