"""Unit tests for simulator/repository/parquet_store.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pyarrow as pa
import pytest

from simulator.models.weather import DataSource, QualityFlag, WeatherObservation


@pytest.fixture
def sample_observations():
    return [
        WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC),
            temperature_2m=25.0,
            precipitation_mm=0.0,
            humidity_pct=70.0,
            pressure_hpa=1013.0,
            wind_speed_10m=3.0,
            wind_direction_10m=180.0,
            solar_radiation=300.0,
            cloud_cover_pct=50.0,
            soil_moisture=0.3,
            data_source=DataSource.OPEN_METEO,
            quality_flag=QualityFlag.RAW,
        ),
        WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=32.0,
            precipitation_mm=5.0,
            humidity_pct=55.0,
            pressure_hpa=1011.0,
            wind_speed_10m=4.0,
            wind_direction_10m=200.0,
            solar_radiation=700.0,
            cloud_cover_pct=30.0,
            soil_moisture=0.28,
        ),
        WeatherObservation(
            location_id="KA-MYS-001",
            latitude=12.30,
            longitude=76.65,
            timestamp=datetime(2024, 6, 1, 6, 0, tzinfo=UTC),
            temperature_2m=22.0,
            precipitation_mm=2.0,
            humidity_pct=80.0,
            pressure_hpa=1014.0,
            wind_speed_10m=2.0,
            wind_direction_10m=150.0,
        ),
    ]


class TestObservationToBatch:
    def test_batch_created(self, sample_observations):
        from simulator.repository.parquet_store import _observation_to_batch

        batch = _observation_to_batch(sample_observations)
        assert isinstance(batch, pa.RecordBatch)
        assert batch.num_rows == 3
        assert batch.schema.field("location_id").type == pa.string()

    def test_batch_fields(self, sample_observations):
        from simulator.repository.parquet_store import _observation_to_batch

        batch = _observation_to_batch(sample_observations[:1])
        assert batch.column("observation_id")[0].as_py() == sample_observations[0].observation_id
        assert batch.column("temperature_2m")[0].as_py() == 25.0

    def test_empty_list(self):
        from simulator.repository.parquet_store import _observation_to_batch

        batch = _observation_to_batch([])
        assert batch.num_rows == 0


class TestBatchToObservation:
    def test_roundtrip(self, sample_observations):
        from simulator.repository.parquet_store import (
            _batch_to_observation,
            _observation_to_batch,
        )

        batch = _observation_to_batch(sample_observations[:1])
        obs = _batch_to_observation(batch, 0)
        assert obs.location_id == sample_observations[0].location_id
        assert obs.temperature_2m == sample_observations[0].temperature_2m
        assert obs.humidity_pct == sample_observations[0].humidity_pct

    def test_roundtrip_optional_fields(self, sample_observations):
        from simulator.repository.parquet_store import (
            _batch_to_observation,
            _observation_to_batch,
        )

        batch = _observation_to_batch(sample_observations[:1])
        obs = _batch_to_observation(batch, 0)
        assert obs.solar_radiation == 300.0
        assert obs.cloud_cover_pct == 50.0

    def test_roundtrip_none_optionals(self, sample_observations):
        from simulator.repository.parquet_store import (
            _batch_to_observation,
            _observation_to_batch,
        )

        batch = _observation_to_batch(sample_observations[2:3])
        obs = _batch_to_observation(batch, 0)
        assert obs.solar_radiation is None
        assert obs.cloud_cover_pct is None
        assert obs.soil_moisture is None


class TestParquetObservationStoreWrite:
    def test_write_empty_returns_zero(self, tmp_path):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        count = store.write_observations([])
        assert count == 0

    def test_write_observations(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        count = store.write_observations(sample_observations)
        assert count == 3

    def test_write_creates_partitioned_files(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        parquet_files = list(tmp_path.rglob("*.parquet"))
        assert len(parquet_files) >= 2


class TestParquetObservationStoreQuery:
    def test_query_by_location(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        results = store.query_observations("KA-BLR-001")
        assert len(results) == 2

    def test_query_unknown_location(self, tmp_path):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        results = store.query_observations("NONEXISTENT")
        assert results == []

    def test_query_with_time_range(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        results = store.query_observations(
            "KA-BLR-001",
            start_time=datetime(2024, 6, 1, 8, 0, tzinfo=UTC),
            end_time=datetime(2024, 6, 1, 18, 0, tzinfo=UTC),
        )
        assert len(results) == 1
        assert results[0].temperature_2m == 32.0


class TestParquetObservationStoreLatest:
    def test_get_latest(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        latest = store.get_latest_observation("KA-BLR-001")
        assert latest is not None
        assert latest.temperature_2m == 32.0

    def test_get_latest_unknown(self, tmp_path):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        assert store.get_latest_observation("NONEXISTENT") is None


class TestParquetObservationStoreList:
    def test_list_locations(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        locations = store.list_locations()
        assert "KA-BLR-001" in locations
        assert "KA-MYS-001" in locations

    def test_list_locations_empty(self, tmp_path):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        assert store.list_locations() == []


class TestParquetObservationStoreCount:
    def test_observation_count(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        assert store.get_observation_count("KA-BLR-001") == 2
        assert store.get_observation_count("KA-MYS-001") == 1

    def test_observation_count_unknown(self, tmp_path):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        assert store.get_observation_count("NONEXISTENT") == 0


class TestParquetObservationStoreSummary:
    def test_storage_summary(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        summary = store.get_storage_summary()
        assert summary["num_locations"] == 2
        assert summary["total_observations"] == 3
        assert "KA-BLR-001" in summary["locations"]
        assert "KA-MYS-001" in summary["locations"]

    def test_storage_summary_empty(self, tmp_path):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        summary = store.get_storage_summary()
        assert summary["num_locations"] == 0
        assert summary["total_observations"] == 0


class TestParquetObservationStoreClear:
    def test_clear(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        assert store.get_observation_count("KA-BLR-001") == 2
        store.clear()
        assert store.get_observation_count("KA-BLR-001") == 0

    def test_base_dir_property(self, tmp_path):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        assert store.base_dir == tmp_path.resolve()


class TestParquetObservationStoreWriteMore:
    def test_write_multiple_locations(self, tmp_path):
        from simulator.models.weather import WeatherObservation
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        obs = [
            WeatherObservation(
                location_id="LOC-A",
                latitude=10.0,
                longitude=10.0,
                timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                temperature_2m=20.0,
                precipitation_mm=0.0,
                humidity_pct=50.0,
                pressure_hpa=1013.0,
                wind_speed_10m=2.0,
                wind_direction_10m=90.0,
            ),
            WeatherObservation(
                location_id="LOC-B",
                latitude=20.0,
                longitude=20.0,
                timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                temperature_2m=25.0,
                precipitation_mm=1.0,
                humidity_pct=60.0,
                pressure_hpa=1012.0,
                wind_speed_10m=3.0,
                wind_direction_10m=180.0,
            ),
        ]
        count = store.write_observations(obs)
        assert count == 2
        assert len(store.list_locations()) == 2


class TestParquetObservationStoreCorruptedFiles:
    def test_query_corrupted_parquet_handles_exception(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        parquet_files = list((tmp_path / "KA-BLR-001").rglob("*.parquet"))
        for pf in parquet_files:
            pf.write_text("not a real parquet file")
        results = store.query_observations("KA-BLR-001")
        assert results == []

    def test_query_corrupted_all_files_returns_empty(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        for loc_dir in tmp_path.iterdir():
            if loc_dir.is_dir():
                for pf in loc_dir.rglob("*.parquet"):
                    pf.write_text("garbage data")
        results = store.query_observations("KA-BLR-001")
        assert results == []

    def test_get_latest_corrupted_handles_exception(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        parquet_files = list((tmp_path / "KA-BLR-001").rglob("*.parquet"))
        for pf in parquet_files:
            pf.write_text("corrupted")
        result = store.get_latest_observation("KA-BLR-001")
        assert result is None

    def test_get_latest_corrupted_all_files_returns_none(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        for loc_dir in tmp_path.iterdir():
            if loc_dir.is_dir():
                for pf in loc_dir.rglob("*.parquet"):
                    pf.write_text("garbage")
        result = store.get_latest_observation("KA-BLR-001")
        assert result is None

    def test_list_locations_when_base_dir_deleted(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        import shutil

        shutil.rmtree(str(tmp_path))
        assert store.list_locations() == []

    def test_get_observation_count_corrupted_handles_exception(self, tmp_path, sample_observations):
        from simulator.repository.parquet_store import ParquetObservationStore

        store = ParquetObservationStore(base_dir=tmp_path)
        store.write_observations(sample_observations)
        parquet_files = list((tmp_path / "KA-BLR-001").rglob("*.parquet"))
        for pf in parquet_files:
            pf.write_text("bad data")
        count = store.get_observation_count("KA-BLR-001")
        assert count == 0
