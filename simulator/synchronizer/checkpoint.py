from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

_logger = logging.getLogger(__name__)


class SyncCheckpoint:
    def __init__(self, path: str | Path = "data/twin_sync/checkpoint.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, str]] = self._load()

    def _load(self) -> dict[str, dict[str, str]]:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                _logger.warning("Failed to load checkpoint, starting fresh: %s", e)
        return {}

    def _save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def is_processed(self, location_id: str, observation_id: str) -> bool:
        with self._lock:
            return observation_id in self._data.get(location_id, {})

    def get_result(self, location_id: str, observation_id: str) -> str | None:
        with self._lock:
            return self._data.get(location_id, {}).get(observation_id)

    def mark_processed(self, location_id: str, observation_id: str, result: str) -> None:
        with self._lock:
            self._data.setdefault(location_id, {})[observation_id] = result
            self._save()

    def mark_batch(self, records: list[tuple[str, str, str]]) -> None:
        with self._lock:
            for location_id, observation_id, result in records:
                self._data.setdefault(location_id, {})[observation_id] = result
            self._save()

    def get_processed_ids(self, location_id: str) -> set[str]:
        with self._lock:
            return set(self._data.get(location_id, {}).keys())

    def get_all_location_ids(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def clear(self) -> None:
        with self._lock:
            self._data = {}
            self._save()
