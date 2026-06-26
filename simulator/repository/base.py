"""Abstract base repository interface for the Digital Twin storage layer.

Completely decoupled so the storage backend can be swapped seamlessly
(e.g., DuckDB, PostgreSQL, Parquet files).
"""

from abc import ABC, abstractmethod

from simulator.state_manager.version import Version


class TwinRepository(ABC):
    """Abstract repository for persisting Digital Twin state versions."""

    @abstractmethod
    def save_version(self, version: Version) -> None:
        """Persist a single version."""
        ...

    @abstractmethod
    def load_versions(self, location_id: str) -> list[Version]:
        """Load all versions for a location."""
        ...

    @abstractmethod
    def load_latest_version(self, location_id: str) -> Version | None:
        """Load the most recent version for a location."""
        ...

    @abstractmethod
    def load_all_location_ids(self) -> list[str]:
        """Load all location IDs that have stored versions."""
        ...

    @abstractmethod
    def delete_location(self, location_id: str) -> None:
        """Delete all versions for a location."""
        ...
