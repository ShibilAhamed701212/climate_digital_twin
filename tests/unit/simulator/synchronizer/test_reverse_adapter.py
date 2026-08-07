from pipeline.providers.authenticity import DataAuthenticity
from pipeline.providers.manager import Observation
from pipeline.providers.reverse_adapter import extract_provenance, observation_to_weather
from simulator.models.weather import DataSource, QualityFlag


def test_observation_to_weather_basic():
    obs = Observation(
        provider="open_meteo",
        source_dataset="OPEN_METEO_FORECAST",
        authenticity=DataAuthenticity.REAL,
        observation_timestamp="2026-07-30T12:00:00+00:00",
        retrieved_timestamp="2026-07-30T12:05:00+00:00",
        values={"temperature_2m": 22.1, "humidity_pct": 88.0, "pressure_hpa": 907.9},
        units={"temperature_2m": "°C", "humidity_pct": "%", "pressure_hpa": "hPa"},
        latitude=12.97,
        longitude=77.59,
        run_id="run_001",
        quality_flag="validated",
        data_source_identifier="obs_abc123",
    )
    wo = observation_to_weather(obs)
    assert wo is not None
    assert wo.temperature_2m == 22.1
    assert wo.humidity_pct == 88.0
    assert wo.pressure_hpa == 907.9
    assert wo.data_source == DataSource.OPEN_METEO
    assert wo.quality_flag == QualityFlag.VALIDATED
    assert wo.latitude == 12.97
    assert wo.longitude == 77.59


def test_observation_to_weather_empty_values():
    obs = Observation(
        latitude=12.97,
        longitude=77.59,
        values={},
    )
    assert observation_to_weather(obs) is None


def test_observation_to_weather_no_coords():
    obs = Observation(
        latitude=0.0,
        longitude=0.0,
        values={"temperature_2m": 22.1},
    )
    wo = observation_to_weather(obs)
    assert wo is None


def test_observation_to_weather_unknown_provider():
    obs = Observation(
        provider="unknown_provider",
        latitude=12.97,
        longitude=77.59,
        observation_timestamp="2026-07-30T12:00:00+00:00",
        values={"temperature_2m": 22.1},
    )
    wo = observation_to_weather(obs)
    assert wo is not None
    assert wo.data_source == DataSource.OPEN_METEO


def test_extract_provenance():
    obs = Observation(
        provider="open_meteo",
        source_dataset="OPEN_METEO_FORECAST",
        authenticity=DataAuthenticity.REAL,
        observation_timestamp="2026-07-30T12:00:00+00:00",
        retrieved_timestamp="2026-07-30T12:05:00+00:00",
        values={"temperature_2m": 22.1},
        latitude=12.97,
        longitude=77.59,
        run_id="run_001",
        quality_flag="validated",
        data_source_identifier="obs_abc123",
    )
    prov = extract_provenance(obs)
    assert prov["observation_id"] == "obs_abc123"
    assert prov["run_id"] == "run_001"
    assert prov["provider"] == "open_meteo"
    assert prov["source_dataset"] == "OPEN_METEO_FORECAST"
    assert prov["authenticity"] == "REAL"
    assert prov["latitude"] == "12.97"
    assert prov["longitude"] == "77.59"
