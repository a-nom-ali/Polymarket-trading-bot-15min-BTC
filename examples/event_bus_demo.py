"""
Event Bus Demo

Demonstrates how to use the event bus abstraction for real-time messaging.

Run with:
    # In-memory (no dependencies)
    python examples/event_bus_demo.py --backend memory

    # Redis (requires docker-compose up)
    docker-compose -f docker-compose.infrastructure.yml up -d redis
    python examples/event_bus_demo.py --backend redis
"""

import asyncio
import argparse
import time
from src.infrastructure.events import create_event_bus


async def demo_basic_pubsub(bus):
    """Demonstrate basic publish/subscribe"""
    print("\n=== Basic Publish/Subscribe ===")

    # Define handler
    async def handle_message(event: dict):
        print(f"   Received: {event['message']}")

    # Subscribe
    print("\n1. Subscribe to 'greetings' channel:")
    await bus.subscribe("greetings", handle_message)

    # Start listening
    await bus.start_listening()

    # Publish
    print("2. Publish messages:")
    await bus.publish("greetings", {"message": "Hello, World!"})
    await bus.publish("greetings", {"message": "Welcome to Event Bus!"})

    # Wait for delivery
    await asyncio.sleep(0.2)


async def demo_multiple_channels(bus):
    """Demonstrate multiple channels"""
    print("\n=== Multiple Channels ===")

    price_updates = []
    trade_executions = []

    async def handle_price(event: dict):
        price_updates.append(event)
        print(f"   Price Update: {event['symbol']} = ${event['price']}")

    async def handle_trade(event: dict):
        trade_executions.append(event)
        print(f"   Trade Executed: {event['side']} {event['quantity']} {event['symbol']}")

    # Subscribe to different channels
    print("\n1. Subscribe to multiple channels:")
    await bus.subscribe("prices", handle_price)
    await bus.subscribe("trades", handle_trade)

    await bus.start_listening()

    # Publish to different channels
    print("2. Publish to different channels:")
    await bus.publish("prices", {"symbol": "BTC-USDT", "price": 50234.56})
    await bus.publish("trades", {"symbol": "BTC-USDT", "side": "buy", "quantity": 0.5})
    await bus.publish("prices", {"symbol": "ETH-USDT", "price": 3012.34})

    await asyncio.sleep(0.2)

    print(f"\n   Total price updates: {len(price_updates)}")
    print(f"   Total trades: {len(trade_executions)}")


async def demo_multiple_subscribers(bus):
    """Demonstrate multiple subscribers to same channel"""
    print("\n=== Multiple Subscribers ===")

    async def logger_handler(event: dict):
        print(f"   [Logger] Event: {event}")

    async def metrics_handler(event: dict):
        print(f"   [Metrics] Count: {event.get('count', 0)}")

    async def alert_handler(event: dict):
        if event.get('critical'):
            print(f"   [Alert] CRITICAL: {event['message']}")

    # Multiple handlers for same channel
    print("\n1. Subscribe multiple handlers to 'system' channel:")
    await bus.subscribe("system", logger_handler)
    await bus.subscribe("system", metrics_handler)
    await bus.subscribe("system", alert_handler)

    await bus.start_listening()

    # Publish event
    print("2. Publish event:")
    await bus.publish("system", {
        "message": "High CPU usage detected",
        "count": 1,
        "critical": True
    })

    await asyncio.sleep(0.2)


async def demo_realistic_node_execution(bus):
    """Demonstrate realistic node execution event streaming"""
    print("\n=== Realistic Use Case: Node Execution Streaming ===")

    execution_log = []

    async def handle_node_execution(event: dict):
        execution_log.append(event)
        status_icon = "✅" if event['status'] == 'success' else "❌"
        print(f"   {status_icon} Node '{event['node_id']}' - {event['execution_time_ms']}ms")

    # Subscribe to node execution events
    print("\n1. Subscribe to node execution events:")
    strategy_id = "arb_btc_001"
    await bus.subscribe(f"node_execution:{strategy_id}", handle_node_execution)

    await bus.start_listening()

    # Simulate workflow execution
    print("2. Simulate workflow execution:")

    nodes = [
        ("price_binance", 23, "success"),
        ("price_coinbase", 28, "success"),
        ("calculate_spread", 12, "success"),
        ("risk_check", 15, "success"),
        ("execute_trade", 156, "success")
    ]

    for node_id, exec_time, status in nodes:
        await bus.publish(f"node_execution:{strategy_id}", {
            "node_id": node_id,
            "status": status,
            "execution_time_ms": exec_time,
            "timestamp": time.time()
        })
        await asyncio.sleep(0.05)  # Simulate time between executions

    await asyncio.sleep(0.2)

    total_time = sum(e['execution_time_ms'] for e in execution_log)
    print(f"\n   Total execution time: {total_time}ms")
    print(f"   Nodes executed: {len(execution_log)}")


async def demo_price_streaming(bus):
    """Demonstrate live price streaming"""
    print("\n=== Realistic Use Case: Price Streaming ===")

    latest_prices = {}

    async def update_price_cache(event: dict):
        latest_prices[event['symbol']] = {
            'price': event['price'],
            'timestamp': event['timestamp']
        }
        print(f"   {event['symbol']}: ${event['price']:,.2f}")

    # Subscribe to prices
    print("\n1. Subscribe to price updates:")
    await bus.subscribe("prices", update_price_cache)

    await bus.start_listening()

    # Simulate price feed
    print("2. Simulate price feed:")

    symbols = [
        ("BTC-USDT", 50234.56),
        ("ETH-USDT", 3012.34),
        ("BTC-USDT", 50245.12),  # Update
        ("SOL-USDT", 98.76),
        ("ETH-USDT", 3015.67),  # Update
    ]

    for symbol, price in symbols:
        await bus.publish("prices", {
            "symbol": symbol,
            "price": price,
            "timestamp": time.time()
        })
        await asyncio.sleep(0.1)

    await asyncio.sleep(0.2)

    print(f"\n   Price cache updated for {len(latest_prices)} symbols")
    for symbol, data in latest_prices.items():
        print(f"   {symbol}: ${data['price']:,.2f}")


async def demo_bot_metrics_aggregation(bus):
    """Demonstrate bot metrics aggregation"""
    print("\n=== Realistic Use Case: Bot Metrics Aggregation ===")

    bot_metrics = {}

    async def aggregate_metrics(event: dict):
        bot_id = event['bot_id']
        if bot_id not in bot_metrics:
            bot_metrics[bot_id] = {'pnl': 0, 'trades': 0}

        bot_metrics[bot_id]['pnl'] += event.get('pnl', 0)
        bot_metrics[bot_id]['trades'] += 1

        print(f"   Bot {bot_id}: PnL=${bot_metrics[bot_id]['pnl']:,.2f}, Trades={bot_metrics[bot_id]['trades']}")

    # Subscribe to bot metrics
    print("\n1. Subscribe to bot metrics:")
    await bus.subscribe("bot_metrics", aggregate_metrics)

    await bus.start_listening()

    # Simulate bot activity
    print("2. Simulate bot activity:")

    bot_updates = [
        ("bot_001", 12.50),
        ("bot_002", -5.30),
        ("bot_001", 8.75),
        ("bot_003", 45.20),
        ("bot_001", -3.10),
        ("bot_002", 15.60),
    ]

    for bot_id, pnl in bot_updates:
        await bus.publish("bot_metrics", {
            "bot_id": bot_id,
            "pnl": pnl,
            "timestamp": time.time()
        })
        await asyncio.sleep(0.05)

    await asyncio.sleep(0.2)

    print(f"\n   Summary:")
    for bot_id, metrics in bot_metrics.items():
        print(f"   {bot_id}: ${metrics['pnl']:,.2f} PnL, {metrics['trades']} trades")


async def demo_alert_system(bus):
    """Demonstrate alert system"""
    print("\n=== Realistic Use Case: Alert System ===")

    alerts = []

    async def handle_alert(event: dict):
        level = event['level']
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level, "📢")
        alerts.append(event)
        print(f"   {icon} [{level.upper()}] {event['message']}")

    # Subscribe to alerts
    print("\n1. Subscribe to alerts:")
    await bus.subscribe("alerts", handle_alert)

    await bus.start_listening()

    # Simulate various alerts
    print("2. Simulate alerts:")

    alert_events = [
        {"level": "info", "message": "Bot started successfully"},
        {"level": "warning", "message": "High API latency detected"},
        {"level": "info", "message": "Trade executed"},
        {"level": "critical", "message": "Daily loss limit approaching"},
        {"level": "critical", "message": "Emergency halt triggered"},
    ]

    for alert in alert_events:
        await bus.publish("alerts", alert)
        await asyncio.sleep(0.1)

    await asyncio.sleep(0.2)

    critical_count = sum(1 for a in alerts if a['level'] == 'critical')
    print(f"\n   Total alerts: {len(alerts)}")
    print(f"   Critical alerts: {critical_count}")


async def demo_unsubscribe(bus):
    """Demonstrate unsubscribing"""
    print("\n=== Unsubscribe Demo ===")

    received = []

    async def handler(event: dict):
        received.append(event)
        print(f"   Received: {event['num']}")

    print("\n1. Subscribe and publish:")
    await bus.subscribe("channel", handler)
    await bus.start_listening()

    await bus.publish("channel", {"num": 1})
    await bus.publish("channel", {"num": 2})
    await asyncio.sleep(0.2)

    print("2. Unsubscribe:")
    await bus.unsubscribe("channel", handler)

    await bus.publish("channel", {"num": 3})  # Should not receive
    await asyncio.sleep(0.2)

    print(f"\n   Total received: {len(received)} (should be 2)")


async def main():
    """Main demo function"""
    parser = argparse.ArgumentParser(description="Event Bus Demo")
    parser.add_argument(
        "--backend",
        choices=["memory", "redis"],
        default="memory",
        help="Event bus backend to use"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Event Bus Demo - {args.backend.upper()} Backend")
    print(f"{'='*60}")

    # Create event bus
    if args.backend == "redis":
        bus = create_event_bus("redis", url="redis://localhost:6379/0")

        # Test connection
        try:
            if not await bus.ping():
                print("\n❌ Error: Cannot connect to Redis")
                print("   Make sure Redis is running:")
                print("   docker-compose -f docker-compose.infrastructure.yml up -d redis")
                return
            print("\n✅ Connected to Redis")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Make sure Redis is running:")
            print("   docker-compose -f docker-compose.infrastructure.yml up -d redis")
            return
    else:
        bus = create_event_bus("memory")
        print("\n✅ Using in-memory bus")

    try:
        # Run demos
        await demo_basic_pubsub(bus)
        await demo_multiple_channels(bus)
        await demo_multiple_subscribers(bus)
        await demo_realistic_node_execution(bus)
        await demo_price_streaming(bus)
        await demo_bot_metrics_aggregation(bus)
        await demo_alert_system(bus)
        await demo_unsubscribe(bus)

        print(f"\n{'='*60}")
        print("Demo Complete!")
        print(f"{'='*60}\n")

    finally:
        await bus.close()


if __name__ == "__main__":
    asyncio.run(main())
