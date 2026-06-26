"""Abstract base class for document loaders."""

from abc import ABC, abstractmethod
from typing import Any

from knowledge.models import Document, DocumentFormat


class LoaderError(Exception):
    """Raised when a document cannot be loaded."""


class BaseLoader(ABC):
    """Abstract document loader.

    Subclasses implement ``load()`` for a specific file format.
    """

    @abstractmethod
    def load(self, file_path: str, **kwargs: Any) -> Document:
        """Load a document from file_path.

        Args:
            file_path: Absolute or relative path to the file.
            **kwargs: Extra metadata (title, source, category, etc.).

        Returns:
            Document with full text content and metadata.

        Raises:
            LoaderError: If the file cannot be read or parsed.
        """

    @property
    @abstractmethod
    def supported_format(self) -> DocumentFormat:
        """Return the format handled by this loader."""

    def _read_raw(self, file_path: str, encoding: str = "utf-8") -> str:
        try:
            with open(file_path, encoding=encoding) as f:
                return f.read()
        except FileNotFoundError as e:
            raise LoaderError(f"File not found: {file_path}") from e
        except UnicodeDecodeError as e:
            raise LoaderError(f"Cannot decode {file_path} with {encoding}") from e
