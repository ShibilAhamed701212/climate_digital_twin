"""Memory models and store implementations.

Memory is structured facts, never raw prompts or paragraphs.
Six store types:
- WorkingMemory: current session state
- ConversationMemory: recent conversation turns
- SessionSummary: summary of current session
- ToolOutputCache: cached provider results
- FactStore: persistent structured facts
- UserPreferenceStore: user preferences
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from runtime.models.evidence import Fact


@dataclass
class MemoryEntry:
    """A single entry in a memory store.

    Can be a Fact, a conversation turn, a preference, or any structured data.
    """

    key: str
    value: Any
    agent: str = "system"
    timestamp: float = field(default_factory=time.time)
    ttl: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


class MemoryStore(ABC):
    """Abstract base class for all memory stores."""

    @abstractmethod
    def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        ...

    @abstractmethod
    def retrieve(self, key: str) -> MemoryEntry | None:
        """Retrieve the latest entry for a key."""
        ...

    @abstractmethod
    def query(self, pattern: str) -> list[MemoryEntry]:
        """Retrieve entries matching a pattern."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete entries for a key."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries."""
        ...

    @abstractmethod
    def list_keys(self) -> list[str]:
        """List all keys in the store."""
        ...


class InMemoryStore(MemoryStore):
    """In-memory implementation of a memory store.

    Used as the default backing store for all memory types.
    Can be replaced with persistent storage in future phases.
    """

    def __init__(self) -> None:
        self._entries: dict[str, list[MemoryEntry]] = {}

    def store(self, entry: MemoryEntry) -> None:
        if entry.key not in self._entries:
            self._entries[entry.key] = []
        self._entries[entry.key].append(entry)

    def retrieve(self, key: str) -> MemoryEntry | None:
        versions = self._entries.get(key, [])
        if not versions:
            return None
        latest = versions[-1]
        if latest.expired():
            return None
        return latest

    def query(self, pattern: str) -> list[MemoryEntry]:
        import fnmatch

        results = []
        for key, versions in self._entries.items():
            if fnmatch.fnmatch(key, pattern):
                latest = versions[-1]
                if not latest.expired():
                    results.append(latest)
        return results

    def delete(self, key: str) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()

    def list_keys(self) -> list[str]:
        return list(self._entries.keys())


class WorkingMemory(InMemoryStore):
    """Current session state — short-lived, cleared between sessions."""

    pass


class ConversationMemory(InMemoryStore):
    """Recent conversation turns preserved for context."""

    def __init__(self, max_turns: int = 50) -> None:
        super().__init__()
        self._max_turns = max_turns
        self._turn_order: list[str] = []

    def store(self, entry: MemoryEntry) -> None:
        super().store(entry)
        if entry.key not in self._turn_order:
            self._turn_order.append(entry.key)
        while len(self._turn_order) > self._max_turns:
            oldest = self._turn_order.pop(0)
            self._entries.pop(oldest, None)


class SessionSummary(InMemoryStore):
    """Summarized state of the current session.

    Updated after each pipeline execution to capture key findings.
    """

    pass


class ToolOutputCache(InMemoryStore):
    """Cache of provider results with TTL.

    Automatically evicts expired entries on access.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        super().__init__()
        self._default_ttl = default_ttl

    def store(self, entry: MemoryEntry) -> None:
        if entry.ttl is None:
            entry.ttl = self._default_ttl
        super().store(entry)


class FactStore(InMemoryStore):
    """Persistent structured fact store.

    Stores Facts as MemoryEntry values.
    """

    def store_fact(self, fact: Fact) -> None:
        entry = MemoryEntry(
            key=f"fact:{fact.subject}:{fact.predicate}",
            value=fact,
            agent=fact.source,
            ttl=fact.ttl,
            metadata={"fact_id": fact.id},
        )
        self.store(entry)

    def get_fact(self, subject: str, predicate: str) -> Fact | None:
        entry = self.retrieve(f"fact:{subject}:{predicate}")
        if entry and isinstance(entry.value, Fact):
            return entry.value
        return None

    def query_subject(self, subject: str) -> list[Fact]:
        prefix = f"fact:{subject}:"
        facts = []
        for key, versions in self._entries.items():
            if key.startswith(prefix):
                latest = versions[-1]
                if not latest.expired() and isinstance(latest.value, Fact):
                    facts.append(latest.value)
        return facts


class UserPreferenceStore(InMemoryStore):
    """User preferences.

    Keys are preference names, values are preference values.
    """

    pass
