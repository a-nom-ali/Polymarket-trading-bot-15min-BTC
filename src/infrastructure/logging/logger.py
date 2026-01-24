"""
Logger Utilities

Provides convenient functions for getting loggers and binding context.
"""

import structlog
from typing import Any


def get_logger(name: str = None):
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the module)
              If None, returns root logger

    Returns:
        Structured logger with all configured processors

    Usage:
        logger = get_logger(__name__)
        logger.info("event_occurred", user_id=123, action="trade")

    Logging Methods:
        logger.debug("message", key=value)    # Debug information
        logger.info("message", key=value)     # General information
        logger.warning("message", key=value)  # Warning messages
        logger.error("message", key=value)    # Error messages
        logger.critical("message", key=value) # Critical errors

    Key-Value Logging:
        All loggers use key-value pairs instead of string formatting:

        # Good (structured)
        logger.info("trade_executed", symbol="BTC-USDT", profit=123.45)

        # Bad (unstructured)
        logger.info(f"Trade executed: BTC-USDT, profit: 123.45")

    Exception Logging:
        logger.error("operation_failed", error=str(e), exc_info=True)
    """
    return structlog.get_logger(name)


def bind_context(**kwargs) -> structlog.BoundLogger:
    """
    Bind context to logger for all subsequent log calls.

    This is useful when you want to add common context to multiple log calls
    without repeating it each time.

    Args:
        **kwargs: Key-value pairs to bind to logger context

    Returns:
        Bound logger with context attached

    Usage:
        # Bind bot and strategy context
        log = bind_context(bot_id="bot_001", strategy_id="arb_btc")

        # All subsequent calls include bot_id and strategy_id
        log.info("strategy_started")
        log.info("opportunity_found", spread=0.44)
        log.info("trade_executed", profit=12.34)

    Output (console format):
        2024-01-24 10:15:23 [info     ] strategy_started     bot_id=bot_001 strategy_id=arb_btc
        2024-01-24 10:15:24 [info     ] opportunity_found    bot_id=bot_001 strategy_id=arb_btc spread=0.44
        2024-01-24 10:15:25 [info     ] trade_executed       bot_id=bot_001 strategy_id=arb_btc profit=12.34

    Common Context Keys:
        - bot_id: Bot identifier
        - strategy_id: Strategy identifier
        - execution_id: Execution/request identifier
        - user_id: User identifier
        - node_id: Workflow node identifier
        - venue: Exchange/marketplace name
    """
    return structlog.get_logger().bind(**kwargs)


# Pre-configured logger instances for common use cases

def get_bot_logger(bot_id: str):
    """
    Get logger pre-configured with bot context.

    Args:
        bot_id: Bot identifier

    Returns:
        Logger with bot_id already bound

    Usage:
        logger = get_bot_logger("bot_001")
        logger.info("bot_started", capital=10000.0)
        logger.info("strategy_added", strategy_id="arb_btc")
    """
    return bind_context(bot_id=bot_id)


def get_strategy_logger(strategy_id: str, bot_id: str = None):
    """
    Get logger pre-configured with strategy context.

    Args:
        strategy_id: Strategy identifier
        bot_id: Optional bot identifier

    Returns:
        Logger with strategy_id (and optionally bot_id) already bound

    Usage:
        logger = get_strategy_logger("arb_btc", bot_id="bot_001")
        logger.info("opportunity_found", spread=0.44)
        logger.info("trade_executed", profit=12.34)
    """
    context = {"strategy_id": strategy_id}
    if bot_id:
        context["bot_id"] = bot_id
    return bind_context(**context)


def get_execution_logger(execution_id: str, **extra_context):
    """
    Get logger pre-configured with execution context.

    Args:
        execution_id: Execution identifier (for correlation)
        **extra_context: Additional context to bind

    Returns:
        Logger with execution_id and extra context already bound

    Usage:
        logger = get_execution_logger(
            "exec_abc123",
            bot_id="bot_001",
            strategy_id="arb_btc"
        )
        logger.info("execution_started", node_count=5)
        logger.info("node_executing", node_id="price_check")
        logger.info("execution_completed", duration_ms=234)
    """
    from .config import set_correlation_id

    # Also set as correlation ID for automatic inclusion
    set_correlation_id(execution_id)

    context = {"execution_id": execution_id}
    context.update(extra_context)
    return bind_context(**context)


def get_node_logger(node_id: str, **extra_context):
    """
    Get logger pre-configured with node context.

    Args:
        node_id: Node identifier
        **extra_context: Additional context to bind

    Returns:
        Logger with node_id and extra context already bound

    Usage:
        logger = get_node_logger("price_binance", strategy_id="arb_btc")
        logger.info("node_started")
        logger.info("price_fetched", price=50234.56)
        logger.info("node_completed", duration_ms=23)
    """
    context = {"node_id": node_id}
    context.update(extra_context)
    return bind_context(**context)


# Performance logging helpers

def log_performance(logger, event_name: str, duration_ms: float, **kwargs):
    """
    Log performance metrics.

    Args:
        logger: Logger instance
        event_name: Event name (e.g., "api_call", "db_query")
        duration_ms: Duration in milliseconds
        **kwargs: Additional context

    Usage:
        import time
        start = time.time()
        result = await expensive_operation()
        duration_ms = (time.time() - start) * 1000

        log_performance(
            logger,
            "api_call",
            duration_ms,
            endpoint="/prices",
            status=200
        )
    """
    logger.info(
        event_name,
        duration_ms=round(duration_ms, 2),
        performance=True,
        **kwargs
    )


def log_slow_operation(logger, event_name: str, duration_ms: float, threshold_ms: float = 1000, **kwargs):
    """
    Log slow operations (only if they exceed threshold).

    Args:
        logger: Logger instance
        event_name: Event name
        duration_ms: Duration in milliseconds
        threshold_ms: Threshold for "slow" (default 1000ms)
        **kwargs: Additional context

    Usage:
        duration_ms = (time.time() - start) * 1000
        log_slow_operation(
            logger,
            "database_query",
            duration_ms,
            threshold_ms=500,
            query="SELECT * FROM trades"
        )
    """
    if duration_ms > threshold_ms:
        logger.warning(
            f"slow_{event_name}",
            duration_ms=round(duration_ms, 2),
            threshold_ms=threshold_ms,
            slow_operation=True,
            **kwargs
        )
