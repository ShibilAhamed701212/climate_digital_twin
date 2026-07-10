from runtime.blackboard import Blackboard


class TestBlackboard:
    def test_publish_and_get(self):
        bb = Blackboard()
        version = bb.publish("test.key", {"value": 42}, "test-agent")
        assert version == 1
        entry = bb.get("test.key")
        assert entry is not None
        assert entry.value["value"] == 42
        assert entry.agent == "test-agent"
        assert entry.version == 1

    def test_get_nonexistent(self):
        bb = Blackboard()
        assert bb.get("nonexistent") is None

    def test_get_specific_version(self):
        bb = Blackboard()
        bb.publish("k", "v1", "a")
        bb.publish("k", "v2", "a")
        v1 = bb.get("k", version=1)
        assert v1.value == "v1"
        v2 = bb.get("k", version=2)
        assert v2.value == "v2"

    def test_get_invalid_version(self):
        bb = Blackboard()
        bb.publish("k", "v1", "a")
        assert bb.get("k", version=99) is None

    def test_publish_increments_version(self):
        bb = Blackboard()
        assert bb.publish("k", "a", "agent") == 1
        assert bb.publish("k", "b", "agent") == 2
        assert bb.publish("k", "c", "agent") == 3

    def test_watch_triggers_on_publish(self):
        bb = Blackboard()
        received = []

        def handler(entry):
            received.append(entry)

        bb.watch("watch.key", handler)
        bb.publish("watch.key", "hello", "test")
        assert len(received) == 1
        assert received[0].value == "hello"

    def test_watch_multiple_handlers(self):
        bb = Blackboard()
        results = []

        def h1(_e):
            results.append("h1")

        def h2(_e):
            results.append("h2")

        bb.watch("k", h1)
        bb.watch("k", h2)
        bb.publish("k", "v", "a")
        assert len(results) == 2

    def test_watch_all_entries(self):
        bb = Blackboard()
        received = []

        def handler(entry):
            received.append(entry.key)

        bb.watch("*", handler)
        bb.publish("key1", "v1", "a")
        bb.publish("key2", "v2", "a")
        assert "key1" in received
        assert "key2" in received

    def test_history(self):
        bb = Blackboard()
        bb.publish("k", "a", "agent")
        bb.publish("k", "b", "agent")
        bb.publish("k", "c", "agent")
        hist = bb.history("k")
        assert len(hist) == 3
        assert [e.value for e in hist] == ["a", "b", "c"]

    def test_history_empty(self):
        bb = Blackboard()
        assert bb.history("nonexistent") == []

    def test_query_pattern(self):
        bb = Blackboard()
        bb.publish("forecast.blr", {"val": 1}, "a")
        bb.publish("forecast.mys", {"val": 2}, "a")
        bb.publish("twin.blr", {"val": 3}, "a")
        results = bb.query("forecast.*")
        assert len(results) == 2

    def test_query_all(self):
        bb = Blackboard()
        bb.publish("a", 1, "t")
        bb.publish("b", 2, "t")
        results = bb.query("*")
        assert len(results) == 2

    def test_concurrent_keys(self):
        bb = Blackboard()
        bb.publish("a", 1, "t")
        bb.publish("b", 2, "t")
        bb.publish("a", 3, "t")
        assert bb.get("a").value == 3
        assert bb.get("b").value == 2

    def test_watch_other_key_does_not_trigger(self):
        bb = Blackboard()
        received = []

        def handler(e):
            received.append(e)

        bb.watch("target", handler)
        bb.publish("other", "v", "a")
        assert len(received) == 0
