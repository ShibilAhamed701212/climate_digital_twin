"""Smoke STAC search (requires network + optional CDSE credentials)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from disaster_intelligence.adapters.stac.cdse import CdseStacAdapter
from disaster_intelligence.config import load_disaster_config


def main() -> int:
    cfg = load_disaster_config()
    stac = cfg.get("stac") or {}
    adapter = CdseStacAdapter(
        search_url=str(stac.get("search_url") or ""),
        cache_dir=Path("data/disaster/tmp/stac_cache"),
        host_allowlist=list(stac.get("host_allowlist") or []),
    )
    aoi = {
        "type": "Polygon",
        "coordinates": [[[77.4, 12.8], [77.8, 12.8], [77.8, 13.15], [77.4, 13.15], [77.4, 12.8]]],
    }
    try:
        items = adapter.search(aoi, "2024-01-01T00:00:00Z", "2024-01-08T00:00:00Z", ["sentinel-1-grd"])
    except Exception as exc:
        print(f"STAC unavailable (external blocker): {exc}")
        return 2
    print(json.dumps({"count": len(items)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
