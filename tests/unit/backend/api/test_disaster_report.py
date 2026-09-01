from __future__ import annotations

from copilot.clients.report_client import _compose_disaster_report


def test_disaster_report_unavailable(monkeypatch) -> None:
    class _Fake:
        def twin_overlay(self, location: str) -> dict:
            return {"available": False, "location_id": location}

    monkeypatch.setattr("climatedt.disaster.client.DisasterHttpClient", _Fake)
    text = _compose_disaster_report("KA-HAS-001")
    assert "No verified disaster assessment is available" in text


def test_disaster_report_uses_kpis(monkeypatch) -> None:
    class _Fake:
        def twin_overlay(self, location: str) -> dict:
            return {
                "available": True,
                "assessment_id": "A1",
                "quality_flags": ["s1_only"],
                "kpis": {"flood_area_km2": 1.1, "buildings_in_water": 3, "pop_exposed_est": None},
            }

    monkeypatch.setattr("climatedt.disaster.client.DisasterHttpClient", _Fake)
    text = _compose_disaster_report("KA-HAS-001")
    assert "1.1" in text
    assert "unavailable" in text
