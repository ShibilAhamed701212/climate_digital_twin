"""Unit tests for simulator/entities/."""


from simulator.entities.climate_entity import ClimateEntity
from simulator.entities.state import StateType


class TestClimateEntity:
    def test_create_entity(self):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            district="Bengaluru Urban",
        )
        assert entity.location_id == "KA-BLR-001"
        assert entity.state_type == StateType.CURRENT.value

    def test_update_state_returns_new_entity(self):
        entity = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59)
        updated = entity.update_state(rainfall=45.5, max_temp=32.0)
        assert updated.rainfall == 45.5
        assert updated.max_temp == 32.0
        assert entity.rainfall == 0.0
        assert entity is not updated

    def test_serialize_roundtrip(self):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=50.0,
            max_temp=32.0,
            min_temp=20.0,
        )
        data = entity.serialize()
        restored = ClimateEntity.deserialize(data)
        assert restored.location_id == entity.location_id
        assert restored.rainfall == entity.rainfall
        assert restored.max_temp == entity.max_temp

    def test_validate_valid_entity(self):
        entity = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59)
        errors = entity.validate()
        assert errors == []

    def test_validate_invalid_coordinates(self):
        entity = ClimateEntity(location_id="KA-BLR-001", latitude=100.0, longitude=77.59)
        errors = entity.validate()
        assert any("latitude" in e.lower() for e in errors)

    def test_validate_invalid_rainfall(self):
        entity = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59, rainfall=-5)
        errors = entity.validate()
        assert any("rainfall" in e.lower() for e in errors)

    def test_validate_invalid_temperature(self):
        entity = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59, max_temp=100)
        errors = entity.validate()
        assert any("max_temp" in e.lower() for e in errors)

    def test_validate_missing_location_id(self):
        entity = ClimateEntity(location_id="", latitude=12.97, longitude=77.59)
        errors = entity.validate()
        assert any("location_id" in e.lower() for e in errors)


class TestStateType:
    def test_valid_values(self):
        assert StateType.CURRENT.value == "current"
        assert StateType.HISTORICAL.value == "historical"
        assert StateType.FORECAST.value == "forecast"
        assert StateType.SCENARIO.value == "scenario"

    def test_all_values_unique(self):
        values = [s.value for s in StateType]
        assert len(values) == len(set(values))
