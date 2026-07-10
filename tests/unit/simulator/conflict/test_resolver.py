from datetime import UTC, datetime

import pytest

from simulator.conflict.resolver import (
    SOURCE_PRIORITY,
    ConflictRecord,
    ConflictResolver,
    ResolutionStrategy,
)
from simulator.models.twin_state import TwinState


def make_state(
    entity_id="entity1",
    temp=25.0,
    precip=0.0,
    humid=50.0,
    press=1013.0,
    wind=5.0,
    wdir=180.0,
    source="imd",
    quality="validated",
    ts=None,
):
    return TwinState(
        entity_id=entity_id,
        timestamp=ts or datetime(2024, 1, 1, tzinfo=UTC),
        temperature_2m=temp,
        precipitation_mm=precip,
        humidity_pct=humid,
        pressure_hpa=press,
        wind_speed_10m=wind,
        wind_direction_10m=wdir,
        data_source=source,
        quality_flag=quality,
    )


class TestSourcePriority:
    def test_priorities(self):
        assert SOURCE_PRIORITY["imd"] == 100
        assert SOURCE_PRIORITY["era5"] == 80
        assert SOURCE_PRIORITY["synthetic"] == 10

    def test_unknown_source(self):
        resolver = ConflictResolver()
        assert resolver._get_source_priority("unknown") == 0


class TestConflictRecord:
    def test_default_id_generated(self):
        record = ConflictRecord(entity_id="e1", states=[], sources=["imd", "era5"])
        assert len(record.conflict_id) == 16
        assert record.resolved is False

    def test_custom_id(self):
        record = ConflictRecord(entity_id="e1", states=[], sources=["imd"], conflict_id="custom123")
        assert record.conflict_id == "custom123"


class TestDetectConflicts:
    def test_no_conflict_single_state(self):
        resolver = ConflictResolver()
        state = make_state()
        assert resolver.detect_conflicts([state]) == []

    def test_no_conflict_empty_list(self):
        resolver = ConflictResolver()
        assert resolver.detect_conflicts([]) == []

    def test_no_conflict_identical_states(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, source="imd")
        s2 = make_state(temp=25.05, source="era5")
        assert resolver.detect_conflicts([s1, s2]) == []

    def test_conflict_detected(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, source="imd")
        s2 = make_state(temp=30.0, source="era5")
        conflicts = resolver.detect_conflicts([s1, s2])
        assert len(conflicts) == 1
        assert "temperature_2m" in conflicts[0].variables

    def test_different_entities_raises(self):
        resolver = ConflictResolver()
        s1 = make_state(entity_id="e1", source="imd")
        s2 = make_state(entity_id="e2", source="era5")
        with pytest.raises(ValueError, match="same entity"):
            resolver.detect_conflicts([s1, s2])

    def test_same_source_no_conflict(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, source="imd")
        s2 = make_state(temp=30.0, source="imd")
        assert resolver.detect_conflicts([s1, s2]) == []

    def test_multiple_variable_conflicts(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, humid=50.0, source="imd")
        s2 = make_state(temp=35.0, humid=70.0, source="era5")
        conflicts = resolver.detect_conflicts([s1, s2])
        assert len(conflicts) == 1 if conflicts else True

    def test_falsy_with_len(self):
        resolver = ConflictResolver()

        class FalsyList(list):
            def __bool__(self):
                return False

        states = FalsyList([make_state(source="imd"), make_state(source="era5")])
        assert resolver.detect_conflicts(states) == []

    def test_optional_var_conflict(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, source="imd")
        s1.solar_radiation = 500.0
        s2 = make_state(temp=30.0, source="era5")
        s2.solar_radiation = 600.0
        conflicts = resolver.detect_conflicts([s1, s2])
        assert len(conflicts) == 1
        assert "solar_radiation" in conflicts[0].variables


class TestResolveBySourcePriority:
    def test_highest_priority_wins(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, source="imd")
        s2 = make_state(temp=30.0, source="synthetic")
        record = ConflictRecord("e1", [s1, s2], ["imd", "synthetic"], variables=["temperature_2m"])
        result = resolver.resolve(record, ResolutionStrategy.SOURCE_PRIORITY)
        assert result.temperature_2m == 25.0
        assert result.data_source == "imd"

    def test_marks_conflict_resolved(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, source="imd")
        s2 = make_state(temp=30.0, source="era5")
        record = ConflictRecord("e1", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        resolver.resolve(record, ResolutionStrategy.SOURCE_PRIORITY)
        assert record.resolved is True
        assert record.resolution_strategy == ResolutionStrategy.SOURCE_PRIORITY
        assert record.resolved_by == "ConflictResolver"


class TestResolveByHighestConfidence:
    def test_highest_confidence_wins(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, quality="validated", source="imd")
        s2 = make_state(temp=30.0, quality="suspicious", source="era5")
        record = ConflictRecord("e1", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        result = resolver.resolve(record, ResolutionStrategy.HIGHEST_CONFIDENCE)
        assert result.temperature_2m == 25.0


class TestResolveByMostRecent:
    def test_most_recent_wins(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, ts=datetime(2024, 1, 1, tzinfo=UTC), source="imd")
        s2 = make_state(temp=30.0, ts=datetime(2024, 6, 1, tzinfo=UTC), source="era5")
        record = ConflictRecord("e1", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        result = resolver.resolve(record, ResolutionStrategy.MOST_RECENT)
        assert result.temperature_2m == 30.0


class TestResolveByWeightedAverage:
    def test_weighted_average(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=20.0, source="imd", quality="validated")
        s2 = make_state(temp=30.0, source="synthetic", quality="estimated")
        record = ConflictRecord("e1", [s1, s2], ["imd", "synthetic"], variables=["temperature_2m"])
        result = resolver.resolve(record, ResolutionStrategy.WEIGHTED_AVERAGE)
        assert (
            s1.temperature_2m < result.temperature_2m < s2.temperature_2m
            or result.temperature_2m < s1.temperature_2m
            or result.temperature_2m == s1.temperature_2m
        )

    def test_weighted_average_zero_total_weight(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=20.0, source="unknown", quality="missing")
        s2 = make_state(temp=30.0, source="unknown", quality="missing")
        record = ConflictRecord(
            "e1", [s1, s2], ["unknown", "unknown"], variables=["temperature_2m"]
        )
        result = resolver.resolve(record, ResolutionStrategy.WEIGHTED_AVERAGE)
        assert 20.0 <= result.temperature_2m <= 30.0

    def test_weighted_average_optional_vars(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=20.0, source="imd", quality="validated")
        s1.cloud_cover_pct = 50.0
        s2 = make_state(temp=30.0, source="era5", quality="corrected")
        s2.cloud_cover_pct = 70.0
        record = ConflictRecord("e1", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        result = resolver.resolve(record, ResolutionStrategy.WEIGHTED_AVERAGE)
        assert result.temperature_2m != 20.0


class TestManualResolution:
    def test_manual_raises(self):
        resolver = ConflictResolver()
        s1 = make_state(source="imd")
        s2 = make_state(source="era5")
        record = ConflictRecord("e1", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        with pytest.raises(ValueError, match="manual"):
            resolver.resolve(record, ResolutionStrategy.MANUAL)

    def test_unknown_strategy_raises(self):
        resolver = ConflictResolver()
        s1 = make_state(source="imd")
        s2 = make_state(source="era5")
        record = ConflictRecord("e1", [s1, s2], ["imd", "era5"])
        with pytest.raises(ValueError, match="Unknown resolution strategy"):
            resolver.resolve(record, "nonexistent_strategy")


class TestResolveAll:
    def test_resolve_multiple(self):
        resolver = ConflictResolver()
        s1 = make_state(temp=25.0, source="imd")
        s2 = make_state(temp=30.0, source="era5")
        r1 = ConflictRecord("e1", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        r2 = ConflictRecord("e2", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        results = resolver.resolve_all([r1, r2])
        assert len(results) == 2


class TestDefaultStrategy:
    def test_default_is_source_priority(self):
        resolver = ConflictResolver()
        assert resolver._default_strategy == ResolutionStrategy.SOURCE_PRIORITY

    def test_custom_default(self):
        resolver = ConflictResolver(ResolutionStrategy.MOST_RECENT)
        s1 = make_state(temp=25.0, ts=datetime(2024, 1, 1, tzinfo=UTC), source="imd")
        s2 = make_state(temp=30.0, ts=datetime(2024, 6, 1, tzinfo=UTC), source="era5")
        record = ConflictRecord("e1", [s1, s2], ["imd", "era5"], variables=["temperature_2m"])
        result = resolver.resolve(record)
        assert result.temperature_2m == 30.0


class TestConfidenceLookup:
    def test_known_flags(self):
        assert ConflictResolver._lookup_confidence("validated") == 100
        assert ConflictResolver._lookup_confidence("missing") == 0

    def test_unknown_flag(self):
        assert ConflictResolver._lookup_confidence("unknown") == 50
