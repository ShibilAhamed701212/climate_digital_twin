"""Data models for the RAG Knowledge Base."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DocumentFormat(Enum):
    PDF = "pdf"
    MARKDOWN = "md"
    TEXT = "txt"
    CSV = "csv"
    JSON = "json"


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    source: str
    category: str
    file_path: str
    format: DocumentFormat
    content: str
    date: str = ""
    region: str = ""
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "file_path": self.file_path,
            "format": self.format.value,
            "content_preview": self.content[:200],
            "date": self.date,
            "region": self.region,
            "keywords": self.keywords,
        }


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    source: str
    category: str
    content: str
    chunk_number: int
    page_number: int = 0
    date: str = ""
    region: str = ""
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "content": self.content,
            "chunk_number": self.chunk_number,
            "page_number": self.page_number,
            "date": self.date,
            "region": self.region,
            "keywords": self.keywords,
        }


@dataclass
class IndexingResult:
    document_id: str
    title: str
    num_chunks: int
    success: bool
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "num_chunks": self.num_chunks,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    title: str
    source: str
    category: str
    content: str
    score: float
    chunk_number: int
    page_number: int = 0
    date: str = ""
    region: str = ""
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "content": self.content,
            "score": self.score,
            "chunk_number": self.chunk_number,
            "page_number": self.page_number,
            "date": self.date,
            "region": self.region,
            "keywords": self.keywords,
        }


@dataclass(frozen=True)
class RetrievalContext:
    query: str
    results: list[SearchResult]
    context_text: str
    total_results: int = 0
    filtered_by_metadata: bool = False
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "context_text": self.context_text,
            "total_results": self.total_results,
            "filtered_by_metadata": self.filtered_by_metadata,
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class SourceInfo:
    category: str
    count: int
    last_indexed: str = ""
