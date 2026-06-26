"""CSV document loader.

Converts tabular data into a readable text representation.
"""

import csv
from typing import Any

from knowledge.loaders.base import BaseLoader, LoaderError
from knowledge.loaders.md_loader import _path_to_id, _path_to_title
from knowledge.models import Document, DocumentFormat


class CSVLoader(BaseLoader):
    """Loads .csv files — converts rows to formatted text."""

    @property
    def supported_format(self) -> DocumentFormat:
        return DocumentFormat.CSV

    def load(self, file_path: str, **kwargs: Any) -> Document:
        rows: list[list[str]] = []
        try:
            with open(file_path, encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    rows.append(row)
        except FileNotFoundError as e:
            raise LoaderError(f"File not found: {file_path}") from e

        if len(rows) < 2:
            raise LoaderError(f"CSV file has insufficient data: {file_path}")

        header = rows[0]
        content_lines: list[str] = [f"Table: {_path_to_title(file_path)}"]
        content_lines.append(f"Columns: {', '.join(header)}")
        content_lines.append(f"Rows: {len(rows) - 1}")
        content_lines.append("")
        for i, row in enumerate(rows[1:], 1):
            row_text = " | ".join(f"{header[j] if j < len(header) else ''}: {val}" for j, val in enumerate(row))
            content_lines.append(f"Row {i}: {row_text}")

        return Document(
            document_id=kwargs.get("document_id", _path_to_id(file_path)),
            title=kwargs.get("title", _path_to_title(file_path)),
            source=kwargs.get("source", "local"),
            category=kwargs.get("category", "data"),
            file_path=file_path,
            format=DocumentFormat.CSV,
            content="\n".join(content_lines),
            date=kwargs.get("date", ""),
            region=kwargs.get("region", ""),
            keywords=kwargs.get("keywords", []),
        )
