from __future__ import annotations

from pathlib import Path

from simulator.repository.overlay_pointer_store import OverlayPointerStore


def test_overlay_pointer_roundtrip(tmp_path: Path) -> None:
    store = OverlayPointerStore(tmp_path / "p.jsonl")
    store.upsert(
        {
            "location_id": "KA-HAS-001",
            "assessment_id": "A1",
            "event_id": "E1",
            "disaster_type": "flood",
            "href_assessment": "/disaster/assessments/A1",
            "updated_at": "2026-01-01T00:00:00Z",
        }
    )
    row = store.get("KA-HAS-001")
    assert row is not None
    assert row["assessment_id"] == "A1"
    assert store.get("missing") is None
