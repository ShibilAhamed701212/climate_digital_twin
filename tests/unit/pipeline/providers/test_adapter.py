from __future__ import annotations

from datetime import UTC, datetime

from pipeline.providers.adapter import to_observation
from pipeline.providers.authenticity import DataAuthenticity
from pipeline.providers.manager import ObservationStatus
from simulator.models.weather import DataSource, WeatherObservation


def _make_wo(
    ts: datetime | None = None,
    source: DataSource = DataSource.OPEN_METEO,
) -> WeatherObservation:
    return WeatherObservation(
        location_id="test-loc",
        latitude=12.97,
        longitude=77.59,
        timestamp=ts or datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC),
        temperature_2m=27.4,
        precipitation_mm=4.2,
        humidity_pct=81.0,
        pressure_hpa=1008.2,
        wind_speed_10m=14.3,
        wind_direction_10m=220.0,
        data_source=source,
    )


class TestToObservation:
    def test_adapter_converts_all_fields(self):
        wo = _make_wo()
        obs = to_observation(wo, run_id="test_run_001")
        assert obs.provider == "open_meteo"
        assert obs.source_dataset == "OPEN_METEO_FORECAST"
        assert obs.authenticity == "REAL"
        assert obs.latitude == 12.97
        assert obs.longitude == 77.59
        assert obs.run_id == "test_run_001"
        assert obs.schema_version == "1.0.0"

    def test_adapter_preserves_values(self):
        wo = _make_wo()
        obs = to_observation(wo)
        assert obs.values["temperature_2m"] == 27.4
        assert obs.values["precipitation_mm"] == 4.2
        assert obs.values["humidity_pct"] == 81.0
        assert obs.values["pressure_hpa"] == 1008.2
        assert obs.values["wind_speed_10m"] == 14.3

    def test_adapter_units_present(self):
        wo = _make_wo()
        obs = to_observation(wo)
        assert obs.units["temperature_2m"] == "°C"
        assert obs.units["precipitation_mm"] == "mm"
        assert obs.units["humidity_pct"] == "%"
        assert obs.units["pressure_hpa"] == "hPa"

    def test_adapter_classifies_live(self):
        wo = _make_wo(ts=datetime.now(UTC))
        obs = to_observation(wo)
        assert obs.status == ObservationStatus.LIVE

    def test_adapter_classifies_historical(self):
        wo = _make_wo(ts=datetime(2020, 6, 15, tzinfo=UTC))
        obs = to_observation(wo)
        assert obs.status == ObservationStatus.HISTORICAL

    def test_adapter_classifies_synthetic(self):
        wo = _make_wo(source=DataSource.SYNTHETIC)
        obs = to_observation(wo)
        assert obs.authenticity == DataAuthenticity.SYNTHETIC.value

    def test_adapter_generates_observation_id(self):
        wo = _make_wo()
        obs = to_observation(wo)
        assert obs.data_source_identifier == "open_meteo"

    def test_adapter_nasa_power_historical(self):
        wo = _make_wo(source=DataSource.NASA_POWER, ts=datetime(2020, 1, 1, tzinfo=UTC))
        obs = to_observation(wo)
        assert obs.status == ObservationStatus.HISTORICAL
        assert obs.provider == "nasa_power"
        assert obs.source_dataset == "NASA_POWER"
        assert obs.authenticity == "REAL"
