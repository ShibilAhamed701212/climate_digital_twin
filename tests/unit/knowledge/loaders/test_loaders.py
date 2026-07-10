"""Tests covering uncovered lines in knowledge/loaders/ modules."""

import os
import tempfile

import pytest

from knowledge.models import DocumentFormat


class TestTextLoaderExtended:
    def test_supported_format(self):
        from knowledge.loaders.txt_loader import TextLoader

        assert TextLoader().supported_format == DocumentFormat.TEXT

    def test_file_not_found(self):
        from knowledge.loaders.base import LoaderError
        from knowledge.loaders.txt_loader import TextLoader

        with pytest.raises(LoaderError, match="File not found"):
            TextLoader().load("/nonexistent/file.txt")

    def test_unicode_decode_error(self):
        from knowledge.loaders.base import LoaderError
        from knowledge.loaders.txt_loader import TextLoader

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"\xff\xfe\x00\xff")
            path = f.name
        try:
            with pytest.raises(LoaderError, match="Cannot decode"):
                TextLoader().load(path)
        finally:
            os.unlink(path)


class TestJSONLoaderExtended:
    def test_supported_format(self):
        from knowledge.loaders.json_loader import JSONLoader

        assert JSONLoader().supported_format == DocumentFormat.JSON

    def test_file_not_found(self):
        from knowledge.loaders.base import LoaderError
        from knowledge.loaders.json_loader import JSONLoader

        with pytest.raises(LoaderError, match="File not found"):
            JSONLoader().load("/nonexistent/file.json")


class TestCSVLoaderExtended:
    def test_supported_format(self):
        from knowledge.loaders.csv_loader import CSVLoader

        assert CSVLoader().supported_format == DocumentFormat.CSV

    def test_file_not_found(self):
        from knowledge.loaders.base import LoaderError
        from knowledge.loaders.csv_loader import CSVLoader

        with pytest.raises(LoaderError, match="File not found"):
            CSVLoader().load("/nonexistent/file.csv")


class TestFactoryExtended:
    def test_no_loader_registered(self):
        from knowledge.loaders import factory as f
        from knowledge.loaders.base import LoaderError

        saved = dict(f._FORMAT_EXTENSIONS)
        f._FORMAT_EXTENSIONS[".xyz"] = "FAKE"
        try:
            with pytest.raises(LoaderError, match="No loader registered"):
                f.get_loader("test.xyz")
        finally:
            f._FORMAT_EXTENSIONS.clear()
            f._FORMAT_EXTENSIONS.update(saved)

    def test_guess_format_md(self):
        from knowledge.loaders.factory import guess_format

        assert guess_format("doc.md") == DocumentFormat.MARKDOWN

    def test_guess_format_txt(self):
        from knowledge.loaders.factory import guess_format

        assert guess_format("doc.txt") == DocumentFormat.TEXT

    def test_guess_format_unknown(self):
        from knowledge.loaders.factory import guess_format

        assert guess_format("doc.pdf") is None
