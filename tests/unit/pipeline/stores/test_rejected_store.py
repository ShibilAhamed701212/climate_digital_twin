from __future__ import annotations

from pathlib import Path

from pipeline.providers.manager import Observation
from pipeline.stores.rejected_store import RejectedStore


def test_save_batch(tmp_path: Path):
    store = RejectedStore(base_dir=str(tmp_path / "real"))
    obs = Observation(
        provider="open_meteo",
        quality_flag="rejected",
        location_id="test-loc",
        variable="temperature_2m",
    )
    count = store.save_batch([obs], run_id="test_run")
    assert count == 1
    files = list((tmp_path / "real" / "rejected").glob("*.parquet"))
    assert len(files) == 1
    assert "rejected_test_run" in files[0].name


def test_save_empty(tmp_path: Path):
    store = RejectedStore(base_dir=str(tmp_path / "real"))
    count = store.save_batch([], run_id="test_run")
    assert count == 0
