from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


class TestVerifyApiKey:
    @pytest.mark.asyncio
    async def test_verify_api_key_returns_none_when_disabled(self) -> None:
        from backend.api.dependencies import verify_api_key

        config = MagicMock()
        config.api_key_enabled = False
        with patch("backend.api.dependencies.get_gateway_config", return_value=config):
            result = await verify_api_key(credentials=None)

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_raises_when_missing(self) -> None:
        from backend.api.dependencies import verify_api_key

        config = MagicMock()
        config.api_key_enabled = True
        with (
            patch("backend.api.dependencies.get_gateway_config", return_value=config),
            pytest.raises(HTTPException) as exc,
        ):
            await verify_api_key(credentials=None)

        assert exc.value.status_code == 401
        assert "Missing API key" in exc.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_raises_when_invalid(self) -> None:
        from backend.api.dependencies import verify_api_key

        config = MagicMock()
        config.api_key_enabled = True
        config.api_key = "valid-key"
        with patch("backend.api.dependencies.get_gateway_config", return_value=config):
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-key")
            with pytest.raises(HTTPException) as exc:
                await verify_api_key(credentials=creds)

        assert exc.value.status_code == 401
        assert "Invalid API key" in exc.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_returns_key_when_valid(self) -> None:
        from backend.api.dependencies import verify_api_key

        config = MagicMock()
        config.api_key_enabled = True
        config.api_key = "valid-key"
        with patch("backend.api.dependencies.get_gateway_config", return_value=config):
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-key")
            result = await verify_api_key(credentials=creds)

        assert result == "valid-key"

    @pytest.mark.asyncio
    async def test_verify_api_key_with_dependency_injection(self) -> None:
        from backend.api.dependencies import verify_api_key

        config = MagicMock()
        config.api_key_enabled = True
        config.api_key = "test-key"
        with patch("backend.api.dependencies.get_gateway_config", return_value=config):
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-key")
            result = await verify_api_key(credentials=creds)

        assert result == "test-key"


class TestServiceGetters:
    def test_get_risk_service_initializes_once(self) -> None:
        from backend.api.dependencies import get_risk_service

        with patch("climatedt.risk.service.RiskService") as mock_cls:
            svc1 = get_risk_service()
            svc2 = get_risk_service()
            mock_cls.assert_called_once()
            assert svc1 is svc2

    def test_get_scenario_service_initializes_once(self) -> None:
        from backend.api.dependencies import get_scenario_service

        with patch("climatedt.scenario.service.ScenarioService") as mock_cls:
            svc1 = get_scenario_service()
            svc2 = get_scenario_service()
            mock_cls.assert_called_once()
            assert svc1 is svc2

    def test_get_feedback_capture_initializes_once(self) -> None:
        from backend.api.dependencies import get_feedback_capture

        with patch("climatedt.feedback.capture.FeedbackCaptureService") as mock_cls:
            svc1 = get_feedback_capture()
            svc2 = get_feedback_capture()
            mock_cls.assert_called_once()
            assert svc1 is svc2

    def test_get_feedback_analyzer_initializes_once(self) -> None:
        from backend.api.dependencies import get_feedback_analyzer

        with (
            patch("climatedt.feedback.storage.FeedbackStore") as mock_store,
            patch("climatedt.feedback.analysis.FeedbackAnalyzer") as mock_analyzer,
        ):
            svc1 = get_feedback_analyzer()
            svc2 = get_feedback_analyzer()
            mock_store.assert_called_once()
            mock_analyzer.assert_called_once()
            assert svc1 is svc2

    def test_get_twin_manager_initializes_once(self) -> None:
        from backend.api.dependencies import get_twin_manager

        with patch("climatedt.twin.state_manager.TwinStateManager") as mock_cls:
            svc1 = get_twin_manager()
            svc2 = get_twin_manager()
            mock_cls.assert_called_once()
            assert svc1 is svc2

    def test_get_rag_service_initializes_once(self) -> None:
        from backend.api.dependencies import get_rag_service

        with (
            patch("climatedt.rag.vector_store.VectorStore") as mock_vs,
            patch("climatedt.rag.service.RAGService") as mock_rag,
        ):
            svc1 = get_rag_service()
            svc2 = get_rag_service()
            mock_vs.assert_called_once_with(dimension=384)
            mock_rag.assert_called_once()
            assert svc1 is svc2

    def test_get_forecast_pipeline_initializes_once(self) -> None:
        from backend.api.dependencies import get_forecast_pipeline

        with patch("climatedt.pipeline.forecast_pipeline.ForecastPipeline") as mock_fp:
            svc1 = get_forecast_pipeline()
            svc2 = get_forecast_pipeline()
            mock_fp.assert_called_once()
            assert svc1 is svc2
