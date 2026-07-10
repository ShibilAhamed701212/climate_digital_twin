from datetime import UTC, datetime

import pytest

from simulator.models.twin_state import StateDelta, TwinEntity, TwinState, TwinStateVersion


class TestTwinEntity:
    def test_create_with_location_id(self):
        entity = TwinEntity(location_id="KA-BLR-001")
        assert entity.location_id == "KA-BLR-001"
        assert entity.name == ""
        assert entity.country == "IN"
        assert len(entity.entity_id) == 16

    def test_create_with_name(self):
        entity = TwinEntity(name="Bangalore Urban")
        assert entity.name == "Bangalore Urban"
        assert entity.location_id == ""

    def test_empty_location_id_and_name_raises(self):
        with pytest.raises(ValueError, match="Either location_id or name"):
            TwinEntity()

    def test_invalid_latitude(self):
        with pytest.raises(ValueError, match="Latitude"):
            TwinEntity(location_id="L1", latitude=100.0)
        with pytest.raises(ValueError, match="Latitude"):
            TwinEntity(location_id="L1", latitude=-100.0)

    def test_invalid_longitude(self):
        with pytest.raises(ValueError, match="Longitude"):
            TwinEntity(location_id="L1", longitude=200.0)
        with pytest.raises(ValueError, match="Longitude"):
            TwinEntity(location_id="L1", longitude=-200.0)

    def test_valid_boundaries(self):
        entity = TwinEntity(location_id="L1", latitude=90.0, longitude=180.0)
        assert entity.latitude == 90.0
        assert entity.longitude == 180.0

    def test_optional_fields(self):
        entity = TwinEntity(
            location_id="L1",
            elevation_m=920.0,
            area_km2=741.0,
            metadata={"region": "south"},
        )
        assert entity.elevation_m == 920.0
        assert entity.area_km2 == 741.0
        assert entity.metadata["region"] == "south"


class TestTwinState:
    def test_create(self):
        ts = TwinState(
            entity_id="ent-1",
            timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            temperature_2m=28.5,
            precipitation_mm=2.0,
            humidity_pct=60.0,
            pressure_hpa=1013.0,
            wind_speed_10m=5.0,
            wind_direction_10m=180.0,
        )
        assert ts.entity_id == "ent-1"
        assert ts.humidity_pct == 60.0
        assert ts.data_source == "open_meteo"
        assert ts.quality_flag == "raw"

    def test_invalid_humidity(self):
        with pytest.raises(ValueError, match="Humidity"):
            TwinState(
                entity_id="ent-1",
                timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
                temperature_2m=28.5,
                precipitation_mm=0.0,
                humidity_pct=150.0,
                pressure_hpa=1013.0,
                wind_speed_10m=5.0,
                wind_direction_10m=180.0,
            )

    def test_invalid_wind_direction(self):
        with pytest.raises(ValueError, match="Wind direction"):
            TwinState(
                entity_id="ent-1",
                timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
                temperature_2m=28.5,
                precipitation_mm=0.0,
                humidity_pct=50.0,
                pressure_hpa=1013.0,
                wind_speed_10m=5.0,
                wind_direction_10m=400.0,
            )

    def test_invalid_cloud_cover(self):
        with pytest.raises(ValueError, match="Cloud cover"):
            TwinState(
                entity_id="ent-1",
                timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
                temperature_2m=28.5,
                precipitation_mm=0.0,
                humidity_pct=50.0,
                pressure_hpa=1013.0,
                wind_speed_10m=5.0,
                wind_direction_10m=180.0,
                cloud_cover_pct=150.0,
            )

    def test_valid_cloud_cover_none(self):
        ts = TwinState(
            entity_id="ent-1",
            timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            temperature_2m=28.5,
            precipitation_mm=0.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=5.0,
            wind_direction_10m=180.0,
        )
        assert ts.cloud_cover_pct is None

    def test_optional_fields(self):
        ts = TwinState(
            entity_id="ent-1",
            timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            temperature_2m=28.5,
            precipitation_mm=2.0,
            humidity_pct=60.0,
            pressure_hpa=1013.0,
            wind_speed_10m=5.0,
            wind_direction_10m=180.0,
            solar_radiation=500.0,
            soil_moisture=0.3,
            metadata={"source": "imd"},
        )
        assert ts.solar_radiation == 500.0
        assert ts.soil_moisture == 0.3
        assert ts.metadata["source"] == "imd"


class TestTwinStateVersion:
    def test_create(self):
        ts = TwinState(
            entity_id="ent-1",
            timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            temperature_2m=28.5,
            precipitation_mm=0.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=5.0,
            wind_direction_10m=180.0,
        )
        tsv = TwinStateVersion(
            entity_id="ent-1",
            version_number=1,
            state=ts,
            created_by="pipeline",
            description="Initial state",
        )
        assert tsv.version_number == 1
        assert tsv.state is ts
        assert tsv.created_by == "pipeline"
        assert len(tsv.version_id) == 16
        assert tsv.parent_version_id is None

    def test_negative_version_number_raises(self):
        with pytest.raises(ValueError, match="Version number"):
            TwinStateVersion(version_number=-1)


class TestStateDelta:
    def test_create(self):
        sd = StateDelta(
            entity_id="ent-1",
            from_version_id="v1",
            to_version_id="v2",
            delta_temperature=1.5,
            delta_precipitation=-0.5,
        )
        assert sd.entity_id == "ent-1"
        assert sd.delta_temperature == 1.5
        assert sd.delta_precipitation == -0.5
        assert len(sd.delta_id) == 16

    def test_defaults(self):
        sd = StateDelta(
            entity_id="ent-1",
            from_version_id="v1",
            to_version_id="v2",
        )
        assert sd.delta_temperature == 0.0
        assert sd.delta_solar_radiation is None
        assert sd.delta_cloud_cover is None
        assert sd.delta_soil_moisture is None
