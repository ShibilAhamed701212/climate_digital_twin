"""JSON document loader.

Converts JSON structures into readable text representation.
"""

import json
from typing import Any

from knowledge.loaders.base import BaseLoader, LoaderError
from knowledge.loaders.md_loader import _path_to_id, _path_to_title
from knowledge.models import Document, DocumentFormat


class JSONLoader(BaseLoader):
    """Loads .json files — flattens nested structure to text."""

    @property
    def supported_format(self) -> DocumentFormat:
        return DocumentFormat.JSON

    def load(self, file_path: str, **kwargs: Any) -> Document:
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise LoaderError(f"File not found: {file_path}") from e
        except json.JSONDecodeError as e:
            raise LoaderError(f"Invalid JSON in {file_path}: {e}") from e

        content = json.dumps(data, indent=2, ensure_ascii=False)

        return Document(
            document_id=kwargs.get("document_id", _path_to_id(file_path)),
            title=kwargs.get("title", _path_to_title(file_path)),
            source=kwargs.get("source", "local"),
            category=kwargs.get("category", "data"),
            file_path=file_path,
            format=DocumentFormat.JSON,
            content=content,
            date=kwargs.get("date", ""),
            region=kwargs.get("region", ""),
            keywords=kwargs.get("keywords", []),
        )
