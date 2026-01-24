"""
Redis Event Bus Implementation

Production-ready event bus using Redis pub/sub.
Works with local Redis or hosted services (ElastiCache, Redis Cloud, etc.).
"""

from typing import Dict, Set, Optional
import json
import asyncio
from .base import EventBus, EventHandler, PublishError, SubscribeError


class RedisEventBus(EventBus):
    """
    Redis-backed event bus for production use.

    Features:
    - Multi-process (shared across workers)
    - Persistent connections
    - Background listener task
    - Pattern matching support
    - High throughput

    Supports:
    - Local Redis (docker-compose)
    - Redis Cloud (managed service)
    - AWS ElastiCache (managed service)
    - Any Redis-compatible service

    Limitations:
    - No message persistence (events are fire-and-forget)
    - No guaranteed delivery (if subscriber is down, event is lost)
    - No message ordering guarantees across channels

    For guaranteed delivery, use Redis Streams or a message queue (Kafka, RabbitMQ).

    Usage:
        # Local Redis
        bus = RedisEventBus("redis://localhost:6379")

        # Redis Cloud
        bus = RedisEventBus("redis://:password@redis-12345.c1.cloud.redislabs.com:12345")

        await bus.start_listening()
        await bus.subscribe("prices", handle_price_update)
        await bus.publish("prices", {"symbol": "BTC", "price": 50000})
    """

    def __init__(self, url: str = "redis://localhost:6379"):
        """
        Initialize Redis event bus.

        Args:
            url: Redis connection URL
                Format: redis://[username]:[password]@[host]:[port]/[db]
        """
        self.url = url
        self._redis = None  # Main Redis connection (for publishing)
        self._pubsub = None  # PubSub connection (for subscribing)
        self._handlers: Dict[str, Set[EventHandler]] = {}
        self._listen_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def _ensure_connected(self):
        """Lazy connection initialization"""
        if self._redis is None:
            try:
                import redis.asyncio as redis
            except ImportError:
                raise ImportError(
                    "redis package not installed. Install with: pip install redis"
                )

            # Create main connection for publishing
            self._redis = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )

            # Create separate connection for pub/sub
            pubsub_redis = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            self._pubsub = pubsub_redis.pubsub()

            # Test connection
            await self._redis.ping()

    async def publish(self, channel: str, event: dict):
        """
        Publish event to a channel.

        Events are serialized as JSON and sent to all subscribers.
        """
        await self._ensure_connected()

        try:
            # Serialize event
            serialized = json.dumps(event)

            # Publish to channel
            await self._redis.publish(channel, serialized)

        except Exception as e:
            raise PublishError(f"Failed to publish to channel '{channel}': {e}")

    async def subscribe(self, channel: str, handler: EventHandler):
        """
        Subscribe handler to channel.

        If this is the first subscriber to this channel,
        subscribes to Redis pub/sub.
        """
        await self._ensure_connected()

        async with self._lock:
            # Track handler
            if channel not in self._handlers:
                self._handlers[channel] = set()
                # Subscribe to Redis channel
                try:
                    await self._pubsub.subscribe(channel)
                except Exception as e:
                    raise SubscribeError(f"Failed to subscribe to channel '{channel}': {e}")

            self._handlers[channel].add(handler)

    async def unsubscribe(self, channel: str, handler: EventHandler):
        """
        Unsubscribe handler from channel.

        If this was the last subscriber to this channel,
        unsubscribes from Redis pub/sub.
        """
        async with self._lock:
            if channel in self._handlers:
                self._handlers[channel].discard(handler)

                # If no more handlers, unsubscribe from Redis
                if not self._handlers[channel]:
                    await self._pubsub.unsubscribe(channel)
                    del self._handlers[channel]

    async def start_listening(self):
        """
        Start background task to listen for events.

        Must be called before events will be received.
        Creates a background asyncio task that continuously polls Redis pub/sub.
        """
        await self._ensure_connected()

        if self._listen_task is None or self._listen_task.done():
            self._listen_task = asyncio.create_task(self._listen())

    async def _listen(self):
        """
        Background task to listen for events.

        Continuously polls Redis pub/sub and dispatches events to handlers.
        Runs until stop_listening() is called.
        """
        try:
            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data_str = message['data']

                    try:
                        # Deserialize event
                        event = json.loads(data_str)

                        # Get handlers for this channel
                        async with self._lock:
                            handlers = self._handlers.get(channel, set()).copy()

                        # Dispatch to all handlers (in background tasks)
                        for handler in handlers:
                            asyncio.create_task(self._safe_call_handler(handler, event, channel))

                    except json.JSONDecodeError as e:
                        print(f"Error decoding event on channel '{channel}': {e}")
                    except Exception as e:
                        print(f"Error processing event on channel '{channel}': {e}")

        except asyncio.CancelledError:
            # Task was cancelled (expected during shutdown)
            pass
        except Exception as e:
            print(f"Error in event listener: {e}")

    async def _safe_call_handler(self, handler: EventHandler, event: dict, channel: str):
        """
        Call handler with error handling.

        Prevents one failing handler from affecting others.
        """
        try:
            await handler(event)
        except Exception as e:
            print(f"Error in event handler for channel '{channel}': {e}")

    async def stop_listening(self):
        """Stop background listener task"""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

    async def close(self):
        """Close connections and cleanup"""
        await self.stop_listening()

        async with self._lock:
            # Unsubscribe from all channels
            if self._pubsub:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
                self._pubsub = None

            # Close main connection
            if self._redis:
                await self._redis.close()
                self._redis = None

            # Clear handlers
            self._handlers.clear()

    # Helper methods

    async def unsubscribe_all(self, handler: EventHandler):
        """Unsubscribe handler from all channels"""
        async with self._lock:
            channels_to_remove = []

            for channel, handlers in list(self._handlers.items()):
                handlers.discard(handler)

                # If no more handlers, unsubscribe from Redis
                if not handlers:
                    channels_to_remove.append(channel)

            # Unsubscribe from Redis
            if channels_to_remove:
                await self._pubsub.unsubscribe(*channels_to_remove)

            # Remove empty channels
            for channel in channels_to_remove:
                del self._handlers[channel]

    async def get_channels(self) -> list[str]:
        """Get list of active channels"""
        async with self._lock:
            return list(self._handlers.keys())

    async def get_subscriber_count(self, channel: str) -> int:
        """Get number of local subscribers to a channel"""
        async with self._lock:
            return len(self._handlers.get(channel, set()))

    async def ping(self) -> bool:
        """
        Test connection to Redis.

        Returns:
            True if connection is healthy
        """
        try:
            await self._ensure_connected()
            await self._redis.ping()
            return True
        except Exception:
            return False

    # Redis-specific features

    async def pattern_subscribe(self, pattern: str, handler: EventHandler):
        """
        Subscribe to channels matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "prices:*", "node_execution:*")
            handler: Handler function

        Note:
            Pattern subscriptions are tracked separately.
            Use pattern_unsubscribe() to remove.
        """
        await self._ensure_connected()

        async with self._lock:
            # Track pattern handler
            pattern_key = f"__pattern__:{pattern}"
            if pattern_key not in self._handlers:
                self._handlers[pattern_key] = set()
                await self._pubsub.psubscribe(pattern)

            self._handlers[pattern_key].add(handler)

    async def pattern_unsubscribe(self, pattern: str, handler: EventHandler):
        """
        Unsubscribe handler from pattern.

        Args:
            pattern: Redis pattern to unsubscribe from
            handler: Handler function to remove
        """
        async with self._lock:
            pattern_key = f"__pattern__:{pattern}"
            if pattern_key in self._handlers:
                self._handlers[pattern_key].discard(handler)

                # If no more handlers, unsubscribe from pattern
                if not self._handlers[pattern_key]:
                    await self._pubsub.punsubscribe(pattern)
                    del self._handlers[pattern_key]

    async def publish_many(self, channel: str, events: list[dict]):
        """
        Publish multiple events to a channel efficiently.

        Uses Redis pipeline for batching.

        Args:
            channel: Channel name
            events: List of event dicts
        """
        await self._ensure_connected()

        try:
            pipe = self._redis.pipeline()
            for event in events:
                serialized = json.dumps(event)
                pipe.publish(channel, serialized)
            await pipe.execute()
        except Exception as e:
            raise PublishError(f"Failed to publish batch to channel '{channel}': {e}")
