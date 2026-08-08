"""Unit tests for simulator/repository/versioned_state_store.py."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from simulator.models.twin_state import TwinState


def make_state(
    entity_id: str = "KA-BLR-001",
    temperature: float = 28.0,
    precipitation: float = 5.0,
    humidity: float = 60.0,
    pressure: float = 1013.0,
    wind_speed: float = 3.0,
    wind_direction: float = 180.0,
    timestamp: datetime | None = None,
) -> TwinState:
    return TwinState(
        entity_id=entity_id,
        timestamp=timestamp or datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        temperature_2m=temperature,
        precipitation_mm=precipitation,
        humidity_pct=humidity,
        pressure_hpa=pressure,
        wind_speed_10m=wind_speed,
        wind_direction_10m=wind_direction,
        data_source="open_meteo",
        quality_flag="raw",
    )


@pytest.fixture
def store(tmp_path):
    from simulator.repository.versioned_state_store import VersionedStateStore

    with patch("simulator.repository.versioned_state_store.get_config") as mock_cfg:
        cfg = mock_cfg.return_value
        cfg.twin_state_dir = str(tmp_path)
        cfg.max_versions_per_location = 10
        cfg.version_index_name = "version_index.parquet"
        yield VersionedStateStore(base_dir=tmp_path)


class TestSaveState:
    def test_save_first_version(self, store):
        state = make_state()
        version = store.save_state(state, created_by="test", description="first")
        assert version.version_number == 1
        assert version.entity_id == "KA-BLR-001"
        assert version.created_by == "test"
        assert version.description == "first"

    def test_save_increments_version(self, store):
        state = make_state()
        v1 = store.save_state(state)
        assert v1.version_number == 1
        v2 = store.save_state(state)
        assert v2.version_number == 2

    def test_save_parent_version(self, store):
        state = make_state()
        v1 = store.save_state(state)
        v2 = store.save_state(state)
        assert v2.parent_version_id == v1.version_id

    def test_save_creates_file(self, store):
        state = make_state()
        store.save_state(state)
        parquet_files = list(store._base_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1

    def test_save_entity_dir_created(self, store):
        state = make_state()
        store.save_state(state)
        entity_dir = store._base_dir / "KA-BLR-001"
        assert entity_dir.exists()

    def test_save_with_solar_and_cloud(self, store):
        state = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=28.0,
            precipitation_mm=5.0,
            humidity_pct=60.0,
            pressure_hpa=1013.0,
            wind_speed_10m=3.0,
            wind_direction_10m=180.0,
            solar_radiation=500.0,
            cloud_cover_pct=40.0,
            soil_moisture=0.25,
        )
        version = store.save_state(state)
        assert version.version_number == 1


class TestGetState:
    def test_get_state_by_version(self, store):
        state = make_state()
        v1 = store.save_state(state)
        retrieved = store.get_state("KA-BLR-001", v1.version_id)
        assert retrieved is not None
        assert retrieved.temperature_2m == 28.0
        assert retrieved.humidity_pct == 60.0

    def test_get_state_not_found(self, store):
        retrieved = store.get_state("KA-BLR-001", "nonexistent")
        assert retrieved is None

    def test_get_state_wrong_entity(self, store):
        state = make_state()
        store.save_state(state)
        retrieved = store.get_state("WRONG-ENTITY", "some_id")
        assert retrieved is None

    def test_get_state_after_multiple_saves(self, store):
        s1 = make_state(temperature=25.0)
        s2 = make_state(temperature=30.0)
        v1 = store.save_state(s1)
        store.save_state(s2)
        retrieved = store.get_state("KA-BLR-001", v1.version_id)
        assert retrieved is not None
        assert retrieved.temperature_2m == 25.0


class TestGetLatestState:
    def test_get_latest(self, store):
        s1 = make_state(temperature=25.0)
        s2 = make_state(temperature=30.0)
        store.save_state(s1)
        store.save_state(s2)
        latest = store.get_latest_state("KA-BLR-001")
        assert latest is not None
        assert latest.temperature_2m == 30.0

    def test_get_latest_no_versions(self, store):
        assert store.get_latest_state("NONEXISTENT") is None


class TestGetVersionHistory:
    def test_history_ordered(self, store):
        s1 = make_state(temperature=25.0)
        s2 = make_state(temperature=30.0)
        store.save_state(s1)
        store.save_state(s2)
        history = store.get_version_history("KA-BLR-001")
        assert len(history) == 2
        assert history[0].version_number == 2
        assert history[1].version_number == 1

    def test_history_empty(self, store):
        assert store.get_version_history("NONEXISTENT") == []

    def test_history_fields(self, store):
        state = make_state()
        _v1 = store.save_state(state, created_by="test_user", description="test_desc")
        history = store.get_version_history("KA-BLR-001")
        assert len(history) == 1
        assert history[0].created_by == "test_user"
        assert history[0].description == "test_desc"


class TestRollback:
    def test_rollback_creates_new_version(self, store):
        s1 = make_state(temperature=25.0)
        s2 = make_state(temperature=35.0)
        v1 = store.save_state(s1)
        store.save_state(s2)
        rolled = store.rollback("KA-BLR-001", v1.version_id)
        assert rolled.temperature_2m == 25.0
        latest = store.get_latest_state("KA-BLR-001")
        assert latest.temperature_2m == 25.0

    def test_rollback_not_found(self, store):
        with pytest.raises(ValueError, match="not found"):
            store.rollback("KA-BLR-001", "nonexistent")


class TestRegisterEntityLocation:
    def test_register_and_query(self, store):
        store.register_entity_location("KA-BLR-001", 12.97, 77.59)
        locations_file = store._base_dir / "entity_locations.parquet"
        assert locations_file.exists()

    def test_register_multiple(self, store):
        store.register_entity_location("LOC-A", 10.0, 20.0)
        store.register_entity_location("LOC-B", 30.0, 40.0)
        locations_file = store._base_dir / "entity_locations.parquet"
        assert locations_file.exists()


class TestQuerySpatial:
    def test_query_spatial_finds_in_bbox(self, store):
        store.register_entity_location("KA-BLR-001", 12.97, 77.59)
        store.save_state(make_state(entity_id="KA-BLR-001"))
        results = store.query_spatial((10.0, 70.0, 15.0, 80.0))
        assert len(results) == 1

    def test_query_spatial_outside_bbox(self, store):
        store.register_entity_location("KA-BLR-001", 12.97, 77.59)
        store.save_state(make_state(entity_id="KA-BLR-001"))
        results = store.query_spatial((20.0, 80.0, 30.0, 90.0))
        assert len(results) == 0

    def test_query_spatial_no_locations(self, store):
        results = store.query_spatial((-90, -180, 90, 180))
        assert results == []


class TestGetStateAtTime:
    def test_find_nearest(self, store):
        s1 = make_state(timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC))
        s2 = make_state(timestamp=datetime(2024, 6, 1, 18, 0, tzinfo=UTC))
        store.save_state(s1)
        store.save_state(s2)
        result = store.get_state_at_time("KA-BLR-001", datetime(2024, 6, 1, 7, 0, tzinfo=UTC))
        assert result is not None
        assert result.timestamp.hour == 6

    def test_no_versions(self, store):
        result = store.get_state_at_time("NONEXISTENT", datetime(2024, 6, 1, 12, 0, tzinfo=UTC))
        assert result is None


class TestQueryStatesInTimeRange:
    def test_finds_in_range(self, store):
        s1 = make_state(timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC))
        s2 = make_state(timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC))
        store.save_state(s1)
        store.save_state(s2)
        results = store.query_states_in_time_range(
            "KA-BLR-001",
            datetime(2024, 6, 1, 8, 0, tzinfo=UTC),
            datetime(2024, 6, 1, 14, 0, tzinfo=UTC),
        )
        assert len(results) == 1
        assert results[0].timestamp.hour == 12

    def test_out_of_range(self, store):
        s1 = make_state(timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC))
        store.save_state(s1)
        results = store.query_states_in_time_range(
            "KA-BLR-001",
            datetime(2024, 7, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 7, 2, 0, 0, tzinfo=UTC),
        )
        assert len(results) == 0

    def test_no_versions(self, store):
        results = store.query_states_in_time_range(
            "NONEXISTENT",
            datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 12, 31, 0, 0, tzinfo=UTC),
        )
        assert results == []


class TestSaveStates:
    def test_save_multiple(self, store):
        states = [
            make_state(entity_id="KA-BLR-001"),
            make_state(entity_id="KA-MYS-001"),
        ]
        versions = store.save_states(states)
        assert len(versions) == 2

    def test_save_states_versions(self, store):
        states = [
            make_state(entity_id="KA-BLR-001", temperature=25.0),
            make_state(entity_id="KA-BLR-001", temperature=30.0),
        ]
        versions = store.save_states(states)
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2


class TestGetStates:
    def test_get_multiple_states(self, store):
        store.save_state(make_state(entity_id="KA-BLR-001"))
        store.save_state(make_state(entity_id="KA-MYS-001"))
        results = store.get_states(["KA-BLR-001", "KA-MYS-001"])
        assert len(results) == 2
        assert "KA-BLR-001" in results
        assert results["KA-BLR-001"] is not None

    def test_get_states_missing(self, store):
        results = store.get_states(["NONEXISTENT"])
        assert results["NONEXISTENT"] is None


class TestComputeDelta:
    def test_compute_delta(self, store):
        s1 = make_state(temperature=25.0, precipitation=5.0)
        s2 = make_state(temperature=30.0, precipitation=10.0)
        v1 = store.save_state(s1)
        v2 = store.save_state(s2)
        delta = store.compute_delta("KA-BLR-001", v1.version_id, v2.version_id)
        assert delta.delta_temperature == 5.0
        assert delta.delta_precipitation == 5.0
        assert delta.from_version_id == v1.version_id
        assert delta.to_version_id == v2.version_id

    def test_compute_delta_reverse(self, store):
        s1 = make_state(temperature=25.0)
        s2 = make_state(temperature=30.0)
        v1 = store.save_state(s1)
        v2 = store.save_state(s2)
        delta = store.compute_delta("KA-BLR-001", v2.version_id, v1.version_id)
        assert delta.delta_temperature == -5.0

    def test_compute_delta_version_a_missing(self, store):
        s = make_state()
        v = store.save_state(s)
        with pytest.raises(ValueError, match="not found"):
            store.compute_delta("KA-BLR-001", "missing", v.version_id)

    def test_compute_delta_version_b_missing(self, store):
        s = make_state()
        v = store.save_state(s)
        with pytest.raises(ValueError, match="not found"):
            store.compute_delta("KA-BLR-001", v.version_id, "missing")


class TestQueryBySource:
    def test_query_by_source(self, store):
        s1 = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=28.0,
            precipitation_mm=5.0,
            humidity_pct=60.0,
            pressure_hpa=1013.0,
            wind_speed_10m=3.0,
            wind_direction_10m=180.0,
            data_source="open_meteo",
        )
        s2 = TwinState(
            entity_id="KA-MYS-001",
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=25.0,
            precipitation_mm=2.0,
            humidity_pct=70.0,
            pressure_hpa=1014.0,
            wind_speed_10m=2.0,
            wind_direction_10m=90.0,
            data_source="era5",
        )
        store.save_state(s1)
        store.save_state(s2)
        results = store.query_by_source("open_meteo")
        assert len(results) == 1

    def test_query_by_source_none(self, store):
        results = store.query_by_source("nonexistent")
        assert results == []


class TestQueryByQuality:
    def test_query_by_quality(self, store):
        s1 = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=28.0,
            precipitation_mm=5.0,
            humidity_pct=60.0,
            pressure_hpa=1013.0,
            wind_speed_10m=3.0,
            wind_direction_10m=180.0,
            quality_flag="validated",
        )
        s2 = TwinState(
            entity_id="KA-MYS-001",
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=25.0,
            precipitation_mm=2.0,
            humidity_pct=70.0,
            pressure_hpa=1014.0,
            wind_speed_10m=2.0,
            wind_direction_10m=90.0,
            quality_flag="raw",
        )
        store.save_state(s1)
        store.save_state(s2)
        results = store.query_by_quality("validated")
        assert len(results) == 1


class TestGetStateByVersionNumber:
    def test_find_by_version_number(self, store):
        s1 = make_state(temperature=25.0)
        s2 = make_state(temperature=30.0)
        store.save_state(s1)
        store.save_state(s2)
        result = store.get_state_by_version_number("KA-BLR-001", 1)
        assert result is not None
        assert result.temperature_2m == 25.0

    def test_version_number_not_found(self, store):
        result = store.get_state_by_version_number("KA-BLR-001", 999)
        assert result is None

    def test_version_number_wrong_entity(self, store):
        store.save_state(make_state())
        result = store.get_state_by_version_number("NONEXISTENT", 1)
        assert result is None


class TestClear:
    def test_clear_removes_data(self, store):
        store.save_state(make_state())
        assert store.get_latest_state("KA-BLR-001") is not None
        store.clear()
        assert store.get_latest_state("KA-BLR-001") is None

    def test_clear_recreates_dir(self, store):
        store.save_state(make_state())
        store.clear()
        assert store._base_dir.exists()


class TestEnforceMaxVersions:
    def test_enforce_removes_old_versions(self, store):
        store._max_versions = 2
        state = make_state()
        store.save_state(state)
        store.save_state(state)
        store.save_state(state)
        history = store.get_version_history("KA-BLR-001")
        assert len(history) == 2

    def test_enforce_max_versions_zero(self, store):
        store._max_versions = 0
        state = make_state()
        v = store.save_state(state)
        assert v.version_number == 1

    def test_enforce_max_versions_negative(self, store):
        store._max_versions = -1
        state = make_state()
        v = store.save_state(state)
        assert v.version_number == 1

    def test_enforce_max_versions_unlink_error(self, store):
        from unittest.mock import patch

        store._max_versions = 1
        state = make_state()
        v1 = store.save_state(state)
        _ = type(v1.state.timestamp).__class__
        with patch("pathlib.Path.unlink", side_effect=PermissionError("locked")):
            v2 = store.save_state(state)
        assert v2.version_number == 2


class TestReadVersionIndexErrors:
    def test_read_version_index_corrupted(self, store):
        index_path = store._version_index_path
        index_path.write_text("not a parquet file")
        table = store._read_version_index()
        assert table.num_rows == 0

    def test_read_version_index_missing(self, store):
        table = store._read_version_index()
        assert table.num_rows == 0


class TestReadStateFileErrors:
    def test_read_state_file_empty(self, store):
        state = make_state()
        v = store.save_state(state)
        file_path = store._base_dir / "KA-BLR-001" / f"v{v.version_number:06d}.parquet"
        import pyarrow as pa
        import pyarrow.parquet as pq

        from simulator.repository.versioned_state_store import _TWIN_STATE_SCHEMA

        empty = pa.Table.from_batches([], schema=_TWIN_STATE_SCHEMA)
        pq.write_table(empty, str(file_path), compression="snappy")
        result = store._read_state_file(str(file_path))
        assert result is None

    def test_read_state_file_corrupted(self, store):
        state = make_state()
        store.save_state(state)
        parquet_files = list(store._base_dir.rglob("v*.parquet"))
        assert len(parquet_files) >= 1
        parquet_files[0].write_text("not a parquet file")
        result = store.get_latest_state("KA-BLR-001")
        assert result is None


class TestEntityLocationsErrors:
    def test_load_entity_locations_corrupted(self, store):
        locations_file = store._base_dir / "entity_locations.parquet"
        locations_file.write_text("not parquet")
        result = store._load_entity_locations()
        assert result == {}

    def test_save_entity_locations_error(self, store):
        with patch("pyarrow.parquet.write_table", side_effect=RuntimeError("write failed")):
            store._save_entity_locations({"test": (1.0, 2.0)})
        assert not store._entity_locations_path().exists()


class TestEntityStateAtTimeContinue:
    def test_entity_state_at_time_skips_none(self, store):
        from datetime import UTC, datetime

        s1 = make_state(
            timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC),
        )
        store.save_state(s1)
        state_path = list((store._base_dir / "KA-BLR-001").glob("v*.parquet"))[0]
        state_path.write_text("corrupt")
        result = store.get_state_at_time("KA-BLR-001", datetime(2024, 6, 1, 12, 0, tzinfo=UTC))
        assert result is None


class TestQueryStatesInTimeRangeContinue:
    def test_skip_none_states(self, store):
        s1 = make_state(timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC))
        s2 = make_state(timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC))
        store.save_state(s1)
        store.save_state(s2)
        parquet_files = list((store._base_dir / "KA-BLR-001").glob("v*.parquet"))
        for pf in parquet_files:
            if pf.name.endswith("000002.parquet"):
                pf.write_text("corrupt")
                break
        results = store.query_states_in_time_range(
            "KA-BLR-001",
            datetime(2024, 6, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 6, 30, 0, 0, tzinfo=UTC),
        )
        assert len(results) == 1


class TestComputeDeltaOptionalFields:
    def test_compute_delta_with_optional_fields(self, store):
        from datetime import UTC, datetime

        from simulator.models.twin_state import TwinState

        s1 = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=28.0,
            precipitation_mm=5.0,
            humidity_pct=60.0,
            pressure_hpa=1013.0,
            wind_speed_10m=3.0,
            wind_direction_10m=180.0,
            solar_radiation=500.0,
            cloud_cover_pct=40.0,
            soil_moisture=0.25,
        )
        s2 = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=30.0,
            precipitation_mm=10.0,
            humidity_pct=65.0,
            pressure_hpa=1010.0,
            wind_speed_10m=4.0,
            wind_direction_10m=190.0,
            solar_radiation=600.0,
            cloud_cover_pct=50.0,
            soil_moisture=0.30,
        )
        v1 = store.save_state(s1)
        v2 = store.save_state(s2)
        delta = store.compute_delta("KA-BLR-001", v1.version_id, v2.version_id)
        assert delta.delta_solar_radiation == 100.0
        assert delta.delta_cloud_cover == 10.0
        assert delta.delta_soil_moisture == pytest.approx(0.05)


class TestClearRetry:
    def test_clear_permission_retry_succeeds(self, store):
        import shutil

        original_rmtree = shutil.rmtree
        call_count = [0]

        def flaky_rmtree(path):
            call_count[0] += 1
            if call_count[0] == 1:
                raise PermissionError("access denied")
            return original_rmtree(path)

        store.save_state(make_state())
        with patch("shutil.rmtree", flaky_rmtree):
            store.clear()
        assert call_count[0] >= 1
        assert store._base_dir.exists()

    def test_clear_permission_all_fail(self, store):
        def always_fail(_path):
            raise PermissionError("always fails")

        store.save_state(make_state())
        with patch("shutil.rmtree", always_fail), pytest.raises(PermissionError):
            store.clear()
