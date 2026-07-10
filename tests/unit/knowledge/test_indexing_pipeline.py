"""Unit tests for IndexingPipeline."""

from unittest.mock import MagicMock, patch

from knowledge.models import Document, DocumentFormat, IndexingResult


class TestIndexingPipelineInit:
    @patch("knowledge.pipelines.indexing_pipeline.load_rag_config")
    def test_init_without_config(self, mock_load):
        mock_load.return_value = {
            "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_dimension": 128},
            "vector_store": {"index_path": "/tmp/i", "metadata_path": "/tmp/m"},
            "documents": {"supported_formats": ["md", "txt"]},
        }
        with (
            patch("knowledge.pipelines.indexing_pipeline.EmbeddingModel"),
            patch("knowledge.pipelines.indexing_pipeline.FAISSStore"),
        ):
            from knowledge.pipelines.indexing_pipeline import IndexingPipeline

            p = IndexingPipeline()
            assert p.chunker.chunk_size == 500

    def test_init_with_config(self):
        config = {
            "rag": {"chunk_size": 300, "chunk_overlap": 30, "embedding_dimension": 64},
            "vector_store": {"index_path": "/tmp/i", "metadata_path": "/tmp/m"},
            "documents": {"supported_formats": ["md"]},
        }
        with (
            patch("knowledge.pipelines.indexing_pipeline.EmbeddingModel"),
            patch("knowledge.pipelines.indexing_pipeline.FAISSStore"),
        ):
            from knowledge.pipelines.indexing_pipeline import IndexingPipeline

            p = IndexingPipeline(config)
            assert p.chunker.chunk_size == 300
            assert p.vector_store is not None


class TestIndexingPipelineIndexDocument:
    @patch("knowledge.pipelines.indexing_pipeline.load_rag_config")
    def make_pipeline(self, mock_load, formats=None):
        mock_load.return_value = {
            "rag": {"chunk_size": 700, "chunk_overlap": 120, "embedding_dimension": 384},
            "vector_store": {"index_path": "/tmp/i", "metadata_path": "/tmp/m"},
            "documents": {"supported_formats": formats or ["md", "txt", "csv", "json"]},
        }
        from knowledge.pipelines.indexing_pipeline import IndexingPipeline

        p = IndexingPipeline.__new__(IndexingPipeline)
        p.config = mock_load.return_value
        p.chunker = MagicMock()
        p.embedding_model = MagicMock()
        p.vector_store = MagicMock()
        p.supported_formats = mock_load.return_value["documents"]["supported_formats"]
        return p

    def test_index_document_unsupported_format(self):
        p = self.make_pipeline(formats=["md"])
        result = p.index_document("/path/file.xyz")
        assert not result.success
        assert "Unsupported format" in result.error

    def test_index_document_format_not_in_supported(self):
        p = self.make_pipeline(formats=["txt"])
        result = p.index_document("/path/file.csv")
        assert not result.success
        assert "not in supported list" in result.error

    @patch("knowledge.pipelines.indexing_pipeline.get_loader")
    def test_index_document_loader_exception(self, mock_get_loader):
        p = self.make_pipeline()
        mock_get_loader.side_effect = ValueError("no loader")
        result = p.index_document("/path/file.md")
        assert not result.success
        assert "no loader" in result.error

    @patch("knowledge.pipelines.indexing_pipeline.get_loader")
    def test_index_document_embedding_exception(self, mock_get_loader):
        p = self.make_pipeline()
        loader = MagicMock()
        loader.load.return_value = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.MARKDOWN,
            content="text",
        )
        mock_get_loader.return_value = loader
        p.chunker.chunk_document.return_value = [MagicMock()]
        p.chunker.chunk_document.return_value[0].content = "text"
        p.embedding_model.encode.side_effect = RuntimeError("embed failed")
        result = p.index_document("/path/file.md")
        assert not result.success
        assert "embed failed" in result.error

    @patch("knowledge.pipelines.indexing_pipeline.get_loader")
    def test_index_document_success(self, mock_get_loader):
        p = self.make_pipeline()
        doc = Document(
            document_id="d1",
            title="Doc",
            source="src",
            category="cat",
            file_path="/p",
            format=DocumentFormat.MARKDOWN,
            content="text",
        )
        loader = MagicMock()
        loader.load.return_value = doc
        mock_get_loader.return_value = loader
        p.chunker.chunk_document.return_value = [MagicMock()]
        p.chunker.chunk_document.return_value[0].content = "text"
        p.embedding_model.encode.return_value = [[0.1] * 384]
        result = p.index_document("/path/file.md")
        assert result.success
        assert result.num_chunks == 1


class TestIndexingPipelineIndexDirectory:
    @patch("knowledge.pipelines.indexing_pipeline.load_rag_config")
    def make_pipeline(self, mock_load):
        mock_load.return_value = {
            "rag": {"chunk_size": 700, "chunk_overlap": 120, "embedding_dimension": 384},
            "vector_store": {"index_path": "/tmp/i", "metadata_path": "/tmp/m"},
            "documents": {"supported_formats": ["md", "txt"]},
        }
        from knowledge.pipelines.indexing_pipeline import IndexingPipeline

        p = IndexingPipeline.__new__(IndexingPipeline)
        p.config = mock_load.return_value
        p.chunker = MagicMock()
        p.embedding_model = MagicMock()
        p.vector_store = MagicMock()
        p.supported_formats = mock_load.return_value["documents"]["supported_formats"]
        p.index_document = MagicMock()
        p.index_document.return_value = IndexingResult("d1", "Doc", 1, True)
        return p

    def test_index_directory_not_found(self):
        p = self.make_pipeline()
        results = p.index_directory("/nonexistent/dir")
        assert results == []

    def test_index_directory_recursive(self, tmp_path):
        p = self.make_pipeline()
        d = tmp_path / "docs"
        d.mkdir()
        (d / "a.md").write_text("hello")
        (d / "b.txt").write_text("world")
        (d / "c.csv").write_text("x,y")  # not in supported formats
        results = p.index_directory(str(d))
        assert len(results) == 2

    def test_index_directory_non_recursive(self, tmp_path):
        p = self.make_pipeline()
        d = tmp_path / "docs"
        d.mkdir()
        (d / "a.md").write_text("hello")
        sub = d / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("world")
        results = p.index_directory(str(d), recursive=False)
        assert len(results) == 1
