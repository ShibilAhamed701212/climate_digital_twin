from datetime import UTC, datetime

import pytest

from simulator.models.weather import DataSource, QualityFlag, WeatherObservation


def make_obs(lat=12.97, lon=77.59, humid=50.0, cloud=None, wdir=180.0):
    return WeatherObservation(
        location_id="KA-BLR-001",
        latitude=lat,
        longitude=lon,
        timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
        temperature_2m=28.5,
        precipitation_mm=2.0,
        humidity_pct=humid,
        pressure_hpa=1013.0,
        wind_speed_10m=5.0,
        wind_direction_10m=wdir,
        cloud_cover_pct=cloud,
    )


class TestWeatherObservation:
    def test_create_valid_observation(self):
        obs = make_obs()
        assert obs.location_id == "KA-BLR-001"
        assert obs.temperature_2m == 28.5
        assert obs.data_source == DataSource.OPEN_METEO
        assert obs.quality_flag == QualityFlag.RAW
        assert len(obs.observation_id) == 16

    def test_optional_fields(self):
        obs = make_obs(cloud=60.0)
        assert obs.solar_radiation is None
        assert obs.cloud_cover_pct == 60.0
        assert obs.soil_moisture is None

    def test_invalid_latitude(self):
        with pytest.raises(ValueError, match="Latitude"):
            make_obs(lat=100.0)
        with pytest.raises(ValueError, match="Latitude"):
            make_obs(lat=-100.0)

    def test_invalid_longitude(self):
        with pytest.raises(ValueError, match="Longitude"):
            make_obs(lon=200.0)
        with pytest.raises(ValueError, match="Longitude"):
            make_obs(lon=-200.0)

    def test_invalid_humidity(self):
        with pytest.raises(ValueError, match="Humidity"):
            make_obs(humid=150.0)
        with pytest.raises(ValueError, match="Humidity"):
            make_obs(humid=-10.0)

    def test_invalid_cloud_cover_pct(self):
        with pytest.raises(ValueError, match="Cloud cover"):
            make_obs(cloud=150.0)
        with pytest.raises(ValueError, match="Cloud cover"):
            make_obs(cloud=-1.0)

    def test_invalid_wind_direction(self):
        with pytest.raises(ValueError, match="Wind direction"):
            make_obs(wdir=400.0)
        with pytest.raises(ValueError, match="Wind direction"):
            make_obs(wdir=-10.0)

    def test_valid_wind_direction_boundaries(self):
        obs = make_obs(wdir=0.0)
        assert obs.wind_direction_10m == 0.0
        obs = make_obs(wdir=359.9)
        assert obs.wind_direction_10m == 359.9

    def test_edge_case_latitude_and_longitude_boundaries(self):
        obs = make_obs(lat=90.0, lon=180.0)
        assert obs.latitude == 90.0
        assert obs.longitude == 180.0
        obs = make_obs(lat=-90.0, lon=-180.0)
        assert obs.latitude == -90.0
        assert obs.longitude == -180.0
