"""Unit tests for RAG document loaders."""

import os
import tempfile

import pytest


class TestMarkdownLoader:
    def test_load_simple_md(self):
        from knowledge.loaders import MarkdownLoader

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Title\n\nContent here.\n")
            path = f.name
        try:
            loader = MarkdownLoader()
            doc = loader.load(path, source="test", category="general")
            assert doc.title == "Title"
            assert "Content here" in doc.content
            assert doc.source == "test"
        finally:
            os.unlink(path)

    def test_load_without_title(self):
        from knowledge.loaders import MarkdownLoader

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("No heading here.\n")
            path = f.name
        try:
            loader = MarkdownLoader()
            doc = loader.load(path)
            assert doc.title != ""
        finally:
            os.unlink(path)

    def test_empty_file_raises(self):
        from knowledge.loaders import MarkdownLoader
        from knowledge.loaders.base import LoaderError

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            path = f.name
        try:
            loader = MarkdownLoader()
            with pytest.raises(LoaderError):
                loader.load(path)
        finally:
            os.unlink(path)

    def test_supported_format(self):
        from knowledge.loaders import MarkdownLoader
        from knowledge.models import DocumentFormat

        loader = MarkdownLoader()
        assert loader.supported_format == DocumentFormat.MARKDOWN


class TestTextLoader:
    def test_load(self):
        from knowledge.loaders import TextLoader

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Plain text content.\nLine two.")
            path = f.name
        try:
            loader = TextLoader()
            doc = loader.load(path, title="My Text")
            assert doc.title == "My Text"
            assert "Plain text content" in doc.content
        finally:
            os.unlink(path)

    def test_empty_file_raises(self):
        from knowledge.loaders import TextLoader
        from knowledge.loaders.base import LoaderError

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            loader = TextLoader()
            with pytest.raises(LoaderError):
                loader.load(path)
        finally:
            os.unlink(path)


class TestCSVLoader:
    def test_load(self):
        from knowledge.loaders import CSVLoader

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,value\nrainfall,120\n")
            path = f.name
        try:
            loader = CSVLoader()
            doc = loader.load(path, source="data")
            assert doc.source == "data"
            assert "name" in doc.content
            assert "rainfall" in doc.content
        finally:
            os.unlink(path)

    def test_insufficient_rows_raises(self):
        from knowledge.loaders import CSVLoader
        from knowledge.loaders.base import LoaderError

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("header_only\n")
            path = f.name
        try:
            loader = CSVLoader()
            with pytest.raises(LoaderError):
                loader.load(path)
        finally:
            os.unlink(path)


class TestJSONLoader:
    def test_load(self):
        from knowledge.loaders import JSONLoader

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value", "number": 42}')
            path = f.name
        try:
            loader = JSONLoader()
            doc = loader.load(path, category="data")
            assert doc.category == "data"
            assert "value" in doc.content
        finally:
            os.unlink(path)

    def test_invalid_json_raises(self):
        from knowledge.loaders import JSONLoader
        from knowledge.loaders.base import LoaderError

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid}")
            path = f.name
        try:
            loader = JSONLoader()
            with pytest.raises(LoaderError):
                loader.load(path)
        finally:
            os.unlink(path)


class TestLoaderFactory:
    def test_get_loader_md(self):
        from knowledge.loaders import MarkdownLoader, get_loader

        loader = get_loader("test.md")
        assert isinstance(loader, MarkdownLoader)

    def test_get_loader_txt(self):
        from knowledge.loaders import TextLoader, get_loader

        loader = get_loader("test.txt")
        assert isinstance(loader, TextLoader)

    def test_get_loader_csv(self):
        from knowledge.loaders import CSVLoader, get_loader

        loader = get_loader("test.csv")
        assert isinstance(loader, CSVLoader)

    def test_get_loader_json(self):
        from knowledge.loaders import JSONLoader, get_loader

        loader = get_loader("test.json")
        assert isinstance(loader, JSONLoader)

    def test_get_loader_unsupported(self):
        from knowledge.loaders import get_loader
        from knowledge.loaders.base import LoaderError

        with pytest.raises(LoaderError):
            get_loader("test.pdf")
