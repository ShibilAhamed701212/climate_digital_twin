"""Integration tests for the Digital Twin Engine.

Tests the full entity lifecycle: create → observe → forecast → scenario → rollback.
"""

from pathlib import Path

import pytest
import yaml

from simulator.engine.twin_engine import DigitalTwinEngine


@pytest.fixture
def engine(tmp_path: Path) -> DigitalTwinEngine:
    config_path = tmp_path / "twin_config.yaml"
    config = {
        "twin": {"name": "test_twin", "version": "1.0", "region": "Karnataka"},
        "storage": {
            "engine": "duckdb",
            "path": str(tmp_path / "twin_store"),
            "parquet_compression": "snappy",
        },
        "state": {
            "max_versions_per_entity": 1000,
            "enforce_immutable": True,
            "validate_coordinates": False,
            "validate_temperatures": {"min": -10, "max": 55},
            "validate_rainfall": {"min": 0, "max": 2000},
        },
        "events": {"enabled": True, "max_subscribers": 50},
        "api": {"host": "0.0.0.0", "port": 8001},
    }
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    store_dir = str(tmp_path / "twin_store")
    return DigitalTwinEngine(config_path=str(config_path), store_dir=store_dir)


class TestDigitalTwinEngine:
    """Integration tests for the full Digital Twin lifecycle."""

    def test_create_and_observe(self, engine: DigitalTwinEngine):
        entity = engine.create_entity("KA-BLR-001", 12.97, 77.59, "Bengaluru Urban")
        result = engine.ingest_observation(entity.update_state(rainfall=50))
        assert result["version_id"] == 1
        state = engine.get_current_state("KA-BLR-001")
        assert state is not None
        assert state["rainfall"] == 50

    def test_observe_then_forecast(self, engine: DigitalTwinEngine):
        e = engine.create_entity("KA-BLR-001", 12.97, 77.59)
        e = e.update_state(rainfall=50, max_temp=32, min_temp=20)
        engine.ingest_observation(e)
        f = e.update_state(rainfall=60, max_temp=30, min_temp=19, prediction_confidence=0.85)
        engine.apply_forecast(f)
        current = engine.get_current_state("KA-BLR-001")
        forecast = engine.get_forecast_state("KA-BLR-001")
        assert current["rainfall"] == 50
        assert forecast["rainfall"] == 60

    def test_full_lifecycle(self, engine: DigitalTwinEngine):
        e = engine.create_entity("KA-BLR-001", 12.97, 77.59)
        engine.ingest_observation(e.update_state(rainfall=50, max_temp=32, min_temp=20))
        engine.apply_forecast(
            e.update_state(rainfall=60, max_temp=30, min_temp=19, prediction_confidence=0.85)
        )
        engine.apply_scenario(
            e.update_state(rainfall=80, max_temp=35, min_temp=22),
            scenario_id="temp_plus_2",
        )
        engine.update_risk("KA-BLR-001", 75.0)
        history = engine.get_state_history("KA-BLR-001")
        assert len(history) == 4

    def test_rollback(self, engine: DigitalTwinEngine):
        e = engine.create_entity("KA-BLR-001", 12.97, 77.59)
        engine.ingest_observation(e.update_state(rainfall=10))
        engine.ingest_observation(e.update_state(rainfall=50))
        result = engine.rollback("KA-BLR-001", 1)
        assert result["version_id"] == 3
        state = engine.get_current_state("KA-BLR-001")
        assert state["rainfall"] == 10

    def test_twin_refresh_event(self, engine: DigitalTwinEngine):
        received = []
        engine.event_bus.subscribe("TwinRefreshed", lambda ev: received.append(ev))
        engine.refresh_twin()
        assert len(received) == 1
        assert received[0].event_type == "TwinRefreshed"

    def test_persistence_across_engines(self, tmp_path: Path):
        config_path = tmp_path / "twin_config.yaml"
        config = {
            "twin": {"name": "test_twin", "version": "1.0", "region": "Karnataka"},
            "storage": {
                "engine": "duckdb",
                "path": str(tmp_path / "twin_store"),
                "parquet_compression": "snappy",
            },
            "state": {"validate_coordinates": False},
            "events": {"enabled": True, "max_subscribers": 50},
            "api": {"host": "0.0.0.0", "port": 8001},
        }
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        store_dir = str(tmp_path / "twin_store")
        e1 = DigitalTwinEngine(config_path=str(config_path), store_dir=store_dir)
        ent = e1.create_entity("KA-BLR-001", 12.97, 77.59)
        e1.ingest_observation(ent.update_state(rainfall=50))
        e2 = DigitalTwinEngine(config_path=str(config_path), store_dir=store_dir)
        state = e2.get_current_state("KA-BLR-001")
        assert state is not None
        assert state["rainfall"] == 50

    def test_multiple_locations(self, engine: DigitalTwinEngine):
        for loc_id, lat, lon in [("LOC-A", 15.0, 76.0), ("LOC-B", 16.0, 77.0)]:
            e = engine.create_entity(loc_id, lat, lon)
            engine.ingest_observation(e.update_state(rainfall=30))
        assert engine.get_current_state("LOC-A") is not None
        assert engine.get_current_state("LOC-B") is not None

    def test_state_history_timestamps(self, engine: DigitalTwinEngine):
        e = engine.create_entity("KA-BLR-001", 12.97, 77.59)
        engine.ingest_observation(e.update_state(rainfall=10))
        engine.ingest_observation(e.update_state(rainfall=20))
        engine.ingest_observation(e.update_state(rainfall=30))
        history = engine.get_state_history("KA-BLR-001")
        assert len(history) == 3
        timestamps = [h["timestamp"] for h in history]
        assert timestamps[0] <= timestamps[1] <= timestamps[2]
