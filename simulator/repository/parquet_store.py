"""Parquet-based observation storage using PyArrow.

Provides efficient write and query operations for weather observations,
with location-based and time-based partitioning, schema evolution support,
and configurable compression.
"""

from __future__ import annotations

import logging
import shutil
import threading
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from simulator.configs.twin_config import get_config, resolve_subdir
from simulator.models.weather import DataSource, QualityFlag, WeatherObservation

_logger = logging.getLogger(__name__)

_OBSERVATION_SCHEMA = pa.schema(
    [
        pa.field("observation_id", pa.string()),
        pa.field("location_id", pa.string()),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
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
        pa.field("ingestion_timestamp", pa.timestamp("us", tz="UTC")),
    ]
)


def _observation_to_batch(obs: list[WeatherObservation]) -> pa.RecordBatch:
    arrays = {
        "observation_id": [o.observation_id for o in obs],
        "location_id": [o.location_id for o in obs],
        "latitude": [o.latitude for o in obs],
        "longitude": [o.longitude for o in obs],
        "timestamp": [o.timestamp for o in obs],
        "temperature_2m": [o.temperature_2m for o in obs],
        "precipitation_mm": [o.precipitation_mm for o in obs],
        "humidity_pct": [o.humidity_pct for o in obs],
        "pressure_hpa": [o.pressure_hpa for o in obs],
        "wind_speed_10m": [o.wind_speed_10m for o in obs],
        "wind_direction_10m": [o.wind_direction_10m for o in obs],
        "solar_radiation": [o.solar_radiation for o in obs],
        "cloud_cover_pct": [o.cloud_cover_pct for o in obs],
        "soil_moisture": [o.soil_moisture for o in obs],
        "data_source": [
            o.data_source.value if isinstance(o.data_source, DataSource) else o.data_source
            for o in obs
        ],
        "quality_flag": [
            o.quality_flag.value if isinstance(o.quality_flag, QualityFlag) else o.quality_flag
            for o in obs
        ],
        "ingestion_timestamp": [o.ingestion_timestamp for o in obs],
    }
    return pa.RecordBatch.from_pydict(arrays, schema=_OBSERVATION_SCHEMA)


def _batch_to_observation(batch: pa.RecordBatch, row_idx: int) -> WeatherObservation:
    return WeatherObservation(
        observation_id=str(batch.column("observation_id")[row_idx].as_py()),
        location_id=str(batch.column("location_id")[row_idx].as_py()),
        latitude=float(batch.column("latitude")[row_idx].as_py()),
        longitude=float(batch.column("longitude")[row_idx].as_py()),
        timestamp=batch.column("timestamp")[row_idx].as_py(),
        temperature_2m=float(batch.column("temperature_2m")[row_idx].as_py()),
        precipitation_mm=float(batch.column("precipitation_mm")[row_idx].as_py()),
        humidity_pct=float(batch.column("humidity_pct")[row_idx].as_py()),
        pressure_hpa=float(batch.column("pressure_hpa")[row_idx].as_py()),
        wind_speed_10m=float(batch.column("wind_speed_10m")[row_idx].as_py()),
        wind_direction_10m=float(batch.column("wind_direction_10m")[row_idx].as_py()),
        solar_radiation=batch.column("solar_radiation")[row_idx].as_py(),
        cloud_cover_pct=batch.column("cloud_cover_pct")[row_idx].as_py(),
        soil_moisture=batch.column("soil_moisture")[row_idx].as_py(),
        data_source=batch.column("data_source")[row_idx].as_py(),
        quality_flag=batch.column("quality_flag")[row_idx].as_py(),
        ingestion_timestamp=batch.column("ingestion_timestamp")[row_idx].as_py(),
    )


class ParquetObservationStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        config = get_config()
        self._base_dir = (base_dir or resolve_subdir(config.observations_dir)).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._compression = config.parquet_compression
        self._row_group_size = config.parquet_row_group_size
        self._lock = threading.Lock()

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def write_observations(self, observations: list[WeatherObservation]) -> int:
        if not observations:
            return 0
        with self._lock:
            location_ids = set(o.location_id for o in observations)
            for loc_id in location_ids:
                loc_dir = self._base_dir / loc_id
                loc_dir.mkdir(parents=True, exist_ok=True)
                mask = [o.location_id == loc_id for o in observations]
                loc_obs = [o for i, o in enumerate(observations) if mask[i]]
                loc_batch = _observation_to_batch(loc_obs)
                loc_table = pa.Table.from_batches([loc_batch])
                timestamp_col = loc_table.column("timestamp")
                for row_idx in range(loc_table.num_rows):
                    ts = timestamp_col[row_idx].as_py()
                    year_str = str(ts.year)
                    month_str = f"{ts.month:02d}"
                    part_dir = loc_dir / year_str / month_str
                    part_dir.mkdir(parents=True, exist_ok=True)
                    file_path = part_dir / "observations.parquet"
                    row_table = loc_table.slice(row_idx, 1)
                    if file_path.exists():
                        existing = pq.read_table(str(file_path))
                        combined = pa.concat_tables([existing, row_table])
                        pq.write_table(
                            combined,
                            str(file_path),
                            compression=self._compression,
                            row_group_size=self._row_group_size,
                        )
                    else:
                        pq.write_table(
                            row_table,
                            str(file_path),
                            compression=self._compression,
                            row_group_size=self._row_group_size,
                        )
        return len(observations)

    def query_observations(
        self, location_id: str, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> list[WeatherObservation]:
        loc_dir = self._base_dir / location_id
        if not loc_dir.exists():
            return []
        all_tables: list[pa.Table] = []
        for parquet_file in sorted(loc_dir.rglob("*.parquet")):
            try:
                table = pq.read_table(str(parquet_file))
                all_tables.append(table)
            except Exception as e:
                _logger.warning("Failed to read %s: %s", parquet_file, e)
        if not all_tables:
            return []
        combined = pa.concat_tables(all_tables)
        ts_col = combined.column("timestamp")
        mask = [True] * combined.num_rows
        if start_time is not None:
            mask = [m and (ts_col[i].as_py() >= start_time) for i, m in enumerate(mask)]
        if end_time is not None:
            mask = [m and (ts_col[i].as_py() <= end_time) for i, m in enumerate(mask)]
        results: list[WeatherObservation] = []
        for i in range(combined.num_rows):
            if mask[i]:
                row = combined.slice(i, 1)
                row_batch = row.to_batches()[0]
                results.append(_batch_to_observation(row_batch, 0))
        return results

    def get_latest_observation(self, location_id: str) -> WeatherObservation | None:
        loc_dir = self._base_dir / location_id
        if not loc_dir.exists():
            return None
        all_tables: list[pa.Table] = []
        for parquet_file in sorted(loc_dir.rglob("*.parquet")):
            try:
                table = pq.read_table(str(parquet_file))
                all_tables.append(table)
            except Exception:
                logging.warning("Skipping corrupted parquet file: %s", parquet_file)
        if not all_tables:
            return None
        combined = pa.concat_tables(all_tables)
        ts_col = combined.column("timestamp")
        latest_idx = 0
        latest_ts = ts_col[0].as_py()
        for i in range(1, combined.num_rows):
            current_ts = ts_col[i].as_py()
            if current_ts > latest_ts:
                latest_ts = current_ts
                latest_idx = i
        row = combined.slice(latest_idx, 1)
        row_batch = row.to_batches()[0]
        return _batch_to_observation(row_batch, 0)

    def list_locations(self) -> list[str]:
        if not self._base_dir.exists():
            return []
        locations: list[str] = []
        for entry in sorted(self._base_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith(".") and any(entry.rglob("*.parquet")):
                locations.append(entry.name)
        return locations

    def get_observation_count(self, location_id: str) -> int:
        loc_dir = self._base_dir / location_id
        if not loc_dir.exists():
            return 0
        total = 0
        for parquet_file in loc_dir.rglob("*.parquet"):
            try:
                metadata = pq.read_metadata(str(parquet_file))
                total += metadata.num_rows
            except Exception:
                logging.warning("Skipping unreadable metadata for: %s", parquet_file)
        return total

    def get_storage_summary(self) -> dict[str, object]:
        locations = self.list_locations()
        total_observations = sum(self.get_observation_count(loc) for loc in locations)
        return {
            "num_locations": len(locations),
            "total_observations": total_observations,
            "base_dir": str(self._base_dir),
            "locations": locations,
        }

    def clear(self) -> None:
        with self._lock:
            if self._base_dir.exists():
                shutil.rmtree(str(self._base_dir))
                self._base_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["ParquetObservationStore"]
