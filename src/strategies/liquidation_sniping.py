"""
Liquidation Sniping Strategy

Place limit orders at liquidation levels to capture flash crashes from cascading liquidations.
High risk, high reward strategy for derivatives markets.

Expected Performance:
- ROI: 2-10% per liquidation event
- Frequency: 1-5 events per week
- Capital: $500-$5,000
- Risk: HIGH (requires fast execution and monitoring)

Key Concept:
- Leveraged positions get liquidated when price hits liquidation price
- Large liquidations trigger cascading sells (longs) or buys (shorts)
- Creates temporary price dislocations
- Smart traders place limit orders just below liquidation clusters
- Capture flash crash, exit immediately on bounce

Strategy:
- Monitor liquidation heatmap (clusters of liquidations at price levels)
- Place buy limit orders just below major long liquidation clusters
- Place sell limit orders just above major short liquidation clusters
- When filled, take profit immediately (liquidation bounce)
- Use tight stop loss (flash crashes can continue)

Example:
- BTC @ $43,000
- Large liquidation cluster at $42,500 (overleveraged longs)
- Place buy limit @ $42,450
- Price crashes to $42,450 as longs get liquidated
- Order fills
- Price bounces to $42,800 (30 seconds later)
- Exit @ $42,800
- Profit: $350 per BTC = 0.82%
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict

from .base import EventDrivenStrategy, Opportunity
from ..providers.base import BaseProvider, OrderSide, OrderType, OrderStatus

logger = logging.getLogger(__name__)


@dataclass
class LiquidationLevel:
    """Liquidation price level."""
    price: float
    size: float  # Total notional value at this level
    side: str  # "long" or "short"


class LiquidationSnipingStrategy(EventDrivenStrategy):
    """
    Liquidation sniping strategy.

    Places limit orders at liquidation levels to capture flash crashes.

    WARNINGS:
    - HIGH RISK: Requires fast execution
    - Flash crashes can continue beyond liquidation levels
    - Needs real-time price monitoring
    - Best used with stop losses
    - Only trade on derivatives exchanges with visible liquidation data

    Example:
        Liquidation cluster: $100M longs at $42,500
        Current price: $43,000

        Action: Place buy limit @ $42,450 (just below cluster)

        Scenario 1 (Success):
        - Price drops to $42,450
        - Order fills during liquidation cascade
        - Price bounces to $42,700
        - Exit with $250 profit per BTC (0.59%)

        Scenario 2 (Failure):
        - Price drops to $42,450
        - Order fills
        - Price continues to $42,000 (more liquidations)
        - Stop loss triggers at $42,200
        - Loss: -$250 per BTC (-0.59%)

        Risk management is CRITICAL.
    """

    def __init__(self, provider: BaseProvider, config: Dict[str, Any]):
        """
        Initialize liquidation sniping strategy.

        Args:
            provider: Derivatives exchange with liquidation data (e.g., Bybit)
            config: Strategy configuration with:
                - pair: Trading pair
                - min_liquidation_size: Minimum notional size to consider ($, default: 10M)
                - buffer_pct: Buffer below/above liquidation level (default: 0.1%)
                - take_profit_pct: Take profit % (default: 0.5%)
                - stop_loss_pct: Stop loss % (default: 0.3%)
                - order_size: Size per trade
                - max_hold_time: Max seconds to hold position (default: 300 = 5 min)
        """
        super().__init__(provider, config)

        self.pair = config.get("pair", "BTCUSDT")
        self.min_liquidation_size = float(config.get("min_liquidation_size", 10_000_000))
        self.buffer_pct = float(config.get("buffer_pct", 0.1))
        self.take_profit_pct = float(config.get("take_profit_pct", 0.5))
        self.stop_loss_pct = float(config.get("stop_loss_pct", 0.3))
        self.order_size = float(config.get("order_size", 0.1))
        self.max_hold_time = int(config.get("max_hold_time", 300))

        # Active orders and positions
        self.pending_orders: Dict[str, Dict] = {}  # order_id -> order_info
        self.active_positions: Dict[str, Dict] = {}  # position_id -> position_info

        logger.warning(
            f"⚠️  Liquidation sniping initialized - HIGH RISK STRATEGY"
        )
        logger.info(
            f"Pair={self.pair}, min_liq_size=${self.min_liquidation_size:,.0f}, "
            f"buffer={self.buffer_pct}%, TP={self.take_profit_pct}%, SL={self.stop_loss_pct}%"
        )

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan for liquidation levels and identify sniping opportunities.

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            # Fetch current price
            current_price = await self._fetch_current_price()
            if not current_price:
                return None

            # Fetch liquidation levels (simulated - real implementation needs exchange API)
            liquidation_levels = await self._fetch_liquidation_levels()

            if not liquidation_levels:
                return None

            # Find significant liquidation clusters
            for level in liquidation_levels:
                # Only consider large enough liquidations
                if level.size < self.min_liquidation_size:
                    continue

                # Calculate entry price with buffer
                if level.side == "long":
                    # Long liquidations push price down, place buy order below
                    entry_price = level.price * (1 - self.buffer_pct / 100)

                    # Only if price is above liquidation level
                    if current_price > level.price:
                        logger.info(
                            f"🎯 Liquidation sniping opportunity: "
                            f"Buy @ ${entry_price:.2f} (${level.size:,.0f} longs at ${level.price:.2f})"
                        )

                        return Opportunity(
                            pair=self.pair,
                            side=OrderSide.BUY,
                            entry_price=entry_price,
                            size=self.order_size,
                            expected_profit=self.take_profit_pct,
                            metadata={
                                "liquidation_level": level,
                                "current_price": current_price,
                                "strategy": "liquidation_sniping"
                            }
                        )

                else:  # short liquidations
                    # Short liquidations push price up, place sell order above
                    entry_price = level.price * (1 + self.buffer_pct / 100)

                    # Only if price is below liquidation level
                    if current_price < level.price:
                        logger.info(
                            f"🎯 Liquidation sniping opportunity: "
                            f"Sell @ ${entry_price:.2f} (${level.size:,.0f} shorts at ${level.price:.2f})"
                        )

                        return Opportunity(
                            pair=self.pair,
                            side=OrderSide.SELL,
                            entry_price=entry_price,
                            size=self.order_size,
                            expected_profit=self.take_profit_pct,
                            metadata={
                                "liquidation_level": level,
                                "current_price": current_price,
                                "strategy": "liquidation_sniping"
                            }
                        )

            return None

        except Exception as e:
            logger.error(f"Error finding liquidation opportunity: {e}")
            return None

    async def execute(self, opportunity: Opportunity) -> bool:
        """
        Execute liquidation sniping trade.

        Places limit order at liquidation level.

        Args:
            opportunity: Liquidation sniping opportunity

        Returns:
            True if order placed successfully
        """
        try:
            logger.info(
                f"Placing liquidation snipe order: {opportunity.side.name} "
                f"{opportunity.size:.4f} {self.pair} @ ${opportunity.entry_price:.2f}"
            )

            # Place limit order
            order = await self._place_order_async(
                self.pair,
                opportunity.side,
                OrderType.LIMIT,  # MUST use limit order
                opportunity.size,
                opportunity.entry_price
            )

            if order:
                # Track pending order
                self.pending_orders[order.order_id] = {
                    "order": order,
                    "opportunity": opportunity,
                    "placed_at": asyncio.get_event_loop().time()
                }

                logger.info(f"✅ Liquidation snipe order placed: {order.order_id}")

                # Start monitoring this order
                asyncio.create_task(self._monitor_order(order.order_id))

                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error executing liquidation snipe: {e}")
            return False

    async def _monitor_order(self, order_id: str):
        """Monitor pending order for fills and manage position."""
        try:
            while order_id in self.pending_orders:
                await asyncio.sleep(1)  # Check every second

                # Check order status
                order_info = self.pending_orders[order_id]
                order = await self._get_order_status(order_id)

                if not order:
                    continue

                # Check if filled
                if order.status == OrderStatus.FILLED:
                    logger.info(f"🎉 Liquidation snipe filled: {order_id}")

                    # Remove from pending
                    del self.pending_orders[order_id]

                    # Create position
                    opportunity = order_info["opportunity"]
                    position_info = {
                        "order_id": order_id,
                        "side": opportunity.side,
                        "entry_price": order.price,
                        "size": order.filled_size,
                        "filled_at": asyncio.get_event_loop().time()
                    }

                    self.active_positions[order_id] = position_info

                    # Start monitoring position
                    asyncio.create_task(self._monitor_position(order_id))

                    self.stats.total_trades += 1
                    break

                # Cancel if order too old (price moved away)
                elif asyncio.get_event_loop().time() - order_info["placed_at"] > 300:
                    logger.info(f"Cancelling stale liquidation snipe order: {order_id}")
                    await self._cancel_order(order_id)
                    del self.pending_orders[order_id]
                    break

        except Exception as e:
            logger.error(f"Error monitoring order {order_id}: {e}")

    async def _monitor_position(self, position_id: str):
        """Monitor active position for take profit / stop loss."""
        try:
            position_info = self.active_positions[position_id]
            entry_price = position_info["entry_price"]
            side = position_info["side"]

            # Calculate TP/SL levels
            if side == OrderSide.BUY:
                take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
                stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
            else:
                take_profit_price = entry_price * (1 - self.take_profit_pct / 100)
                stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)

            logger.info(
                f"Monitoring position {position_id}: TP=${take_profit_price:.2f}, "
                f"SL=${stop_loss_price:.2f}"
            )

            start_time = asyncio.get_event_loop().time()

            while position_id in self.active_positions:
                await asyncio.sleep(0.5)  # Check every 500ms (fast execution needed)

                # Fetch current price
                current_price = await self._fetch_current_price()
                if not current_price:
                    continue

                # Check take profit
                if (side == OrderSide.BUY and current_price >= take_profit_price) or \
                   (side == OrderSide.SELL and current_price <= take_profit_price):
                    logger.info(f"✅ Take profit hit for {position_id} @ ${current_price:.2f}")
                    await self._close_position(position_id, "take_profit")
                    self.stats.winning_trades += 1
                    profit = position_info["size"] * abs(current_price - entry_price)
                    self.stats.total_profit += profit
                    break

                # Check stop loss
                elif (side == OrderSide.BUY and current_price <= stop_loss_price) or \
                     (side == OrderSide.SELL and current_price >= stop_loss_price):
                    logger.warning(f"❌ Stop loss hit for {position_id} @ ${current_price:.2f}")
                    await self._close_position(position_id, "stop_loss")
                    loss = position_info["size"] * abs(current_price - entry_price)
                    self.stats.total_profit -= loss
                    break

                # Force close if held too long
                elif asyncio.get_event_loop().time() - start_time > self.max_hold_time:
                    logger.warning(f"⏱️  Max hold time reached for {position_id}, closing")
                    await self._close_position(position_id, "timeout")
                    break

        except Exception as e:
            logger.error(f"Error monitoring position {position_id}: {e}")

    async def _close_position(self, position_id: str, reason: str):
        """Close an active position."""
        try:
            if position_id not in self.active_positions:
                return

            position_info = self.active_positions[position_id]

            # Reverse the side
            close_side = OrderSide.SELL if position_info["side"] == OrderSide.BUY else OrderSide.BUY

            logger.info(f"Closing position {position_id} (reason: {reason})")

            # Place market order to close
            order = await self._place_order_async(
                self.pair,
                close_side,
                OrderType.MARKET,
                position_info["size"],
                None
            )

            if order:
                del self.active_positions[position_id]
                logger.info(f"✅ Position {position_id} closed")

        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")

    async def _fetch_liquidation_levels(self) -> List[LiquidationLevel]:
        """
        Fetch liquidation levels from exchange.

        NOTE: This is a placeholder. Real implementation needs exchange-specific API.
        Bybit, Binance, and some exchanges provide liquidation data.
        """
        # Placeholder - would fetch from exchange API
        # Most exchanges don't expose this directly, need to use third-party services
        # like Coinalyze or exchange-specific liquidation maps

        logger.warning("Liquidation data not available - using mock data")

        # Return empty list (no opportunities without real data)
        return []

    async def _fetch_current_price(self) -> Optional[float]:
        """Fetch current market price."""
        try:
            if hasattr(self.provider, 'get_ticker_price'):
                return await asyncio.get_event_loop().run_in_executor(
                    None, self.provider.get_ticker_price, self.pair
                )
            return None
        except Exception as e:
            logger.error(f"Error fetching current price: {e}")
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
            logger.error(f"Error placing order: {e}")
            return None

    async def _get_order_status(self, order_id: str):
        """Get order status."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self.provider.get_order,
                order_id,
                self.pair
            )
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None

    async def _cancel_order(self, order_id: str):
        """Cancel an order."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self.provider.cancel_order,
                order_id,
                self.pair
            )
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
