import logging
import uuid
from typing import Any

from knowledge.chunkers import TextChunker
from knowledge.config_loader import load_rag_config
from knowledge.embeddings.embedding_model import EmbeddingModel
from knowledge.models import Document as KDocument
from knowledge.models import DocumentFormat
from knowledge.vector_store.faiss_store import FAISSStore

logger = logging.getLogger(__name__)


class DocumentIngestion:
    def __init__(
        self,
        embed_service: EmbeddingModel,
        vector_store: FAISSStore,
    ) -> None:
        self._embed = embed_service
        self._store = vector_store
        config = load_rag_config()
        rag_cfg = config.get("rag", {})
        self._chunker = TextChunker(
            chunk_size=rag_cfg.get("chunk_size", 700),
            chunk_overlap=rag_cfg.get("chunk_overlap", 120),
        )

    def ingest(self, doc: Any) -> list[Any]:
        content = (
            doc.content
            if hasattr(doc, "content")
            else (doc.get("content", "") if isinstance(doc, dict) else str(doc))
        )
        title = (
            doc.title
            if hasattr(doc, "title")
            else (doc.get("title", "") if isinstance(doc, dict) else "")
        )
        source = (
            doc.source
            if hasattr(doc, "source")
            else (doc.get("source", "") if isinstance(doc, dict) else "")
        )
        document_id = (
            doc.document_id
            if hasattr(doc, "document_id")
            else (doc.get("document_id", "") if isinstance(doc, dict) else uuid.uuid4().hex[:16])
        )

        kdoc = KDocument(
            document_id=document_id,
            title=title or "Untitled",
            source=source or "unknown",
            category="general",
            file_path="",
            format=DocumentFormat.TEXT,
            content=content,
        )
        chunks = self._chunker.chunk_document(kdoc)
        texts = [c.content for c in chunks]
        embeddings = self._embed.encode(texts)
        self._store.add(chunks, embeddings)
        logger.info("Ingested document %s: %d chunks", document_id, len(chunks))
        return chunks
