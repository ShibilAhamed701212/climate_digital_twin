from __future__ import annotations

import json
from pathlib import Path

from pipeline.stores.raw_data_store import RawDataStore
from simulator.models.weather import DataSource


def test_save_raw_response(tmp_path: Path):
    store = RawDataStore(base_dir=str(tmp_path / "real"))
    result = store.save(
        provider=DataSource.OPEN_METEO,
        run_id="test_run_001",
        response_body='{"hourly": {"temperature_2m": [27.4]}}',
        endpoint="https://api.open-meteo.com/v1/forecast",
        coordinates=(12.97, 77.59),
    )
    assert result.exists()
    assert "test_run_001" in result.name
    assert result.suffix == ".json"


def test_save_includes_metadata(tmp_path: Path):
    store = RawDataStore(base_dir=str(tmp_path / "real"))
    result = store.save(
        provider=DataSource.OPEN_METEO,
        run_id="test_run_002",
        response_body='{"key": "value"}',
    )
    content = json.loads(result.read_text())
    assert "metadata" in content
    assert "response" in content
    assert content["metadata"]["provider"] == "open_meteo"
    assert content["metadata"]["run_id"] == "test_run_002"
    assert "response_sha256" in content["metadata"]
    assert content["response"] == '{"key": "value"}'


def test_save_nasa_power(tmp_path: Path):
    store = RawDataStore(base_dir=str(tmp_path / "real"))
    result = store.save(
        provider=DataSource.NASA_POWER,
        run_id="test_run_003",
        response_body="nasa data",
    )
    assert "nasa_power" in str(result)
    assert result.exists()
