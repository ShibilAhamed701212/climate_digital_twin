from __future__ import annotations

import threading
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from runtime.models.events import Event

EventCallback = Callable[[Event], Any]

MAX_HISTORY = 10_000


class EventBus:
    """Thread-safe pub/sub event system with bounded history.

    All communication between Runtime components goes through the EventBus.
    Events carry trace_ids for distributed tracing.

    Thread-safe: uses threading.Lock for mutable state.
    Bounded history: oldest events evicted at MAX_HISTORY (10,000).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._history: deque[Event] = deque(maxlen=MAX_HISTORY)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        with self._lock:
            self._history.append(event)
            for handler in self._subscribers.get(event.type, []):
                handler(event)

    def subscribe(self, event_type: str, handler: EventCallback) -> None:
        """Subscribe to a specific event type."""
        self._subscribers[event_type].append(handler)

    def history(self) -> list[Event]:
        """Get full event history."""
        with self._lock:
            return list(self._history)
