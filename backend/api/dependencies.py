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
_feedback_store: Any = None
_feedback_capture: Any = None
_feedback_analyzer: Any = None
_twin_manager: Any = None
_forecast_pipeline: Any = None


def get_feedback_store() -> Any:
    global _feedback_store
    if _feedback_store is None:
        from climatedt.feedback.storage import FeedbackStore

        _feedback_store = FeedbackStore()
        _logger.info("FeedbackStore initialized")
    return _feedback_store


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
    """Use the indexed knowledge FAISS store (same source as :8004)."""
    global _rag_service
    if _rag_service is None:
        from types import SimpleNamespace

        from knowledge.api.search_api import KnowledgeAPI

        knowledge_api = KnowledgeAPI()

        class _KnowledgeRAGAdapter:
            def __init__(self, api: KnowledgeAPI) -> None:
                self._api = api

            async def ask(
                self, query: str, k: int = 5, _collection_id: str | None = None
            ) -> list[Any]:
                results = self._api.search(query=query, top_k=k, score_threshold=0.0)
                adapted: list[Any] = []
                for rank, item in enumerate(results, start=1):
                    data = item.to_dict() if hasattr(item, "to_dict") else dict(item)
                    chunk = SimpleNamespace(
                        chunk_id=data.get("chunk_id", ""),
                        document_id=data.get("document_id", ""),
                        text=data.get("content", data.get("text", "")),
                        metadata={
                            "title": data.get("title", ""),
                            "source": data.get("source", ""),
                            "category": data.get("category", ""),
                        },
                    )
                    adapted.append(
                        SimpleNamespace(chunk=chunk, score=float(data.get("score", 0)), rank=rank)
                    )
                return adapted

            async def ingest(self, doc: Any) -> list[Any]:
                from pathlib import Path

                title = getattr(doc, "title", "untitled")
                content = getattr(doc, "content", "")
                source = getattr(doc, "source", "manual")
                docs = Path("knowledge/documents/manual")
                docs.mkdir(parents=True, exist_ok=True)
                safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title.lower())[:60]
                path = docs / f"{safe or 'doc'}.md"
                path.write_text(f"# {title}\n\nSource: {source}\n\n{content}", encoding="utf-8")
                result = self._api.index_document(
                    str(path), category="manual", title=title, source=source
                )
                n_chunks = int(getattr(result, "num_chunks", 0) or 0)
                doc_id = getattr(result, "document_id", None) or getattr(
                    doc, "document_id", path.stem
                )
                if hasattr(doc, "document_id"):
                    doc.document_id = doc_id
                return [SimpleNamespace(chunk_id=f"{doc_id}-{i}") for i in range(max(n_chunks, 1))]

            async def ingest_batch(self, documents: list[Any]) -> dict[str, list[Any]]:
                out: dict[str, list[Any]] = {}
                for doc in documents:
                    chunks = await self.ingest(doc)
                    out[getattr(doc, "document_id", "")] = chunks
                return out

        _rag_service = _KnowledgeRAGAdapter(knowledge_api)
        # Provide a knowledge_base shim so /rag/collections works.
        class _KBShim:
            def __init__(self, api: KnowledgeAPI) -> None:
                self._api = api
            def list_collections(self) -> list[dict[str, str]]:
                # Return a single default collection derived from the store stats.
                try:
                    store = self._api.vector_store
                    n_chunks = len(store.chunks) if hasattr(store, "chunks") else 0
                except Exception:
                    n_chunks = 0
                return [{"id": "default", "name": "Default Collection", "chunk_count": n_chunks}]
        _rag_service.knowledge_base = _KBShim(knowledge_api)  # type: ignore[attr-defined]
        _logger.info("RAGService initialized via KnowledgeAPI adapter")
    return _rag_service


def get_feedback_capture() -> Any:
    global _feedback_capture
    if _feedback_capture is None:
        from climatedt.feedback.capture import FeedbackCaptureService

        _feedback_capture = FeedbackCaptureService(store=get_feedback_store())
        _logger.info("FeedbackCaptureService initialized")
    return _feedback_capture


def get_feedback_analyzer() -> Any:
    global _feedback_analyzer
    if _feedback_analyzer is None:
        from climatedt.feedback.analysis import FeedbackAnalyzer

        _feedback_analyzer = FeedbackAnalyzer(feedback_store=get_feedback_store())
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
