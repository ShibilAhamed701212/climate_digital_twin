from runtime.event_bus import EventBus
from runtime.models.events import Event


class TestEventBus:
    def test_publish_and_subscribe(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.publish(Event(type="test.event", data={"k": "v"}, source="test", trace_id="t1"))
        assert len(received) == 1
        assert received[0].type == "test.event"
        assert received[0].data["k"] == "v"

    def test_subscribe_no_trigger_for_other_events(self):
        bus = EventBus()
        received = []

        def handler(e):
            received.append(e)

        bus.subscribe("target.event", handler)
        bus.publish(Event(type="other.event", data={}, source="test", trace_id="t1"))
        assert len(received) == 0

    def test_multiple_subscribers_same_event(self):
        bus = EventBus()
        results = []

        def h1(_e):
            results.append("h1")

        def h2(_e):
            results.append("h2")

        bus.subscribe("e", h1)
        bus.subscribe("e", h2)
        bus.publish(Event(type="e", data={}, source="t", trace_id="t1"))
        assert len(results) == 2

    def test_history(self):
        bus = EventBus()
        bus.publish(Event(type="a", data={}, source="t", trace_id="t1"))
        bus.publish(Event(type="b", data={}, source="t", trace_id="t2"))
        hist = bus.history()
        assert len(hist) == 2

    def test_multiple_event_types(self):
        bus = EventBus()
        received = []

        def handler(e):
            received.append(e.type)

        bus.subscribe("type1", handler)
        bus.subscribe("type2", handler)
        bus.publish(Event(type="type1", data={}, source="t", trace_id="t1"))
        bus.publish(Event(type="type2", data={}, source="t", trace_id="t2"))
        bus.publish(Event(type="type3", data={}, source="t", trace_id="t3"))
        assert received == ["type1", "type2"]
