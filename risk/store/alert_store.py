"""AlertStore — JSONL persistence for Alert records.

Supports append/history, latest active by location, lookup by ID,
restart recovery.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from risk.models.hazard import Alert, AlertStatus


class AlertStore:
    def __init__(self, path: str = "data/hazard/alerts.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: dict[str, Alert] | None = None

    def save(self, alert: Alert) -> None:
        with self._lock:
            if self._cache is not None:
                self._cache[alert.alert_id] = alert
            with open(self._path, "a") as f:
                f.write(json.dumps(alert.to_dict()) + "\n")

    def update(self, alert: Alert) -> None:
        with self._lock:
            if self._cache is not None:
                self._cache[alert.alert_id] = alert
            with open(self._path, "a") as f:
                f.write(json.dumps(alert.to_dict()) + "\n")

    def _load_all(self) -> dict[str, Alert]:
        if self._cache is not None:
            return self._cache
        if not self._path.exists():
            self._cache = {}
            return self._cache
        result: dict[str, Alert] = {}
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    a = Alert.from_dict(json.loads(line))
                    result[a.alert_id] = a  # later lines overwrite earlier
                except Exception:
                    continue
        self._cache = result
        return result

    def get(self, alert_id: str) -> Alert | None:
        return self._load_all().get(alert_id)

    def list_recent(self, limit: int = 20) -> list[Alert]:
        all_a = list(self._load_all().values())
        all_a.sort(key=lambda a: a.issued_at, reverse=True)
        return all_a[:limit]

    def list_active(self) -> list[Alert]:
        return [
            a
            for a in self._load_all().values()
            if a.status in (AlertStatus.ACTIVE, AlertStatus.ESCALATED)
        ]

    def list_active_by_location(self, location_id: str) -> list[Alert]:
        return [
            a
            for a in self._load_all().values()
            if a.location_id == location_id
            and a.status in (AlertStatus.ACTIVE, AlertStatus.ESCALATED)
        ]

    def count(self) -> int:
        return len(self._load_all())

    def clear(self) -> None:
        with self._lock:
            self._cache = {}
            if self._path.exists():
                self._path.unlink()
