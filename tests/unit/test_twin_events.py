"""Unit tests for simulator/events/."""

import pytest

from simulator.events.event_bus import EventBus
from simulator.events.events import TwinEvent


class TestTwinEvent:
    def test_valid_event_types(self):
        for etype in [
            "ObservationUpdated",
            "ForecastGenerated",
            "ScenarioApplied",
            "RiskUpdated",
            "TwinRefreshed",
        ]:
            event = TwinEvent(
                event_type=etype,
                location_id="KA-BLR-001",
                timestamp="2026-06-26T00:00:00",
                version_id=1,
            )
            assert event.event_type == etype

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValueError):
            TwinEvent(
                event_type="InvalidEvent",
                location_id="KA-BLR-001",
                timestamp="2026-06-26T00:00:00",
                version_id=1,
            )

    def test_event_immutability(self):
        event = TwinEvent(
            event_type="ObservationUpdated",
            location_id="KA-BLR-001",
            timestamp="2026-06-26T00:00:00",
            version_id=1,
        )
        with pytest.raises(AttributeError):
            event.location_id = "changed"


class TestEventBus:
    def test_publish_notifies_subscribers(self):
        bus = EventBus()
        received = []

        def callback(event):
            received.append(event)

        bus.subscribe("ObservationUpdated", callback)
        event = TwinEvent(
            event_type="ObservationUpdated",
            location_id="KA-BLR-001",
            timestamp="2026-06-26T00:00:00",
            version_id=1,
        )
        bus.publish(event)
        assert len(received) == 1
        assert received[0].location_id == "KA-BLR-001"

    def test_unsubscribe_stops_notifications(self):
        bus = EventBus()
        received = []

        def callback(event):
            received.append(event)

        bus.subscribe("ObservationUpdated", callback)
        bus.unsubscribe("ObservationUpdated", callback)
        bus.publish(TwinEvent("ObservationUpdated", "KA-BLR-001", "2026-06-26T00:00:00", 1))
        assert len(received) == 0

    def test_event_history(self):
        bus = EventBus()
        bus.publish(TwinEvent("ObservationUpdated", "KA-BLR-001", "2026-06-26T00:00:00", 1))
        bus.publish(TwinEvent("ForecastGenerated", "KA-BLR-002", "2026-06-26T00:00:00", 1))
        history = bus.get_event_history()
        assert len(history) == 2

    def test_clear_resets_state(self):
        bus = EventBus()
        bus.publish(TwinEvent("ObservationUpdated", "KA-BLR-001", "2026-06-26T00:00:00", 1))
        bus.clear()
        assert len(bus.get_event_history()) == 0

    def test_subscriber_error_does_not_crash_bus(self):
        bus = EventBus()

        def failing(event):  # noqa: ARG001
            raise RuntimeError("fail")

        bus.subscribe("ObservationUpdated", failing)
        bus.publish(TwinEvent("ObservationUpdated", "KA-BLR-001", "2026-06-26T00:00:00", 1))

    def test_event_data(self):
        event = TwinEvent(
            event_type="ForecastGenerated",
            location_id="KA-BLR-001",
            timestamp="2026-06-26T00:00:00",
            version_id=1,
            data={"confidence": 0.85},
        )
        assert event.data["confidence"] == 0.85
