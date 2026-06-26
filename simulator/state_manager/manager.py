"""State Manager — immutable versioning and rollback for the Digital Twin.

Strictly enforces:
  - Each update creates a new immutable version (never overwrite).
  - Rollback restores a previous version as a new version.
  - Version IDs are monotonically increasing per location.
"""

import logging

from simulator.entities.climate_entity import ClimateEntity
from simulator.state_manager.version import Version

logger = logging.getLogger(__name__)


class VersionNotFoundError(Exception):
    """Raised when a requested version does not exist."""


class StateManager:
    """Manages immutable version history for all climate entities.

    Maintains an in-memory version chain per location.
    The repository layer persists versions to disk.
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[Version]] = {}
        self._current: dict[str, Version] = {}

    def _next_version_id(self, location_id: str) -> int:
        return len(self._versions.get(location_id, [])) + 1

    def create_version(
        self, entity: ClimateEntity, state_type: str | None = None
    ) -> Version:
        """Create an immutable version from a ClimateEntity.

        Returns the new Version. Raises ValueError on validation failure.
        """
        errors = entity.validate()
        if errors:
            raise ValueError(f"Entity validation failed: {errors}")
        loc_id = entity.location_id
        vid = self._next_version_id(loc_id)
        version = Version(
            version_id=vid,
            location_id=loc_id,
            entity_data=entity.serialize(),
            state_type=state_type or entity.state_type,
        )
        if loc_id not in self._versions:
            self._versions[loc_id] = []
        self._versions[loc_id].append(version)
        self._current[loc_id] = version
        logger.info(
            "Version %d created for %s (type=%s)",
            vid,
            loc_id,
            version.state_type,
        )
        return version

    def get_current(self, location_id: str) -> Version | None:
        """Get the current (latest) version for a location."""
        return self._current.get(location_id)

    def get_version(self, location_id: str, version_id: int) -> Version:
        """Get a specific version for a location."""
        versions = self._versions.get(location_id, [])
        for v in versions:
            if v.version_id == version_id:
                return v
        raise VersionNotFoundError(
            f"Version {version_id} not found for {location_id}"
        )

    def get_version_history(
        self, location_id: str
    ) -> list[Version]:
        """Get the full version history for a location."""
        return list(self._versions.get(location_id, []))

    def rollback(
        self, location_id: str, target_version_id: int
    ) -> Version:
        """Rollback to a previous version.

        Creates a *new* version with the data from target_version_id.
        The original version is never modified — strict immutability.
        """
        target = self.get_version(location_id, target_version_id)
        entity = ClimateEntity.deserialize(target.entity_data)
        entity.timestamp = entity.timestamp  # keep original timestamp
        new_version = self.create_version(entity, state_type=target.state_type)
        logger.info(
            "Rollback for %s: version %d -> version %d",
            location_id,
            target_version_id,
            new_version.version_id,
        )
        return new_version

    def has_location(self, location_id: str) -> bool:
        """Check if a location has any versions."""
        return location_id in self._versions and len(self._versions[location_id]) > 0

    def get_all_location_ids(self) -> list[str]:
        """Get all location IDs with version history."""
        return list(self._versions.keys())

    def version_count(self, location_id: str) -> int:
        """Get the number of versions for a location."""
        return len(self._versions.get(location_id, []))
