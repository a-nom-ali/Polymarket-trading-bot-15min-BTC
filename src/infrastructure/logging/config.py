"""
Logging Configuration

Sets up structured logging with correlation IDs for distributed tracing.
"""

import structlog
import logging
import sys
from typing import Literal
import contextvars


# Correlation ID context variable (for async request tracing)
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)


def set_correlation_id(correlation_id: str):
    """
    Set correlation ID for this async context.

    All logs within this context will include this correlation ID,
    making it easy to trace a request/execution across multiple components.

    Args:
        correlation_id: Unique identifier for this execution (e.g., execution_id, request_id)

    Example:
        async def execute_strategy():
            execution_id = str(uuid.uuid4())
            set_correlation_id(execution_id)

            # All logs will now include correlation_id=execution_id
            logger.info("execution_started")
            await do_work()
            logger.info("execution_completed")
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """
    Get current correlation ID.

    Returns:
        Current correlation ID, or None if not set
    """
    return correlation_id_var.get()


def add_correlation_id_processor(logger, method_name, event_dict):
    """
    Processor to add correlation ID to all log entries.

    This is automatically added to the processor chain when correlation IDs are enabled.
    """
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    return event_dict


def configure_logging(
    level: str = "INFO",
    format: Literal["json", "console"] = "console",
    add_correlation_id: bool = True,
    show_locals: bool = False
):
    """
    Configure structured logging for the entire application.

    This should be called once at application startup.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Output format
            - "json": Structured JSON (for production, log aggregation)
            - "console": Colorful console output (for development)
        add_correlation_id: Whether to add correlation IDs to logs
        show_locals: Whether to show local variables in exceptions (dev only)

    Examples:
        # Development
        configure_logging(level="DEBUG", format="console")

        # Production
        configure_logging(level="INFO", format="json", show_locals=False)

    Output Examples:

        Console (development):
            2024-01-24 10:15:23 [info     ] bot_started bot_id=bot_001 capital=10000.0

        JSON (production):
            {
                "event": "bot_started",
                "level": "info",
                "timestamp": "2024-01-24T10:15:23.456Z",
                "logger": "src.bot",
                "bot_id": "bot_001",
                "capital": 10000.0,
                "correlation_id": "exec_abc123"
            }
    """

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )

    # Build processor chain
    processors = [
        # Filter by level
        structlog.stdlib.filter_by_level,

        # Add logger name
        structlog.stdlib.add_logger_name,

        # Add log level
        structlog.stdlib.add_log_level,

        # Support positional args
        structlog.stdlib.PositionalArgumentsFormatter(),

        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),

        # Add stack info if available
        structlog.processors.StackInfoRenderer(),

        # Format exceptions
        structlog.processors.format_exc_info,

        # Decode unicode
        structlog.processors.UnicodeDecoder(),
    ]

    # Add correlation ID processor if enabled
    if add_correlation_id:
        processors.insert(0, add_correlation_id_processor)

    # Add output renderer
    if format == "json":
        # JSON renderer for production (easy parsing)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console renderer for development (colorful, readable)
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=show_locals
                )
            )
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set logging level for structlog
    logging.getLogger().setLevel(getattr(logging, level.upper()))


# Default configuration (console for development)
# This runs on import but can be overridden by calling configure_logging()
try:
    configure_logging(level="INFO", format="console")
except Exception:
    # Fallback if structlog not installed
    logging.basicConfig(level=logging.INFO)
