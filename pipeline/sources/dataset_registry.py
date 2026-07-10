from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class DatasetRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self._registry_file = (
            registry_path or Path.home() / ".climatedt" / "datasets" / "dataset_registry.json"
        ).resolve()
        self._lock = threading.Lock()
        self._entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._registry_file.exists():
            try:
                with open(self._registry_file) as f:
                    self._entries = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                _logger.warning("Failed to load registry from %s: %s", self._registry_file, e)
                self._entries = []

    def _save(self) -> None:
        self._registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_file, "w") as f:
            json.dump(self._entries, f, indent=2, default=str)

    def register_dataset(
        self,
        source: str,
        date_range: tuple[date, date],
        location_ids: list[str],
        checksum: str = "",
        record_count: int = 0,
        parquet_path: str = "",
        metadata: dict[str, str] | None = None,
    ) -> str:
        dataset_id = uuid.uuid4().hex[:16]
        if not checksum:
            hash_input = f"{source}:{date_range[0]}:{date_range[1]}:{sorted(location_ids)}"
            checksum = hashlib.sha256(hash_input.encode()).hexdigest()
        entry = {
            "dataset_id": dataset_id,
            "source_name": source,
            "start_date": date_range[0].isoformat(),
            "end_date": date_range[1].isoformat(),
            "location_ids": location_ids,
            "checksum": checksum,
            "record_count": record_count,
            "ingestion_timestamp": datetime.now(UTC).isoformat(),
            "status": "completed",
            "parquet_path": parquet_path,
            "metadata_json": json.dumps(metadata or {}),
        }
        with self._lock:
            self._entries.append(entry)
            self._save()
        _logger.debug(
            "Registered dataset %s: %s %s-%s (%d records)",
            dataset_id,
            source,
            date_range[0],
            date_range[1],
            record_count,
        )
        return dataset_id

    def get_ingestion_status(self, source: str, dt: date) -> str | None:
        with self._lock:
            for entry in self._entries:
                if entry["source_name"] != source:
                    continue
                start = date.fromisoformat(entry["start_date"])
                end = date.fromisoformat(entry["end_date"])
                if start <= dt <= end:
                    return entry["status"]
        return None

    def list_datasets(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._entries)

    def get_dataset_by_checksum(self, checksum: str) -> dict[str, Any] | None:
        with self._lock:
            for entry in self._entries:
                if entry["checksum"] == checksum:
                    return entry
        return None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            if self._registry_file.exists():
                self._registry_file.unlink()
            _logger.info("Cleared dataset registry")


__all__ = ["DatasetRegistry"]
