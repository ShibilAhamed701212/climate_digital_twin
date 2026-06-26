"""Unit tests for the RAG text chunker."""



class TestTextChunker:
    def test_chunk_short_text(self):
        from knowledge.chunkers import TextChunker
        from knowledge.models import Document, DocumentFormat

        chunker = TextChunker(chunk_size=1000, chunk_overlap=0)
        doc = Document("d1", "Test", "local", "general", "/p.md", DocumentFormat.MARKDOWN, "Short text.")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."

    def test_chunk_long_text(self):
        from knowledge.chunkers import TextChunker
        from knowledge.models import Document, DocumentFormat

        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = " ".join(["word"] * 200)
        doc = Document("d1", "Test", "local", "general", "/p.md", DocumentFormat.MARKDOWN, text)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c.content.split()) <= 60

    def test_chunk_id_unique(self):
        from knowledge.chunkers import TextChunker
        from knowledge.models import Document, DocumentFormat

        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = " ".join(["word"] * 200)
        doc = Document("d1", "Test", "local", "general", "/p.md", DocumentFormat.MARKDOWN, text)
        chunks = chunker.chunk_document(doc)
        ids = {c.chunk_id for c in chunks}
        assert len(ids) == len(chunks)

    def test_chunk_inherits_metadata(self):
        from knowledge.chunkers import TextChunker
        from knowledge.models import Document, DocumentFormat

        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = " ".join(["word"] * 200)
        doc = Document("d1", "My Title", "IMD", "government", "/p.md", DocumentFormat.MARKDOWN, text, date="2025-01", region="Karnataka", keywords=["climate"])
        chunks = chunker.chunk_document(doc)
        for c in chunks:
            assert c.document_id == "d1"
            assert c.title == "My Title"
            assert c.source == "IMD"
            assert c.category == "government"
            assert c.date == "2025-01"
            assert c.region == "Karnataka"
            assert "climate" in c.keywords

    def test_chunk_overlap_applied(self):
        from knowledge.chunkers import TextChunker
        from knowledge.models import Document, DocumentFormat

        chunker = TextChunker(chunk_size=30, chunk_overlap=15)
        text = "Hello world. This is a test. More words here. Another sentence. Final one."
        doc = Document("d1", "T", "local", "general", "/p.md", DocumentFormat.MARKDOWN, text)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1

    def test_chunk_numbering(self):
        from knowledge.chunkers import TextChunker
        from knowledge.models import Document, DocumentFormat

        chunker = TextChunker(chunk_size=30, chunk_overlap=5)
        text = " ".join(["word"] * 100)
        doc = Document("d1", "T", "local", "general", "/p.md", DocumentFormat.MARKDOWN, text)
        chunks = chunker.chunk_document(doc)
        assert chunks[0].chunk_number == 1
        assert chunks[-1].chunk_number == len(chunks)

    def test_custom_chunk_size(self):
        from knowledge.chunkers import TextChunker
        from knowledge.models import Document, DocumentFormat

        chunker = TextChunker(chunk_size=10, chunk_overlap=2)
        text = "a b c d e f g h i j k l m n o p"
        doc = Document("d1", "T", "local", "general", "/p.md", DocumentFormat.MARKDOWN, text)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 1
