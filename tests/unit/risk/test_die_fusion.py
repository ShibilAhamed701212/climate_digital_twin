from __future__ import annotations

from types import SimpleNamespace

from climatedt.risk.service import RiskService


def test_die_fusion_attaches_metadata_without_score(monkeypatch) -> None:
    monkeypatch.setenv("RISK_DIE_FUSION", "true")
    monkeypatch.setenv("RISK_DIE_ADJUST_SCORE", "true")

    class _Fake:
        def twin_overlay(self, location_id: str) -> dict:
            assert location_id == "KA-HAS-001"
            return {
                "available": True,
                "assessment_id": "A1",
                "kpis": {"flood_area_km2": 2.5, "flood_fraction": 0.4},
            }

    monkeypatch.setattr("climatedt.disaster.client.DisasterHttpClient", _Fake)
    result = SimpleNamespace(metadata={})
    RiskService._attach_disaster_metadata(object.__new__(RiskService), result, "KA-HAS-001")
    assert result.metadata["disaster_available"] == "true"
    assert result.metadata["disaster_assessment_id"] == "A1"
    assert result.metadata["observed_flood_area_km2"] == "2.5"


def test_die_fusion_off_skips(monkeypatch) -> None:
    monkeypatch.setenv("RISK_DIE_FUSION", "false")
    result = SimpleNamespace(metadata={})
    RiskService._attach_disaster_metadata(object.__new__(RiskService), result, "KA-HAS-001")
    assert result.metadata == {}
