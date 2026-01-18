"""
Cross-Exchange Arbitrage Strategy

Buy low on one exchange, sell high on another.
Exploits price differences between exchanges like Binance, Coinbase, and Kraken.

Expected Performance:
- ROI: 0.3-1.5% per trade
- Frequency: 5-20 opportunities per day
- Capital: $500-$5,000

Key Opportunity:
- Coinbase often trades at 0.3-1.5% premium vs Binance (US demand)
- Kraken EUR pairs offer triangular opportunities
- Account for fees, slippage, and withdrawal times
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

from .base import PollingStrategy, Opportunity
from ..providers.base import BaseProvider, OrderSide, OrderType

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    """Cross-exchange arbitrage opportunity."""
    buy_exchange: str
    sell_exchange: str
    pair: str
    buy_price: float
    sell_price: float
    spread_pct: float
    profit_pct: float  # After fees
    max_volume: float
    timestamp: int


class CrossExchangeArbitrageStrategy(PollingStrategy):
    """
    Cross-exchange arbitrage strategy.

    Buy on cheaper exchange, sell on more expensive exchange.
    Accounts for fees, slippage, and inventory management.

    Example:
        Binance: BTC @ $43,000
        Coinbase: BTC @ $43,500
        Spread: 1.16% (before fees)
        Net profit: ~0.4-0.7% after fees
    """

    def __init__(self, provider_a: BaseProvider, provider_b: BaseProvider, config: Dict[str, Any]):
        """
        Initialize cross-exchange arbitrage strategy.

        Args:
            provider_a: First exchange (e.g., Binance)
            provider_b: Second exchange (e.g., Coinbase)
            config: Strategy configuration with:
                - pair: Trading pair (must exist on both exchanges)
                - min_spread_pct: Minimum spread % to execute (default: 0.3)
                - order_size: Size per trade in base currency
                - max_imbalance: Max inventory imbalance (0.5 = 50%)
                - fee_a: Trading fee on exchange A (default: 0.1%)
                - fee_b: Trading fee on exchange B (default: 0.5%)
                - slippage_tolerance: Max slippage % (default: 0.1%)
        """
        # Store both providers
        self.provider_a = provider_a
        self.provider_b = provider_b

        # Use provider_a as primary for base class
        super().__init__(provider_a, config)

        self.pair = config.get("pair", "BTCUSDT")
        self.min_spread_pct = float(config.get("min_spread_pct", 0.3))
        self.order_size = float(config.get("order_size", 0.01))
        self.max_imbalance = float(config.get("max_imbalance", 0.5))

        # Fee structure (as percentage)
        self.fee_a = float(config.get("fee_a", 0.1))  # Binance: 0.1%
        self.fee_b = float(config.get("fee_b", 0.5))  # Coinbase: 0.5%
        self.slippage_tolerance = float(config.get("slippage_tolerance", 0.1))

        # Inventory tracking
        self.inventory_a = 0.0  # Net position on exchange A
        self.inventory_b = 0.0  # Net position on exchange B

        logger.info(
            f"Cross-exchange arbitrage initialized: {self.provider_a.__class__.__name__} ↔ "
            f"{self.provider_b.__class__.__name__}, pair={self.pair}, "
            f"min_spread={self.min_spread_pct}%"
        )

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan both exchanges for arbitrage opportunities.

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            # Fetch orderbooks from both exchanges concurrently
            orderbook_a, orderbook_b = await asyncio.gather(
                self._fetch_orderbook(self.provider_a, self.pair),
                self._fetch_orderbook(self.provider_b, self.pair)
            )

            if not orderbook_a or not orderbook_b:
                return None

            # Check both directions for arbitrage

            # Direction 1: Buy on A, Sell on B
            opportunity_a_to_b = self._check_arbitrage(
                buy_exchange="A",
                sell_exchange="B",
                buy_price=orderbook_a.best_ask.price,
                sell_price=orderbook_b.best_bid.price,
                buy_volume=orderbook_a.best_ask.volume,
                sell_volume=orderbook_b.best_bid.volume
            )

            # Direction 2: Buy on B, Sell on A
            opportunity_b_to_a = self._check_arbitrage(
                buy_exchange="B",
                sell_exchange="A",
                buy_price=orderbook_b.best_ask.price,
                sell_price=orderbook_a.best_bid.price,
                buy_volume=orderbook_b.best_ask.volume,
                sell_volume=orderbook_a.best_bid.volume
            )

            # Choose best opportunity
            best_opportunity = None

            if opportunity_a_to_b and opportunity_b_to_a:
                best_opportunity = (
                    opportunity_a_to_b if opportunity_a_to_b.profit_pct > opportunity_b_to_a.profit_pct
                    else opportunity_b_to_a
                )
            elif opportunity_a_to_b:
                best_opportunity = opportunity_a_to_b
            elif opportunity_b_to_a:
                best_opportunity = opportunity_b_to_a

            if best_opportunity:
                # Check inventory constraints
                if not self._check_inventory_ok(best_opportunity.buy_exchange):
                    logger.info(
                        f"Skipping opportunity due to inventory imbalance: "
                        f"A={self.inventory_a:.4f}, B={self.inventory_b:.4f}"
                    )
                    return None

                logger.info(
                    f"💰 Cross-exchange arbitrage found: Buy {best_opportunity.buy_exchange} @ "
                    f"${best_opportunity.buy_price:.2f}, Sell {best_opportunity.sell_exchange} @ "
                    f"${best_opportunity.sell_price:.2f}, Profit: {best_opportunity.profit_pct:.2f}%"
                )

                return Opportunity(
                    pair=self.pair,
                    side=OrderSide.BUY,  # Buy side (we'll handle both sides in execute)
                    entry_price=best_opportunity.buy_price,
                    size=min(self.order_size, best_opportunity.max_volume),
                    expected_profit=best_opportunity.profit_pct,
                    metadata={
                        "opportunity": best_opportunity,
                        "strategy": "cross_exchange_arbitrage"
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Error finding cross-exchange opportunity: {e}")
            return None

    async def execute(self, opportunity: Opportunity) -> bool:
        """
        Execute cross-exchange arbitrage trade.

        Places simultaneous buy and sell orders on both exchanges.

        Args:
            opportunity: Arbitrage opportunity

        Returns:
            True if executed successfully
        """
        arb_opp: ArbitrageOpportunity = opportunity.metadata["opportunity"]

        try:
            # Determine which provider is which
            buy_provider = self.provider_a if arb_opp.buy_exchange == "A" else self.provider_b
            sell_provider = self.provider_b if arb_opp.buy_exchange == "A" else self.provider_a

            logger.info(
                f"Executing cross-exchange arbitrage: "
                f"Buy {opportunity.size:.6f} {self.pair} on {arb_opp.buy_exchange} @ ${arb_opp.buy_price:.2f}, "
                f"Sell on {arb_opp.sell_exchange} @ ${arb_opp.sell_price:.2f}"
            )

            # Place both orders simultaneously using IOC (Immediate-or-Cancel)
            buy_order, sell_order = await asyncio.gather(
                self._place_order(
                    buy_provider,
                    self.pair,
                    OrderSide.BUY,
                    OrderType.IOC,
                    opportunity.size,
                    arb_opp.buy_price * 1.001  # Small buffer for slippage
                ),
                self._place_order(
                    sell_provider,
                    self.pair,
                    OrderSide.SELL,
                    OrderType.IOC,
                    opportunity.size,
                    arb_opp.sell_price * 0.999  # Small buffer for slippage
                ),
                return_exceptions=True
            )

            # Check if both orders succeeded
            buy_success = not isinstance(buy_order, Exception) and buy_order is not None
            sell_success = not isinstance(sell_order, Exception) and sell_order is not None

            if buy_success and sell_success:
                # Update inventory tracking
                if arb_opp.buy_exchange == "A":
                    self.inventory_a += opportunity.size
                    self.inventory_b -= opportunity.size
                else:
                    self.inventory_b += opportunity.size
                    self.inventory_a -= opportunity.size

                logger.info(
                    f"✅ Cross-exchange arbitrage executed successfully. "
                    f"Inventory: A={self.inventory_a:.4f}, B={self.inventory_b:.4f}"
                )

                self.stats.total_trades += 1
                self.stats.winning_trades += 1
                profit = opportunity.size * arb_opp.buy_price * (arb_opp.profit_pct / 100)
                self.stats.total_profit += profit

                return True

            else:
                # Partial fill - need to handle carefully
                logger.warning(
                    f"Partial execution: buy_success={buy_success}, sell_success={sell_success}"
                )

                # Try to reverse the successful order
                if buy_success and not sell_success:
                    logger.warning("Buy succeeded but sell failed - reversing buy")
                    await self._place_order(
                        buy_provider,
                        self.pair,
                        OrderSide.SELL,
                        OrderType.MARKET,
                        opportunity.size,
                        None
                    )
                elif sell_success and not buy_success:
                    logger.warning("Sell succeeded but buy failed - reversing sell")
                    await self._place_order(
                        sell_provider,
                        self.pair,
                        OrderSide.BUY,
                        OrderType.MARKET,
                        opportunity.size,
                        None
                    )

                self.stats.total_trades += 1
                return False

        except Exception as e:
            logger.error(f"Error executing cross-exchange arbitrage: {e}")
            self.stats.total_trades += 1
            return False

    def _check_arbitrage(
        self,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: float,
        sell_price: float,
        buy_volume: float,
        sell_volume: float
    ) -> Optional[ArbitrageOpportunity]:
        """
        Check if arbitrage opportunity exists in given direction.

        Args:
            buy_exchange: Exchange to buy from ("A" or "B")
            sell_exchange: Exchange to sell on ("A" or "B")
            buy_price: Best ask price on buy exchange
            sell_price: Best bid price on sell exchange
            buy_volume: Available volume on buy side
            sell_volume: Available volume on sell side

        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        # Calculate gross spread
        spread_pct = ((sell_price - buy_price) / buy_price) * 100

        # Subtract fees
        total_fee_pct = self.fee_a + self.fee_b
        net_profit_pct = spread_pct - total_fee_pct - self.slippage_tolerance

        # Check if profitable
        if net_profit_pct < self.min_spread_pct:
            return None

        # Calculate max volume
        max_volume = min(buy_volume, sell_volume, self.order_size)

        if max_volume < self.order_size * 0.1:  # At least 10% of target size
            return None

        return ArbitrageOpportunity(
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            pair=self.pair,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_pct=spread_pct,
            profit_pct=net_profit_pct,
            max_volume=max_volume,
            timestamp=0
        )

    def _check_inventory_ok(self, buy_exchange: str) -> bool:
        """
        Check if inventory imbalance is within acceptable limits.

        Prevents excessive inventory buildup on one exchange.

        Args:
            buy_exchange: Exchange we plan to buy on

        Returns:
            True if inventory check passes
        """
        total_inventory = abs(self.inventory_a) + abs(self.inventory_b)

        if total_inventory == 0:
            return True

        # Calculate current imbalance
        if buy_exchange == "A":
            new_inventory_a = self.inventory_a + self.order_size
            imbalance = abs(new_inventory_a - self.inventory_b) / total_inventory
        else:
            new_inventory_b = self.inventory_b + self.order_size
            imbalance = abs(new_inventory_b - self.inventory_a) / total_inventory

        return imbalance <= self.max_imbalance

    async def _fetch_orderbook(self, provider: BaseProvider, pair: str):
        """Fetch orderbook with error handling."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, provider.get_orderbook, pair, 10
            )
        except Exception as e:
            logger.error(f"Error fetching orderbook from {provider.__class__.__name__}: {e}")
            return None

    async def _place_order(
        self,
        provider: BaseProvider,
        pair: str,
        side: OrderSide,
        order_type: OrderType,
        size: float,
        price: Optional[float]
    ):
        """Place order with error handling."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                provider.place_order,
                pair,
                side,
                order_type,
                size,
                price
            )
        except Exception as e:
            logger.error(f"Error placing order on {provider.__class__.__name__}: {e}")
            raise
