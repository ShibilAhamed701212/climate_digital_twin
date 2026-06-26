"""Unit tests for RAG index reports."""

import os
import tempfile


class TestIndexReport:
    def test_generate_summary(self):
        from knowledge.reports import IndexReport

        sources = [
            {"document_id": "d1", "title": "Doc One", "source": "IMD", "category": "climate", "chunk_count": 5},
        ]
        summary = IndexReport.generate_summary(sources, total_chunks=5)
        assert "# Knowledge Base Index Report" in summary
        assert "Doc One" in summary
        assert "Total Documents" in summary
        assert "Total Chunks" in summary
        assert "1" in summary.split("Total Documents")[1][:5]
        assert "5" in summary.split("Total Chunks")[1][:5]

    def test_save_json(self):
        from knowledge.reports import IndexReport

        with tempfile.TemporaryDirectory() as tmp:
            sources = [{"document_id": "d1", "title": "Doc", "source": "IMD", "category": "climate", "chunk_count": 3}]
            result = IndexReport.save_index_report(sources, total_chunks=3, output_dir=tmp, formats=["json"])
            assert "json" in result
            assert os.path.exists(result["json"])

    def test_save_markdown(self):
        from knowledge.reports import IndexReport

        with tempfile.TemporaryDirectory() as tmp:
            sources = [{"document_id": "d1", "title": "Doc", "source": "IMD", "category": "climate", "chunk_count": 3}]
            result = IndexReport.save_index_report(sources, total_chunks=3, output_dir=tmp, formats=["markdown"])
            assert "markdown" in result
            assert os.path.exists(result["markdown"])

    def test_save_both_formats(self):
        from knowledge.reports import IndexReport

        with tempfile.TemporaryDirectory() as tmp:
            sources = [{"document_id": "d1", "title": "Doc", "source": "IMD", "category": "climate", "chunk_count": 3}]
            result = IndexReport.save_index_report(sources, total_chunks=3, output_dir=tmp, formats=["json", "markdown"])
            assert "json" in result
            assert "markdown" in result
