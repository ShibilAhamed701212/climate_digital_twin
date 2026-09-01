from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


class OverlayPointerStore:
    def __init__(self, path: Path | None = None) -> None:
        base = Path(os.environ.get("TWIN_STORE_DIR", "data/twin_store"))
        self._path = path or (base / "overlay_pointers.jsonl")
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
                loc = str(row.get("location_id") or "")
                if loc:
                    self._rows[loc] = row

    def upsert(self, pointer: dict[str, Any]) -> dict[str, Any]:
        loc = str(pointer.get("location_id") or "")
        with self._lock:
            self._rows[loc] = pointer
            tmp = self._path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                for row in self._rows.values():
                    fh.write(json.dumps(row, default=str) + "\n")
            tmp.replace(self._path)
        return pointer

    def get(self, location_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._rows.get(location_id)
            return dict(row) if row else None
