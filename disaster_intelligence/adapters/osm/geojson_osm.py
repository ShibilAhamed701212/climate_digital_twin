from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GeojsonOsmAdapter:
    """Loads OSM-like GeoJSON grouped by layer name (buildings, roads, amenities)."""

    def __init__(self, extract_path: str) -> None:
        self._path = Path(extract_path)

    def load(self, aoi: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        _ = aoi
        empty: dict[str, list[dict[str, Any]]] = {
            "buildings": [],
            "roads": [],
            "amenities": [],
        }
        if not self._path.exists():
            return empty
        data = json.loads(self._path.read_text(encoding="utf-8"))
        features = list(data.get("features") or [])
        for feat in features:
            props = feat.get("properties") or {}
            layer = str(props.get("layer") or "")
            amenity = str(props.get("amenity") or "")
            if layer == "buildings" or props.get("building"):
                empty["buildings"].append(feat)
            elif layer == "roads" or props.get("highway"):
                empty["roads"].append(feat)
            elif amenity in {"hospital", "school", "clinic"} or layer == "amenities":
                empty["amenities"].append(feat)
        return empty
