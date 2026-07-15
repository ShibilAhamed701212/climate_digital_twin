"""Base provider interface for all climate data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pipeline.providers.manager import Observation


class BaseProvider(ABC):
    """Abstract base class for climate data providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is currently available."""

    @abstractmethod
    def fetch(self, location_id: str, variable: str, timestamp: str | None = None) -> Observation | None:
        """Fetch an observation from this provider.

        Returns None if the provider cannot fulfill the request.
        """

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return provider health status."""
