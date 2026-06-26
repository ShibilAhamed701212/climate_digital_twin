"""Plain text document loader."""

from typing import Any

from knowledge.loaders.base import BaseLoader, LoaderError
from knowledge.loaders.md_loader import _path_to_id, _path_to_title
from knowledge.models import Document, DocumentFormat


class TextLoader(BaseLoader):
    """Loads .txt files as Documents."""

    @property
    def supported_format(self) -> DocumentFormat:
        return DocumentFormat.TEXT

    def load(self, file_path: str, **kwargs: Any) -> Document:
        content = self._read_raw(file_path)
        if not content.strip():
            raise LoaderError(f"Empty text file: {file_path}")
        return Document(
            document_id=kwargs.get("document_id", _path_to_id(file_path)),
            title=kwargs.get("title", _path_to_title(file_path)),
            source=kwargs.get("source", "local"),
            category=kwargs.get("category", "general"),
            file_path=file_path,
            format=DocumentFormat.TEXT,
            content=content,
            date=kwargs.get("date", ""),
            region=kwargs.get("region", ""),
            keywords=kwargs.get("keywords", []),
        )
