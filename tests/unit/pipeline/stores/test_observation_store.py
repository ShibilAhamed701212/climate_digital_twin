from __future__ import annotations

from pathlib import Path

from pipeline.providers.manager import Observation
from pipeline.stores.observation_store import ObservationStore


def _make_obs(run_id: str = "test_run") -> Observation:
    return Observation(
        provider="open_meteo",
        source_dataset="OPEN_METEO_FORECAST",
        authenticity="REAL",
        location_id="test-loc",
        variable="temperature_2m",
        latitude=12.97,
        longitude=77.59,
        observation_timestamp="2026-07-30T12:00:00Z",
        retrieved_timestamp="2026-07-30T12:05:00Z",
        run_id=run_id,
        schema_version="1.0.0",
        quality_flag="raw",
        values={"temperature_2m": 27.4},
        units={"temperature_2m": "°C"},
    )


def test_save_batch(tmp_path: Path):
    store = ObservationStore(base_dir=str(tmp_path / "real"))
    count = store.save_batch([_make_obs()], run_id="test_run")
    assert count == 1
    files = list((tmp_path / "real" / "normalized").glob("*.parquet"))
    assert len(files) == 1
    assert "test_run" in files[0].name


def test_save_empty_batch(tmp_path: Path):
    store = ObservationStore(base_dir=str(tmp_path / "real"))
    count = store.save_batch([], run_id="test_run")
    assert count == 0


def test_latest_no_data(tmp_path: Path):
    store = ObservationStore(base_dir=str(tmp_path / "real"))
    result = store.latest()
    assert result is None


def test_save_and_latest(tmp_path: Path):
    store = ObservationStore(base_dir=str(tmp_path / "real"))
    store.save_batch([_make_obs()], run_id="test_run")
    result = store.latest(variable="temperature_2m")
    assert result is not None
    assert result.provider == "open_meteo"
    assert result.authenticity == "REAL"


def test_query_no_results(tmp_path: Path):
    store = ObservationStore(base_dir=str(tmp_path / "real"))
    results = store.query(variable="nonexistent")
    assert results == []
