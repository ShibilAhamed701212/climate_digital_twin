"""Markdown document loader."""

from typing import Any

from knowledge.loaders.base import BaseLoader, LoaderError
from knowledge.models import Document, DocumentFormat


class MarkdownLoader(BaseLoader):
    """Loads .md files as Documents."""

    @property
    def supported_format(self) -> DocumentFormat:
        return DocumentFormat.MARKDOWN

    def load(self, file_path: str, **kwargs: Any) -> Document:
        content = self._read_raw(file_path)
        if not content.strip():
            raise LoaderError(f"Empty markdown file: {file_path}")
        return self._build_document(file_path, content, **kwargs)

    def _build_document(self, file_path: str, content: str, **kwargs: Any) -> Document:
        lines = content.split("\n")
        title = kwargs.get("title", "")
        if not title:
            for line in lines:
                if line.startswith("# "):
                    title = line.lstrip("# ").strip()
                    break
        return Document(
            document_id=kwargs.get("document_id", _path_to_id(file_path)),
            title=title or _path_to_title(file_path),
            source=kwargs.get("source", "local"),
            category=kwargs.get("category", "general"),
            file_path=file_path,
            format=DocumentFormat.MARKDOWN,
            content=content,
            date=kwargs.get("date", ""),
            region=kwargs.get("region", ""),
            keywords=kwargs.get("keywords", []),
        )


def _path_to_id(file_path: str) -> str:
    import hashlib
    return hashlib.md5(file_path.encode()).hexdigest()[:12]


def _path_to_title(file_path: str) -> str:
    import os
    name = os.path.splitext(os.path.basename(file_path))[0]
    return name.replace("_", " ").replace("-", " ").title()
