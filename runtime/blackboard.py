from __future__ import annotations

import fnmatch
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from runtime.models.blackboard import BBEntry

MAX_VERSIONS_PER_KEY = 100


class Blackboard:
    """Thread-safe shared versioned state store with bounded history.

    All agents communicate through the Blackboard.
    Every entry is versioned, attributed, and observable.

    Thread-safe: uses threading.Lock for all mutable state.
    Bounded: each key keeps at most MAX_VERSIONS_PER_KEY (100) entries.
    TTL-aware: expired entries are skipped during get/query.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: dict[str, list[BBEntry]] = {}
        self._watchers: dict[str, list[Callable[[BBEntry], None]]] = defaultdict(list)

    def publish(
        self,
        key: str,
        value: Any,
        agent: str,
        parent_version: int | None = None,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Publish a value to the Blackboard. Returns version number."""
        with self._lock:
            if key not in self._entries:
                self._entries[key] = []
            version = len(self._entries[key]) + 1
            entry = BBEntry(
                key=key,
                value=value,
                agent=agent,
                version=version,
                timestamp=time.time(),
                parent_version=parent_version,
                ttl=ttl,
                metadata=metadata or {},
            )
            self._entries[key].append(entry)

            # Enforce per-key version limit
            if len(self._entries[key]) > MAX_VERSIONS_PER_KEY:
                self._entries[key] = self._entries[key][-MAX_VERSIONS_PER_KEY:]

        for handler in self._watchers.get(key, []):
            handler(entry)
        for handler in self._watchers.get("*", []):
            handler(entry)

        return version

    def get(self, key: str, version: int | None = None) -> BBEntry | None:
        """Get the latest (or specific version) of a key.

        Skips expired entries (TTL expired).
        """
        with self._lock:
            versions = self._entries.get(key, [])
            if not versions:
                return None
            if version is not None:
                if 1 <= version <= len(versions):
                    return versions[version - 1]
                return None
            # Find latest non-expired entry
            for candidate in reversed(versions):
                if not candidate.expired():
                    return candidate
            return versions[-1]

    def watch(self, key: str, handler: Callable[[BBEntry], None]) -> None:
        """Watch a key for changes. '*' watches all keys."""
        self._watchers[key].append(handler)

    def history(self, key: str) -> list[BBEntry]:
        """Get full version history for a key."""
        with self._lock:
            return self._entries.get(key, []).copy()

    def query(self, pattern: str) -> list[BBEntry]:
        """Get latest non-expired entries for all keys matching a glob pattern."""
        with self._lock:
            results = []
            for key, versions in self._entries.items():
                if fnmatch.fnmatch(key, pattern) and versions:
                    # Find latest non-expired
                    for candidate in reversed(versions):
                        if not candidate.expired():
                            results.append(candidate)
                            break
                    else:
                        results.append(versions[-1])
            return results

    def cleanup_expired(self) -> int:
        """Remove expired entries from all keys. Returns count of entries removed."""
        removed = 0
        with self._lock:
            for key in list(self._entries.keys()):
                versions = self._entries[key]
                active = [v for v in versions if not v.expired()]
                if len(active) != len(versions):
                    removed += len(versions) - len(active)
                if active:
                    self._entries[key] = active
                else:
                    del self._entries[key]
        return removed
