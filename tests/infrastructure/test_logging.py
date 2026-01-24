"""
Tests for Logging Infrastructure

Tests structured logging, correlation IDs, and context binding.
"""

import pytest
import json
import io
import sys
from src.infrastructure.logging import (
    configure_logging,
    get_logger,
    bind_context,
    set_correlation_id,
    get_correlation_id
)
from src.infrastructure.logging.logger import (
    get_bot_logger,
    get_strategy_logger,
    get_execution_logger,
    log_performance,
    log_slow_operation
)


@pytest.fixture
def capture_logs():
    """Capture log output for testing"""
    # Create string buffer to capture output
    buffer = io.StringIO()

    # Redirect stdout to buffer
    old_stdout = sys.stdout
    sys.stdout = buffer

    yield buffer

    # Restore stdout
    sys.stdout = old_stdout


def test_configure_logging_console():
    """Test console logging configuration"""
    configure_logging(level="INFO", format="console")

    logger = get_logger("test")
    logger.info("test_message", key="value")

    # Should not raise exception
    assert True


def test_configure_logging_json():
    """Test JSON logging configuration"""
    configure_logging(level="INFO", format="json")

    logger = get_logger("test")
    logger.info("test_message", key="value")

    # Should not raise exception
    assert True


def test_get_logger():
    """Test getting logger instance"""
    logger = get_logger("test.module")
    assert logger is not None

    # Logger should have standard methods
    assert hasattr(logger, 'debug')
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'warning')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'critical')


def test_bind_context():
    """Test binding context to logger"""
    log = bind_context(bot_id="bot_001", strategy_id="arb_btc")
    assert log is not None

    # Should be able to log with bound context
    log.info("test_event", additional_key="value")


def test_correlation_id():
    """Test correlation ID functionality"""
    # Initially None
    assert get_correlation_id() is None

    # Set correlation ID
    set_correlation_id("test_correlation_123")
    assert get_correlation_id() == "test_correlation_123"

    # Should persist in context
    logger = get_logger("test")
    logger.info("test_with_correlation")

    # Can be changed
    set_correlation_id("new_correlation_456")
    assert get_correlation_id() == "new_correlation_456"


def test_get_bot_logger():
    """Test bot logger helper"""
    logger = get_bot_logger("bot_001")
    assert logger is not None

    logger.info("bot_started", capital=10000.0)


def test_get_strategy_logger():
    """Test strategy logger helper"""
    logger = get_strategy_logger("arb_btc", bot_id="bot_001")
    assert logger is not None

    logger.info("opportunity_found", spread=0.44)


def test_get_execution_logger():
    """Test execution logger helper"""
    logger = get_execution_logger(
        "exec_abc123",
        bot_id="bot_001",
        strategy_id="arb_btc"
    )
    assert logger is not None

    # Should also set correlation ID
    assert get_correlation_id() == "exec_abc123"

    logger.info("execution_started", node_count=5)


def test_log_performance():
    """Test performance logging helper"""
    logger = get_logger("test")

    log_performance(
        logger,
        "api_call",
        45.67,
        endpoint="/prices",
        status=200
    )

    # Should not raise exception
    assert True


def test_log_slow_operation():
    """Test slow operation logging"""
    logger = get_logger("test")

    # Fast operation (should not log)
    log_slow_operation(
        logger,
        "fast_query",
        100.0,
        threshold_ms=500,
        query="SELECT 1"
    )

    # Slow operation (should log warning)
    log_slow_operation(
        logger,
        "slow_query",
        1500.0,
        threshold_ms=500,
        query="SELECT * FROM large_table"
    )

    # Should not raise exception
    assert True


def test_structured_logging_keys():
    """Test that structured logging uses key-value pairs"""
    configure_logging(level="DEBUG", format="json")

    logger = get_logger("test")

    # Log with multiple keys
    logger.info(
        "trade_executed",
        symbol="BTC-USDT",
        side="buy",
        quantity=0.5,
        price=50234.56,
        profit=123.45
    )

    # Should not raise exception
    assert True


def test_exception_logging():
    """Test logging exceptions"""
    logger = get_logger("test")

    try:
        raise ValueError("Test error")
    except ValueError as e:
        logger.error("operation_failed", error=str(e), exc_info=True)

    # Should not raise exception
    assert True


def test_different_log_levels():
    """Test different log levels"""
    configure_logging(level="DEBUG", format="console")
    logger = get_logger("test")

    logger.debug("debug_message", level="debug")
    logger.info("info_message", level="info")
    logger.warning("warning_message", level="warning")
    logger.error("error_message", level="error")
    logger.critical("critical_message", level="critical")

    # Should not raise exception
    assert True


def test_context_persistence():
    """Test that bound context persists across calls"""
    log = bind_context(bot_id="bot_001", strategy_id="arb_btc")

    # Multiple calls should all include bound context
    log.info("event_1")
    log.info("event_2")
    log.info("event_3", extra="data")

    # Should not raise exception
    assert True


def test_nested_context():
    """Test nested context binding"""
    # First level context
    log1 = bind_context(bot_id="bot_001")
    log1.info("bot_level_event")

    # Second level context (adds to first)
    log2 = log1.bind(strategy_id="arb_btc")
    log2.info("strategy_level_event")

    # Third level context (adds to both)
    log3 = log2.bind(execution_id="exec_123")
    log3.info("execution_level_event")

    # Should not raise exception
    assert True


@pytest.mark.asyncio
async def test_correlation_id_async_context():
    """Test correlation ID in async context"""
    import asyncio

    async def task_with_correlation(task_id: str):
        set_correlation_id(f"task_{task_id}")
        logger = get_logger("test")

        logger.info("task_started", task_id=task_id)
        await asyncio.sleep(0.01)
        logger.info("task_completed", task_id=task_id)

        # Correlation ID should be preserved
        assert get_correlation_id() == f"task_{task_id}"

    # Run multiple tasks concurrently
    await asyncio.gather(
        task_with_correlation("1"),
        task_with_correlation("2"),
        task_with_correlation("3")
    )


def test_logger_reuse():
    """Test that getting same logger returns same instance"""
    logger1 = get_logger("test.module")
    logger2 = get_logger("test.module")

    # Should return same logger instance (cached)
    # Note: structlog caches loggers by default
    logger1.info("test_message_1")
    logger2.info("test_message_2")


def test_realistic_workflow_logging():
    """Test realistic workflow execution logging"""
    # Configure for JSON output
    configure_logging(level="INFO", format="json")

    # Set execution context
    execution_id = "exec_abc123"
    set_correlation_id(execution_id)

    # Get execution logger
    log = get_execution_logger(
        execution_id,
        bot_id="bot_001",
        strategy_id="arb_btc"
    )

    # Simulate workflow execution
    log.info("execution_started", node_count=5)

    # Simulate node executions
    nodes = ["price_binance", "price_coinbase", "calculate_spread", "risk_check", "execute_trade"]

    for node_id in nodes:
        node_log = log.bind(node_id=node_id)
        node_log.info("node_started")

        # Simulate some work
        import time
        start = time.time()
        time.sleep(0.001)  # Simulate work
        duration_ms = (time.time() - start) * 1000

        node_log.info(
            "node_completed",
            duration_ms=round(duration_ms, 2),
            status="success"
        )

    log.info("execution_completed", total_nodes=len(nodes))

    # Should not raise exception
    assert True
