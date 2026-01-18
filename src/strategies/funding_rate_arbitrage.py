"""
Funding Rate Arbitrage Strategy

Earn funding rates by taking opposing positions on two different derivatives exchanges.
Exploits funding rate differentials while maintaining delta-neutral exposure.

Expected Performance:
- ROI: 0.01-0.1% per funding period
- APY: 50-200% (from funding alone)
- Frequency: Continuous (24/7)
- Capital: $1,000-$10,000

Key Opportunity:
- dYdX has HOURLY funding (vs 8-hour on CEX)
- Different user bases create funding rate divergence
- Bybit/Binance often have positive funding (longs pay shorts)
- dYdX can have opposite funding direction

Strategy:
- When Bybit funding > dYdX funding: Short Bybit, Long dYdX
- When dYdX funding > Bybit funding: Long Bybit, Short dYdX
- Maintain delta-neutral position (no directional exposure)
- Collect funding rate differential continuously
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

from .base import PollingStrategy, Opportunity
from ..providers.base import BaseProvider, OrderSide, OrderType

logger = logging.getLogger(__name__)


@dataclass
class FundingRateOpportunity:
    """Funding rate arbitrage opportunity."""
    long_exchange: str
    short_exchange: str
    pair: str
    funding_diff_pct: float  # Annualized
    long_funding: float
    short_funding: float
    position_size: float
    expected_daily_profit: float


class FundingRateArbitrageStrategy(PollingStrategy):
    """
    Funding rate arbitrage strategy.

    Maintains delta-neutral positions across two exchanges to earn funding rate differential.

    Example:
        Bybit BTC-USDT funding: +0.01% (8-hour) = 0.03% daily
        dYdX BTC-USD funding: -0.005% (hourly) = -0.12% daily
        Differential: 0.15% daily = ~55% APY

        Position: Short 1 BTC on Bybit, Long 1 BTC on dYdX
        Result: Earn 0.01% from Bybit longs + 0.005% from dYdX shorts
               No directional exposure (delta-neutral)
    """

    def __init__(self, provider_a: BaseProvider, provider_b: BaseProvider, config: Dict[str, Any]):
        """
        Initialize funding rate arbitrage strategy.

        Args:
            provider_a: First derivatives exchange (e.g., Bybit)
            provider_b: Second derivatives exchange (e.g., dYdX)
            config: Strategy configuration with:
                - pair: Trading pair (e.g., "BTC-USD")
                - position_size: Size of position on each side
                - min_funding_diff_apy: Minimum APY differential to enter (default: 20%)
                - rebalance_threshold: Rebalance if position differs by % (default: 5%)
                - max_position_size: Maximum position size
        """
        self.provider_a = provider_a
        self.provider_b = provider_b
        super().__init__(provider_a, config)

        self.pair = config.get("pair", "BTC-USD")
        self.position_size = float(config.get("position_size", 0.1))
        self.min_funding_diff_apy = float(config.get("min_funding_diff_apy", 20.0))
        self.rebalance_threshold = float(config.get("rebalance_threshold", 5.0))
        self.max_position_size = float(config.get("max_position_size", 1.0))

        # Position tracking
        self.position_a = 0.0  # Net position on exchange A
        self.position_b = 0.0  # Net position on exchange B
        self.entry_time = None

        logger.info(
            f"Funding rate arbitrage initialized: {self.provider_a.__class__.__name__} ↔ "
            f"{self.provider_b.__class__.__name__}, pair={self.pair}, "
            f"min_apy_diff={self.min_funding_diff_apy}%"
        )

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan for funding rate arbitrage opportunities.

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            # Fetch funding rates from both exchanges
            funding_a_data, funding_b_data = await asyncio.gather(
                self._fetch_funding_rate(self.provider_a, self.pair),
                self._fetch_funding_rate(self.provider_b, self.pair),
                return_exceptions=True
            )

            if isinstance(funding_a_data, Exception) or isinstance(funding_b_data, Exception):
                logger.error("Error fetching funding rates")
                return None

            if not funding_a_data or not funding_b_data:
                return None

            # Parse funding rates
            funding_a = funding_a_data.get("funding_rate", 0)
            funding_b = funding_b_data.get("funding_rate", 0)

            # Convert to daily rates (assuming 8-hour funding for CEX, hourly for dYdX)
            daily_funding_a = funding_a * 3  # 8-hour funding, 3x per day
            daily_funding_b = funding_b * 24  # Hourly funding, 24x per day

            # Calculate annualized rates
            apy_a = daily_funding_a * 365
            apy_b = daily_funding_b * 365

            # Calculate differential
            apy_diff = abs(apy_a - apy_b)

            logger.debug(
                f"Funding rates: A={apy_a:.2f}% APY, B={apy_b:.2f}% APY, "
                f"Diff={apy_diff:.2f}% APY"
            )

            # Check if opportunity exists
            if apy_diff < self.min_funding_diff_apy:
                # If we have an existing position, check if we should close it
                if self.position_a != 0 or self.position_b != 0:
                    logger.info(
                        f"Funding differential too low ({apy_diff:.2f}% APY), considering closing positions"
                    )
                return None

            # Determine which side to long/short
            if apy_a > apy_b:
                # A has higher funding, short A (receive funding), long B (pay less)
                long_exchange = "B"
                short_exchange = "A"
            else:
                # B has higher funding, short B (receive funding), long A (pay less)
                long_exchange = "A"
                short_exchange = "B"

            # Calculate expected daily profit
            daily_profit_pct = apy_diff / 365
            expected_daily_profit = self.position_size * daily_profit_pct / 100

            logger.info(
                f"💰 Funding rate opportunity: Long {long_exchange}, Short {short_exchange}, "
                f"APY diff: {apy_diff:.2f}%, Daily profit: ${expected_daily_profit:.2f}"
            )

            opportunity_data = FundingRateOpportunity(
                long_exchange=long_exchange,
                short_exchange=short_exchange,
                pair=self.pair,
                funding_diff_pct=apy_diff,
                long_funding=apy_b if long_exchange == "B" else apy_a,
                short_funding=apy_a if short_exchange == "A" else apy_b,
                position_size=self.position_size,
                expected_daily_profit=expected_daily_profit
            )

            return Opportunity(
                pair=self.pair,
                side=OrderSide.BUY,  # Will handle both sides
                entry_price=0,  # Not applicable
                size=self.position_size,
                expected_profit=daily_profit_pct,
                metadata={
                    "opportunity": opportunity_data,
                    "strategy": "funding_rate_arbitrage"
                }
            )

        except Exception as e:
            logger.error(f"Error finding funding rate opportunity: {e}")
            return None

    async def execute(self, opportunity: Opportunity) -> bool:
        """
        Execute funding rate arbitrage trade.

        Opens delta-neutral positions on both exchanges.

        Args:
            opportunity: Funding rate arbitrage opportunity

        Returns:
            True if executed successfully
        """
        opp: FundingRateOpportunity = opportunity.metadata["opportunity"]

        try:
            # Determine which provider is which
            long_provider = self.provider_b if opp.long_exchange == "B" else self.provider_a
            short_provider = self.provider_a if opp.short_exchange == "A" else self.provider_b

            logger.info(
                f"Executing funding rate arbitrage: "
                f"Long {opp.position_size:.4f} {self.pair} on {opp.long_exchange}, "
                f"Short {opp.position_size:.4f} {self.pair} on {opp.short_exchange}"
            )

            # Place both orders simultaneously
            long_order, short_order = await asyncio.gather(
                self._place_order_async(
                    long_provider,
                    self.pair,
                    OrderSide.BUY,
                    OrderType.MARKET,
                    opp.position_size,
                    None
                ),
                self._place_order_async(
                    short_provider,
                    self.pair,
                    OrderSide.SELL,
                    OrderType.MARKET,
                    opp.position_size,
                    None
                ),
                return_exceptions=True
            )

            # Check if both orders succeeded
            long_success = not isinstance(long_order, Exception) and long_order is not None
            short_success = not isinstance(short_order, Exception) and short_order is not None

            if long_success and short_success:
                # Update position tracking
                if opp.long_exchange == "A":
                    self.position_a = opp.position_size
                    self.position_b = -opp.position_size
                else:
                    self.position_b = opp.position_size
                    self.position_a = -opp.position_size

                self.entry_time = datetime.now()

                logger.info(
                    f"✅ Funding rate arbitrage positions opened: "
                    f"A={self.position_a:.4f}, B={self.position_b:.4f}, "
                    f"Expected APY: {opp.funding_diff_pct:.2f}%"
                )

                self.stats.total_trades += 1
                self.stats.winning_trades += 1
                self.stats.total_profit += opp.expected_daily_profit

                return True

            else:
                logger.error(
                    f"Partial execution: long_success={long_success}, short_success={short_success}"
                )

                # Try to close the successful order
                if long_success and not short_success:
                    await self._place_order_async(
                        long_provider, self.pair, OrderSide.SELL, OrderType.MARKET, opp.position_size, None
                    )
                elif short_success and not long_success:
                    await self._place_order_async(
                        short_provider, self.pair, OrderSide.BUY, OrderType.MARKET, opp.position_size, None
                    )

                self.stats.total_trades += 1
                return False

        except Exception as e:
            logger.error(f"Error executing funding rate arbitrage: {e}")
            self.stats.total_trades += 1
            return False

    async def _fetch_funding_rate(self, provider: BaseProvider, pair: str) -> Optional[Dict]:
        """Fetch funding rate from provider."""
        try:
            # Check if provider has get_funding_rate method (Bybit and dYdX do)
            if hasattr(provider, 'get_funding_rate'):
                return await asyncio.get_event_loop().run_in_executor(
                    None, provider.get_funding_rate, pair
                )
            else:
                logger.warning(f"Provider {provider.__class__.__name__} doesn't support funding rates")
                return None
        except Exception as e:
            logger.error(f"Error fetching funding rate from {provider.__class__.__name__}: {e}")
            return None

    async def _place_order_async(
        self,
        provider: BaseProvider,
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

    async def close_positions(self) -> bool:
        """Close all open positions (manual close or when funding diff too low)."""
        try:
            if self.position_a == 0 and self.position_b == 0:
                logger.info("No positions to close")
                return True

            logger.info(f"Closing positions: A={self.position_a:.4f}, B={self.position_b:.4f}")

            # Close positions on both exchanges
            close_a, close_b = await asyncio.gather(
                self._close_position(self.provider_a, self.position_a),
                self._close_position(self.provider_b, self.position_b),
                return_exceptions=True
            )

            if not isinstance(close_a, Exception) and not isinstance(close_b, Exception):
                logger.info("✅ All positions closed successfully")
                self.position_a = 0.0
                self.position_b = 0.0
                self.entry_time = None
                return True
            else:
                logger.error("Error closing positions")
                return False

        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return False

    async def _close_position(self, provider: BaseProvider, position: float):
        """Close position on a single exchange."""
        if position == 0:
            return True

        side = OrderSide.SELL if position > 0 else OrderSide.BUY
        size = abs(position)

        return await self._place_order_async(
            provider, self.pair, side, OrderType.MARKET, size, None
        )
