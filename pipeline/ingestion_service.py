from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pipeline.providers.adapter import to_observation
from pipeline.providers.fetch_result import FetchResult
from pipeline.providers.imd_status import fetch_imd
from pipeline.providers.nasa_power_provider import fetch_nasa_power
from pipeline.providers.open_meteo_provider import fetch_open_meteo
from pipeline.stores.manifest_writer import ManifestWriter
from pipeline.stores.observation_store import ObservationStore
from pipeline.stores.raw_data_store import RawDataStore
from pipeline.stores.rejected_store import RejectedStore
from simulator.models.weather import DataSource

_logger = logging.getLogger(__name__)


def _generate_run_id() -> str:
    now = datetime.now(UTC)
    nano = now.strftime("%Y%m%dT%H%M%SZ")
    suffix = now.microsecond % 1000000
    return f"{nano}_{suffix:06x}"


def _resolve_provider(intent: str, provider_override: str | None) -> list[str]:
    if provider_override:
        return [provider_override]
    if intent == "forecast":
        return ["open_meteo"]
    if intent == "historical":
        return ["nasa_power", "open_meteo"]
    return ["open_meteo", "nasa_power"]


ProviderFunc = Any  # callable that returns FetchResult


def _get_provider_func(name: str) -> ProviderFunc:
    mapping: dict[str, ProviderFunc] = {
        "open_meteo": fetch_open_meteo,
        "nasa_power": fetch_nasa_power,
        "imd": fetch_imd,
    }
    return mapping[name]


class IngestionService:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        data_dir = self._config.get("data_dir", "data/real")
        self._raw_store = RawDataStore(data_dir)
        self._obs_store = ObservationStore(data_dir)
        self._rejected_store = RejectedStore(data_dir)
        self._manifest_writer = ManifestWriter("data")

    def run_single(
        self,
        lat: float,
        lon: float,
        intent: str = "recent",
        provider_override: str | None = None,
        location_id: str = "auto",
    ) -> dict[str, Any]:
        run_id = _generate_run_id()
        provider_names = _resolve_provider(intent, provider_override)
        last_error: str | None = None

        for provider_name in provider_names:
            func = _get_provider_func(provider_name)
            _logger.info(
                "Attempting provider=%s intent=%s lat=%.4f lon=%.4f",
                provider_name,
                intent,
                lat,
                lon,
            )
            result = func(lat=lat, lon=lon, location_id=location_id, intent=intent)

            if result.status == "SUCCESS":
                return self._handle_success(result, provider_name, run_id, lat, lon)

            last_error = f"{provider_name}: {result.error_code} - {result.error_message}"
            _logger.warning("Provider %s failed: %s", provider_name, last_error)

        return {
            "run_id": run_id,
            "status": "FAILED",
            "error": last_error or "All providers exhausted",
            "records_persisted": 0,
        }

    def _handle_success(
        self,
        result: FetchResult,
        provider_name: str,
        run_id: str,
        lat: float,
        lon: float,
    ) -> dict[str, Any]:
        provider_enum = DataSource(result.provider)

        raw_path = self._raw_store.save(
            provider=provider_enum,
            run_id=run_id,
            response_body=str(result.observations),
            endpoint=result.request_metadata.get("endpoint", ""),
            coordinates=(lat, lon),
        )

        weather_obs = result.observations
        observations = [to_observation(wo, run_id=run_id) for wo in weather_obs]

        valid, rejected = self._validate_observations(observations)

        normalized_path = str(self._obs_store._normalized_dir / f"observations_{run_id}.parquet")
        self._obs_store.save_batch(valid, run_id=run_id)

        rejected_path = None
        if rejected:
            rejected_path = str(self._rejected_store._rejected_dir / f"rejected_{run_id}.parquet")
            self._rejected_store.save_batch(rejected, run_id=run_id)

        manifest = self._manifest_writer.write(
            run_id=run_id,
            fetch_result=result,
            valid=valid,
            rejected=rejected,
            raw_path=str(raw_path),
            normalized_path=normalized_path,
            validated_path=normalized_path,
            rejected_path=rejected_path,
        )

        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "provider": provider_name,
            "source_dataset": valid[0].source_dataset if valid else "",
            "authenticity": valid[0].authenticity if valid else "REAL",
            "observation_timestamp": valid[0].observation_timestamp if valid else "",
            "ingestion_timestamp": valid[0].retrieved_timestamp if valid else "",
            "records_received": len(weather_obs),
            "records_validated": len(valid),
            "records_rejected": len(rejected),
            "synthetic_count": manifest.synthetic_count,
            "error": None,
            "paths": manifest.paths,
            "values": valid[0].values if valid else {},
            "units": valid[0].units if valid else {},
        }

    def _validate_observations(self, observations: list[Any]) -> tuple[list[Any], list[Any]]:
        valid: list[Any] = []
        rejected: list[Any] = []
        for obs in observations:
            qf = getattr(obs, "quality_flag", "raw")
            if qf in ("rejected",):
                rejected.append(obs)
            else:
                valid.append(obs)
        return valid, rejected
