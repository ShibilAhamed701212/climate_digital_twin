"""Versioned state store for digital twin entities.

Provides append-only versioned storage for twin states with support for
saving, querying by version, retrieving version history, and rollback.
Uses Parquet for persistence with a separate version index.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from simulator.configs.twin_config import get_config, resolve_subdir
from simulator.models.twin_state import StateDelta, TwinState, TwinStateVersion

_logger = logging.getLogger(__name__)

_ENTITY_LOCATION_SCHEMA = pa.schema(
    [
        pa.field("entity_id", pa.string()),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
    ]
)

_VERSION_INDEX_SCHEMA = pa.schema(
    [
        pa.field("version_id", pa.string()),
        pa.field("entity_id", pa.string()),
        pa.field("version_number", pa.int64()),
        pa.field("created_at", pa.timestamp("us", tz="UTC")),
        pa.field("created_by", pa.string()),
        pa.field("parent_version_id", pa.string()),
        pa.field("description", pa.string()),
        pa.field("file_path", pa.string()),
    ]
)

_TWIN_STATE_SCHEMA = pa.schema(
    [
        pa.field("entity_id", pa.string()),
        pa.field("timestamp", pa.timestamp("us", tz="UTC")),
        pa.field("temperature_2m", pa.float64()),
        pa.field("precipitation_mm", pa.float64()),
        pa.field("humidity_pct", pa.float64()),
        pa.field("pressure_hpa", pa.float64()),
        pa.field("wind_speed_10m", pa.float64()),
        pa.field("wind_direction_10m", pa.float64()),
        pa.field("solar_radiation", pa.float64()),
        pa.field("cloud_cover_pct", pa.float64()),
        pa.field("soil_moisture", pa.float64()),
        pa.field("data_source", pa.string()),
        pa.field("quality_flag", pa.string()),
        pa.field("observation_id", pa.string()),
        pa.field("run_id", pa.string()),
        pa.field("source_dataset", pa.string()),
        pa.field("authenticity", pa.string()),
        pa.field("ingestion_timestamp", pa.timestamp("us", tz="UTC")),
    ]
)


class VersionedStateStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        config = get_config()
        self._base_dir = (base_dir or resolve_subdir(config.twin_state_dir)).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._max_versions = config.max_versions_per_location
        self._lock = threading.Lock()
        self._version_index_path = self._base_dir / config.version_index_name

    def _get_entity_dir(self, entity_id: str) -> Path:
        entity_dir = self._base_dir / entity_id
        entity_dir.mkdir(parents=True, exist_ok=True)
        return entity_dir

    def _read_version_index(self) -> pa.Table:
        if self._version_index_path.exists():
            try:
                return pq.read_table(str(self._version_index_path))
            except Exception as e:
                _logger.warning("Failed to read version index: %s", e)
                return self._empty_index_table()
        return self._empty_index_table()

    def _empty_index_table(self) -> pa.Table:
        return pa.Table.from_pydict(
            {field.name: [] for field in _VERSION_INDEX_SCHEMA}, schema=_VERSION_INDEX_SCHEMA
        )

    def _write_version_index(self, table: pa.Table) -> None:
        pq.write_table(table, str(self._version_index_path), compression="snappy")

    def save_state(
        self, state: TwinState, created_by: str = "system", description: str = ""
    ) -> TwinStateVersion:
        if state.authenticity.upper() != "REAL":
            raise ValueError(
                f"Refusing to persist non-REAL '{state.authenticity}' state "
                f"into the authoritative twin store"
            )
        entity_dir = self._get_entity_dir(state.entity_id)
        with self._lock:
            index = self._read_version_index()
            entity_index = index.filter(
                pa.compute.equal(index.column("entity_id"), state.entity_id)
            )
            current_version_number = 0
            parent_version_id: str | None = None
            if entity_index.num_rows > 0:
                current_version_number = max(
                    int(v.as_py()) for v in entity_index.column("version_number")
                )
                latest_row = entity_index.sort_by([("version_number", "descending")]).slice(0, 1)
                parent_version_id = str(latest_row.column("version_id")[0].as_py())
            version_number = current_version_number + 1
            version = TwinStateVersion(
                entity_id=state.entity_id,
                version_number=version_number,
                state=state,
                created_at=datetime.now(UTC),
                created_by=created_by,
                parent_version_id=parent_version_id,
                description=description,
            )
            ing_ts = state.ingestion_timestamp if state.ingestion_timestamp else datetime.now(UTC)
            state_table = pa.Table.from_pydict(
                {
                    "entity_id": [state.entity_id],
                    "timestamp": [state.timestamp],
                    "temperature_2m": [state.temperature_2m],
                    "precipitation_mm": [state.precipitation_mm],
                    "humidity_pct": [state.humidity_pct],
                    "pressure_hpa": [state.pressure_hpa],
                    "wind_speed_10m": [state.wind_speed_10m],
                    "wind_direction_10m": [state.wind_direction_10m],
                    "solar_radiation": [state.solar_radiation],
                    "cloud_cover_pct": [state.cloud_cover_pct],
                    "soil_moisture": [state.soil_moisture],
                    "data_source": [state.data_source],
                    "quality_flag": [state.quality_flag],
                    "observation_id": [state.observation_id],
                    "run_id": [state.run_id],
                    "source_dataset": [state.source_dataset],
                    "authenticity": [state.authenticity],
                    "ingestion_timestamp": [ing_ts],
                },
                schema=_TWIN_STATE_SCHEMA,
            )
            file_name = f"v{version_number:06d}.parquet"
            file_path = entity_dir / file_name
            pq.write_table(state_table, str(file_path), compression="snappy")
            new_row = pa.Table.from_pydict(
                {
                    "version_id": [version.version_id],
                    "entity_id": [state.entity_id],
                    "version_number": [version_number],
                    "created_at": [version.created_at],
                    "created_by": [created_by],
                    "parent_version_id": [parent_version_id or ""],
                    "description": [description],
                    "file_path": [str(file_path)],
                },
                schema=_VERSION_INDEX_SCHEMA,
            )
            updated_index = pa.concat_tables([index, new_row])
            self._write_version_index(updated_index)
            self._enforce_max_versions(state.entity_id)
        return version

    def _enforce_max_versions(self, entity_id: str) -> None:
        if self._max_versions <= 0:
            return
        index = self._read_version_index()
        entity_index = index.filter(pa.compute.equal(index.column("entity_id"), entity_id))
        if entity_index.num_rows <= self._max_versions:
            return
        sorted_idx = entity_index.sort_by([("version_number", "ascending")])
        excess = sorted_idx.slice(0, entity_index.num_rows - self._max_versions)
        for i in range(excess.num_rows):
            file_path = str(excess.column("file_path")[i].as_py())
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                _logger.warning("Failed to remove old version file %s: %s", file_path, e)
        excess_version_ids = set(
            str(excess.column("version_id")[i].as_py()) for i in range(excess.num_rows)
        )
        remaining_rows = [
            i
            for i in range(index.num_rows)
            if str(index.column("version_id")[i].as_py()) not in excess_version_ids
        ]
        remaining = index.take(pa.array(remaining_rows, type=pa.int64()))
        self._write_version_index(remaining)

    def get_state(self, entity_id: str, version_id: str) -> TwinState | None:
        index = self._read_version_index()
        mask = pa.compute.and_(
            pa.compute.equal(index.column("entity_id"), entity_id),
            pa.compute.equal(index.column("version_id"), version_id),
        )
        matches = index.filter(mask)
        if matches.num_rows == 0:
            return None
        file_path = str(matches.column("file_path")[0].as_py())
        return self._read_state_file(file_path)

    def get_latest_state(self, entity_id: str) -> TwinState | None:
        index = self._read_version_index()
        entity_index = index.filter(pa.compute.equal(index.column("entity_id"), entity_id))
        if entity_index.num_rows == 0:
            return None
        latest = entity_index.sort_by([("version_number", "descending")]).slice(0, 1)
        file_path = str(latest.column("file_path")[0].as_py())
        state = self._read_state_file(file_path)
        if state is not None:
            state.version_number = int(latest.column("version_number")[0].as_py())
        return state

    def get_version_history(self, entity_id: str) -> list[TwinStateVersion]:
        index = self._read_version_index()
        entity_index = index.filter(pa.compute.equal(index.column("entity_id"), entity_id))
        if entity_index.num_rows == 0:
            return []
        sorted_idx = entity_index.sort_by([("version_number", "descending")])
        versions: list[TwinStateVersion] = []
        for i in range(sorted_idx.num_rows):
            state = self._read_state_file(str(sorted_idx.column("file_path")[i].as_py()))
            versions.append(
                TwinStateVersion(
                    version_id=str(sorted_idx.column("version_id")[i].as_py()),
                    entity_id=entity_id,
                    version_number=int(sorted_idx.column("version_number")[i].as_py()),
                    state=state,
                    created_at=sorted_idx.column("created_at")[i].as_py(),
                    created_by=str(sorted_idx.column("created_by")[i].as_py()),
                    parent_version_id=str(sorted_idx.column("parent_version_id")[i].as_py())
                    or None,
                    description=str(sorted_idx.column("description")[i].as_py()),
                )
            )
        return versions

    def rollback(self, entity_id: str, version_id: str) -> TwinState:
        state = self.get_state(entity_id, version_id)
        if state is None:
            raise ValueError(f"Version '{version_id}' not found for entity '{entity_id}'")
        new_version = self.save_state(
            state, created_by="system.rollback", description=f"Rollback to version {version_id}"
        )
        return new_version.state if new_version.state else state

    def _read_state_file(self, file_path: str) -> TwinState | None:
        try:
            table = pq.read_table(file_path)
            if table.num_rows == 0:
                return None
            row = table.slice(0, 1)
            ing_ts = None
            try:
                ing_ts = (
                    row.column("ingestion_timestamp")[0].as_py()
                    if "ingestion_timestamp" in row.schema.names
                    else None
                )
            except Exception:
                ing_ts = None
            return TwinState(
                entity_id=str(row.column("entity_id")[0].as_py()),
                timestamp=row.column("timestamp")[0].as_py(),
                temperature_2m=float(row.column("temperature_2m")[0].as_py()),
                precipitation_mm=float(row.column("precipitation_mm")[0].as_py()),
                humidity_pct=float(row.column("humidity_pct")[0].as_py()),
                pressure_hpa=float(row.column("pressure_hpa")[0].as_py()),
                wind_speed_10m=float(row.column("wind_speed_10m")[0].as_py()),
                wind_direction_10m=float(row.column("wind_direction_10m")[0].as_py()),
                solar_radiation=row.column("solar_radiation")[0].as_py(),
                cloud_cover_pct=row.column("cloud_cover_pct")[0].as_py(),
                soil_moisture=row.column("soil_moisture")[0].as_py(),
                data_source=str(row.column("data_source")[0].as_py()),
                quality_flag=str(row.column("quality_flag")[0].as_py()),
                observation_id=str(row.column("observation_id")[0].as_py()),
                run_id=str(row.column("run_id")[0].as_py()),
                source_dataset=str(row.column("source_dataset")[0].as_py()),
                authenticity=str(row.column("authenticity")[0].as_py()),
                ingestion_timestamp=ing_ts,
            )
        except Exception as e:
            _logger.warning("Failed to read state file %s: %s", file_path, e)
            return None

    def _entity_locations_path(self) -> Path:
        return self._base_dir / "entity_locations.parquet"

    def _load_entity_locations(self) -> dict[str, tuple[float, float]]:
        path = self._entity_locations_path()
        if not path.exists():
            return {}
        try:
            table = pq.read_table(str(path))
            locations: dict[str, tuple[float, float]] = {}
            for i in range(table.num_rows):
                eid = str(table.column("entity_id")[i].as_py())
                lat = float(table.column("latitude")[i].as_py())
                lon = float(table.column("longitude")[i].as_py())
                locations[eid] = (lat, lon)
            return locations
        except Exception as e:
            _logger.warning("Failed to load entity locations: %s", e)
            return {}

    def _save_entity_locations(self, locations: dict[str, tuple[float, float]]) -> None:
        path = self._entity_locations_path()
        try:
            entities = list(locations.keys())
            table = pa.Table.from_pydict(
                {
                    "entity_id": entities,
                    "latitude": [locations[e][0] for e in entities],
                    "longitude": [locations[e][1] for e in entities],
                },
                schema=_ENTITY_LOCATION_SCHEMA,
            )
            pq.write_table(table, str(path), compression="snappy")
        except Exception as e:
            _logger.warning("Failed to save entity locations: %s", e)

    def register_entity_location(self, entity_id: str, latitude: float, longitude: float) -> None:
        with self._lock:
            locations = self._load_entity_locations()
            locations[entity_id] = (latitude, longitude)
            self._save_entity_locations(locations)

    def query_spatial(self, bbox: tuple[float, float, float, float]) -> list[TwinState]:
        min_lat, min_lon, max_lat, max_lon = bbox
        locations = self._load_entity_locations()
        matching: list[str] = []
        for entity_id, (lat, lon) in locations.items():
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                matching.append(entity_id)
        results: list[TwinState] = []
        for entity_id in matching:
            state = self.get_latest_state(entity_id)
            if state is not None:
                results.append(state)
        return results

    def _entity_state_at_time(self, entity_id: str, timestamp: datetime) -> TwinState | None:
        index = self._read_version_index()
        entity_index = index.filter(pa.compute.equal(index.column("entity_id"), entity_id))
        if entity_index.num_rows == 0:
            return None
        best_state: TwinState | None = None
        best_diff: float | None = None
        for i in range(entity_index.num_rows):
            file_path = str(entity_index.column("file_path")[i].as_py())
            state = self._read_state_file(file_path)
            if state is None:
                continue
            diff = abs((state.timestamp - timestamp).total_seconds())
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_state = state
        return best_state

    def get_state_at_time(self, entity_id: str, timestamp: datetime) -> TwinState | None:
        return self._entity_state_at_time(entity_id, timestamp)

    def query_states_in_time_range(
        self, entity_id: str, start: datetime, end: datetime
    ) -> list[TwinState]:
        index = self._read_version_index()
        entity_index = index.filter(pa.compute.equal(index.column("entity_id"), entity_id))
        if entity_index.num_rows == 0:
            return []
        results: list[TwinState] = []
        for i in range(entity_index.num_rows):
            file_path = str(entity_index.column("file_path")[i].as_py())
            state = self._read_state_file(file_path)
            if state is None:
                continue
            if start <= state.timestamp <= end:
                results.append(state)
        results.sort(key=lambda s: s.timestamp)
        return results

    def save_states(
        self, states: list[TwinState], created_by: str = "system", description: str = ""
    ) -> list[TwinStateVersion]:
        return [
            self.save_state(state, created_by=created_by, description=description)
            for state in states
        ]

    def get_states(self, entity_ids: list[str]) -> dict[str, TwinState | None]:
        return {eid: self.get_latest_state(eid) for eid in entity_ids}

    def compute_delta(self, entity_id: str, version_id_a: str, version_id_b: str) -> StateDelta:
        state_a = self.get_state(entity_id, version_id_a)
        state_b = self.get_state(entity_id, version_id_b)
        if state_a is None:
            raise ValueError(f"Version '{version_id_a}' not found for entity '{entity_id}'")
        if state_b is None:
            raise ValueError(f"Version '{version_id_b}' not found for entity '{entity_id}'")

        def _diff(a: TwinState, b: TwinState, attr: str) -> float:
            return float(getattr(b, attr)) - float(getattr(a, attr))

        def _opt_diff(a: TwinState, b: TwinState, attr: str) -> float | None:
            va = getattr(a, attr)
            vb = getattr(b, attr)
            if va is not None and vb is not None:
                return float(vb) - float(va)
            return None

        return StateDelta(
            entity_id=entity_id,
            from_version_id=version_id_a,
            to_version_id=version_id_b,
            delta_temperature=_diff(state_a, state_b, "temperature_2m"),
            delta_precipitation=_diff(state_a, state_b, "precipitation_mm"),
            delta_humidity=_diff(state_a, state_b, "humidity_pct"),
            delta_pressure=_diff(state_a, state_b, "pressure_hpa"),
            delta_wind_speed=_diff(state_a, state_b, "wind_speed_10m"),
            delta_wind_direction=_diff(state_a, state_b, "wind_direction_10m"),
            delta_solar_radiation=_opt_diff(state_a, state_b, "solar_radiation"),
            delta_cloud_cover=_opt_diff(state_a, state_b, "cloud_cover_pct"),
            delta_soil_moisture=_opt_diff(state_a, state_b, "soil_moisture"),
        )

    def query_by_source(self, source: str) -> list[TwinState]:
        index = self._read_version_index()
        entity_ids = set(str(index.column("entity_id")[i].as_py()) for i in range(index.num_rows))
        results: list[TwinState] = []
        for entity_id in entity_ids:
            state = self.get_latest_state(entity_id)
            if state is not None and state.data_source == source:
                results.append(state)
        return results

    def query_by_quality(self, quality_flag: str) -> list[TwinState]:
        index = self._read_version_index()
        entity_ids = set(str(index.column("entity_id")[i].as_py()) for i in range(index.num_rows))
        results: list[TwinState] = []
        for entity_id in entity_ids:
            state = self.get_latest_state(entity_id)
            if state is not None and state.quality_flag == quality_flag:
                results.append(state)
        return results

    def get_state_by_version_number(self, entity_id: str, version_number: int) -> TwinState | None:
        index = self._read_version_index()
        mask = pa.compute.and_(
            pa.compute.equal(index.column("entity_id"), entity_id),
            pa.compute.equal(index.column("version_number"), pa.scalar(version_number, pa.int64())),
        )
        matches = index.filter(mask)
        if matches.num_rows == 0:
            return None
        file_path = str(matches.column("file_path")[0].as_py())
        return self._read_state_file(file_path)

    def clear(self) -> None:
        import gc
        import shutil

        with self._lock:
            if self._base_dir.exists():
                # On Windows, Parquet files may be locked by open handles.
                # Force garbage collection to close any dangling file handles,
                # then retry the deletion with exponential backoff.
                gc.collect()
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        shutil.rmtree(str(self._base_dir))
                        break
                    except PermissionError:
                        if attempt < max_retries - 1:
                            time.sleep(0.1 * (2**attempt))
                            gc.collect()
                        else:
                            raise
                self._base_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["VersionedStateStore"]
