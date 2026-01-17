"""
Cross-Platform Arbitrage Strategy.

Strategy: Exploit price discrepancies between different platforms
Returns: $40M+ extracted in 2024-2025, top traders earned $4.2M+
Risk: Medium (execution risk, withdrawal delays)

Examples:
1. Polymarket vs Kalshi arbitrage
   - BTC > $95k on Polymarket: $0.45
   - Same on Kalshi: $0.52
   - Profit: $0.07 per share (15.5% return)

2. Luno vs Binance arbitrage
   - BTC on Luno: 1,250,000 ZAR
   - BTC on Binance: 1,252,000 ZAR
   - Profit: 2,000 ZAR (~$110) per BTC

Reference: https://www.chaincatcher.com/en/article/2233047
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Tuple

from .base import PollingStrategy, Opportunity, TradeResult
from ..providers.base import BaseProvider, OrderSide, OrderType


logger = logging.getLogger(__name__)


class CrossPlatformArbitrageStrategy(PollingStrategy):
    """
    Cross-platform arbitrage strategy.

    Buys on cheaper platform, sells on more expensive platform to capture spread.
    """

    def __init__(
        self,
        provider_a: BaseProvider,
        provider_b: BaseProvider,
        config: Dict[str, Any],
        name: Optional[str] = None
    ):
        """
        Initialize cross-platform arbitrage strategy.

        Args:
            provider_a: First trading provider
            provider_b: Second trading provider
            config: Strategy configuration with:
                - pair: Trading pair/market (must exist on both platforms)
                - min_spread_pct: Minimum spread % to execute (default: 0.5)
                - order_size: Size of arbitrage orders
                - order_type: FOK, GTC, etc.
                - scan_interval: Seconds between scans (default: 5)
                - max_imbalance: Max inventory imbalance (default: 0.5)
                - withdrawal_enabled: Enable cross-platform transfers (default: False)
            name: Optional custom name
        """
        # Initialize with provider_a as primary
        super().__init__(provider_a, config, name or "CrossPlatformArbitrage")

        self.provider_a = provider_a
        self.provider_b = provider_b
        self.provider_a_name = type(provider_a).__name__
        self.provider_b_name = type(provider_b).__name__

        # Strategy-specific config
        self.pair = config.get("pair")
        if not self.pair:
            raise ValueError("Cross-platform arbitrage requires 'pair' in config")

        self.min_spread_pct = config.get("min_spread_pct", 0.5)
        self.order_size = config.get("order_size", 100.0)
        self.order_type_str = config.get("order_type", "FOK")
        self.max_imbalance = config.get("max_imbalance", 0.5)  # Max 50% inventory imbalance
        self.withdrawal_enabled = config.get("withdrawal_enabled", False)

        # Map string to OrderType enum
        order_type_map = {
            "FOK": OrderType.FOK,
            "GTC": OrderType.GTC,
            "IOC": OrderType.IOC,
        }
        self.order_type = order_type_map.get(self.order_type_str.upper(), OrderType.FOK)

        # Track inventory on each platform
        self.inventory_a = 0.0
        self.inventory_b = 0.0

        self.logger.info(f"Cross-platform arbitrage configured:")
        self.logger.info(f"  Platform A: {self.provider_a_name}")
        self.logger.info(f"  Platform B: {self.provider_b_name}")
        self.logger.info(f"  Pair: {self.pair}")
        self.logger.info(f"  Min spread: {self.min_spread_pct}%")
        self.logger.info(f"  Order size: {self.order_size}")
        self.logger.info(f"  Max imbalance: {self.max_imbalance * 100}%")
        self.logger.info(f"  Withdrawals: {'Enabled' if self.withdrawal_enabled else 'Disabled'}")

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan both platforms for price discrepancies.

        Returns:
            Opportunity if spread is profitable, None otherwise
        """
        try:
            # Fetch orderbooks from both platforms concurrently
            orderbook_a, orderbook_b = await asyncio.gather(
                asyncio.to_thread(self.provider_a.get_orderbook, self.pair, 10),
                asyncio.to_thread(self.provider_b.get_orderbook, self.pair, 10)
            )

            # Validate orderbooks
            if not orderbook_a.best_ask or not orderbook_a.best_bid:
                self.logger.debug(f"{self.provider_a_name}: No bids/asks available")
                return None

            if not orderbook_b.best_ask or not orderbook_b.best_bid:
                self.logger.debug(f"{self.provider_b_name}: No bids/asks available")
                return None

            # Check both directions

            # Direction 1: Buy on A, sell on B
            buy_price_a = orderbook_a.best_ask.price
            sell_price_b = orderbook_b.best_bid.price
            spread_a_to_b = sell_price_b - buy_price_a
            spread_pct_a_to_b = (spread_a_to_b / buy_price_a) * 100

            # Direction 2: Buy on B, sell on A
            buy_price_b = orderbook_b.best_ask.price
            sell_price_a = orderbook_a.best_bid.price
            spread_b_to_a = sell_price_a - buy_price_b
            spread_pct_b_to_a = (spread_b_to_a / buy_price_b) * 100

            # Choose best direction
            if spread_pct_a_to_b > spread_pct_b_to_a:
                if spread_pct_a_to_b < self.min_spread_pct:
                    return None

                buy_platform = "A"
                sell_platform = "B"
                buy_provider = self.provider_a
                sell_provider = self.provider_b
                buy_price = buy_price_a
                sell_price = sell_price_b
                spread_pct = spread_pct_a_to_b
                profit_per_unit = spread_a_to_b
            else:
                if spread_pct_b_to_a < self.min_spread_pct:
                    return None

                buy_platform = "B"
                sell_platform = "A"
                buy_provider = self.provider_b
                sell_provider = self.provider_a
                buy_price = buy_price_b
                sell_price = sell_price_a
                spread_pct = spread_pct_b_to_a
                profit_per_unit = spread_b_to_a

            # Check inventory imbalance
            if not self._check_inventory_ok(buy_platform):
                self.logger.debug(
                    f"Inventory imbalance prevents trade: "
                    f"A={self.inventory_a}, B={self.inventory_b}"
                )
                return None

            # Check liquidity
            min_liquidity = self.order_size
            buy_orderbook = orderbook_a if buy_platform == "A" else orderbook_b
            sell_orderbook = orderbook_b if sell_platform == "B" else orderbook_a

            if buy_orderbook.best_ask.volume < min_liquidity:
                self.logger.debug(f"Insufficient buy liquidity on {buy_platform}")
                return None

            if sell_orderbook.best_bid.volume < min_liquidity:
                self.logger.debug(f"Insufficient sell liquidity on {sell_platform}")
                return None

            # Calculate expected profit
            expected_profit = profit_per_unit * self.order_size

            # Create opportunity
            opportunity = Opportunity(
                strategy_name=self.name,
                timestamp=int(time.time() * 1000),
                confidence=0.85,  # Lower confidence due to execution risk
                expected_profit=expected_profit,
                metadata={
                    "pair": self.pair,
                    "buy_platform": buy_platform,
                    "sell_platform": sell_platform,
                    "buy_provider_name": self.provider_a_name if buy_platform == "A" else self.provider_b_name,
                    "sell_provider_name": self.provider_b_name if sell_platform == "B" else self.provider_a_name,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "spread": profit_per_unit,
                    "spread_pct": spread_pct,
                    "order_size": self.order_size,
                    "buy_provider": buy_provider,
                    "sell_provider": sell_provider,
                }
            )

            self.logger.info(
                f"🎯 Cross-platform arbitrage: Buy {self.pair} on {buy_platform} @ {buy_price:.4f}, "
                f"Sell on {sell_platform} @ {sell_price:.4f} → {spread_pct:.2f}% spread"
            )

            return opportunity

        except Exception as e:
            self.logger.error(f"Error finding opportunity: {e}", exc_info=True)
            return None

    def _check_inventory_ok(self, buy_platform: str) -> bool:
        """
        Check if inventory imbalance allows trading.

        Args:
            buy_platform: "A" or "B"

        Returns:
            True if trade won't exceed max imbalance
        """
        # Calculate new inventory after trade
        new_inventory_a = self.inventory_a - self.order_size if buy_platform == "B" else self.inventory_a + self.order_size
        new_inventory_b = self.inventory_b + self.order_size if buy_platform == "B" else self.inventory_b - self.order_size

        total_inventory = abs(new_inventory_a) + abs(new_inventory_b)
        if total_inventory == 0:
            return True

        # Check imbalance ratio
        imbalance = abs(new_inventory_a - new_inventory_b) / total_inventory
        return imbalance <= self.max_imbalance

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute cross-platform arbitrage.

        Args:
            opportunity: Arbitrage opportunity

        Returns:
            TradeResult with execution details
        """
        metadata = opportunity.metadata

        buy_platform = metadata["buy_platform"]
        sell_platform = metadata["sell_platform"]
        buy_provider = metadata["buy_provider"]
        sell_provider = metadata["sell_provider"]
        buy_price = metadata["buy_price"]
        sell_price = metadata["sell_price"]
        order_size = metadata["order_size"]

        self.logger.info("=" * 70)
        self.logger.info("🎯 EXECUTING CROSS-PLATFORM ARBITRAGE")
        self.logger.info("=" * 70)
        self.logger.info(f"Pair:         {metadata['pair']}")
        self.logger.info(f"Buy:          {metadata['buy_provider_name']} @ ${buy_price:.4f}")
        self.logger.info(f"Sell:         {metadata['sell_provider_name']} @ ${sell_price:.4f}")
        self.logger.info(f"Spread:       ${metadata['spread']:.4f} ({metadata['spread_pct']:.2f}%)")
        self.logger.info(f"Order size:   {order_size}")
        self.logger.info(f"Expected profit: ${opportunity.expected_profit:.2f}")
        self.logger.info("=" * 70)

        if self.dry_run:
            self.logger.info("🔸 DRY RUN MODE - No real orders placed")
            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,
                orders=[],
            )

        orders = []

        try:
            # Execute both legs simultaneously
            self.logger.info(f"📤 Placing BUY order on {buy_platform}: {order_size} @ ${buy_price:.4f}")
            self.logger.info(f"📤 Placing SELL order on {sell_platform}: {order_size} @ ${sell_price:.4f}")

            buy_order, sell_order = await asyncio.gather(
                asyncio.to_thread(
                    buy_provider.place_order,
                    pair=metadata["pair"],
                    side=OrderSide.BUY,
                    order_type=self.order_type,
                    size=order_size,
                    price=buy_price
                ),
                asyncio.to_thread(
                    sell_provider.place_order,
                    pair=metadata["pair"],
                    side=OrderSide.SELL,
                    order_type=self.order_type,
                    size=order_size,
                    price=sell_price
                )
            )

            orders = [buy_order, sell_order]
            self.logger.info(f"✅ BUY order placed: {buy_order.order_id}")
            self.logger.info(f"✅ SELL order placed: {sell_order.order_id}")

            # For FOK orders, verify both filled
            if self.order_type == OrderType.FOK:
                await asyncio.sleep(1.0)

                buy_status, sell_status = await asyncio.gather(
                    asyncio.to_thread(buy_provider.get_order, buy_order.order_id),
                    asyncio.to_thread(sell_provider.get_order, sell_order.order_id)
                )

                if buy_status.is_complete and sell_status.is_complete:
                    self.logger.info("✅ Both orders filled successfully")

                    # Update inventory
                    if buy_platform == "A":
                        self.inventory_a += order_size
                        self.inventory_b -= order_size
                    else:
                        self.inventory_b += order_size
                        self.inventory_a -= order_size

                    return TradeResult(
                        opportunity=opportunity,
                        success=True,
                        actual_profit=opportunity.expected_profit,
                        orders=orders,
                    )
                else:
                    self.logger.warning("⚠️ One or more orders not filled")
                    # TODO: Cancel unfilled orders and attempt to flatten
                    return TradeResult(
                        opportunity=opportunity,
                        success=False,
                        orders=orders,
                        error="Partial fill or execution failure"
                    )

            # For GTC/IOC, assume success
            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,
                orders=orders,
            )

        except Exception as e:
            self.logger.error(f"Error executing arbitrage: {e}", exc_info=True)

            # Attempt to cancel any placed orders
            for order in orders:
                try:
                    provider = buy_provider if order == orders[0] else sell_provider
                    provider.cancel_order(order.order_id)
                    self.logger.info(f"Cancelled order: {order.order_id}")
                except Exception as cancel_err:
                    self.logger.error(f"Failed to cancel order: {cancel_err}")

            return TradeResult(
                opportunity=opportunity,
                success=False,
                orders=orders,
                error=str(e)
            )

    def get_inventory(self) -> Dict[str, float]:
        """
        Get current inventory on both platforms.

        Returns:
            Dict with inventory for each platform
        """
        return {
            self.provider_a_name: self.inventory_a,
            self.provider_b_name: self.inventory_b,
            "total": self.inventory_a + self.inventory_b,
            "imbalance": abs(self.inventory_a - self.inventory_b),
        }
