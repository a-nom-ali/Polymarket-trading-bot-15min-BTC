"""
Simple Market Making Strategy.

Strategy: Post bid/ask orders to capture spread
Returns: 80-200% APY from liquidity provision on Polymarket
Risk: Medium-High (inventory risk, adverse selection)

How it works:
1. Post buy orders below mid-price
2. Post sell orders above mid-price
3. Earn spread when both sides fill
4. Manage inventory to stay market-neutral

Example (Polymarket):
- Mid-price: $0.50
- Post bid: $0.48 (buy)
- Post ask: $0.52 (sell)
- Spread: $0.04 per share (8% return per round-trip)

Reference: https://www.chaincatcher.com/en/article/2233047
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from collections import deque

from .base import EventDrivenStrategy, Opportunity, TradeResult
from ..providers.base import BaseProvider, OrderSide, OrderType, Order, Orderbook


logger = logging.getLogger(__name__)


class SimpleMarketMakingStrategy(EventDrivenStrategy):
    """
    Simple market making strategy.

    Posts bid/ask orders around mid-price to capture spread.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: Dict[str, Any],
        market_pair: str,
        name: Optional[str] = None
    ):
        """
        Initialize market making strategy.

        Args:
            provider: Trading provider
            config: Strategy configuration with:
                - spread_pct: Target spread percentage (default: 2.0)
                - order_size: Size per level
                - num_levels: Number of price levels on each side (default: 3)
                - level_spacing_pct: Spacing between levels (default: 0.5)
                - max_inventory: Maximum inventory in shares (default: 1000)
                - inventory_skew: Skew quotes when inventory builds (default: True)
                - rebalance_threshold: Inventory % to trigger rebalancing (default: 0.7)
                - quote_refresh_interval: Seconds between quote updates (default: 30)
            market_pair: Trading pair or token ID
            name: Optional custom name
        """
        super().__init__(provider, config, name or "SimpleMarketMaking")

        self.market_pair = market_pair

        # Strategy-specific config
        self.spread_pct = config.get("spread_pct", 2.0)
        self.order_size = config.get("order_size", 50.0)
        self.num_levels = config.get("num_levels", 3)
        self.level_spacing_pct = config.get("level_spacing_pct", 0.5)
        self.max_inventory = config.get("max_inventory", 1000.0)
        self.inventory_skew = config.get("inventory_skew", True)
        self.rebalance_threshold = config.get("rebalance_threshold", 0.7)
        self.quote_refresh_interval = config.get("quote_refresh_interval", 30)

        # State
        self.current_inventory = 0.0
        self.active_orders: List[Order] = []
        self.last_quote_time = 0
        self.mid_price = 0.0

        # Performance tracking
        self.spreads_earned = deque(maxlen=100)
        self.inventory_history = deque(maxlen=1000)

        self.logger.info(f"Market making configured:")
        self.logger.info(f"  Market: {self.market_pair}")
        self.logger.info(f"  Spread: {self.spread_pct}%")
        self.logger.info(f"  Levels: {self.num_levels} × {self.order_size} shares")
        self.logger.info(f"  Max inventory: ±{self.max_inventory} shares")
        self.logger.info(f"  Inventory skew: {'Enabled' if self.inventory_skew else 'Disabled'}")

    async def run(self):
        """
        Main market making loop.

        Manages quotes and inventory continuously.
        """
        self.logger.info(f"🚀 Starting market making on {self.market_pair}")

        while self.running:
            try:
                # Get current orderbook
                orderbook = self.provider.get_orderbook(self.market_pair, depth=20)

                # Update mid-price
                if orderbook.best_bid and orderbook.best_ask:
                    self.mid_price = (orderbook.best_bid.price + orderbook.best_ask.price) / 2
                else:
                    self.logger.warning("No valid mid-price, skipping cycle")
                    await asyncio.sleep(5)
                    continue

                # Check if we need to refresh quotes
                current_time = time.time()
                if current_time - self.last_quote_time >= self.quote_refresh_interval:
                    await self._refresh_quotes(orderbook)
                    self.last_quote_time = current_time

                # Check if we need to rebalance inventory
                if self._need_rebalancing():
                    await self._rebalance_inventory(orderbook)

                # Track inventory
                self.inventory_history.append({
                    "timestamp": current_time,
                    "inventory": self.current_inventory,
                    "mid_price": self.mid_price,
                })

                # Wait before next cycle
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in market making loop: {e}", exc_info=True)
                await asyncio.sleep(5)

        # Clean up on stop
        await self._cancel_all_orders()
        self.logger.info("Market making stopped")

    async def _refresh_quotes(self, orderbook: Orderbook):
        """
        Refresh bid/ask quotes.

        Args:
            orderbook: Current market orderbook
        """
        try:
            self.logger.info(f"🔄 Refreshing quotes (mid: ${self.mid_price:.4f}, inventory: {self.current_inventory})")

            # Cancel existing orders
            await self._cancel_all_orders()

            # Calculate quote prices with inventory skew
            bid_prices, ask_prices = self._calculate_quote_prices()

            # Place new orders
            for i, (bid_price, ask_price) in enumerate(zip(bid_prices, ask_prices)):
                # Check if we should skip this level due to inventory
                if self._should_skip_level(i, "bid"):
                    self.logger.debug(f"Skipping bid level {i} due to inventory")
                else:
                    # Place bid order
                    try:
                        bid_order = self.provider.place_order(
                            pair=self.market_pair,
                            side=OrderSide.BUY,
                            order_type=OrderType.GTC,
                            size=self.order_size,
                            price=bid_price,
                        )
                        self.active_orders.append(bid_order)
                        self.logger.debug(f"  Bid {i+1}: {self.order_size} @ ${bid_price:.4f}")
                    except Exception as e:
                        self.logger.error(f"Failed to place bid: {e}")

                if self._should_skip_level(i, "ask"):
                    self.logger.debug(f"Skipping ask level {i} due to inventory")
                else:
                    # Place ask order
                    try:
                        ask_order = self.provider.place_order(
                            pair=self.market_pair,
                            side=OrderSide.SELL,
                            order_type=OrderType.GTC,
                            size=self.order_size,
                            price=ask_price,
                        )
                        self.active_orders.append(ask_order)
                        self.logger.debug(f"  Ask {i+1}: {self.order_size} @ ${ask_price:.4f}")
                    except Exception as e:
                        self.logger.error(f"Failed to place ask: {e}")

            self.logger.info(f"✅ Quotes refreshed: {len(self.active_orders)} orders posted")

        except Exception as e:
            self.logger.error(f"Error refreshing quotes: {e}", exc_info=True)

    def _calculate_quote_prices(self) -> tuple[List[float], List[float]]:
        """
        Calculate bid/ask prices for all levels with inventory skew.

        Returns:
            Tuple of (bid_prices, ask_prices)
        """
        # Base spread (half-spread each side)
        half_spread = (self.spread_pct / 100) * self.mid_price / 2

        # Calculate inventory skew
        skew = 0.0
        if self.inventory_skew and self.max_inventory > 0:
            inventory_pct = self.current_inventory / self.max_inventory
            # Skew quotes away from inventory side
            # If long inventory, widen bids and tighten asks to encourage selling
            skew = inventory_pct * half_spread * 0.5  # 50% max skew

        bid_prices = []
        ask_prices = []

        for level in range(self.num_levels):
            # Calculate level offset
            level_offset = level * (self.level_spacing_pct / 100) * self.mid_price

            # Calculate prices with skew
            bid_price = self.mid_price - half_spread - level_offset + skew
            ask_price = self.mid_price + half_spread + level_offset + skew

            # Clamp to valid range (for prediction markets: 0.01 to 0.99)
            bid_price = max(0.01, min(0.99, bid_price))
            ask_price = max(0.01, min(0.99, ask_price))

            bid_prices.append(bid_price)
            ask_prices.append(ask_price)

        return bid_prices, ask_prices

    def _should_skip_level(self, level: int, side: str) -> bool:
        """
        Check if we should skip posting this level due to inventory limits.

        Args:
            level: Level index (0 = closest to mid)
            side: "bid" or "ask"

        Returns:
            True if level should be skipped
        """
        inventory_pct = abs(self.current_inventory) / self.max_inventory

        # If inventory near limit, stop posting on that side
        if inventory_pct > 0.9:
            if side == "bid" and self.current_inventory > 0:
                return True  # Long inventory, don't buy more
            if side == "ask" and self.current_inventory < 0:
                return True  # Short inventory, don't sell more

        return False

    def _need_rebalancing(self) -> bool:
        """
        Check if inventory needs rebalancing.

        Returns:
            True if rebalancing needed
        """
        if self.max_inventory == 0:
            return False

        inventory_pct = abs(self.current_inventory) / self.max_inventory
        return inventory_pct >= self.rebalance_threshold

    async def _rebalance_inventory(self, orderbook: Orderbook):
        """
        Rebalance inventory to neutral.

        Args:
            orderbook: Current orderbook
        """
        try:
            self.logger.info(f"⚠️ Rebalancing inventory: {self.current_inventory} shares")

            if self.current_inventory > 0:
                # Long inventory → Sell at market
                size = abs(self.current_inventory)
                price = orderbook.best_bid.price if orderbook.best_bid else self.mid_price * 0.95

                self.logger.info(f"📤 Rebalancing SELL: {size} shares @ ${price:.4f}")

                if not self.dry_run:
                    order = self.provider.place_order(
                        pair=self.market_pair,
                        side=OrderSide.SELL,
                        order_type=OrderType.IOC,  # Immediate-or-Cancel
                        size=size,
                        price=price,
                    )
                    self.logger.info(f"✅ Rebalance order placed: {order.order_id}")

                self.current_inventory = 0.0

            elif self.current_inventory < 0:
                # Short inventory → Buy at market
                size = abs(self.current_inventory)
                price = orderbook.best_ask.price if orderbook.best_ask else self.mid_price * 1.05

                self.logger.info(f"📤 Rebalancing BUY: {size} shares @ ${price:.4f}")

                if not self.dry_run:
                    order = self.provider.place_order(
                        pair=self.market_pair,
                        side=OrderSide.BUY,
                        order_type=OrderType.IOC,
                        size=size,
                        price=price,
                    )
                    self.logger.info(f"✅ Rebalance order placed: {order.order_id}")

                self.current_inventory = 0.0

        except Exception as e:
            self.logger.error(f"Error rebalancing inventory: {e}", exc_info=True)

    async def _cancel_all_orders(self):
        """Cancel all active orders."""
        for order in self.active_orders:
            try:
                self.provider.cancel_order(order.order_id)
            except Exception as e:
                self.logger.debug(f"Failed to cancel order {order.order_id}: {e}")

        self.active_orders.clear()

    def on_orderbook_update(self, pair: str, orderbook: Orderbook):
        """
        Handle orderbook update (for event-driven mode).

        Args:
            pair: Trading pair
            orderbook: Updated orderbook
        """
        if pair != self.market_pair:
            return

        # Update mid-price
        if orderbook.best_bid and orderbook.best_ask:
            self.mid_price = (orderbook.best_bid.price + orderbook.best_ask.price) / 2

        # Check for fills (simplified - would need fill notifications)
        # This is a placeholder for more sophisticated fill detection

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute opportunity (not used in market making).

        Market making is passive - we don't actively execute opportunities,
        we post quotes and wait for fills.
        """
        # Not applicable for market making
        return TradeResult(
            opportunity=opportunity,
            success=False,
            error="Market making does not use execute()"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get market making statistics."""
        stats = super().get_stats()

        # Add market making specific stats
        stats.update({
            "current_inventory": self.current_inventory,
            "max_inventory": self.max_inventory,
            "inventory_utilization": abs(self.current_inventory) / self.max_inventory if self.max_inventory > 0 else 0,
            "active_orders": len(self.active_orders),
            "mid_price": self.mid_price,
            "spread_pct": self.spread_pct,
        })

        return stats

    def print_status(self):
        """Print current market making status."""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("📊 MARKET MAKING STATUS")
        self.logger.info("=" * 70)
        self.logger.info(f"Market:           {self.market_pair}")
        self.logger.info(f"Mid-price:        ${self.mid_price:.4f}")
        self.logger.info(f"Spread:           {self.spread_pct}%")
        self.logger.info(f"Active orders:    {len(self.active_orders)}")
        self.logger.info(f"Current inventory: {self.current_inventory:+.1f} / {self.max_inventory:.1f} shares")
        self.logger.info(f"Inventory %:      {(self.current_inventory / self.max_inventory * 100):+.1f}%")
        self.logger.info("=" * 70 + "\n")
