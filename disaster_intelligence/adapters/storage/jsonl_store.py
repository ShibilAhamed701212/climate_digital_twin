from __future__ import annotations

import json
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any


class JsonlStore:
    """Append-friendly JSONL with in-memory index; rewrites on update."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._rows: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                key = str(row.get("id") or "")
                if "assessment_id" in row and "event_id" in row and "version" in row:
                    key = str(row["assessment_id"])
                elif "job_id" in row:
                    key = str(row["job_id"])
                elif "scene_id" in row:
                    key = str(row["scene_id"])
                elif "event_id" in row and "disaster_type" in row and "aoi" in row:
                    key = str(row["event_id"])
                elif "location_id" in row:
                    key = str(row["location_id"])
                elif not key:
                    key = str(row.get("event_id") or "")
                if key:
                    self._rows[key] = row

    def _rewrite(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for row in self._rows.values():
                fh.write(json.dumps(row, default=str) + "\n")
        tmp.replace(self._path)

    def put(self, key: str, row: dict[str, Any]) -> None:
        with self._lock:
            self._rows[key] = row
            self._rewrite()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._rows.get(key)
            return dict(row) if row else None

    def values(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._rows.values()]

    def find(self, pred: Callable[[dict[str, Any]], bool]) -> dict[str, Any] | None:
        with self._lock:
            for row in self._rows.values():
                if pred(row):
                    return dict(row)
        return None
