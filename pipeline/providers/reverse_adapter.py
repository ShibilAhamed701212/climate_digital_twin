from __future__ import annotations

from datetime import UTC, datetime

from pipeline.providers.manager import Observation
from simulator.models.weather import DataSource, QualityFlag, WeatherObservation


def observation_to_weather(obs: Observation) -> WeatherObservation | None:
    if not obs.values:
        return None
    lat = obs.latitude
    lon = obs.longitude
    if not lat and not lon:
        return None
    ts_str = obs.observation_timestamp
    try:
        ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now(UTC)
    except (ValueError, TypeError):
        ts = datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)

    provider = obs.provider or ""
    try:
        ds = DataSource(provider.lower())
    except (ValueError, TypeError):
        ds = DataSource.OPEN_METEO

    qf = obs.quality_flag or "raw"
    try:
        quality = QualityFlag(qf.lower())
    except (ValueError, TypeError):
        quality = QualityFlag.RAW

    v = obs.values
    ing_str = obs.retrieved_timestamp
    try:
        ing_ts = datetime.fromisoformat(ing_str) if ing_str else datetime.now(UTC)
    except (ValueError, TypeError):
        ing_ts = datetime.now(UTC)
    if ing_ts.tzinfo is None:
        ing_ts = ing_ts.replace(tzinfo=UTC)

    return WeatherObservation(
        location_id=obs.location_id or f"{lat:.4f}_{lon:.4f}",
        latitude=lat,
        longitude=lon,
        timestamp=ts,
        temperature_2m=v.get("temperature_2m", 0.0),
        precipitation_mm=v.get("precipitation_mm", 0.0),
        humidity_pct=v.get("humidity_pct", 0.0),
        pressure_hpa=v.get("pressure_hpa", 0.0),
        wind_speed_10m=v.get("wind_speed_10m", 0.0),
        wind_direction_10m=v.get("wind_direction_10m", 0.0),
        solar_radiation=v.get("solar_radiation"),
        cloud_cover_pct=v.get("cloud_cover_pct"),
        soil_moisture=v.get("soil_moisture"),
        data_source=ds,
        quality_flag=quality,
        observation_id=obs.data_source_identifier or "",
        ingestion_timestamp=ing_ts,
    )


def extract_provenance(obs: Observation) -> dict[str, str]:
    return {
        "observation_id": obs.data_source_identifier or "",
        "run_id": obs.run_id or "",
        "provider": obs.provider or "",
        "source_dataset": obs.source_dataset or "",
        "authenticity": obs.authenticity or "REAL",
        "quality_flag": obs.quality_flag or "raw",
        "observation_timestamp": obs.observation_timestamp or "",
        "ingestion_timestamp": obs.retrieved_timestamp or "",
        "latitude": str(obs.latitude) if obs.latitude else "",
        "longitude": str(obs.longitude) if obs.longitude else "",
    }
