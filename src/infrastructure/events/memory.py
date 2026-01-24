"""
In-Memory Event Bus Implementation

Fast, simple event bus for local development and testing.
Events are delivered synchronously within the same process.
"""

from typing import Dict, Set
import asyncio
from .base import EventBus, EventHandler


class InMemoryEventBus(EventBus):
    """
    In-memory event bus for local development and testing.

    Features:
    - Fast (no network overhead, synchronous delivery)
    - Simple (no external dependencies)
    - Thread-safe (async lock)
    - Immediate delivery (no background task needed)

    Limitations:
    - Single process only (not shared across workers)
    - Events lost on restart
    - No persistence or replay

    Usage:
        bus = InMemoryEventBus()
        await bus.subscribe("prices", handle_price_update)
        await bus.publish("prices", {"symbol": "BTC", "price": 50000})
    """

    def __init__(self):
        # Map of channel -> set of handlers
        self._handlers: Dict[str, Set[EventHandler]] = {}
        self._lock = asyncio.Lock()
        self._running = False

    async def publish(self, channel: str, event: dict):
        """
        Publish event to all subscribers immediately.

        Note: In-memory implementation calls all handlers synchronously.
        If a handler is slow, it will block other handlers on the same channel.
        """
        async with self._lock:
            handlers = self._handlers.get(channel, set()).copy()

        # Call handlers outside lock to avoid blocking
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                # Log error but don't stop other handlers
                print(f"Error in event handler for channel '{channel}': {e}")

    async def subscribe(self, channel: str, handler: EventHandler):
        """Subscribe handler to channel"""
        async with self._lock:
            if channel not in self._handlers:
                self._handlers[channel] = set()
            self._handlers[channel].add(handler)

    async def unsubscribe(self, channel: str, handler: EventHandler):
        """Unsubscribe handler from channel"""
        async with self._lock:
            if channel in self._handlers:
                self._handlers[channel].discard(handler)
                # Clean up empty channel
                if not self._handlers[channel]:
                    del self._handlers[channel]

    async def start_listening(self):
        """Start listening (no-op for in-memory)"""
        self._running = True

    async def stop_listening(self):
        """Stop listening (no-op for in-memory)"""
        self._running = False

    async def close(self):
        """Clear all subscriptions"""
        async with self._lock:
            self._handlers.clear()
        self._running = False

    # Helper methods

    async def unsubscribe_all(self, handler: EventHandler):
        """Unsubscribe handler from all channels"""
        async with self._lock:
            for channel in list(self._handlers.keys()):
                self._handlers[channel].discard(handler)
                # Clean up empty channels
                if not self._handlers[channel]:
                    del self._handlers[channel]

    async def get_channels(self) -> list[str]:
        """Get list of active channels"""
        async with self._lock:
            return list(self._handlers.keys())

    async def get_subscriber_count(self, channel: str) -> int:
        """Get number of subscribers to a channel"""
        async with self._lock:
            return len(self._handlers.get(channel, set()))

    # Testing helpers

    async def clear_all(self):
        """Clear all subscriptions (useful for testing)"""
        await self.close()

    async def get_all_handlers(self) -> Dict[str, Set[EventHandler]]:
        """Get all handlers (useful for debugging)"""
        async with self._lock:
            return {
                channel: handlers.copy()
                for channel, handlers in self._handlers.items()
            }
