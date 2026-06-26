"""Parquet-file-based implementation of the TwinRepository."""

import json
import logging
from pathlib import Path

import pandas as pd

from simulator.repository.base import TwinRepository
from simulator.state_manager.version import Version

logger = logging.getLogger(__name__)


class ParquetRepository(TwinRepository):
    """Repository implementation using Parquet files for storage.

    Each location gets its own Parquet file under the store directory.
    The storage backend can be swapped by implementing TwinRepository.
    """

    def __init__(self, store_dir: str = "data/twin_store") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, list[Version]] = {}

    def _location_path(self, location_id: str) -> Path:
        safe_name = location_id.replace("/", "_").replace("\\", "_")
        return self.store_dir / f"{safe_name}.parquet"

    def _version_to_dict(self, v: Version) -> dict:
        return {
            "version_id": v.version_id,
            "location_id": v.location_id,
            "entity_data": json.dumps(v.entity_data),
            "timestamp": v.timestamp,
            "state_type": v.state_type,
        }

    def _dict_to_version(self, d: dict) -> Version:
        return Version(
            version_id=int(d["version_id"]),
            location_id=str(d["location_id"]),
            entity_data=dict(json.loads(str(d["entity_data"]))),
            timestamp=str(d["timestamp"]),
            state_type=str(d["state_type"]),
        )

    def save_version(self, version: Version) -> None:
        path = self._location_path(version.location_id)
        row = self._version_to_dict(version)
        if path.exists():
            existing = pd.read_parquet(path)
            df = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
        else:
            df = pd.DataFrame([row])
        df.to_parquet(path, index=False, compression="snappy")
        if version.location_id in self._cache:
            self._cache[version.location_id].append(version)
        logger.debug("Version %d saved for %s", version.version_id, version.location_id)

    def load_versions(self, location_id: str) -> list[Version]:
        if location_id in self._cache:
            return list(self._cache[location_id])
        path = self._location_path(location_id)
        if not path.exists():
            return []
        df = pd.read_parquet(path)
        versions = [self._dict_to_version(row) for _, row in df.iterrows()]
        self._cache[location_id] = versions
        return versions

    def load_latest_version(self, location_id: str) -> Version | None:
        versions = self.load_versions(location_id)
        if not versions:
            return None
        return max(versions, key=lambda v: v.version_id)

    def load_all_location_ids(self) -> list[str]:
        ids = set()
        for path in self.store_dir.glob("*.parquet"):
            ids.add(path.stem)
        return sorted(ids)

    def delete_location(self, location_id: str) -> None:
        path = self._location_path(location_id)
        if path.exists():
            path.unlink()
        self._cache.pop(location_id, None)
        logger.info("Deleted all versions for %s", location_id)
