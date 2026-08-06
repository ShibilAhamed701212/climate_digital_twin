import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipeline.providers.authenticity import DataAuthenticity
from pipeline.providers.manager import Observation
from pipeline.sources.location_registry import Location, LocationRegistry
from pipeline.stores.observation_store import ObservationStore
from simulator.events.event_bus import EventBus
from simulator.models.twin_state import TwinState
from simulator.repository.versioned_state_store import VersionedStateStore
from simulator.synchronizer.checkpoint import SyncCheckpoint
from simulator.synchronizer.sync_result import (
    CREATED,
    FAILED,
    NO_STATE_CHANGE,
    OUT_OF_ORDER,
    REJECTED_QUALITY,
    REJECTED_SYNTHETIC,
    SKIPPED_DUPLICATE,
    UPDATED,
)
from simulator.synchronizer.twin_sync_service import TwinSyncService


def _make_obs(
    provider="open_meteo",
    authenticity=DataAuthenticity.REAL,
    quality_flag="validated",
    temp=22.1,
    humidity=88.0,
    pressure=907.9,
    lat=12.97,
    lon=77.59,
    run_id="run_001",
    obs_id="obs_001",
    timestamp=None,
) -> Observation:
    ts = timestamp or "2026-07-30T12:00:00+00:00"
    return Observation(
        provider=provider,
        source_dataset="OPEN_METEO_FORECAST",
        authenticity=authenticity,
        observation_timestamp=ts,
        retrieved_timestamp="2026-07-30T12:05:00+00:00",
        values={
            "temperature_2m": temp,
            "humidity_pct": humidity,
            "pressure_hpa": pressure,
            "wind_speed_10m": 16.6,
            "wind_direction_10m": 255.0,
            "precipitation_mm": 0.0,
        },
        units={"temperature_2m": "°C", "humidity_pct": "%"},
        location_id="",
        latitude=lat,
        longitude=lon,
        run_id=run_id,
        quality_flag=quality_flag,
        data_source_identifier=obs_id,
    )


def _make_service(
    tmp_dir: str,
) -> tuple[TwinSyncService, VersionedStateStore, EventBus, SyncCheckpoint]:
    store_dir = Path(tmp_dir) / "twin_store"
    store = VersionedStateStore(store_dir)
    cp_path = Path(tmp_dir) / "checkpoint.json"
    cp = SyncCheckpoint(cp_path)
    eb = EventBus()
    loc_reg = LocationRegistry(
        [
            Location(
                location_id="KA-BLR",
                name="Bengaluru",
                latitude=12.97,
                longitude=77.59,
                district="Bengaluru Urban",
            ),
        ]
    )
    service = TwinSyncService(store=store, event_bus=eb, checkpoint=cp, location_registry=loc_reg)
    return service, store, eb, cp


class TestSyncService:
    def test_initial_state_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs = _make_obs()
            result = service.sync_from_observation(obs)
            assert result.status == CREATED
            assert result.new_version == 1
            state = store.get_latest_state("KA-BLR")
            assert state is not None
            assert state.temperature_2m == 22.1
            assert state.authenticity == "REAL"
            assert state.observation_id == "obs_001"
            assert state.run_id == "run_001"

    def test_update_creates_new_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs1 = _make_obs(temp=22.1, obs_id="obs_001")
            r1 = service.sync_from_observation(obs1)
            assert r1.status == CREATED
            assert r1.new_version == 1
            obs2 = _make_obs(
                temp=22.8, humidity=84.0, obs_id="obs_002", timestamp="2026-07-30T13:00:00+00:00"
            )
            r2 = service.sync_from_observation(obs2)
            assert r2.status == UPDATED
            assert r2.old_version == 1
            assert r2.new_version == 2
            state = store.get_latest_state("KA-BLR")
            assert state is not None
            assert state.temperature_2m == 22.8
            assert state.humidity_pct == 84.0
            # Old version still retrievable
            v1 = store.get_state_by_version_number("KA-BLR", 1)
            assert v1 is not None
            assert v1.temperature_2m == 22.1

    def test_duplicate_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs = _make_obs(obs_id="obs_001")
            r1 = service.sync_from_observation(obs)
            assert r1.status == CREATED
            r2 = service.sync_from_observation(obs)
            assert r2.status == SKIPPED_DUPLICATE
            assert r2.new_version == 0
            state = store.get_latest_state("KA-BLR")
            assert state is not None
            # Only one version
            hist = store.get_version_history("KA-BLR")
            assert len(hist) == 1

    def test_synthetic_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs = _make_obs(authenticity=DataAuthenticity.SYNTHETIC)
            result = service.sync_from_observation(obs)
            assert result.status == REJECTED_SYNTHETIC
            state = store.get_latest_state("KA-BLR")
            assert state is None

    def test_rejected_quality_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs = _make_obs(quality_flag="rejected")
            result = service.sync_from_observation(obs)
            assert result.status == REJECTED_QUALITY
            state = store.get_latest_state("KA-BLR")
            assert state is None

    def test_out_of_order_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs1 = _make_obs(obs_id="obs_001", timestamp="2026-07-30T13:00:00+00:00")
            r1 = service.sync_from_observation(obs1)
            assert r1.status == CREATED
            obs2 = _make_obs(obs_id="obs_002", timestamp="2026-07-30T12:00:00+00:00")
            r2 = service.sync_from_observation(obs2)
            assert r2.status == OUT_OF_ORDER
            # Current state unchanged
            state = store.get_latest_state("KA-BLR")
            assert state is not None
            assert state.timestamp == datetime(2026, 7, 30, 13, 0, tzinfo=UTC)
            assert len(store.get_version_history("KA-BLR")) == 1

    def test_no_change_no_new_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs1 = _make_obs(temp=22.1, humidity=88.0, obs_id="obs_001")
            r1 = service.sync_from_observation(obs1)
            assert r1.status == CREATED
            obs2 = _make_obs(
                temp=22.1, humidity=88.0, obs_id="obs_002", timestamp="2026-07-30T13:00:00+00:00"
            )
            r2 = service.sync_from_observation(obs2)
            assert r2.status == NO_STATE_CHANGE
            assert r2.new_version == 1
            assert len(store.get_version_history("KA-BLR")) == 1

    def test_missing_variable_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs1 = Observation(
                provider="open_meteo",
                authenticity=DataAuthenticity.REAL,
                observation_timestamp="2026-07-30T12:00:00+00:00",
                retrieved_timestamp="2026-07-30T12:05:00+00:00",
                values={
                    "temperature_2m": 22.1,
                    "humidity_pct": 88.0,
                    "pressure_hpa": 907.9,
                    "wind_speed_10m": 16.6,
                    "wind_direction_10m": 255.0,
                    "precipitation_mm": 0.0,
                    "solar_radiation": 500.0,
                    "cloud_cover_pct": 75.0,
                },
                latitude=12.97,
                longitude=77.59,
                run_id="run_001",
                quality_flag="validated",
                data_source_identifier="obs_001",
            )
            r1 = service.sync_from_observation(obs1)
            assert r1.status == CREATED
            obs2 = Observation(
                provider="open_meteo",
                authenticity=DataAuthenticity.REAL,
                observation_timestamp="2026-07-30T13:00:00+00:00",
                retrieved_timestamp="2026-07-30T13:05:00+00:00",
                values={
                    "temperature_2m": 22.8,
                    "humidity_pct": 84.0,
                    "pressure_hpa": 908.0,
                    "wind_speed_10m": 16.6,
                    "wind_direction_10m": 255.0,
                    "precipitation_mm": 0.0,
                },
                latitude=12.97,
                longitude=77.59,
                run_id="run_002",
                quality_flag="validated",
                data_source_identifier="obs_002",
            )
            r2 = service.sync_from_observation(obs2)
            assert r2.status == UPDATED
            state = store.get_latest_state("KA-BLR")
            assert state is not None
            assert state.solar_radiation == 500.0
            assert state.cloud_cover_pct == 75.0

    def test_location_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            # Coordinates far from KA-BLR
            obs = _make_obs(lat=28.61, lon=77.23, obs_id="obs_001")
            result = service.sync_from_observation(obs)
            # Falls back to lat_lon slug, not KA-BLR
            assert "28" in result.location_id
            assert "77" in result.location_id
            state = store.get_latest_state("KA-BLR")
            assert state is None

    def test_event_emitted_on_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs = _make_obs(obs_id="obs_001")
            service.sync_from_observation(obs)
            events = eb.get_event_history()
            assert len(events) == 1
            assert events[0].event_type == "TwinStateCreated"
            assert events[0].location_id == "KA-BLR"

    def test_event_emitted_on_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs1 = _make_obs(temp=22.1, obs_id="obs_001")
            service.sync_from_observation(obs1)
            obs2 = _make_obs(temp=22.8, obs_id="obs_002", timestamp="2026-07-30T13:00:00+00:00")
            service.sync_from_observation(obs2)
            events = eb.get_event_history()
            assert len(events) == 2
            assert events[0].event_type == "TwinStateCreated"
            assert events[1].event_type == "TwinStateUpdated"

    def test_checkpoint_persists_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            cp_path = Path(tmp) / "checkpoint.json"
            store_dir = Path(tmp) / "twin_store"
            store = VersionedStateStore(store_dir)
            cp = SyncCheckpoint(cp_path)
            loc_reg = LocationRegistry(
                [
                    Location(
                        location_id="KA-BLR",
                        name="Bengaluru",
                        latitude=12.97,
                        longitude=77.59,
                        district="Bengaluru Urban",
                    ),
                ]
            )
            service = TwinSyncService(store=store, checkpoint=cp, location_registry=loc_reg)
            obs = _make_obs(obs_id="obs_001")
            r1 = service.sync_from_observation(obs)
            assert r1.status == CREATED
            # Simulate restart
            store2 = VersionedStateStore(store_dir)
            cp2 = SyncCheckpoint(cp_path)
            service2 = TwinSyncService(store=store2, checkpoint=cp2, location_registry=loc_reg)
            r2 = service2.sync_from_observation(obs)
            assert r2.status == SKIPPED_DUPLICATE
            state = store2.get_latest_state("KA-BLR")
            assert state is not None
            assert state.temperature_2m == 22.1

    def test_freshness_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs = _make_obs(obs_id="obs_001", timestamp=datetime.now(UTC).isoformat())
            service.sync_from_observation(obs)
            f = service.get_twin_freshness("KA-BLR")
            assert f["status"] == "HEALTHY"
            assert f["freshness"] == "FRESH"
            assert f["authenticity"] == "REAL"

    def test_freshness_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            f = service.get_twin_freshness("KA-BLR")
            assert f["status"] == "NO_REAL_DATA"
            assert f["freshness"] is None

    def test_provenance_preserved_in_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, store, eb, cp = _make_service(tmp)
            obs = Observation(
                provider="open_meteo",
                source_dataset="OPEN_METEO_FORECAST",
                authenticity=DataAuthenticity.REAL,
                observation_timestamp="2026-07-30T12:00:00+00:00",
                retrieved_timestamp="2026-07-30T12:05:00+00:00",
                values={
                    "temperature_2m": 22.1,
                    "humidity_pct": 88.0,
                    "pressure_hpa": 907.9,
                    "wind_speed_10m": 16.6,
                    "wind_direction_10m": 255.0,
                    "precipitation_mm": 0.0,
                },
                latitude=12.97,
                longitude=77.59,
                run_id="run_001",
                quality_flag="validated",
                data_source_identifier="obs_001",
            )
            service.sync_from_observation(obs)
            state = store.get_latest_state("KA-BLR")
            assert state is not None
            assert state.observation_id == "obs_001"
            assert state.run_id == "run_001"
            assert state.source_dataset == "OPEN_METEO_FORECAST"
            assert state.authenticity == "REAL"
            assert state.data_source == "open_meteo"
