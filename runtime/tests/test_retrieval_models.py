"""Tests for Retrieval models."""


from runtime.models.retrieval import Chunk, Citation, RetrievalQuery, RetrievalResult


class TestRetrievalQuery:
    def test_create_query(self):
        q = RetrievalQuery(query="climate data for Bangalore", top_k=5)
        assert q.query == "climate data for Bangalore"
        assert q.top_k == 5
        assert q.min_score == 0.3
        assert q.query_id.startswith("rq_")


class TestChunk:
    def test_create_chunk(self):
        chunk = Chunk(
            text="Bangalore has a tropical climate",
            source="climate_db",
            score=0.85,
        )
        assert chunk.text == "Bangalore has a tropical climate"
        assert chunk.source == "climate_db"
        assert chunk.score == 0.85

    def test_passed_filter(self):
        chunk = Chunk(text="test", source="src", score=0.5)
        assert chunk.passed_filter(0.3)
        assert not chunk.passed_filter(0.7)


class TestRetrievalResult:
    def test_empty_result(self):
        result = RetrievalResult(query="test")
        assert len(result.chunks) == 0
        assert result.total_results == 0

    def test_with_chunks(self):
        result = RetrievalResult(
            query="climate",
            chunks=[
                Chunk(text="chunk 1", source="src", score=0.9),
                Chunk(text="chunk 2", source="src", score=0.7),
                Chunk(text="chunk 3", source="src", score=0.5),
            ],
        )
        assert len(result.chunks) == 3

    def test_top_chunks_sorted(self):
        result = RetrievalResult(
            query="test",
            chunks=[
                Chunk(text="low", source="src", score=0.3),
                Chunk(text="high", source="src", score=0.9),
                Chunk(text="mid", source="src", score=0.6),
            ],
        )
        top = result.top_chunks
        assert top[0].score == 0.9
        assert top[1].score == 0.6
        assert top[2].score == 0.3

    def test_citations_from_chunks(self):
        result = RetrievalResult(
            query="test",
            chunks=[
                Chunk(text="chunk A", source="source1", score=0.95),
                Chunk(text="chunk B", source="source2", score=0.85),
            ],
        )
        citations = result.citations
        assert len(citations) == 2
        assert citations[0].source == "source1"

    def test_passed_with_sufficient_score(self):
        result = RetrievalResult(
            query="test",
            chunks=[Chunk(text="x", source="src", score=0.8)],
        )
        assert result.passed(min_score=0.5)

    def test_failed_with_insufficient_score(self):
        result = RetrievalResult(
            query="test",
            chunks=[Chunk(text="x", source="src", score=0.1)],
        )
        assert not result.passed(min_score=0.5)

    def test_citation_creation(self):
        cit = Citation(source="KB", text="some text", relevance=0.9)
        assert cit.source == "KB"
        assert cit.relevance == 0.9
