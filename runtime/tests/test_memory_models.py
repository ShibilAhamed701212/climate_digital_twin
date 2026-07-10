"""Tests for Memory models and stores."""

import time

from runtime.models.evidence import Fact
from runtime.models.memory import (
    ConversationMemory,
    FactStore,
    InMemoryStore,
    MemoryEntry,
    ToolOutputCache,
    UserPreferenceStore,
)


class TestMemoryEntry:
    def test_create_entry(self):
        entry = MemoryEntry(key="test_key", value={"data": 42}, agent="test")
        assert entry.key == "test_key"
        assert entry.value["data"] == 42
        assert entry.agent == "test"

    def test_expired(self):
        entry = MemoryEntry(key="test", value="x", ttl=1)
        assert not entry.expired()
        time.sleep(1.1)
        assert entry.expired()

    def test_no_expiry(self):
        entry = MemoryEntry(key="test", value="x", ttl=None)
        assert not entry.expired()


class TestInMemoryStore:
    def test_store_and_retrieve(self):
        store = InMemoryStore()
        store.store(MemoryEntry(key="greeting", value="hello"))
        entry = store.retrieve("greeting")
        assert entry is not None
        assert entry.value == "hello"

    def test_retrieve_missing(self):
        store = InMemoryStore()
        assert store.retrieve("nonexistent") is None

    def test_query_pattern(self):
        store = InMemoryStore()
        store.store(MemoryEntry(key="user.name", value="Alice"))
        store.store(MemoryEntry(key="user.age", value=30))
        store.store(MemoryEntry(key="config.theme", value="dark"))
        results = store.query("user.*")
        assert len(results) == 2

    def test_delete(self):
        store = InMemoryStore()
        store.store(MemoryEntry(key="test", value="x"))
        store.delete("test")
        assert store.retrieve("test") is None

    def test_clear(self):
        store = InMemoryStore()
        store.store(MemoryEntry(key="a", value=1))
        store.store(MemoryEntry(key="b", value=2))
        store.clear()
        assert len(store.list_keys()) == 0

    def test_list_keys(self):
        store = InMemoryStore()
        store.store(MemoryEntry(key="a", value=1))
        store.store(MemoryEntry(key="b", value=2))
        keys = store.list_keys()
        assert "a" in keys
        assert "b" in keys

    def test_expired_not_returned(self):
        store = InMemoryStore()
        store.store(MemoryEntry(key="temp", value="x", ttl=0))
        time.sleep(0.1)
        assert store.retrieve("temp") is None


class TestConversationMemory:
    def test_max_turns(self):
        store = ConversationMemory(max_turns=3)
        for i in range(5):
            store.store(MemoryEntry(key=f"turn:{i}", value=f"msg {i}"))
        assert len(store.list_keys()) <= 3

    def test_conversation_order(self):
        store = ConversationMemory(max_turns=10)
        store.store(MemoryEntry(key="turn:1", value="first"))
        store.store(MemoryEntry(key="turn:2", value="second"))
        first = store.retrieve("turn:1")
        second = store.retrieve("turn:2")
        assert first.value == "first"
        assert second.value == "second"


class TestToolOutputCache:
    def test_default_ttl(self):
        cache = ToolOutputCache(default_ttl=60)
        entry = MemoryEntry(key="result", value="cached")
        cache.store(entry)
        assert entry.ttl == 60

    def test_custom_ttl(self):
        cache = ToolOutputCache(default_ttl=60)
        entry = MemoryEntry(key="result", value="cached", ttl=30)
        cache.store(entry)
        assert entry.ttl == 30


class TestFactStore:
    def test_store_fact(self):
        store = FactStore()
        fact = Fact(subject="Bangalore", predicate="temperature", object_value=32.5)
        store.store_fact(fact)
        retrieved = store.get_fact("Bangalore", "temperature")
        assert retrieved is not None
        assert retrieved.object_value == 32.5

    def test_get_fact_nonexistent(self):
        store = FactStore()
        assert store.get_fact("Unknown", "property") is None

    def test_query_subject(self):
        store = FactStore()
        store.store_fact(Fact(subject="Bangalore", predicate="temp", object_value=30))
        store.store_fact(
            Fact(subject="Bangalore", predicate="humidity", object_value=65)
        )
        store.store_fact(Fact(subject="Mumbai", predicate="temp", object_value=35))
        bangalore_facts = store.query_subject("Bangalore")
        assert len(bangalore_facts) == 2
        mumbai_facts = store.query_subject("Mumbai")
        assert len(mumbai_facts) == 1


class TestUserPreferenceStore:
    def test_store_preference(self):
        store = UserPreferenceStore()
        store.store(MemoryEntry(key="units", value="metric"))
        entry = store.retrieve("units")
        assert entry.value == "metric"

    def test_overwrite_preference(self):
        store = UserPreferenceStore()
        store.store(MemoryEntry(key="theme", value="light"))
        store.store(MemoryEntry(key="theme", value="dark"))
        entry = store.retrieve("theme")
        assert entry.value == "dark"
