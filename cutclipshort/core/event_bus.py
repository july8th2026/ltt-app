"""Typed publish/subscribe event system.

Decouples GUI from core and worker threads completely.
Events are emitted by core/workers, subscribed by GUI controllers.
Thread-safe: emit() can be called from any thread.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

EventCallback = Callable[[Any], None]


class EventBus:
    """Thread-safe publish/subscribe event bus.

    Usage:
        bus = EventBus()
        bus.on("analysis.progress", lambda data: print(data))
        bus.emit("analysis.progress", {"engine": "scene", "pct": 0.5})
        bus.off("analysis.progress", callback)
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._lock = threading.Lock()

    def on(self, event: str, callback: EventCallback) -> None:
        """Subscribe to an event."""
        with self._lock:
            if callback not in self._subscribers[event]:
                self._subscribers[event].append(callback)
                logger.debug("Subscribed to '%s': %s", event, callback.__qualname__)

    def off(self, event: str, callback: EventCallback) -> None:
        """Unsubscribe from an event."""
        with self._lock:
            try:
                self._subscribers[event].remove(callback)
                logger.debug("Unsubscribed from '%s': %s", event, callback.__qualname__)
            except ValueError:
                pass

    def emit(self, event: str, data: Any = None) -> None:
        """Emit an event to all subscribers. Thread-safe."""
        with self._lock:
            callbacks = list(self._subscribers.get(event, []))

        for callback in callbacks:
            try:
                callback(data)
            except Exception as exc:
                logger.exception(
                    "Error in event handler for '%s': %s",
                    event,
                    callback.__qualname__,
                )

    def clear(self, event: str | None = None) -> None:
        """Remove all subscribers for an event, or all events if None."""
        with self._lock:
            if event is None:
                self._subscribers.clear()
            else:
                self._subscribers.pop(event, None)

    def has_subscribers(self, event: str) -> bool:
        """Check if an event has any subscribers."""
        with self._lock:
            return bool(self._subscribers.get(event))
