from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.config import get_gateway_config

_logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_risk_service: Any = None
_scenario_service: Any = None
_rag_service: Any = None
_feedback_capture: Any = None
_feedback_analyzer: Any = None
_twin_manager: Any = None
_forecast_pipeline: Any = None


def get_risk_service() -> Any:
    global _risk_service
    if _risk_service is None:
        from climatedt.risk.service import RiskService

        _risk_service = RiskService()
        _logger.info("RiskService initialized")
    return _risk_service


def get_scenario_service() -> Any:
    global _scenario_service
    if _scenario_service is None:
        from climatedt.scenario.service import ScenarioService

        _scenario_service = ScenarioService()
        _logger.info("ScenarioService initialized")
    return _scenario_service


def get_rag_service() -> Any:
    global _rag_service
    if _rag_service is None:
        from climatedt.rag.embeddings import EmbeddingService
        from climatedt.rag.ingestion import DocumentIngestion
        from climatedt.rag.knowledge_base import KnowledgeBase
        from climatedt.rag.retrieval import RetrievalService
        from climatedt.rag.service import RAGService
        from climatedt.rag.vector_store import VectorStore

        vector_store = VectorStore(dimension=384)
        embed_service = EmbeddingService()
        ingestion = DocumentIngestion(embed_service=embed_service, vector_store=vector_store)
        retrieval = RetrievalService(vector_store=vector_store)
        knowledge_base = KnowledgeBase(vector_store=vector_store, retrieval_service=retrieval)
        _rag_service = RAGService(
            ingestion=ingestion,
            retrieval=retrieval,
            knowledge_base=knowledge_base,
        )
        _logger.info("RAGService initialized")
    return _rag_service


def get_feedback_capture() -> Any:
    global _feedback_capture
    if _feedback_capture is None:
        from climatedt.feedback.capture import FeedbackCaptureService

        _feedback_capture = FeedbackCaptureService()
        _logger.info("FeedbackCaptureService initialized")
    return _feedback_capture


def get_feedback_analyzer() -> Any:
    global _feedback_analyzer
    if _feedback_analyzer is None:
        from climatedt.feedback.analysis import FeedbackAnalyzer
        from climatedt.feedback.storage import FeedbackStore

        store = FeedbackStore()
        _feedback_analyzer = FeedbackAnalyzer(feedback_store=store)
        _logger.info("FeedbackAnalyzer initialized")
    return _feedback_analyzer


def get_twin_manager() -> Any:
    global _twin_manager
    if _twin_manager is None:
        from climatedt.twin.state_manager import TwinStateManager

        _twin_manager = TwinStateManager()
        _logger.info("TwinStateManager initialized")
    return _twin_manager


def get_forecast_pipeline() -> Any:
    global _forecast_pipeline
    if _forecast_pipeline is None:
        from climatedt.ml.features import FeatureEngine
        from climatedt.pipeline.forecast_pipeline import ForecastPipeline

        _logger.info("ForecastPipeline initialized (minimal - needs store/registry)")
        from climatedt.ml.models import ModelRegistry
        from climatedt.storage.parquet_store import ParquetObservationStore

        store = ParquetObservationStore()
        registry = ModelRegistry()
        feature_engine = FeatureEngine()
        _forecast_pipeline = ForecastPipeline(
            feature_engine=feature_engine,
            model_registry=registry,
            observation_store=store,
        )
    return _forecast_pipeline


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> str | None:
    config = get_gateway_config()
    if not config.api_key_enabled:
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide it via Authorization: Bearer <key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(credentials.credentials, config.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
