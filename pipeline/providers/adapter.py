from __future__ import annotations

from datetime import UTC, datetime

from pipeline.providers.authenticity import DataAuthenticity
from pipeline.providers.manager import Observation, ObservationStatus
from simulator.models.weather import DataSource, WeatherObservation


def _classify_observation_status(
    obs_timestamp: datetime, provider: DataSource
) -> ObservationStatus:
    now = datetime.now(UTC)
    if provider == DataSource.OPEN_METEO:
        if obs_timestamp > now:
            return ObservationStatus.FORECAST
        delta = (now - obs_timestamp).total_seconds()
        if delta < 86400 * 7:
            return ObservationStatus.LIVE
        return ObservationStatus.HISTORICAL
    if provider == DataSource.NASA_POWER:
        return ObservationStatus.HISTORICAL
    if provider == DataSource.SYNTHETIC:
        return ObservationStatus.HISTORICAL
    return ObservationStatus.HISTORICAL


def _source_dataset_for(provider: DataSource) -> str:
    mapping = {
        DataSource.OPEN_METEO: "OPEN_METEO_FORECAST",
        DataSource.NASA_POWER: "NASA_POWER",
        DataSource.IMD: "IMD",
        DataSource.ERA5: "ERA5",
        DataSource.SYNTHETIC: "SYNTHETIC",
    }
    return mapping.get(provider, provider.value)


_UNIT_MAP: dict[str, str] = {
    "temperature_2m": "°C",
    "precipitation": "mm",
    "precipitation_mm": "mm",
    "relative_humidity_2m": "%",
    "humidity_pct": "%",
    "surface_pressure": "hPa",
    "pressure_hpa": "hPa",
    "wind_speed_10m": "km/h",
    "wind_direction_10m": "°",
    "shortwave_radiation": "W/m²",
    "cloud_cover": "%",
    "cloud_cover_pct": "%",
    "soil_moisture_0_to_7cm": "m³/m³",
    "soil_moisture": "m³/m³",
}


def to_observation(
    wo: WeatherObservation,
    run_id: str = "",
    provider_override: DataSource | None = None,
) -> Observation:
    provider = provider_override or wo.data_source
    status = _classify_observation_status(wo.timestamp, provider)
    authenticity = (
        DataAuthenticity.REAL if provider != DataSource.SYNTHETIC else DataAuthenticity.SYNTHETIC
    )

    values: dict[str, float] = {}
    units: dict[str, str] = {}
    for attr, key in [
        ("temperature_2m", "temperature_2m"),
        ("precipitation_mm", "precipitation_mm"),
        ("humidity_pct", "humidity_pct"),
        ("pressure_hpa", "pressure_hpa"),
        ("wind_speed_10m", "wind_speed_10m"),
        ("wind_direction_10m", "wind_direction_10m"),
    ]:
        val = getattr(wo, attr, None)
        if val is not None:
            values[key] = val
            units[key] = _UNIT_MAP.get(key, "")
    for attr, key in [
        ("solar_radiation", "shortwave_radiation"),
        ("cloud_cover_pct", "cloud_cover_pct"),
        ("soil_moisture", "soil_moisture"),
    ]:
        val = getattr(wo, attr, None)
        if val is not None:
            values[key] = val
            units[key] = _UNIT_MAP.get(key, "")

    return Observation(
        status=status,
        provider=provider.value,
        source_dataset=_source_dataset_for(provider),
        authenticity=authenticity.value,
        observation_timestamp=wo.timestamp.isoformat(),
        retrieved_timestamp=datetime.now(UTC).isoformat(),
        values=values,
        units=units,
        location_id=wo.location_id,
        variable=",".join(values.keys()),
        latitude=wo.latitude,
        longitude=wo.longitude,
        run_id=run_id,
        quality_flag=wo.quality_flag.value,
        data_source_identifier=provider.value,
        dataset_version="",
    )
