"""Tests for models/forecast_provenance.py."""

from pathlib import Path

from models.forecast_provenance import ForecastResult, ForecastStore


class TestForecastResult:
    def test_roundtrip_dict(self):
        fr = ForecastResult(
            location_id="KA-BLR-001",
            rainfall=10.5,
            max_temp=32.0,
            min_temp=22.0,
            model_id="lstm-v1",
            training_run_id="run_abc123",
            authenticity="REAL",
        )
        d = fr.to_dict()
        assert d["location_id"] == "KA-BLR-001"
        assert d["rainfall"] == 10.5
        assert d["model_id"] == "lstm-v1"

        fr2 = ForecastResult.from_dict(d)
        assert fr2.location_id == "KA-BLR-001"
        assert fr2.rainfall == 10.5
        assert fr2.model_id == "lstm-v1"
        assert fr2.forecast_id == fr.forecast_id

    def test_default_id_is_unique(self):
        fr1 = ForecastResult()
        fr2 = ForecastResult()
        assert fr1.forecast_id != fr2.forecast_id


class TestForecastStore:
    def test_save_and_list(self, tmp_path: Path):
        store = ForecastStore(path=str(tmp_path / "forecasts.jsonl"))
        fr = ForecastResult(location_id="KA-BLR-001", rainfall=5.0)
        store.save(fr)

        recent = store.list_recent(limit=5)
        assert len(recent) == 1
        assert recent[0].location_id == "KA-BLR-001"
        assert recent[0].rainfall == 5.0

    def test_empty_store_returns_empty(self, tmp_path: Path):
        store = ForecastStore(path=str(tmp_path / "nonexistent.jsonl"))
        assert store.list_recent() == []

    def test_limit_works(self, tmp_path: Path):
        store = ForecastStore(path=str(tmp_path / "multi.jsonl"))
        for i in range(10):
            store.save(ForecastResult(location_id=f"LOC-{i}"))
        recent = store.list_recent(limit=3)
        assert len(recent) == 3
        assert recent[0].location_id == "LOC-9"
