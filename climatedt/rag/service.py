import uuid
from typing import Any

from climatedt.rag.ingestion import DocumentIngestion
from climatedt.rag.knowledge_base import KnowledgeBase
from climatedt.rag.retrieval import RetrievalService
from knowledge.api.search_api import KnowledgeAPI
from knowledge.models import SearchResult


class RAGService:
    def __init__(
        self,
        ingestion: DocumentIngestion,
        retrieval: RetrievalService,
        knowledge_base: KnowledgeBase,
    ) -> None:
        self._ingestion = ingestion
        self._retrieval = retrieval
        self._knowledge_base = knowledge_base
        self._api = KnowledgeAPI()
        self.knowledge_base = knowledge_base

    async def ask(
        self,
        query: str,
        k: int = 5,
        _collection_id: str | None = None,
    ) -> list[Any]:
        # Use the shared retrieval service instead of KnowledgeAPI (which has its own store)
        results = await self._knowledge_base.search(query, k=k, _collection_id=_collection_id)
        return results

    async def ingest(self, doc: Any) -> list[Any]:
        chunks = self._ingestion.ingest(doc)
        return chunks

    async def ingest_batch(self, documents: list[Any]) -> dict[str, list[Any]]:
        results: dict[str, list[Any]] = {}
        for doc in documents:
            did = doc.document_id if hasattr(doc, "document_id") else uuid.uuid4().hex[:16]
            results[did] = self._ingestion.ingest(doc)
        return results

    async def get_context(self, query: str, max_tokens: int = 2000) -> str:
        return self._api.get_context(query, max_tokens=max_tokens)


def _wrap_result(r: SearchResult) -> Any:
    class WrappedChunk:
        def __init__(self) -> None:
            self.chunk_id = r.chunk_id
            self.document_id = r.document_id
            self.text = r.content[:500] if r.content else ""
            self.metadata = {
                "title": r.title,
                "source": r.source,
                "category": r.category,
            }

    class WrappedResult:
        def __init__(self) -> None:
            self.chunk = WrappedChunk()
            self.score = r.score
            self.rank = 0

    return WrappedResult()
