"""End-to-end indexing pipeline.

Orchestrates: document loading → chunking → embedding → vector store storage.
Supports single document, directory, and batch indexing with logging.
"""

import logging
import os
from pathlib import Path
from typing import Any

from knowledge.chunkers import TextChunker
from knowledge.config_loader import load_rag_config
from knowledge.embeddings import EmbeddingModel
from knowledge.loaders import get_loader, guess_format
from knowledge.models import IndexingResult
from knowledge.vector_store import FAISSStore

logger = logging.getLogger(__name__)


class IndexingPipeline:
    """End-to-end pipeline for indexing documents into the knowledge base.

    Usage:
        pipeline = IndexingPipeline()
        result = pipeline.index_document("path/to/doc.md")
        pipeline.index_directory("knowledge/documents/government")
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_rag_config()
        self.config = config
        rag_cfg = config.get("rag", {})
        self.chunker = TextChunker(
            chunk_size=rag_cfg.get("chunk_size", 700),
            chunk_overlap=rag_cfg.get("chunk_overlap", 120),
        )
        self.embedding_model = EmbeddingModel(config)
        vs_cfg = config.get("vector_store", {})
        self.vector_store = FAISSStore(
            index_path=vs_cfg.get("index_path", "knowledge/vector_store/index.faiss"),
            metadata_path=vs_cfg.get("metadata_path", "knowledge/vector_store/metadata.pkl"),
            dimension=rag_cfg.get("embedding_dimension", 384),
        )
        self.supported_formats = config.get("documents", {}).get("supported_formats", ["md", "txt", "csv", "json"])

    def index_document(self, file_path: str, **metadata: Any) -> IndexingResult:
        """Index a single document.

        Args:
            file_path: Path to the document.
            **metadata: Optional metadata overrides (title, source, category, etc.).

        Returns:
            IndexingResult with status and chunk count.
        """
        fmt = guess_format(file_path)
        if fmt is None:
            file_ext = os.path.splitext(file_path)[1].lstrip(".").lower()
            return IndexingResult(
                document_id="",
                title=os.path.basename(file_path),
                num_chunks=0,
                success=False,
                error=f"Unsupported format: .{file_ext}",
            )
        if fmt.value not in self.supported_formats:
            return IndexingResult(
                document_id="",
                title=os.path.basename(file_path),
                num_chunks=0,
                success=False,
                error=f"Format '{fmt.value}' not in supported list: {self.supported_formats}",
            )
        try:
            loader = get_loader(file_path)
            doc = loader.load(file_path, **metadata)
        except Exception as e:
            return IndexingResult(
                document_id="",
                title=os.path.basename(file_path),
                num_chunks=0,
                success=False,
                error=str(e),
            )

        try:
            chunks = self.chunker.chunk_document(doc)
            texts = [c.content for c in chunks]
            embeddings = self.embedding_model.encode(texts)
            self.vector_store.add(chunks, embeddings)
            logger.info("Indexed %s: %d chunks", file_path, len(chunks))
            return IndexingResult(
                document_id=doc.document_id,
                title=doc.title,
                num_chunks=len(chunks),
                success=True,
            )
        except Exception as e:
            logger.error("Failed to index %s: %s", file_path, e)
            return IndexingResult(
                document_id=doc.document_id if "doc" in dir() else "",
                title=doc.title if "doc" in dir() else os.path.basename(file_path),
                num_chunks=0,
                success=False,
                error=str(e),
            )

    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        **metadata: Any,
    ) -> list[IndexingResult]:
        """Index all supported documents in a directory.

        Args:
            directory: Path to the directory.
            recursive: Whether to scan subdirectories.
            **metadata: Metadata to apply to all documents.

        Returns:
            List of IndexingResult for each file.
        """
        results: list[IndexingResult] = []
        base = Path(directory)
        if not base.exists():
            logger.warning("Directory not found: %s", directory)
            return results

        pattern = "**/*" if recursive else "*"
        for file_path in base.glob(pattern):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lstrip(".").lower()
            if ext not in self.supported_formats:
                continue
            result = self.index_document(str(file_path), **metadata)
            results.append(result)

        logger.info("Indexed %d of %d files in %s", sum(1 for r in results if r.success), len(results), directory)
        return results
