"""Publish/subscribe event bus for the Digital Twin."""

import logging
from collections.abc import Callable

from simulator.events.events import TwinEvent

logger = logging.getLogger(__name__)

SubscriberFn = Callable[[TwinEvent], None]


class EventBus:
    """Simple publish/subscribe event bus.

    Subscribers register for specific event types and are notified
    when events of that type are published.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[SubscriberFn]] = {}
        self._event_history: list[TwinEvent] = []

    def subscribe(self, event_type: str, callback: SubscriberFn) -> None:
        """Register a subscriber for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug("Subscriber registered for event: %s", event_type)

    def unsubscribe(self, event_type: str, callback: SubscriberFn) -> None:
        """Remove a subscriber for a specific event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb is not callback
            ]
            logger.debug("Subscriber removed for event: %s", event_type)

    def publish(self, event: TwinEvent) -> None:
        """Publish an event to all registered subscribers."""
        self._event_history.append(event)
        subscribers = self._subscribers.get(event.event_type, [])
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                logger.exception(
                    "Subscriber failed for event %s: %s",
                    event.event_type,
                    event.location_id,
                )
        logger.info(
            "Event published: %s | location=%s | version=%d",
            event.event_type,
            event.location_id,
            event.version_id,
        )

    def get_event_history(self) -> list[TwinEvent]:
        """Return the full event history."""
        return list(self._event_history)

    def clear(self) -> None:
        """Clear all subscribers and event history."""
        self._subscribers.clear()
        self._event_history.clear()
