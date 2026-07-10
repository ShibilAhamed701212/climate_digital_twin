"""Unit tests for TextChunker."""

from knowledge.chunkers.text_chunker import TextChunker
from knowledge.models import Document, DocumentFormat


class TestTextChunker:
    def test_init_clamps_overlap(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=200)
        assert chunker.chunk_overlap == 50

    def test_chunk_document_single_chunk(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="short text",
        )
        chunks = TextChunker(chunk_size=700).chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].document_id == "d1"

    def test_chunk_document_splits_long(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="word " * 500,
        )
        chunks = TextChunker(chunk_size=100).chunk_document(doc)
        assert len(chunks) > 1

    def test_chunk_by_sentences_empty_content(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="   ",
        )
        chunks = TextChunker().chunk_by_sentences(doc)
        assert chunks == []

    def test_chunk_by_sentences(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence.",
        )
        chunks = TextChunker().chunk_by_sentences(doc, max_sentences=2)
        assert len(chunks) == 3
        assert all(c.document_id == "d1" for c in chunks)
        assert chunks[0].chunk_number == 1
        assert chunks[1].chunk_number == 2

    def test_chunk_by_sections_empty_content(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="   ",
        )
        chunks = TextChunker().chunk_by_sections(doc)
        assert chunks == []

    def test_chunk_by_sections_no_headers(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="Just a plain paragraph with no headers at all.",
        )
        chunks = TextChunker().chunk_by_sections(doc)
        assert len(chunks) == 1
        assert "root" not in chunks[0].content

    def test_chunk_by_sections_with_headers(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="# Introduction\n\nFirst paragraph.\n\n## Details\n\nSecond paragraph.",
        )
        chunks = TextChunker().chunk_by_sections(doc)
        assert len(chunks) == 2
        assert "Introduction" in chunks[0].content
        assert "Details" in chunks[1].content

    def test_chunk_by_sections_with_underline_headers(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="Intro\n=====\n\nFirst paragraph.\n\nDetails\n------\n\nSecond paragraph.",
        )
        chunks = TextChunker().chunk_by_sections(doc)
        assert len(chunks) == 2

    def test_chunk_by_sections_content_before_first_header(self):
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.TEXT,
            content="Preamble content.\n\n# Main\n\nBody content.",
        )
        chunks = TextChunker().chunk_by_sections(doc)
        assert len(chunks) == 2

    def test_split_text_returns_single(self):
        chunker = TextChunker(chunk_size=1000)
        result = chunker._split_text("short text")
        assert result == ["short text"]

    def test_split_text_on_paragraphs(self):
        chunker = TextChunker(chunk_size=5)
        result = chunker._split_text("hello\n\nworld\n\nfoo bar baz qux")
        assert len(result) >= 2

    def test_split_on_sentences_appends_current(self):
        chunker = TextChunker(chunk_size=30)
        text = "This is the first sentence. And here is the second. Third one is short."
        result = chunker._split_on_sentences(text)
        assert len(result) >= 1

    def test_split_on_sentences_splits_long_sentence(self):
        chunker = TextChunker(chunk_size=5)
        text = "A B C D E F G H I J K L M N O P"
        result = chunker._split_on_sentences(text)
        assert len(result) >= 1

    def test_split_on_sentences_long_sentence_no_prev(self):
        chunker = TextChunker(chunk_size=3)
        result = chunker._split_on_sentences("A B C D E F")
        assert len(result) >= 1

    def test_merge_small_chunks_single(self):
        chunker = TextChunker(chunk_size=100)
        assert chunker._merge_small_chunks(["hello"]) == ["hello"]

    def test_merge_small_chunks_merges(self):
        chunker = TextChunker(chunk_size=20)
        result = chunker._merge_small_chunks(["hello world", "foo bar"])
        assert len(result) >= 1

    def test_apply_overlap_single_chunk(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=10)
        assert chunker._apply_overlap(["only"]) == ["only"]

    def test_apply_overlap_merges(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=3)
        result = chunker._apply_overlap(["aaa bbb ccc", "ddd eee fff"])
        assert len(result) == 2
        assert "ccc" in result[1]

    def test_apply_overlap_zero(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=0)
        assert chunker._apply_overlap(["aaa", "bbb"]) == ["aaa", "bbb"]

    def test_apply_overlap_no_overlap_text(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=0)
        result = chunker._apply_overlap(["aaa", "bbb"])
        assert result == ["aaa", "bbb"]

    def test_estimate_tokens(self):
        assert TextChunker.estimate_tokens("hello world") == 2
        assert TextChunker.estimate_tokens("") == 1

    def test_extract_overlap(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=2)
        assert chunker._extract_overlap("a b c d e") == "d e"
        assert chunker._extract_overlap("a") == "a"

    def test_split_on_words(self):
        chunker = TextChunker(chunk_size=3)
        result = chunker._split_on_words("a b c d e f g h")
        assert len(result) >= 2
