"""
Triangular Arbitrage Strategy

Exploit price inefficiencies in circular trading paths on a single exchange.
Example: BTC → ETH → USDT → BTC

Expected Performance:
- ROI: 0.1-0.5% per cycle
- Frequency: 10-50 opportunities per day
- Capital: $200-$2,000

Key Advantages:
- Single exchange (no transfer risk)
- Fast execution
- Lower capital requirements
- No withdrawal delays
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from dataclasses import dataclass

from .base import PollingStrategy, Opportunity
from ..providers.base import BaseProvider, OrderSide, OrderType

logger = logging.getLogger(__name__)


@dataclass
class TriangularPath:
    """Triangular arbitrage path."""
    pair1: str  # BTC/USDT
    pair2: str  # ETH/USDT
    pair3: str  # ETH/BTC
    side1: OrderSide  # Buy or Sell on pair1
    side2: OrderSide
    side3: OrderSide
    profit_pct: float
    path_description: str


class TriangularArbitrageStrategy(PollingStrategy):
    """
    Triangular arbitrage strategy on a single exchange.

    Exploits price inefficiencies in circular paths.

    Example Path:
        Start: 1.0 BTC
        1. Sell BTC for USDT: 1.0 BTC → 43,000 USDT (BTC/USDT @ 43,000)
        2. Buy ETH with USDT: 43,000 USDT → 19.5 ETH (ETH/USDT @ 2,200)
        3. Sell ETH for BTC: 19.5 ETH → 1.005 BTC (ETH/BTC @ 0.0515)
        Profit: 0.005 BTC (0.5%)

    The strategy checks multiple triangular paths and executes when
    the circular trade results in more than the starting amount.
    """

    def __init__(self, provider: BaseProvider, config: Dict[str, Any]):
        """
        Initialize triangular arbitrage strategy.

        Args:
            provider: Single exchange provider (e.g., Binance)
            config: Strategy configuration with:
                - triangle_pairs: Comma-separated triangle (e.g., "BTCUSDT,ETHUSDT,ETHBTC")
                - min_profit_pct: Minimum profit % to execute (default: 0.1)
                - order_size: Size in base currency (default: 0.01 BTC)
                - slippage_tolerance: Max slippage % (default: 0.1)
                - fee_pct: Trading fee percentage (default: 0.1 for Binance)
        """
        super().__init__(provider, config)

        # Parse triangle configuration
        triangle_str = config.get("triangle_pairs", "BTCUSDT,ETHUSDT,ETHBTC")
        self.triangle_pairs = [p.strip() for p in triangle_str.split(",")]

        if len(self.triangle_pairs) != 3:
            raise ValueError(f"Triangle must have exactly 3 pairs, got {len(self.triangle_pairs)}")

        self.min_profit_pct = float(config.get("min_profit_pct", 0.1))
        self.order_size = float(config.get("order_size", 0.01))
        self.slippage_tolerance = float(config.get("slippage_tolerance", 0.1))
        self.fee_pct = float(config.get("fee_pct", 0.1))  # 0.1% per trade

        logger.info(
            f"Triangular arbitrage initialized: {' → '.join(self.triangle_pairs)}, "
            f"min_profit={self.min_profit_pct}%"
        )

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan for triangular arbitrage opportunities.

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            # Fetch all three orderbooks concurrently
            orderbooks = await asyncio.gather(*[
                self._fetch_orderbook(pair) for pair in self.triangle_pairs
            ])

            if any(ob is None for ob in orderbooks):
                return None

            ob1, ob2, ob3 = orderbooks

            # Check both directions of the triangle

            # Direction 1: pair1 → pair2 → pair3
            path1 = self._calculate_triangular_profit(
                ob1, ob2, ob3,
                path_description=f"{self.triangle_pairs[0]} → {self.triangle_pairs[1]} → {self.triangle_pairs[2]}"
            )

            # Direction 2: Reverse path
            path2 = self._calculate_triangular_profit(
                ob1, ob2, ob3,
                reverse=True,
                path_description=f"{self.triangle_pairs[2]} → {self.triangle_pairs[1]} → {self.triangle_pairs[0]}"
            )

            # Choose best path
            best_path = None
            if path1 and path2:
                best_path = path1 if path1.profit_pct > path2.profit_pct else path2
            elif path1:
                best_path = path1
            elif path2:
                best_path = path2

            if best_path and best_path.profit_pct >= self.min_profit_pct:
                logger.info(
                    f"🔺 Triangular arbitrage found: {best_path.path_description}, "
                    f"Profit: {best_path.profit_pct:.3f}%"
                )

                return Opportunity(
                    pair=self.triangle_pairs[0],  # Starting pair
                    side=best_path.side1,
                    entry_price=0,  # Not applicable for triangular
                    size=self.order_size,
                    expected_profit=best_path.profit_pct,
                    metadata={
                        "path": best_path,
                        "strategy": "triangular_arbitrage"
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Error finding triangular opportunity: {e}")
            return None

    async def execute(self, opportunity: Opportunity) -> bool:
        """
        Execute triangular arbitrage trade.

        Places three sequential trades to complete the triangle.

        Args:
            opportunity: Triangular arbitrage opportunity

        Returns:
            True if executed successfully
        """
        path: TriangularPath = opportunity.metadata["path"]

        try:
            logger.info(
                f"Executing triangular arbitrage: {path.path_description}, "
                f"Expected profit: {path.profit_pct:.3f}%"
            )

            # Execute trades sequentially (must complete in order)
            # Trade 1
            order1 = await self._place_order_async(
                path.pair1,
                path.side1,
                OrderType.MARKET,
                self.order_size,
                None
            )

            if not order1:
                logger.error("Trade 1 failed")
                self.stats.total_trades += 1
                return False

            # Calculate size for trade 2 based on trade 1 fill
            size2 = order1.filled_size  # Use actual filled amount

            # Trade 2
            order2 = await self._place_order_async(
                path.pair2,
                path.side2,
                OrderType.MARKET,
                size2,
                None
            )

            if not order2:
                logger.error("Trade 2 failed - need to reverse trade 1")
                # Try to reverse trade 1
                await self._reverse_trade(path.pair1, path.side1, order1.filled_size)
                self.stats.total_trades += 1
                return False

            # Calculate size for trade 3 based on trade 2 fill
            size3 = order2.filled_size

            # Trade 3
            order3 = await self._place_order_async(
                path.pair3,
                path.side3,
                OrderType.MARKET,
                size3,
                None
            )

            if not order3:
                logger.error("Trade 3 failed - need to reverse trades 1 and 2")
                # Try to reverse previous trades
                await self._reverse_trade(path.pair2, path.side2, order2.filled_size)
                await self._reverse_trade(path.pair1, path.side1, order1.filled_size)
                self.stats.total_trades += 1
                return False

            # Calculate actual profit
            final_amount = order3.filled_size
            initial_amount = self.order_size
            actual_profit_pct = ((final_amount - initial_amount) / initial_amount) * 100

            logger.info(
                f"✅ Triangular arbitrage executed: Started with {initial_amount:.6f}, "
                f"Ended with {final_amount:.6f}, Profit: {actual_profit_pct:.3f}%"
            )

            self.stats.total_trades += 1
            if actual_profit_pct > 0:
                self.stats.winning_trades += 1
                profit_value = initial_amount * (actual_profit_pct / 100)
                self.stats.total_profit += profit_value

            return True

        except Exception as e:
            logger.error(f"Error executing triangular arbitrage: {e}")
            self.stats.total_trades += 1
            return False

    def _calculate_triangular_profit(
        self,
        ob1,
        ob2,
        ob3,
        reverse: bool = False,
        path_description: str = ""
    ) -> Optional[TriangularPath]:
        """
        Calculate profit for a triangular path.

        Args:
            ob1, ob2, ob3: Orderbooks for the three pairs
            reverse: Calculate reverse path
            path_description: Human-readable path description

        Returns:
            TriangularPath if profitable, None otherwise
        """
        try:
            # Example: BTC → USDT → ETH → BTC
            # Start with 1.0 BTC

            if not reverse:
                # Forward path
                # 1. Sell pair1 (BTC/USDT): BTC → USDT
                price1 = ob1.best_bid.price
                amount_after_1 = 1.0 * price1 * (1 - self.fee_pct / 100)

                # 2. Buy pair2 (ETH/USDT): USDT → ETH
                price2 = ob2.best_ask.price
                amount_after_2 = (amount_after_1 / price2) * (1 - self.fee_pct / 100)

                # 3. Sell pair3 (ETH/BTC): ETH → BTC
                price3 = ob3.best_bid.price
                amount_after_3 = amount_after_2 * price3 * (1 - self.fee_pct / 100)

                profit_pct = (amount_after_3 - 1.0) * 100 - self.slippage_tolerance

                return TriangularPath(
                    pair1=self.triangle_pairs[0],
                    pair2=self.triangle_pairs[1],
                    pair3=self.triangle_pairs[2],
                    side1=OrderSide.SELL,
                    side2=OrderSide.BUY,
                    side3=OrderSide.SELL,
                    profit_pct=profit_pct,
                    path_description=path_description
                ) if profit_pct > 0 else None

            else:
                # Reverse path
                # 1. Buy pair1 (BTC/USDT): USDT → BTC
                price1 = ob1.best_ask.price
                amount_after_1 = (1.0 / price1) * (1 - self.fee_pct / 100)

                # 2. Sell pair3 (ETH/BTC): BTC → ETH
                price3 = ob3.best_ask.price
                amount_after_2 = (amount_after_1 / price3) * (1 - self.fee_pct / 100)

                # 3. Sell pair2 (ETH/USDT): ETH → USDT
                price2 = ob2.best_bid.price
                amount_after_3 = amount_after_2 * price2 * (1 - self.fee_pct / 100)

                profit_pct = (amount_after_3 - 1.0) * 100 - self.slippage_tolerance

                return TriangularPath(
                    pair1=self.triangle_pairs[0],
                    pair2=self.triangle_pairs[1],
                    pair3=self.triangle_pairs[2],
                    side1=OrderSide.BUY,
                    side2=OrderSide.SELL,
                    side3=OrderSide.BUY,
                    profit_pct=profit_pct,
                    path_description=path_description
                ) if profit_pct > 0 else None

        except Exception as e:
            logger.error(f"Error calculating triangular profit: {e}")
            return None

    async def _fetch_orderbook(self, pair: str):
        """Fetch orderbook with error handling."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self.provider.get_orderbook, pair, 5
            )
        except Exception as e:
            logger.error(f"Error fetching orderbook for {pair}: {e}")
            return None

    async def _place_order_async(
        self,
        pair: str,
        side: OrderSide,
        order_type: OrderType,
        size: float,
        price: Optional[float]
    ):
        """Place order asynchronously."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self.provider.place_order,
                pair,
                side,
                order_type,
                size,
                price
            )
        except Exception as e:
            logger.error(f"Error placing order on {pair}: {e}")
            return None

    async def _reverse_trade(self, pair: str, original_side: OrderSide, size: float):
        """Reverse a trade by executing opposite side."""
        try:
            reverse_side = OrderSide.SELL if original_side == OrderSide.BUY else OrderSide.BUY
            await self._place_order_async(pair, reverse_side, OrderType.MARKET, size, None)
            logger.info(f"Reversed trade on {pair}")
        except Exception as e:
            logger.error(f"Error reversing trade on {pair}: {e}")
