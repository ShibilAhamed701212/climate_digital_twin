"""Unit tests for RAG data models."""

import pytest


class TestDocumentFormat:
    def test_enum_values(self):
        from knowledge.models import DocumentFormat

        assert DocumentFormat.PDF.value == "pdf"
        assert DocumentFormat.MARKDOWN.value == "md"
        assert DocumentFormat.TEXT.value == "txt"
        assert DocumentFormat.CSV.value == "csv"
        assert DocumentFormat.JSON.value == "json"


class TestDocument:
    def test_create_minimal(self):
        from knowledge.models import Document, DocumentFormat

        doc = Document(
            document_id="doc_001",
            title="Test Doc",
            source="local",
            category="general",
            file_path="/path/to/doc.md",
            format=DocumentFormat.MARKDOWN,
            content="Hello world",
        )
        assert doc.document_id == "doc_001"
        assert doc.content == "Hello world"

    def test_to_dict(self):
        from knowledge.models import Document, DocumentFormat

        doc = Document("doc_001", "Test", "local", "general", "/path/f.md", DocumentFormat.MARKDOWN, "content")
        d = doc.to_dict()
        assert d["document_id"] == "doc_001"
        assert d["format"] == "md"

    def test_immutable(self):
        from knowledge.models import Document, DocumentFormat

        doc = Document("doc_001", "Test", "local", "general", "/path/f.md", DocumentFormat.MARKDOWN, "content")
        with pytest.raises(AttributeError):
            doc.title = "Changed"


class TestChunk:
    def test_create(self):
        from knowledge.models import Chunk

        c = Chunk(
            chunk_id="chunk_001",
            document_id="doc_001",
            title="Test",
            source="local",
            category="general",
            content="Some text",
            chunk_number=1,
        )
        assert c.chunk_id == "chunk_001"
        assert c.chunk_number == 1

    def test_to_dict(self):
        from knowledge.models import Chunk

        c = Chunk("chunk_001", "doc_001", "Test", "local", "general", "text", 1)
        d = c.to_dict()
        assert d["chunk_id"] == "chunk_001"


class TestIndexingResult:
    def test_success(self):
        from knowledge.models import IndexingResult

        r = IndexingResult("doc_001", "Test", 10, True)
        assert r.success
        assert r.num_chunks == 10

    def test_failure(self):
        from knowledge.models import IndexingResult

        r = IndexingResult("doc_001", "Test", 0, False, error="Failed to parse")
        assert not r.success
        assert r.error == "Failed to parse"

    def test_to_dict(self):
        from knowledge.models import IndexingResult

        r = IndexingResult("doc_001", "Test", 5, True)
        d = r.to_dict()
        assert d["document_id"] == "doc_001"


class TestSearchResult:
    def test_create(self):
        from knowledge.models import SearchResult

        r = SearchResult(
            chunk_id="chunk_001",
            document_id="doc_001",
            title="Test",
            source="local",
            category="general",
            content="text",
            score=0.95,
            chunk_number=1,
        )
        assert r.score == 0.95

    def test_to_dict(self):
        from knowledge.models import SearchResult

        r = SearchResult("c1", "d1", "T", "s", "g", "txt", 0.9, 1)
        d = r.to_dict()
        assert d["score"] == 0.9


class TestRetrievalContext:
    def test_create(self):
        from knowledge.models import RetrievalContext, SearchResult

        results = [SearchResult("c1", "d1", "T", "s", "g", "txt", 0.9, 1)]
        ctx = RetrievalContext(
            query="test query",
            results=results,
            context_text="Some context",
            total_results=1,
        )
        assert ctx.query == "test query"
        assert ctx.total_results == 1
        assert ctx.latency_ms == 0.0

    def test_to_dict(self):
        from knowledge.models import RetrievalContext

        ctx = RetrievalContext("query", [], "", total_results=0)
        d = ctx.to_dict()
        assert d["query"] == "query"


class TestSourceInfo:
    def test_create(self):
        from knowledge.models import SourceInfo

        s = SourceInfo(category="risk", count=5, last_indexed="2025-01-01")
        assert s.category == "risk"
        assert s.count == 5
