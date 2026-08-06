from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pipeline.providers.fetch_result import FetchResult
from pipeline.providers.manager import Observation
from pipeline.stores.manifest_writer import ManifestWriter
from simulator.models.weather import DataSource


def test_write_manifest(tmp_path: Path):
    writer = ManifestWriter(base_dir=str(tmp_path))
    result = FetchResult(
        provider=DataSource.OPEN_METEO,
        status="SUCCESS",
        observations=[{"dummy": "obs"}],
        requested_at=datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 30, 12, 5, tzinfo=UTC),
    )
    valid = [
        Observation(
            provider="open_meteo",
            authenticity="REAL",
            location_id="loc1",
            variable="temperature_2m",
            observation_timestamp="2026-07-30T12:00:00Z",
            retrieved_timestamp="2026-07-30T12:05:00Z",
        )
    ]
    manifest = writer.write(run_id="test_run", fetch_result=result, valid=valid, rejected=[])
    assert manifest.run_id == "test_run"
    assert manifest.provider == "open_meteo"
    assert manifest.status == "SUCCESS"
    assert manifest.records_received == 1
    assert manifest.records_normalized == 1
    assert manifest.records_validated == 1
    assert manifest.records_rejected == 0
    assert manifest.records_persisted == 1
    assert manifest.synthetic_count == 0
    assert manifest.error is None


def test_write_manifest_failure(tmp_path: Path):
    writer = ManifestWriter(base_dir=str(tmp_path))
    result = FetchResult(
        provider=DataSource.NASA_POWER,
        status="FAILED",
        observations=[],
        error_code="SOURCE_UNAVAILABLE",
        error_message="API down",
    )
    manifest = writer.write(run_id="test_fail", fetch_result=result, valid=[], rejected=[])
    assert manifest.status == "FAILED"
    assert manifest.error == "API down"
    assert manifest.records_persisted == 0
    assert manifest.synthetic_count == 0


def test_write_manifest_file_created(tmp_path: Path):
    writer = ManifestWriter(base_dir=str(tmp_path))
    result = FetchResult(provider=DataSource.OPEN_METEO, status="SUCCESS", observations=[{}])
    writer.write(run_id="verify_file", fetch_result=result, valid=[], rejected=[])
    manifest_file = tmp_path / "manifests" / "verify_file.json"
    assert manifest_file.exists()
    import json

    data = json.loads(manifest_file.read_text())
    assert data["run_id"] == "verify_file"
    assert data["synthetic_count"] == 0
