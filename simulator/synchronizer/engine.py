from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from simulator.anomaly.detector import AnomalyDetector
from simulator.configs.twin_config import get_config, resolve_subdir
from simulator.historical.computer import BaselineComputer
from simulator.models.twin_state import StateDelta, TwinState
from simulator.models.weather import DataSource, WeatherObservation
from simulator.repository.parquet_store import ParquetObservationStore
from simulator.repository.versioned_state_store import VersionedStateStore
from simulator.state_manager.twin_state_manager import TwinStateManager

_logger = logging.getLogger(__name__)

SYNC_HISTORY_SCHEMA = pa.schema(
    [
        pa.field("sync_id", pa.string()),
        pa.field("location_id", pa.string()),
        pa.field("sync_type", pa.string()),
        pa.field("start_time", pa.timestamp("us", tz="UTC")),
        pa.field("end_time", pa.timestamp("us", tz="UTC")),
        pa.field("observations_synced", pa.int64()),
        pa.field("anomalies_detected", pa.int64()),
        pa.field("status", pa.string()),
        pa.field("error", pa.string()),
        pa.field("timestamp", pa.timestamp("us", tz="UTC")),
    ]
)


class TwinSynchronizer:
    def __init__(
        self,
        state_manager: TwinStateManager | None = None,
        observation_store: ParquetObservationStore | None = None,
        baseline_computer: BaselineComputer | None = None,
        anomaly_detector: AnomalyDetector | None = None,
    ) -> None:
        self._state_manager = state_manager or TwinStateManager()
        self._observation_store = observation_store or ParquetObservationStore()
        self._baseline_computer = baseline_computer or BaselineComputer()
        self._anomaly_detector = anomaly_detector or AnomalyDetector(
            baseline_computer=self._baseline_computer,
        )
        self._store: VersionedStateStore = self._state_manager.store

        config = get_config()
        base = resolve_subdir(config, "sync_history")
        base.mkdir(parents=True, exist_ok=True)
        self._sync_history_path = str(base / "sync_history.parquet")

    async def sync_observations_to_twin(
        self,
        location_id: str,
        observations: list[WeatherObservation],
    ) -> dict[str, Any]:
        if not observations:
            return {"location_id": location_id, "observations_synced": 0, "status": "no_data"}

        sorted_obs = sorted(observations, key=lambda o: o.timestamp)
        synced_count = 0
        anomaly_count = 0
        previous_state: TwinState | None = None

        try:
            previous_state = await self._state_manager.get_current_state(location_id)
        except ValueError:
            previous_state = None

        for obs in sorted_obs:
            if previous_state is None:
                state = TwinState(
                    entity_id=location_id,
                    timestamp=obs.timestamp,
                    temperature_2m=obs.temperature_2m,
                    precipitation_mm=obs.precipitation_mm,
                    humidity_pct=obs.humidity_pct,
                    pressure_hpa=obs.pressure_hpa,
                    wind_speed_10m=obs.wind_speed_10m,
                    wind_direction_10m=obs.wind_direction_10m,
                    data_source=(
                        obs.data_source.value
                        if isinstance(obs.data_source, DataSource)
                        else obs.data_source
                    ),
                    quality_flag=(
                        obs.quality_flag.value
                        if hasattr(obs.quality_flag, "value")
                        else obs.quality_flag
                    ),
                )
                self._store.save_state(state, created_by="twin_synchronizer")
                previous_state = state
                synced_count += 1
                continue

            delta = StateDelta(
                entity_id=location_id,
                from_version_id="",
                to_version_id="",
                delta_temperature=obs.temperature_2m - previous_state.temperature_2m,
                delta_precipitation=obs.precipitation_mm - previous_state.precipitation_mm,
                delta_humidity=obs.humidity_pct - previous_state.humidity_pct,
                delta_pressure=obs.pressure_hpa - previous_state.pressure_hpa,
                delta_wind_speed=obs.wind_speed_10m - previous_state.wind_speed_10m,
                delta_wind_direction=obs.wind_direction_10m - previous_state.wind_direction_10m,
            )
            await self._state_manager.update_state(location_id, delta, source="twin_synchronizer")

            anomaly_report = self._anomaly_detector.detect_anomalies(obs)
            anomaly_count += sum(1 for a in anomaly_report.anomalies if a.is_significant)
            synced_count += 1

        self._record_sync(
            location_id=location_id,
            sync_type="incremental",
            start_time=sorted_obs[0].timestamp,
            end_time=sorted_obs[-1].timestamp,
            synced_count=synced_count,
            anomaly_count=anomaly_count,
            status="success",
        )

        return {
            "location_id": location_id,
            "observations_synced": synced_count,
            "significant_anomalies": anomaly_count,
            "status": "success",
        }

    async def sync_historical_baseline(
        self,
        location_id: str,
        start_year: int = 1991,
        end_year: int = 2020,
        source: str = "era5",
    ) -> dict[str, Any]:
        collection = self._baseline_computer.compute_full_climatology(
            location_id=location_id,
            start_year=start_year,
            end_year=end_year,
            source=source,
        )
        self._baseline_computer.save_climatology(collection)

        total_records = len(collection.daily) + len(collection.monthly) + len(collection.seasonal)

        return {
            "location_id": location_id,
            "total_records": total_records,
            "daily_records": len(collection.daily),
            "monthly_records": len(collection.monthly),
            "seasonal_records": len(collection.seasonal),
            "version": collection.version,
            "status": "success",
        }

    async def build_historical_state(
        self,
        location_id: str,
        start_year: int = 1991,
        end_year: int = 2020,
    ) -> dict[str, Any]:
        observations = self._observation_store.query_observations(
            location_id=location_id,
            start_time=datetime(start_year, 1, 1, tzinfo=UTC),
            end_time=datetime(end_year, 12, 31, 23, 59, 59, tzinfo=UTC),
        )

        if not observations:
            _logger.warning("No historical observations for %s", location_id)
            return {"location_id": location_id, "synced": 0, "status": "no_data"}

        return await self.sync_observations_to_twin(
            location_id=location_id,
            observations=observations,
        )

    async def sync_full_location(
        self,
        location_id: str,
        baseline_years: tuple[int, int] = (1991, 2020),
        historical_years: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        _logger.info("Starting full sync for %s", location_id)

        baseline_result = await self.sync_historical_baseline(
            location_id=location_id,
            start_year=baseline_years[0],
            end_year=baseline_years[1],
        )

        hist_years = historical_years or baseline_years
        historical_result = await self.build_historical_state(
            location_id=location_id,
            start_year=hist_years[0],
            end_year=hist_years[1],
        )

        return {
            "location_id": location_id,
            "baseline": baseline_result,
            "historical_state": historical_result,
            "status": "success",
        }

    def _record_sync(
        self,
        location_id: str,
        sync_type: str,
        start_time: datetime,
        end_time: datetime,
        synced_count: int,
        anomaly_count: int,
        status: str,
        error: str = "",
    ) -> None:
        now = datetime.now(UTC)
        record = {
            "sync_id": [uuid.uuid4().hex[:16]],
            "location_id": [location_id],
            "sync_type": [sync_type],
            "start_time": [start_time],
            "end_time": [end_time],
            "observations_synced": [synced_count],
            "anomalies_detected": [anomaly_count],
            "status": [status],
            "error": [error],
            "timestamp": [now],
        }

        batch = pa.RecordBatch.from_pydict(record, schema=SYNC_HISTORY_SCHEMA)
        table = pa.Table.from_batches([batch])

        try:
            existing = pq.read_table(self._sync_history_path)
            combined = pa.concat_tables([existing, table])
            pq.write_table(combined, self._sync_history_path, compression="zstd")
        except (FileNotFoundError, pa.ArrowInvalid):
            pq.write_table(table, self._sync_history_path, compression="zstd")
