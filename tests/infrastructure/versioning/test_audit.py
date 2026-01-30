"""
Tests for AuditLog.
"""

import pytest
from datetime import datetime, timedelta

from src.infrastructure.versioning import create_version_store
from src.infrastructure.versioning.audit import AuditLog, AuditEventType, AuditEvent


class TestAuditLog:
    """Tests for AuditLog"""

    @pytest.fixture
    async def audit_log(self):
        store = create_version_store("memory")
        audit = AuditLog(store)
        yield audit
        await store.close()

    @pytest.mark.asyncio
    async def test_record_event(self, audit_log: AuditLog):
        """Test recording an audit event"""
        meta = await audit_log.record(
            event_type=AuditEventType.TRADE_EXECUTED,
            entity_type="bot",
            entity_id="bot_001",
            actor="system",
            action="Executed arbitrage trade",
            data={"profit": 12.50, "pair": "BTC-USD"}
        )

        assert meta.version == 1

    @pytest.mark.asyncio
    async def test_query_events(self, audit_log: AuditLog):
        """Test querying events"""
        # Record multiple events
        for i in range(5):
            await audit_log.record(
                event_type=AuditEventType.TRADE_EXECUTED,
                entity_type="bot",
                entity_id="bot_001",
                actor="system",
                action=f"Trade {i+1}"
            )

        events = await audit_log.query(
            entity_type="bot",
            entity_id="bot_001",
            limit=10
        )

        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_query_filter_event_type(self, audit_log: AuditLog):
        """Test filtering by event type"""
        await audit_log.record(
            event_type=AuditEventType.TRADE_EXECUTED,
            entity_type="bot",
            entity_id="filter_test",
            actor="system",
            action="Trade"
        )
        await audit_log.record(
            event_type=AuditEventType.BOT_STARTED,
            entity_type="bot",
            entity_id="filter_test",
            actor="user",
            action="Started"
        )

        trades = await audit_log.query(
            entity_type="bot",
            entity_id="filter_test",
            event_type=AuditEventType.TRADE_EXECUTED
        )

        assert len(trades) == 1
        assert trades[0].event_type == AuditEventType.TRADE_EXECUTED

    @pytest.mark.asyncio
    async def test_query_filter_actor(self, audit_log: AuditLog):
        """Test filtering by actor"""
        await audit_log.record(
            event_type=AuditEventType.CONFIG_CHANGED,
            entity_type="config",
            entity_id="main",
            actor="admin",
            action="Changed settings"
        )
        await audit_log.record(
            event_type=AuditEventType.CONFIG_CHANGED,
            entity_type="config",
            entity_id="main",
            actor="user",
            action="Changed other settings"
        )

        admin_events = await audit_log.query(
            entity_type="config",
            entity_id="main",
            actor="admin"
        )

        assert len(admin_events) == 1
        assert admin_events[0].actor == "admin"

    @pytest.mark.asyncio
    async def test_get_event(self, audit_log: AuditLog):
        """Test getting a specific event"""
        await audit_log.record(
            event_type=AuditEventType.BOT_STARTED,
            entity_type="bot",
            entity_id="get_test",
            actor="user",
            action="Started bot"
        )

        event = await audit_log.get_event("bot", "get_test", 1)

        assert event is not None
        assert event.action == "Started bot"
        assert event.event_type == AuditEventType.BOT_STARTED

    @pytest.mark.asyncio
    async def test_correlation_id(self, audit_log: AuditLog):
        """Test correlation ID tracking"""
        correlation = "req-12345"

        await audit_log.record(
            event_type=AuditEventType.TRADE_EXECUTED,
            entity_type="bot",
            entity_id="corr_test",
            actor="system",
            action="Trade",
            correlation_id=correlation
        )

        event = await audit_log.get_event("bot", "corr_test", 1)

        assert event.correlation_id == correlation

    @pytest.mark.asyncio
    async def test_event_data(self, audit_log: AuditLog):
        """Test event data preservation"""
        data = {
            "profit": 100.50,
            "symbol": "ETH-USD",
            "quantity": 0.5
        }

        await audit_log.record(
            event_type=AuditEventType.TRADE_EXECUTED,
            entity_type="bot",
            entity_id="data_test",
            actor="system",
            action="Trade",
            data=data
        )

        event = await audit_log.get_event("bot", "data_test", 1)

        assert event.data["profit"] == 100.50
        assert event.data["symbol"] == "ETH-USD"

    @pytest.mark.asyncio
    async def test_replay_events(self, audit_log: AuditLog):
        """Test replaying events"""
        for i in range(5):
            await audit_log.record(
                event_type=AuditEventType.TRADE_EXECUTED,
                entity_type="bot",
                entity_id="replay_test",
                actor="system",
                action=f"Trade {i+1}"
            )

        replayed = []

        async def handler(event: AuditEvent):
            replayed.append(event)

        count = await audit_log.replay(
            entity_type="bot",
            entity_id="replay_test",
            handler=handler
        )

        assert count == 5
        assert len(replayed) == 5
        # Events should be in order (oldest first)
        assert replayed[0].action == "Trade 1"
        assert replayed[4].action == "Trade 5"

    @pytest.mark.asyncio
    async def test_replay_from_version(self, audit_log: AuditLog):
        """Test replaying from specific version"""
        for i in range(5):
            await audit_log.record(
                event_type=AuditEventType.TRADE_EXECUTED,
                entity_type="bot",
                entity_id="replay_from",
                actor="system",
                action=f"Trade {i+1}"
            )

        replayed = []

        async def handler(event: AuditEvent):
            replayed.append(event)

        count = await audit_log.replay(
            entity_type="bot",
            entity_id="replay_from",
            handler=handler,
            from_version=3
        )

        assert count == 3  # Versions 3, 4, 5
        assert replayed[0].action == "Trade 3"

    @pytest.mark.asyncio
    async def test_replay_filter_event_types(self, audit_log: AuditLog):
        """Test replaying with event type filter"""
        await audit_log.record(
            event_type=AuditEventType.BOT_STARTED,
            entity_type="bot",
            entity_id="replay_filter",
            actor="user",
            action="Started"
        )
        await audit_log.record(
            event_type=AuditEventType.TRADE_EXECUTED,
            entity_type="bot",
            entity_id="replay_filter",
            actor="system",
            action="Trade"
        )
        await audit_log.record(
            event_type=AuditEventType.BOT_STOPPED,
            entity_type="bot",
            entity_id="replay_filter",
            actor="user",
            action="Stopped"
        )

        replayed = []

        async def handler(event: AuditEvent):
            replayed.append(event)

        count = await audit_log.replay(
            entity_type="bot",
            entity_id="replay_filter",
            handler=handler,
            event_types=[AuditEventType.BOT_STARTED, AuditEventType.BOT_STOPPED]
        )

        assert count == 2
        assert all(e.event_type in [AuditEventType.BOT_STARTED, AuditEventType.BOT_STOPPED] for e in replayed)

    @pytest.mark.asyncio
    async def test_count_events(self, audit_log: AuditLog):
        """Test counting events"""
        for i in range(10):
            await audit_log.record(
                event_type=AuditEventType.TRADE_EXECUTED,
                entity_type="bot",
                entity_id="count_test",
                actor="system",
                action=f"Trade {i}"
            )

        count = await audit_log.count_events("bot", "count_test")

        assert count == 10


class TestAuditEvent:
    """Tests for AuditEvent dataclass"""

    def test_to_dict(self):
        """Test serialization to dict"""
        event = AuditEvent(
            event_type=AuditEventType.TRADE_EXECUTED,
            entity_type="bot",
            entity_id="test",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            actor="system",
            action="Test action",
            data={"key": "value"},
            correlation_id="corr-123"
        )

        d = event.to_dict()

        assert d["event_type"] == "trade_executed"
        assert d["entity_type"] == "bot"
        assert d["actor"] == "system"
        assert d["correlation_id"] == "corr-123"

    def test_from_dict(self):
        """Test deserialization from dict"""
        d = {
            "event_type": "bot_started",
            "entity_type": "bot",
            "entity_id": "bot_001",
            "timestamp": "2024-01-15T10:30:00",
            "actor": "user",
            "action": "Started",
            "data": {},
            "correlation_id": None
        }

        event = AuditEvent.from_dict(d)

        assert event.event_type == AuditEventType.BOT_STARTED
        assert event.entity_id == "bot_001"
        assert event.actor == "user"
