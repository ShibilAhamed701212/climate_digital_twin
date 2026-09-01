from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from disaster_intelligence.domain.paths import safe_layer_name, safe_storage_name


class JsonVectorStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, assessment_id: str, name: str) -> Path:
        folder = self._root / safe_storage_name(assessment_id)
        folder.mkdir(parents=True, exist_ok=True)
        layer = safe_layer_name(name)
        return folder / f"{layer}.geojson"

    def write_features(self, assessment_id: str, name: str, features: list[dict[str, Any]]) -> str:
        path = self._path(assessment_id, name)
        payload = {"type": "FeatureCollection", "features": features}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def read_features(self, assessment_id: str, name: str) -> list[dict[str, Any]]:
        path = self._path(assessment_id, name)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("features") or [])
