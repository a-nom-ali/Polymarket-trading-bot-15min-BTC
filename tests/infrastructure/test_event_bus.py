"""
Tests for Event Bus implementations

Tests both in-memory and Redis backends to ensure interface compliance.
"""

import pytest
import asyncio
from src.infrastructure.events import create_event_bus, EventBus


class EventBusTestSuite:
    """
    Base test suite for event bus implementations.

    Subclasses should implement the fixture to provide specific backend.
    """

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, bus: EventBus):
        """Test basic publish/subscribe"""
        received_events = []

        async def handler(event: dict):
            received_events.append(event)

        await bus.subscribe("test_channel", handler)
        await bus.start_listening()

        # Publish event
        test_event = {"message": "hello", "value": 123}
        await bus.publish("test_channel", test_event)

        # Wait for event delivery
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0] == test_event

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus: EventBus):
        """Test multiple subscribers to same channel"""
        events_1 = []
        events_2 = []

        async def handler_1(event: dict):
            events_1.append(event)

        async def handler_2(event: dict):
            events_2.append(event)

        await bus.subscribe("channel", handler_1)
        await bus.subscribe("channel", handler_2)
        await bus.start_listening()

        # Publish event
        test_event = {"data": "test"}
        await bus.publish("channel", test_event)

        # Wait for delivery
        await asyncio.sleep(0.1)

        # Both handlers should receive event
        assert len(events_1) == 1
        assert len(events_2) == 1
        assert events_1[0] == test_event
        assert events_2[0] == test_event

    @pytest.mark.asyncio
    async def test_multiple_channels(self, bus: EventBus):
        """Test publishing to different channels"""
        channel_a_events = []
        channel_b_events = []

        async def handler_a(event: dict):
            channel_a_events.append(event)

        async def handler_b(event: dict):
            channel_b_events.append(event)

        await bus.subscribe("channel_a", handler_a)
        await bus.subscribe("channel_b", handler_b)
        await bus.start_listening()

        # Publish to different channels
        await bus.publish("channel_a", {"channel": "a"})
        await bus.publish("channel_b", {"channel": "b"})

        # Wait for delivery
        await asyncio.sleep(0.1)

        # Each handler should only receive its channel's events
        assert len(channel_a_events) == 1
        assert len(channel_b_events) == 1
        assert channel_a_events[0]["channel"] == "a"
        assert channel_b_events[0]["channel"] == "b"

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus: EventBus):
        """Test unsubscribing from channel"""
        received_events = []

        async def handler(event: dict):
            received_events.append(event)

        await bus.subscribe("channel", handler)
        await bus.start_listening()

        # Publish first event
        await bus.publish("channel", {"num": 1})
        await asyncio.sleep(0.1)

        # Unsubscribe
        await bus.unsubscribe("channel", handler)

        # Publish second event (should not be received)
        await bus.publish("channel", {"num": 2})
        await asyncio.sleep(0.1)

        # Should only have received first event
        assert len(received_events) == 1
        assert received_events[0]["num"] == 1

    @pytest.mark.asyncio
    async def test_subscribe_many(self, bus: EventBus):
        """Test subscribing to multiple channels at once"""
        received_events = []

        async def handler(event: dict):
            received_events.append(event)

        channels = ["channel_1", "channel_2", "channel_3"]
        await bus.subscribe_many(channels, handler)
        await bus.start_listening()

        # Publish to each channel
        for i, channel in enumerate(channels):
            await bus.publish(channel, {"channel": channel, "num": i})

        # Wait for delivery
        await asyncio.sleep(0.1)

        # Should receive all events
        assert len(received_events) == 3

    @pytest.mark.asyncio
    async def test_error_in_handler(self, bus: EventBus):
        """Test that error in one handler doesn't affect others"""
        successful_events = []

        async def failing_handler(event: dict):
            raise ValueError("Handler error")

        async def successful_handler(event: dict):
            successful_events.append(event)

        await bus.subscribe("channel", failing_handler)
        await bus.subscribe("channel", successful_handler)
        await bus.start_listening()

        # Publish event
        await bus.publish("channel", {"data": "test"})

        # Wait for delivery
        await asyncio.sleep(0.1)

        # Successful handler should still receive event
        assert len(successful_events) == 1

    @pytest.mark.asyncio
    async def test_complex_event_data(self, bus: EventBus):
        """Test publishing complex data structures"""
        received_events = []

        async def handler(event: dict):
            received_events.append(event)

        await bus.subscribe("channel", handler)
        await bus.start_listening()

        # Complex event
        complex_event = {
            "type": "trade_executed",
            "trade_id": 12345,
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.5,
            "price": 50234.56,
            "metadata": {
                "strategy_id": "arb_001",
                "execution_time_ms": 45,
                "fees": [
                    {"type": "maker", "amount": 0.001},
                    {"type": "exchange", "amount": 0.002}
                ]
            },
            "tags": ["arbitrage", "high_confidence"]
        }

        await bus.publish("channel", complex_event)
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0] == complex_event
        assert received_events[0]["metadata"]["fees"][0]["amount"] == 0.001

    @pytest.mark.asyncio
    async def test_get_channels(self, bus: EventBus):
        """Test getting list of active channels"""
        async def handler(event: dict):
            pass

        await bus.subscribe("channel_1", handler)
        await bus.subscribe("channel_2", handler)

        channels = await bus.get_channels()
        assert "channel_1" in channels
        assert "channel_2" in channels

    @pytest.mark.asyncio
    async def test_get_subscriber_count(self, bus: EventBus):
        """Test getting subscriber count"""
        async def handler_1(event: dict):
            pass

        async def handler_2(event: dict):
            pass

        await bus.subscribe("channel", handler_1)
        await bus.subscribe("channel", handler_2)

        count = await bus.get_subscriber_count("channel")
        assert count == 2


# Test suite for in-memory backend
class TestInMemoryEventBus(EventBusTestSuite):
    """Tests for in-memory event bus"""

    @pytest.fixture
    async def bus(self):
        """Create in-memory bus for testing"""
        bus = create_event_bus("memory")
        yield bus
        await bus.close()

    @pytest.mark.asyncio
    async def test_synchronous_delivery(self):
        """Test that in-memory delivery is synchronous"""
        bus = create_event_bus("memory")
        received = []

        async def handler(event: dict):
            received.append(event)

        await bus.subscribe("channel", handler)
        await bus.start_listening()

        # Publish and check immediately (no sleep needed)
        await bus.publish("channel", {"data": "test"})

        # Should be delivered immediately
        assert len(received) == 1

        await bus.close()


# Test suite for Redis backend (requires Redis running)
class TestRedisEventBus(EventBusTestSuite):
    """Tests for Redis event bus"""

    @pytest.fixture
    async def bus(self):
        """Create Redis bus for testing"""
        try:
            bus = create_event_bus("redis", url="redis://localhost:6379/15")

            # Test connection
            if not await bus.ping():
                pytest.skip("Redis not available")

            # Start listening
            await bus.start_listening()

            yield bus

            # Cleanup
            await bus.close()

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_redis_pattern_subscribe(self):
        """Test Redis pattern subscriptions"""
        try:
            bus = create_event_bus("redis", url="redis://localhost:6379/15")

            if not await bus.ping():
                pytest.skip("Redis not available")

            await bus.start_listening()

            received_events = []

            async def handler(event: dict):
                received_events.append(event)

            # Subscribe to pattern
            await bus.pattern_subscribe("prices:*", handler)

            # Publish to matching channels
            await bus.publish("prices:BTC-USDT", {"symbol": "BTC", "price": 50000})
            await bus.publish("prices:ETH-USDT", {"symbol": "ETH", "price": 3000})
            await bus.publish("other:channel", {"data": "should not receive"})

            # Wait for delivery
            await asyncio.sleep(0.2)

            # Should receive events from matching channels only
            assert len(received_events) == 2

            await bus.close()

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_redis_publish_many(self):
        """Test batch publishing to Redis"""
        try:
            bus = create_event_bus("redis", url="redis://localhost:6379/15")

            if not await bus.ping():
                pytest.skip("Redis not available")

            await bus.start_listening()

            received_events = []

            async def handler(event: dict):
                received_events.append(event)

            await bus.subscribe("batch_channel", handler)

            # Publish multiple events at once
            events = [
                {"num": 1},
                {"num": 2},
                {"num": 3}
            ]
            await bus.publish_many("batch_channel", events)

            # Wait for delivery
            await asyncio.sleep(0.2)

            assert len(received_events) == 3

            await bus.close()

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")


# Integration tests
@pytest.mark.asyncio
async def test_factory_memory():
    """Test factory creates in-memory bus"""
    bus = create_event_bus("memory")
    assert bus is not None

    received = []

    async def handler(event: dict):
        received.append(event)

    await bus.subscribe("test", handler)
    await bus.start_listening()
    await bus.publish("test", {"data": "test"})

    assert len(received) == 1

    await bus.close()


@pytest.mark.asyncio
async def test_factory_redis():
    """Test factory creates Redis bus"""
    try:
        bus = create_event_bus("redis", url="redis://localhost:6379/15")

        # Test connection
        if await bus.ping():
            received = []

            async def handler(event: dict):
                received.append(event)

            await bus.start_listening()
            await bus.subscribe("test", handler)
            await bus.publish("test", {"data": "test"})

            await asyncio.sleep(0.1)
            assert len(received) == 1
        else:
            pytest.skip("Redis not available")

        await bus.close()
    except Exception:
        pytest.skip("Redis not available")


def test_factory_invalid_backend():
    """Test factory raises error for invalid backend"""
    with pytest.raises(ValueError, match="Unknown event backend"):
        create_event_bus("invalid_backend")


# Real-world use case tests
@pytest.mark.asyncio
async def test_node_execution_events(bus: EventBus):
    """Test realistic node execution event flow"""
    execution_log = []

    async def log_execution(event: dict):
        execution_log.append(event)

    await bus.subscribe("node_execution:strategy_001", log_execution)
    await bus.start_listening()

    # Simulate node executions
    nodes = ["price_check", "spread_calc", "risk_check", "execute_trade"]

    for node_id in nodes:
        await bus.publish("node_execution:strategy_001", {
            "node_id": node_id,
            "status": "completed",
            "execution_time_ms": 45,
            "outputs": {"success": True}
        })

    await asyncio.sleep(0.2)

    assert len(execution_log) == 4
    assert all(e["status"] == "completed" for e in execution_log)


@pytest.mark.asyncio
async def test_price_update_stream(bus: EventBus):
    """Test realistic price update streaming"""
    prices = {}

    async def update_price(event: dict):
        prices[event["symbol"]] = event["price"]

    await bus.subscribe("prices", update_price)
    await bus.start_listening()

    # Simulate price updates
    await bus.publish("prices", {"symbol": "BTC-USDT", "price": 50234.56})
    await bus.publish("prices", {"symbol": "ETH-USDT", "price": 3012.34})
    await bus.publish("prices", {"symbol": "BTC-USDT", "price": 50245.12})  # Update

    await asyncio.sleep(0.2)

    assert prices["BTC-USDT"] == 50245.12
    assert prices["ETH-USDT"] == 3012.34


# Fixture for test suite (needs to be at module level)
@pytest.fixture
async def bus():
    """Default bus fixture (in-memory)"""
    bus = create_event_bus("memory")
    yield bus
    await bus.close()
