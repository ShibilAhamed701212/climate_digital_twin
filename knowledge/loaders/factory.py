"""Loader factory — returns the right loader for a file format."""

from knowledge.loaders.base import BaseLoader, LoaderError
from knowledge.loaders.csv_loader import CSVLoader
from knowledge.loaders.json_loader import JSONLoader
from knowledge.loaders.md_loader import MarkdownLoader
from knowledge.loaders.txt_loader import TextLoader
from knowledge.models import DocumentFormat

_LOADER_MAP: dict[DocumentFormat, type[BaseLoader]] = {
    DocumentFormat.MARKDOWN: MarkdownLoader,
    DocumentFormat.TEXT: TextLoader,
    DocumentFormat.CSV: CSVLoader,
    DocumentFormat.JSON: JSONLoader,
}

_FORMAT_EXTENSIONS: dict[str, DocumentFormat] = {
    ".md": DocumentFormat.MARKDOWN,
    ".txt": DocumentFormat.TEXT,
    ".csv": DocumentFormat.CSV,
    ".json": DocumentFormat.JSON,
}


def get_loader(file_path: str) -> BaseLoader:
    """Get the appropriate loader for a file based on its extension.

    Args:
        file_path: Path to the file.

    Returns:
        An instance of the matching loader.

    Raises:
        LoaderError: If the file format is not supported.
    """
    import os
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    fmt = _FORMAT_EXTENSIONS.get(ext)
    if fmt is None:
        raise LoaderError(f"Unsupported file format: {ext}")

    loader_cls = _LOADER_MAP.get(fmt)
    if loader_cls is None:
        raise LoaderError(f"No loader registered for format: {fmt}")

    return loader_cls()


def guess_format(file_path: str) -> DocumentFormat | None:
    """Guess document format from file extension."""
    import os
    _, ext = os.path.splitext(file_path)
    return _FORMAT_EXTENSIONS.get(ext.lower())
