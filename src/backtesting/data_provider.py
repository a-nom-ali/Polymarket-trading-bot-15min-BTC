"""
Historical Data Provider

Mock provider for backtesting that replays historical data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..providers.base import BaseProvider
from ..core.order_book import OrderBook, OrderBookLevel

logger = logging.getLogger(__name__)


class HistoricalDataProvider(BaseProvider):
    """Provider that replays historical data for backtesting."""

    def __init__(self, historical_data: List[Dict[str, Any]]):
        """
        Initialize historical data provider.

        Args:
            historical_data: List of historical data points
        """
        super().__init__("historical", {})

        self.historical_data = sorted(historical_data, key=lambda x: x['timestamp'])
        self.current_index = 0

        logger.info(f"Historical data provider initialized ({len(historical_data)} points)")

    def set_current_index(self, index: int):
        """Set current data index."""
        self.current_index = min(index, len(self.historical_data) - 1)

    async def get_order_book(self, market_pair: str) -> Optional[OrderBook]:
        """Get current order book from historical data."""
        if self.current_index >= len(self.historical_data):
            return None

        data = self.historical_data[self.current_index]

        # Create mock order book
        price = data.get('price', 0.0)
        spread = data.get('spread', 0.001)  # 0.1% default spread

        bid_price = price * (1 - spread / 2)
        ask_price = price * (1 + spread / 2)

        # Mock liquidity
        size = data.get('volume', 1.0)

        return OrderBook(
            market_pair=market_pair,
            bids=[
                OrderBookLevel(price=bid_price, size=size),
                OrderBookLevel(price=bid_price * 0.999, size=size * 1.5),
                OrderBookLevel(price=bid_price * 0.998, size=size * 2.0)
            ],
            asks=[
                OrderBookLevel(price=ask_price, size=size),
                OrderBookLevel(price=ask_price * 1.001, size=size * 1.5),
                OrderBookLevel(price=ask_price * 1.002, size=size * 2.0)
            ],
            timestamp=data['timestamp']
        )

    async def get_balance(self) -> Dict[str, Any]:
        """Get mock balance."""
        return {
            "USDT": type('Balance', (), {"total": 10000.0, "available": 10000.0})(),
            "BTC": type('Balance', (), {"total": 0.0, "available": 0.0})()
        }

    async def place_order(self, market_pair: str, side, order_type, size: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Mock place order."""
        return {
            "order_id": f"backtest_{self.current_index}",
            "status": "FILLED",
            "filled_size": size,
            "avg_price": price or self.historical_data[self.current_index]['price']
        }

    async def cancel_order(self, order_id: str, market_pair: str = "") -> bool:
        """Mock cancel order."""
        return True

    async def get_order(self, order_id: str, market_pair: str = "") -> Optional[Dict[str, Any]]:
        """Mock get order."""
        return {
            "order_id": order_id,
            "status": "FILLED"
        }

    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Mock fetch markets."""
        return [{"symbol": "BTC/USDT", "base": "BTC", "quote": "USDT"}]


def load_csv_data(filepath: str) -> List[Dict[str, Any]]:
    """
    Load historical data from CSV file.

    Expected CSV format:
    timestamp,price,volume,spread

    Args:
        filepath: Path to CSV file

    Returns:
        List of data points
    """
    import csv
    from pathlib import Path

    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'timestamp': datetime.fromisoformat(row['timestamp']),
                'price': float(row['price']),
                'volume': float(row.get('volume', 1.0)),
                'spread': float(row.get('spread', 0.001))
            })

    logger.info(f"Loaded {len(data)} data points from {filepath}")
    return data


def load_json_data(filepath: str) -> List[Dict[str, Any]]:
    """
    Load historical data from JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        List of data points
    """
    import json
    from pathlib import Path

    with open(filepath, 'r') as f:
        data = json.load(f)

    # Parse timestamps
    for point in data:
        if isinstance(point['timestamp'], str):
            point['timestamp'] = datetime.fromisoformat(point['timestamp'])

    logger.info(f"Loaded {len(data)} data points from {filepath}")
    return data


def generate_sample_data(
    start_date: datetime,
    end_date: datetime,
    interval_minutes: int = 1,
    initial_price: float = 40000.0,
    volatility: float = 0.02
) -> List[Dict[str, Any]]:
    """
    Generate sample historical data for testing.

    Args:
        start_date: Start date
        end_date: End date
        interval_minutes: Data interval in minutes
        initial_price: Starting price
        volatility: Price volatility (std dev as fraction of price)

    Returns:
        List of data points
    """
    import random
    from datetime import timedelta

    data = []
    current_time = start_date
    current_price = initial_price

    while current_time <= end_date:
        # Random walk
        change_pct = random.gauss(0, volatility)
        current_price *= (1 + change_pct)

        # Generate data point
        data.append({
            'timestamp': current_time,
            'price': current_price,
            'volume': random.uniform(0.5, 2.0),
            'spread': random.uniform(0.0005, 0.002)
        })

        current_time += timedelta(minutes=interval_minutes)

    logger.info(f"Generated {len(data)} sample data points")
    return data
