"""
Event Bus Abstraction

Provides a unified interface for pub/sub messaging across different backends.
Enables real-time event streaming for node executions, price updates, and alerts.
"""

from abc import ABC, abstractmethod
from typing import Callable, Any, Awaitable, Dict, Set

# Type alias for event handler functions
EventHandler = Callable[[dict], Awaitable[None]]


class EventBus(ABC):
    """
    Abstract pub/sub event bus.

    This interface allows the application to be backend-agnostic,
    making it easy to switch between:
    - In-memory (fast dev/testing, single process)
    - Local Redis (docker-compose, multi-process)
    - Hosted Redis (ElastiCache, Redis Cloud, etc.)
    - Future: Kafka, RabbitMQ, AWS SNS/SQS, etc.

    Event Flow:
        Publisher → Channel → Subscribers
                      ↓
                  Handler(event)

    Example:
        # Subscribe to events
        async def handle_price_update(event: dict):
            print(f"Price: {event['symbol']} = ${event['price']}")

        await bus.subscribe("prices:BTC-USDT", handle_price_update)

        # Publish events
        await bus.publish("prices:BTC-USDT", {
            "symbol": "BTC-USDT",
            "price": 50234.56,
            "timestamp": time.time()
        })
    """

    @abstractmethod
    async def publish(self, channel: str, event: dict):
        """
        Publish event to a channel.

        All subscribers to this channel will receive the event.

        Args:
            channel: Channel name (e.g., "prices:BTC-USDT", "node_execution:arb_btc")
            event: Event data (must be JSON-serializable dict)

        Note:
            Publishing is fire-and-forget. No guarantee that subscribers received it.
            For guaranteed delivery, use a message queue instead.
        """
        pass

    @abstractmethod
    async def subscribe(self, channel: str, handler: EventHandler):
        """
        Subscribe to a channel with a handler function.

        The handler will be called for each event published to this channel.

        Args:
            channel: Channel name to subscribe to
            handler: Async function that receives event dict

        Note:
            Same handler can be subscribed to multiple channels.
            Same channel can have multiple handlers.
        """
        pass

    @abstractmethod
    async def unsubscribe(self, channel: str, handler: EventHandler):
        """
        Unsubscribe handler from a channel.

        Args:
            channel: Channel name
            handler: Handler function to remove

        Note:
            If handler is subscribed to other channels, those remain active.
        """
        pass

    @abstractmethod
    async def start_listening(self):
        """
        Start listening for events (background task).

        Must be called before events will be received.
        Should be called once during application startup.

        For in-memory: No-op (events are synchronous)
        For Redis: Starts background listener task
        """
        pass

    @abstractmethod
    async def stop_listening(self):
        """
        Stop listening for events.

        Should be called during application shutdown.
        Stops all background tasks and cleans up resources.
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Close connections and cleanup resources.

        Should be called when shutting down the application.
        Stops listening and closes all connections.
        """
        pass

    # Helper methods

    async def subscribe_many(self, channels: list[str], handler: EventHandler):
        """
        Subscribe same handler to multiple channels.

        Args:
            channels: List of channel names
            handler: Handler function for all channels
        """
        for channel in channels:
            await self.subscribe(channel, handler)

    async def unsubscribe_all(self, handler: EventHandler):
        """
        Unsubscribe handler from all channels.

        Args:
            handler: Handler function to remove from all channels

        Note:
            Implementation-specific. Base implementation does nothing.
            Subclasses can optimize this if they track handler subscriptions.
        """
        pass

    async def get_channels(self) -> list[str]:
        """
        Get list of active channels.

        Returns:
            List of channel names that have subscribers

        Note:
            Optional method. Base implementation returns empty list.
            Subclasses can implement if they track active channels.
        """
        return []

    async def get_subscriber_count(self, channel: str) -> int:
        """
        Get number of subscribers to a channel.

        Args:
            channel: Channel name

        Returns:
            Number of handlers subscribed to this channel

        Note:
            Optional method. Base implementation returns 0.
            Subclasses can implement if they track subscriber counts.
        """
        return 0


class EventBusError(Exception):
    """Base exception for event bus errors"""
    pass


class PublishError(EventBusError):
    """Error publishing event"""
    pass


class SubscribeError(EventBusError):
    """Error subscribing to channel"""
    pass


class ConnectionError(EventBusError):
    """Error connecting to event bus backend"""
    pass
