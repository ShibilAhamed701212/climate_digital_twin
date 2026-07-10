from __future__ import annotations

import pytest

from pipeline.sources.location_registry import Location, LocationRegistry


class TestLocation:
    def test_valid_coordinates(self):
        loc = Location("TST-001", "Test", 12.0, 77.0, "Test District")
        assert loc.latitude == 12.0
        assert loc.longitude == 77.0

    def test_invalid_latitude_above(self):
        with pytest.raises(ValueError, match="Latitude must be in"):
            Location("TST-001", "Test", 100.0, 77.0, "Test District")

    def test_invalid_latitude_below(self):
        with pytest.raises(ValueError, match="Latitude must be in"):
            Location("TST-001", "Test", -100.0, 77.0, "Test District")

    def test_invalid_longitude_above(self):
        with pytest.raises(ValueError, match="Longitude must be in"):
            Location("TST-001", "Test", 12.0, 200.0, "Test District")

    def test_invalid_longitude_below(self):
        with pytest.raises(ValueError, match="Longitude must be in"):
            Location("TST-001", "Test", 12.0, -200.0, "Test District")

    def test_from_dict(self):
        data = {
            "location_id": "TST-001",
            "name": "Test",
            "latitude": 12.0,
            "longitude": 77.0,
            "district": "Test District",
        }
        loc = Location.from_dict(data)
        assert loc.location_id == "TST-001"
        assert loc.elevation_m is None
        assert loc.state == "Karnataka"
        assert loc.metadata == {}

    def test_from_dict_with_optional_fields(self):
        data = {
            "location_id": "TST-002",
            "name": "Test2",
            "latitude": 14.0,
            "longitude": 76.0,
            "district": "D2",
            "elevation_m": 500.0,
            "state": "Goa",
            "metadata": {"key": "val"},
        }
        loc = Location.from_dict(data)
        assert loc.elevation_m == 500.0
        assert loc.state == "Goa"
        assert loc.metadata == {"key": "val"}

    def test_to_dict(self):
        loc = Location("TST-001", "Test", 12.0, 77.0, "Test District", elevation_m=500.0)
        d = loc.to_dict()
        assert d["location_id"] == "TST-001"
        assert d["elevation_m"] == 500.0
        assert d["state"] == "Karnataka"

    def test_to_dict_roundtrip(self):
        data = {
            "location_id": "TST-001",
            "name": "Test",
            "latitude": 12.0,
            "longitude": 77.0,
            "district": "Test District",
            "elevation_m": 500.0,
            "state": "Karnataka",
            "metadata": {},
        }
        loc = Location.from_dict(data)
        assert loc.to_dict() == data


class TestLocationRegistry:
    def test_init_with_defaults(self):
        reg = LocationRegistry()
        assert reg.count() == 8
        assert reg.get_location("KA-BLR-001") is not None

    def test_init_with_custom_locations(self):
        locs = [Location("CUS-001", "Custom", 15.0, 75.0, "Custom District")]
        reg = LocationRegistry(locations=locs)
        assert reg.count() == 1

    def test_get_location_found(self):
        reg = LocationRegistry()
        loc = reg.get_location("KA-BLR-001")
        assert loc is not None
        assert loc.name == "Bengaluru"

    def test_get_location_not_found(self):
        reg = LocationRegistry()
        assert reg.get_location("NONEXISTENT") is None

    def test_get_coordinates_found(self):
        reg = LocationRegistry()
        coords = reg.get_coordinates("KA-BLR-001")
        assert coords == (12.97, 77.59, "KA-BLR-001")

    def test_get_coordinates_not_found(self):
        reg = LocationRegistry()
        assert reg.get_coordinates("NONEXISTENT") is None

    def test_add_location_new(self):
        reg = LocationRegistry()
        loc = Location("NEW-001", "New", 14.0, 76.0, "New District")
        reg.add_location(loc)
        assert reg.get_location("NEW-001") is loc
        assert reg.count() == 9

    def test_add_location_duplicate(self):
        reg = LocationRegistry()
        loc = reg.get_location("KA-BLR-001")
        reg.add_location(loc)
        assert reg.count() == 8

    def test_add_locations(self):
        reg = LocationRegistry()
        locs = [
            Location("BAT-001", "Batch1", 14.0, 76.0, "D1"),
            Location("BAT-002", "Batch2", 15.0, 77.0, "D2"),
        ]
        reg.add_locations(locs)
        assert reg.count() == 10

    def test_list_locations_all(self):
        reg = LocationRegistry()
        assert len(reg.list_locations()) == 8

    def test_list_locations_filter_by_district(self):
        reg = LocationRegistry()
        filtered = reg.list_locations(district="Mysuru")
        assert len(filtered) == 1
        assert filtered[0].name == "Mysuru"

    def test_list_locations_filter_by_state(self):
        reg = LocationRegistry()
        filtered = reg.list_locations(state="Karnataka")
        assert len(filtered) == 8

    def test_list_locations_filter_both(self):
        reg = LocationRegistry()
        filtered = reg.list_locations(district="Mysuru", state="Karnataka")
        assert len(filtered) == 1

    def test_list_locations_no_match(self):
        reg = LocationRegistry()
        assert reg.list_locations(district="Nonexistent") == []

    def test_count(self):
        reg = LocationRegistry()
        assert reg.count() == 8

    def test_clear(self):
        reg = LocationRegistry()
        assert reg.count() > 0
        reg.clear()
        assert reg.count() == 0
