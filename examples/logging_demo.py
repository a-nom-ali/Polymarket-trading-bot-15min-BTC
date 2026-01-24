"""
Logging Demo

Demonstrates structured logging with correlation IDs and context binding.

Run with:
    # Console output (development)
    python examples/logging_demo.py --format console

    # JSON output (production)
    python examples/logging_demo.py --format json
"""

import asyncio
import argparse
import time
import uuid
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
    get_node_logger,
    log_performance,
    log_slow_operation
)


def demo_basic_logging():
    """Demonstrate basic structured logging"""
    print("\n=== Basic Structured Logging ===\n")

    logger = get_logger(__name__)

    # Key-value logging (structured)
    logger.info("application_started", version="1.0.0", environment="development")

    # Multiple data types
    logger.info(
        "bot_configured",
        bot_id="bot_001",
        capital=10000.0,
        strategies=["arb_btc", "momentum_eth"],
        enabled=True
    )

    # Complex nested data
    logger.info(
        "trade_executed",
        trade={
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.5,
            "price": 50234.56
        },
        fees={"maker": 0.001, "taker": 0.002},
        profit=123.45
    )


def demo_log_levels():
    """Demonstrate different log levels"""
    print("\n=== Log Levels ===\n")

    logger = get_logger(__name__)

    logger.debug("debug_information", detail="Only shown in DEBUG mode")
    logger.info("informational_message", status="normal")
    logger.warning("warning_message", issue="High API latency", latency_ms=500)
    logger.error("error_message", error="Connection timeout", retry_count=3)
    logger.critical("critical_message", issue="Daily loss limit exceeded", loss=-500.0)


def demo_context_binding():
    """Demonstrate context binding"""
    print("\n=== Context Binding ===\n")

    # Bind bot context
    log = bind_context(bot_id="bot_001")

    # All subsequent logs include bot_id
    log.info("bot_started", capital=10000.0)
    log.info("strategy_added", strategy_id="arb_btc", weight=0.5)
    log.info("strategy_added", strategy_id="momentum_eth", weight=0.3)

    # Add more context
    log = log.bind(strategy_id="arb_btc")

    # Now includes both bot_id and strategy_id
    log.info("opportunity_found", spread=0.44, confidence=0.92)
    log.info("trade_executed", profit=12.34)


def demo_correlation_ids():
    """Demonstrate correlation IDs for request tracing"""
    print("\n=== Correlation IDs (Request Tracing) ===\n")

    logger = get_logger(__name__)

    # Set correlation ID
    execution_id = str(uuid.uuid4())
    set_correlation_id(execution_id)

    # All logs will include correlation_id
    logger.info("execution_started", execution_id=execution_id)
    logger.info("fetching_prices")
    logger.info("calculating_spread")
    logger.info("execution_completed")

    print(f"\n  All logs above have correlation_id={execution_id}")
    print("  This allows tracing a single execution across multiple components")


def demo_helper_loggers():
    """Demonstrate pre-configured logger helpers"""
    print("\n=== Helper Loggers ===\n")

    # Bot logger
    bot_log = get_bot_logger("bot_001")
    bot_log.info("bot_initialized", capital=10000.0)

    # Strategy logger
    strategy_log = get_strategy_logger("arb_btc", bot_id="bot_001")
    strategy_log.info("opportunity_detected", spread=0.44)

    # Execution logger (sets correlation ID automatically)
    exec_log = get_execution_logger("exec_abc123", bot_id="bot_001", strategy_id="arb_btc")
    exec_log.info("execution_started", node_count=5)
    exec_log.info("node_executing", node_id="price_check")

    # Node logger
    node_log = get_node_logger("price_binance", strategy_id="arb_btc")
    node_log.info("fetching_price")
    node_log.info("price_received", price=50234.56)


def demo_performance_logging():
    """Demonstrate performance logging"""
    print("\n=== Performance Logging ===\n")

    logger = get_logger(__name__)

    # Simulate API call
    start = time.time()
    time.sleep(0.05)  # Simulate 50ms API call
    duration_ms = (time.time() - start) * 1000

    log_performance(
        logger,
        "api_call",
        duration_ms,
        endpoint="/prices",
        status=200,
        response_size=1024
    )

    # Simulate database query
    start = time.time()
    time.sleep(0.02)  # Simulate 20ms query
    duration_ms = (time.time() - start) * 1000

    log_performance(
        logger,
        "database_query",
        duration_ms,
        query="SELECT * FROM trades WHERE bot_id = ?",
        rows_returned=42
    )


def demo_slow_operation_detection():
    """Demonstrate slow operation detection"""
    print("\n=== Slow Operation Detection ===\n")

    logger = get_logger(__name__)

    # Fast operation (won't log)
    start = time.time()
    time.sleep(0.01)  # 10ms
    duration_ms = (time.time() - start) * 1000

    log_slow_operation(
        logger,
        "fast_operation",
        duration_ms,
        threshold_ms=500,
        operation="cache_lookup"
    )

    # Slow operation (will log warning)
    start = time.time()
    time.sleep(0.6)  # 600ms
    duration_ms = (time.time() - start) * 1000

    log_slow_operation(
        logger,
        "slow_operation",
        duration_ms,
        threshold_ms=500,
        operation="blockchain_sync"
    )


def demo_exception_logging():
    """Demonstrate exception logging with stack traces"""
    print("\n=== Exception Logging ===\n")

    logger = get_logger(__name__)

    try:
        # Simulate error
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error(
            "division_error",
            error=str(e),
            numerator=1,
            denominator=0,
            exc_info=True  # Include stack trace
        )

    try:
        # Simulate network error
        raise ConnectionError("Failed to connect to exchange API")
    except ConnectionError as e:
        logger.error(
            "connection_failed",
            error=str(e),
            endpoint="https://api.exchange.com",
            retry_count=3,
            exc_info=True
        )


async def demo_realistic_workflow():
    """Demonstrate realistic workflow execution logging"""
    print("\n=== Realistic Workflow Execution ===\n")

    # Set up execution
    execution_id = str(uuid.uuid4())
    log = get_execution_logger(
        execution_id,
        bot_id="bot_001",
        strategy_id="arb_btc"
    )

    # Start execution
    log.info("execution_started", node_count=5)

    # Execute nodes
    nodes = [
        ("price_binance", 23),
        ("price_coinbase", 28),
        ("calculate_spread", 12),
        ("risk_check", 15),
        ("execute_trade", 156)
    ]

    total_duration = 0

    for node_id, expected_duration_ms in nodes:
        # Start node
        node_log = log.bind(node_id=node_id)
        node_log.info("node_started")

        # Simulate node execution
        start = time.time()
        await asyncio.sleep(expected_duration_ms / 1000)
        duration_ms = (time.time() - start) * 1000

        total_duration += duration_ms

        # Complete node
        node_log.info(
            "node_completed",
            duration_ms=round(duration_ms, 2),
            status="success"
        )

    # Complete execution
    log.info(
        "execution_completed",
        total_duration_ms=round(total_duration, 2),
        nodes_executed=len(nodes)
    )


async def demo_concurrent_executions():
    """Demonstrate concurrent executions with correlation IDs"""
    print("\n=== Concurrent Executions (Correlation IDs) ===\n")

    async def execute_strategy(strategy_id: str, delay: float):
        # Each execution gets its own correlation ID
        execution_id = f"exec_{strategy_id}_{uuid.uuid4().hex[:8]}"
        set_correlation_id(execution_id)

        log = get_logger(__name__)
        log = log.bind(strategy_id=strategy_id)

        log.info("strategy_execution_started")
        await asyncio.sleep(delay)
        log.info("strategy_execution_completed")

    # Run multiple strategies concurrently
    # Each will have its own correlation ID for tracing
    await asyncio.gather(
        execute_strategy("arb_btc", 0.1),
        execute_strategy("momentum_eth", 0.15),
        execute_strategy("market_making_sol", 0.12)
    )


def demo_real_world_events():
    """Demonstrate real-world event logging"""
    print("\n=== Real-World Events ===\n")

    logger = get_logger(__name__)

    # Bot lifecycle
    logger.info("bot_started", bot_id="bot_001", capital=10000.0, strategies=3)

    # Opportunity detection
    logger.info(
        "opportunity_found",
        strategy_id="arb_btc",
        type="arbitrage",
        spread=0.44,
        expected_profit=12.34,
        confidence=0.92
    )

    # Risk assessment
    logger.warning(
        "risk_limit_approaching",
        bot_id="bot_001",
        limit_type="daily_loss",
        used=450.0,
        limit=500.0,
        utilization=0.90
    )

    # Trade execution
    logger.info(
        "trade_executed",
        bot_id="bot_001",
        strategy_id="arb_btc",
        symbol="BTC-USDT",
        side="buy",
        quantity=0.5,
        price=50234.56,
        fees=10.05,
        net_profit=12.29
    )

    # Emergency halt
    logger.critical(
        "emergency_halt_triggered",
        bot_id="bot_001",
        reason="Daily loss limit exceeded",
        total_loss=-512.34,
        limit=-500.0
    )


async def main():
    """Main demo function"""
    parser = argparse.ArgumentParser(description="Logging Demo")
    parser.add_argument(
        "--format",
        choices=["console", "json"],
        default="console",
        help="Log output format"
    )
    parser.add_argument(
        "--level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Logging Demo - {args.format.upper()} Format")
    print(f"{'='*60}")

    # Configure logging
    configure_logging(level=args.level, format=args.format)

    if args.format == "json":
        print("\nNote: JSON output is optimized for log aggregation tools")
        print("      Each line is a complete JSON object")
        print("      Perfect for: Elasticsearch, CloudWatch, Datadog, etc.\n")

    # Run demos
    demo_basic_logging()
    demo_log_levels()
    demo_context_binding()
    demo_correlation_ids()
    demo_helper_loggers()
    demo_performance_logging()
    demo_slow_operation_detection()
    demo_exception_logging()
    await demo_realistic_workflow()
    await demo_concurrent_executions()
    demo_real_world_events()

    print(f"\n{'='*60}")
    print("Demo Complete!")
    print(f"{'='*60}\n")

    if args.format == "console":
        print("Try running with --format json to see structured output!")
    else:
        print("Try running with --format console to see colorful output!")


if __name__ == "__main__":
    asyncio.run(main())
