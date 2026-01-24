"""
Event Bus Infrastructure

Provides abstraction for pub/sub messaging with multiple backend implementations.

Usage:
    # Create event bus based on configuration
    from src.infrastructure.events import create_event_bus

    # Local development (in-memory)
    bus = create_event_bus("memory")

    # Local Redis
    bus = create_event_bus("redis", url="redis://localhost:6379")

    # Hosted Redis (Redis Cloud, ElastiCache, etc.)
    bus = create_event_bus("redis", url="redis://:password@host:port")

    # Use the bus
    async def handle_price_update(event: dict):
        print(f"Price: {event['symbol']} = ${event['price']}")

    await bus.start_listening()
    await bus.subscribe("prices:BTC-USDT", handle_price_update)
    await bus.publish("prices:BTC-USDT", {"symbol": "BTC-USDT", "price": 50234.56})
    await bus.close()
"""

from typing import Optional
from .base import EventBus, EventHandler
from .memory import InMemoryEventBus
from .redis_bus import RedisEventBus


def create_event_bus(backend: str, **kwargs) -> EventBus:
    """
    Factory function to create event bus based on backend type.

    Args:
        backend: Backend type ("memory" or "redis")
        **kwargs: Backend-specific configuration

    Returns:
        EventBus instance

    Examples:
        # In-memory bus (development/testing)
        bus = create_event_bus("memory")

        # Local Redis
        bus = create_event_bus("redis", url="redis://localhost:6379")

        # Redis Cloud (hosted)
        bus = create_event_bus(
            "redis",
            url="redis://:password@redis-12345.c1.cloud.redislabs.com:12345"
        )

        # AWS ElastiCache
        bus = create_event_bus(
            "redis",
            url="redis://master.xxx.cache.amazonaws.com:6379"
        )

    Raises:
        ValueError: If backend is not recognized
    """
    if backend == "memory":
        return InMemoryEventBus()

    elif backend == "redis":
        url = kwargs.get("url", "redis://localhost:6379")
        return RedisEventBus(url=url)

    else:
        raise ValueError(
            f"Unknown event backend: {backend}. "
            f"Supported backends: 'memory', 'redis'"
        )


__all__ = [
    "EventBus",
    "EventHandler",
    "InMemoryEventBus",
    "RedisEventBus",
    "create_event_bus"
]
