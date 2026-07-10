
from simulator.entities.climate_entity import ClimateEntity
from simulator.entities.state import StateType


class TestClimateEntity:
    def test_create_with_all_fields(self):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            district="Bangalore Urban",
            timestamp="2024-06-15T12:00:00",
            rainfall=45.0,
            max_temp=32.0,
            min_temp=21.0,
            risk_score=35.0,
            prediction_confidence=0.85,
            scenario_id="s1",
            data_source="IMD",
            state_type="current",
        )
        assert entity.location_id == "KA-BLR-001"
        assert entity.latitude == 12.97
        assert entity.longitude == 77.59
        assert entity.rainfall == 45.0
        assert entity.risk_score == 35.0
        assert entity.state_type == "current"

    def test_default_values(self):
        entity = ClimateEntity(location_id="LOC-001", latitude=10.0, longitude=20.0)
        assert entity.district == ""
        assert entity.rainfall == 0.0
        assert entity.max_temp == 25.0
        assert entity.min_temp == 18.0
        assert entity.data_source == "IMD"
        assert entity.state_type == StateType.CURRENT.value
        assert entity.timestamp is not None

    def test_serialize_deserialize_roundtrip(self):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            district="Bangalore Urban",
            rainfall=45.0,
            max_temp=32.0,
            min_temp=21.0,
            risk_score=35.0,
            prediction_confidence=0.85,
            scenario_id="s1",
            data_source="IMD",
            state_type="current",
        )
        data = entity.serialize()
        restored = ClimateEntity.deserialize(data)
        assert restored == entity

    def test_update_state_immutability(self):
        original = ClimateEntity(
            location_id="KA-BLR-001", latitude=12.97, longitude=77.59, rainfall=10.0
        )
        updated = original.update_state(rainfall=25.0, max_temp=35.0)
        assert original.rainfall == 10.0
        assert updated.rainfall == 25.0
        assert updated.max_temp == 35.0
        assert updated.location_id == original.location_id

    def test_update_state_returns_new_instance(self):
        original = ClimateEntity(location_id="KA-BLR-001", latitude=12.97, longitude=77.59)
        updated = original.update_state(rainfall=5.0)
        assert original is not updated

    def test_validate_valid_entity(self):
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=50.0,
            max_temp=30.0,
            min_temp=20.0,
            state_type="current",
        )
        assert entity.validate() == []

    def test_validate_empty_location_id(self):
        entity = ClimateEntity(
            location_id="",
            latitude=12.97,
            longitude=77.59,
        )
        errors = entity.validate()
        assert "location_id is required" in errors

    def test_validate_invalid_latitude(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=100.0,
            longitude=77.59,
        )
        errors = entity.validate()
        assert any("latitude" in e.lower() for e in errors)

    def test_validate_invalid_longitude_low(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=12.97,
            longitude=-200.0,
        )
        errors = entity.validate()
        assert any("longitude" in e.lower() for e in errors)

    def test_validate_invalid_longitude_high(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=12.97,
            longitude=200.0,
        )
        errors = entity.validate()
        assert any("longitude" in e.lower() for e in errors)

    def test_validate_invalid_rainfall(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=12.97,
            longitude=77.59,
            rainfall=-1.0,
        )
        errors = entity.validate()
        assert any("rainfall" in e.lower() for e in errors)

    def test_validate_invalid_max_temp(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=12.97,
            longitude=77.59,
            max_temp=60.0,
        )
        errors = entity.validate()
        assert any("max_temp" in e.lower() for e in errors)

    def test_validate_invalid_min_temp_low(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=12.97,
            longitude=77.59,
            min_temp=-15.0,
        )
        errors = entity.validate()
        assert any("min_temp" in e.lower() for e in errors)

    def test_validate_invalid_min_temp_high(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=12.97,
            longitude=77.59,
            min_temp=60.0,
        )
        errors = entity.validate()
        assert any("min_temp" in e.lower() for e in errors)

    def test_validate_invalid_state_type(self):
        entity = ClimateEntity(
            location_id="LOC-001",
            latitude=12.97,
            longitude=77.59,
            state_type="invalid_state",
        )
        errors = entity.validate()
        assert any("state_type" in e.lower() for e in errors)
