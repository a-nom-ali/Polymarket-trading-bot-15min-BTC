"""
Structured Logging Infrastructure

Provides structured, searchable logging with correlation IDs for distributed tracing.

Features:
- JSON logging for production (easy parsing/aggregation)
- Colorful console logging for development
- Correlation IDs across async contexts
- Automatic context binding (bot_id, strategy_id, etc.)
- Performance metrics logging
- Error tracking with stack traces

Usage:
    # Configure logging once at startup
    from src.infrastructure.logging import configure_logging
    configure_logging(level="INFO", format="json")

    # Use logger throughout application
    from src.infrastructure.logging import get_logger
    logger = get_logger(__name__)

    logger.info("bot_started", bot_id="bot_001", capital=10000.0)
    logger.error("trade_failed", error="Insufficient balance", exc_info=True)

    # Bind context for multiple log calls
    from src.infrastructure.logging import bind_context
    log = bind_context(bot_id="bot_001", strategy_id="arb_btc")
    log.info("opportunity_found", spread=0.44)
    log.info("trade_executed", profit=12.34)

    # Set correlation ID for request tracing
    from src.infrastructure.logging import set_correlation_id
    set_correlation_id("exec_abc123")
"""

from .config import configure_logging, set_correlation_id, get_correlation_id
from .logger import get_logger, bind_context

__all__ = [
    "configure_logging",
    "get_logger",
    "bind_context",
    "set_correlation_id",
    "get_correlation_id"
]
