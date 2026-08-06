from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pipeline.providers.authenticity import DataAuthenticity
from pipeline.providers.manager import Observation
from pipeline.providers.reverse_adapter import extract_provenance, observation_to_weather
from pipeline.sources.location_registry import Location, LocationRegistry
from pipeline.stores.observation_store import ObservationStore
from simulator.events.event_bus import EventBus
from simulator.events.events import TwinEvent
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
    SyncResult,
)

_logger = logging.getLogger(__name__)


class TwinSyncService:
    def __init__(
        self,
        store: VersionedStateStore | None = None,
        event_bus: EventBus | None = None,
        checkpoint: SyncCheckpoint | None = None,
        location_registry: LocationRegistry | None = None,
        freshness_threshold_minutes: int = 480,
        stale_threshold_minutes: int = 1440,
    ) -> None:
        self._store = store or VersionedStateStore()
        self._event_bus = event_bus or EventBus()
        self._checkpoint = checkpoint or SyncCheckpoint()
        self._location_registry = location_registry or LocationRegistry()
        self._freshness_threshold = freshness_threshold_minutes
        self._stale_threshold = stale_threshold_minutes

    def _resolve_location(
        self, observation: Observation, location_id: str | None
    ) -> tuple[str, Location | None]:
        if location_id:
            loc = self._location_registry.get_location(location_id)
            if loc is None:
                loc = self._location_registry.find_nearest(
                    observation.latitude, observation.longitude
                )
            return location_id, loc
        loc = self._location_registry.find_nearest(observation.latitude, observation.longitude)
        if loc:
            return loc.location_id, loc
        fallback = f"{observation.latitude:.4f}_{observation.longitude:.4f}"
        return fallback, None

    def sync_from_observation(
        self,
        observation: Observation,
        location_id: str | None = None,
    ) -> SyncResult:
        obs_id = observation.data_source_identifier or ""

        if observation.authenticity != DataAuthenticity.REAL:
            return SyncResult(
                status=REJECTED_SYNTHETIC,
                location_id=location_id or "",
                observation_id=obs_id,
                authenticity=observation.authenticity,
                error=f"Authenticity is {observation.authenticity}, not REAL",
            )

        qf = (observation.quality_flag or "").lower()
        if qf in ("rejected", "missing", "suspicious"):
            return SyncResult(
                status=REJECTED_QUALITY,
                location_id=location_id or "",
                observation_id=obs_id,
                authenticity=observation.authenticity,
                error=f"Quality flag is {qf}",
            )

        actual_location_id, resolved_location = self._resolve_location(observation, location_id)
        if resolved_location is None and location_id is not None:
            resolved_location = self._location_registry.get_location(location_id)

        wo = observation_to_weather(observation)
        if wo is None:
            return SyncResult(
                status=FAILED,
                location_id=actual_location_id,
                observation_id=obs_id,
                authenticity=observation.authenticity,
                error="Failed to convert Observation to WeatherObservation",
            )

        if resolved_location:
            wo.location_id = resolved_location.location_id
            wo.latitude = resolved_location.latitude
            wo.longitude = resolved_location.longitude
        else:
            wo.location_id = actual_location_id

        if not obs_id:
            obs_id = wo.observation_id or ""

        if self._checkpoint.is_processed(actual_location_id, obs_id):
            existing = self._checkpoint.get_result(actual_location_id, obs_id)
            return SyncResult(
                status=SKIPPED_DUPLICATE,
                location_id=actual_location_id,
                observation_id=obs_id,
                run_id=observation.run_id or "",
                provider=observation.provider or "",
                authenticity=observation.authenticity,
                new_version=0,
                error=f"Already processed: {existing}",
            )

        current_state: TwinState | None = self._store.get_latest_state(actual_location_id)
        current_version = 0
        if current_state is not None:
            try:
                hist = self._store.get_version_history(actual_location_id)
                if hist:
                    current_version = hist[0].version_number
            except Exception:
                current_version = 0

        if current_state is not None and wo.timestamp < current_state.timestamp:
            self._checkpoint.mark_processed(actual_location_id, obs_id, OUT_OF_ORDER)
            return SyncResult(
                status=OUT_OF_ORDER,
                location_id=actual_location_id,
                observation_id=obs_id,
                run_id=observation.run_id or "",
                provider=observation.provider or "",
                authenticity=observation.authenticity,
                old_version=current_version,
                new_version=current_version,
                error=f"Observation timestamp {wo.timestamp} < current state timestamp {current_state.timestamp}",
            )

        provenance = extract_provenance(observation)
        merged = TwinState(
            entity_id=actual_location_id,
            timestamp=wo.timestamp,
            temperature_2m=wo.temperature_2m,
            precipitation_mm=wo.precipitation_mm,
            humidity_pct=wo.humidity_pct,
            pressure_hpa=wo.pressure_hpa,
            wind_speed_10m=wo.wind_speed_10m,
            wind_direction_10m=wo.wind_direction_10m,
            solar_radiation=wo.solar_radiation if wo.solar_radiation is not None else None,
            cloud_cover_pct=wo.cloud_cover_pct if wo.cloud_cover_pct is not None else None,
            soil_moisture=wo.soil_moisture if wo.soil_moisture is not None else None,
            data_source=wo.data_source.value
            if hasattr(wo.data_source, "value")
            else str(wo.data_source),
            quality_flag=wo.quality_flag.value
            if hasattr(wo.quality_flag, "value")
            else str(wo.quality_flag),
            observation_id=obs_id,
            run_id=observation.run_id or "",
            source_dataset=observation.source_dataset or "",
            authenticity=observation.authenticity or "REAL",
            ingestion_timestamp=wo.ingestion_timestamp,
        )

        carried_fields: list[str] = []
        if current_state is not None:
            for field in ("solar_radiation", "cloud_cover_pct", "soil_moisture"):
                new_val = getattr(merged, field)
                old_val = getattr(current_state, field)
                if new_val is None and old_val is not None:
                    setattr(merged, field, old_val)
                    carried_fields.append(field)
        if carried_fields:
            merged.metadata["carried_forward_fields"] = ",".join(carried_fields)

        if current_state is not None:
            changed = _compute_changed(current_state, merged)
            if not changed:
                self._checkpoint.mark_processed(actual_location_id, obs_id, NO_STATE_CHANGE)
                return SyncResult(
                    status=NO_STATE_CHANGE,
                    location_id=actual_location_id,
                    observation_id=obs_id,
                    run_id=observation.run_id or "",
                    provider=observation.provider or "",
                    authenticity=observation.authenticity,
                    old_version=current_version,
                    new_version=current_version,
                    changed_variables=[],
                )

        description = (
            f"Initial state from {observation.provider or 'unknown'} observation {obs_id}"
            if current_state is None
            else f"Synced from {observation.provider or 'unknown'} observation {obs_id}"
        )
        twin_version = self._store.save_state(
            merged,
            created_by=f"sync:{observation.provider or 'unknown'}",
            description=description,
        )

        new_ver = twin_version.version_number
        event_type = "TwinStateCreated" if current_state is None else "TwinStateUpdated"
        self._event_bus.publish(
            TwinEvent(
                event_type=event_type,
                location_id=actual_location_id,
                timestamp=datetime.now(UTC).isoformat(),
                version_id=new_ver,
                data={
                    "observation_id": obs_id,
                    "run_id": observation.run_id or "",
                    "provider": observation.provider or "",
                    "old_version": current_version,
                    "new_version": new_ver,
                },
            )
        )

        sync_status = CREATED if current_state is None else UPDATED
        self._checkpoint.mark_processed(actual_location_id, obs_id, sync_status)

        changed_vars = (
            _compute_changed(current_state, merged)
            if current_state
            else list(
                v
                for v in [
                    "temperature_2m",
                    "precipitation_mm",
                    "humidity_pct",
                    "pressure_hpa",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "solar_radiation",
                    "cloud_cover_pct",
                    "soil_moisture",
                ]
                if getattr(merged, v) is not None
            )
        )

        return SyncResult(
            status=sync_status,
            location_id=actual_location_id,
            observation_id=obs_id,
            run_id=observation.run_id or "",
            provider=observation.provider or "",
            authenticity=observation.authenticity,
            old_version=current_version,
            new_version=new_ver,
            changed_variables=changed_vars,
        )

    def sync_pending_observations(
        self,
        obs_store: ObservationStore,
        location_id: str | None = None,
    ) -> list[SyncResult]:
        all_obs = obs_store.query()
        results: list[SyncResult] = []
        for obs in all_obs:
            if location_id and obs.location_id and obs.location_id != location_id:
                continue
            result = self.sync_from_observation(obs, location_id=location_id)
            results.append(result)
            _logger.info(
                "Sync %s: %s for %s (obs=%s)",
                result.status,
                result.location_id,
                result.observation_id,
                result.run_id,
            )
        return results

    def get_twin_freshness(self, location_id: str) -> dict[str, Any]:
        state: TwinState | None = self._store.get_latest_state(location_id)
        if state is None:
            return {
                "location_id": location_id,
                "status": "NO_REAL_DATA",
                "latest_version": 0,
                "latest_observation_at": None,
                "latest_twin_update_at": None,
                "freshness": None,
                "provider": None,
                "authenticity": None,
                "quality": None,
            }

        latest_version = 0
        try:
            hist = self._store.get_version_history(location_id)
            if hist:
                latest_version = hist[0].version_number
        except Exception:
            latest_version = 0

        now = datetime.now(UTC)
        obs_age = (now - state.timestamp).total_seconds() / 60.0

        if obs_age <= self._freshness_threshold:
            freshness = "FRESH"
            status = "HEALTHY"
        elif obs_age <= self._stale_threshold:
            freshness = "STALE"
            status = "STALE"
        else:
            freshness = "VERY_STALE"
            status = "STALE"

        return {
            "location_id": location_id,
            "status": status,
            "freshness": freshness,
            "latest_version": latest_version,
            "latest_observation_at": state.timestamp.isoformat() if state.timestamp else None,
            "latest_twin_update_at": None,
            "provider": state.data_source,
            "authenticity": state.authenticity,
            "quality": state.quality_flag,
        }

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def store(self) -> VersionedStateStore:
        return self._store

    @property
    def checkpoint(self) -> SyncCheckpoint:
        return self._checkpoint


def _compute_changed(old: TwinState, new: TwinState) -> list[str]:
    changed: list[str] = []
    for attr in [
        "temperature_2m",
        "precipitation_mm",
        "humidity_pct",
        "pressure_hpa",
        "wind_speed_10m",
        "wind_direction_10m",
    ]:
        if abs(getattr(old, attr) - getattr(new, attr)) > 0.001:
            changed.append(attr)
    for attr in ["solar_radiation", "cloud_cover_pct", "soil_moisture"]:
        if getattr(old, attr) != getattr(new, attr):
            changed.append(attr)
    return changed
