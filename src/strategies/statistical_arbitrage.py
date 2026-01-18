"""
Statistical Arbitrage Strategy (Mean Reversion)

Trade price deviations from historical mean across multiple exchanges.
When one exchange diverges significantly, trade expecting convergence.

Expected Performance:
- ROI: 0.5-2% per convergence
- Frequency: 3-10 opportunities per day
- Capital: $1,000-$5,000

Key Concept:
- BTC price across exchanges is correlated
- Temporary deviations occur due to liquidity/demand differences
- Prices tend to revert to mean (arbitrageurs close gaps)
- Coinbase often trades at premium during US hours
- Statistical measures (z-score) identify significant deviations

Strategy:
- Track price across Binance, Coinbase, Kraken
- Calculate z-score for each exchange vs group mean
- When z-score > 2: Price is abnormally high, short that exchange, long others
- When z-score < -2: Price is abnormally low, long that exchange, short others
- Exit when prices converge (z-score returns to normal range)
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dataclasses import dataclass
from collections import deque
import statistics

from .base import PollingStrategy, Opportunity
from ..providers.base import BaseProvider, OrderSide, OrderType

logger = logging.getLogger(__name__)


@dataclass
class PriceDeviation:
    """Price deviation from mean."""
    exchange: str
    price: float
    mean_price: float
    deviation_pct: float
    z_score: float


class StatisticalArbitrageStrategy(PollingStrategy):
    """
    Statistical arbitrage strategy using mean reversion.

    Tracks price across multiple exchanges and trades when price deviates
    significantly from the group mean.

    Example:
        Binance: $43,000
        Coinbase: $43,600 (z-score: 2.5 - abnormally high)
        Kraken: $43,100

        Mean: $43,233
        Action: Short Coinbase, Long Binance
        Exit: When Coinbase drops to ~$43,200 (convergence)
        Profit: $400 per BTC = 0.9%
    """

    def __init__(self, providers: List[BaseProvider], config: Dict[str, Any]):
        """
        Initialize statistical arbitrage strategy.

        Args:
            providers: List of providers to track (e.g., [Binance, Coinbase, Kraken])
            config: Strategy configuration with:
                - pair: Trading pair (must exist on all exchanges)
                - min_z_score: Minimum z-score to trade (default: 2.0)
                - position_size: Size per trade
                - lookback_window: Number of price points for statistics (default: 20)
                - exit_z_score: Z-score to exit position (default: 0.5)
        """
        if len(providers) < 2:
            raise ValueError("Statistical arbitrage requires at least 2 providers")

        self.providers = providers
        super().__init__(providers[0], config)

        self.pair = config.get("pair", "BTCUSDT")
        self.min_z_score = float(config.get("min_z_score", 2.0))
        self.position_size = float(config.get("position_size", 0.1))
        self.lookback_window = int(config.get("lookback_window", 20))
        self.exit_z_score = float(config.get("exit_z_score", 0.5))

        # Price history for each exchange
        self.price_history: Dict[str, deque] = {
            provider.__class__.__name__: deque(maxlen=self.lookback_window)
            for provider in self.providers
        }

        # Active positions
        self.active_positions: Dict[str, float] = {}  # Exchange -> Position size

        logger.info(
            f"Statistical arbitrage initialized with {len(self.providers)} exchanges, "
            f"min_z_score={self.min_z_score}, lookback={self.lookback_window}"
        )

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan for statistical arbitrage opportunities.

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            # Fetch current prices from all exchanges
            prices = await self._fetch_all_prices()

            if not prices or len(prices) < 2:
                return None

            # Update price history
            for exchange, price in prices.items():
                self.price_history[exchange].append(price)

            # Need enough history for statistical significance
            if any(len(hist) < self.lookback_window for hist in self.price_history.values()):
                logger.debug("Not enough price history yet")
                return None

            # Calculate mean and standard deviation across exchanges
            current_prices = list(prices.values())
            mean_price = statistics.mean(current_prices)
            std_dev = statistics.stdev(current_prices) if len(current_prices) > 1 else 0

            if std_dev == 0:
                return None

            # Calculate z-scores for each exchange
            deviations = []
            for exchange, price in prices.items():
                z_score = (price - mean_price) / std_dev
                deviation_pct = ((price - mean_price) / mean_price) * 100

                deviations.append(PriceDeviation(
                    exchange=exchange,
                    price=price,
                    mean_price=mean_price,
                    deviation_pct=deviation_pct,
                    z_score=z_score
                ))

            # Find extreme deviations
            for dev in deviations:
                logger.debug(
                    f"{dev.exchange}: ${dev.price:.2f}, z-score={dev.z_score:.2f}, "
                    f"deviation={dev.deviation_pct:.2f}%"
                )

                # Check if we should enter a new position
                if abs(dev.z_score) >= self.min_z_score and dev.exchange not in self.active_positions:
                    # Price is abnormally high - short it
                    if dev.z_score > 0:
                        logger.info(
                            f"📊 Statistical arbitrage: {dev.exchange} abnormally HIGH "
                            f"(z={dev.z_score:.2f}), shorting"
                        )

                        return Opportunity(
                            pair=self.pair,
                            side=OrderSide.SELL,
                            entry_price=dev.price,
                            size=self.position_size,
                            expected_profit=abs(dev.deviation_pct),
                            metadata={
                                "deviation": dev,
                                "strategy": "statistical_arbitrage",
                                "action": "short"
                            }
                        )

                    # Price is abnormally low - long it
                    else:
                        logger.info(
                            f"📊 Statistical arbitrage: {dev.exchange} abnormally LOW "
                            f"(z={dev.z_score:.2f}), longing"
                        )

                        return Opportunity(
                            pair=self.pair,
                            side=OrderSide.BUY,
                            entry_price=dev.price,
                            size=self.position_size,
                            expected_profit=abs(dev.deviation_pct),
                            metadata={
                                "deviation": dev,
                                "strategy": "statistical_arbitrage",
                                "action": "long"
                            }
                        )

            # Check if we should exit existing positions
            await self._check_exit_positions(prices, mean_price, std_dev)

            return None

        except Exception as e:
            logger.error(f"Error finding statistical arbitrage opportunity: {e}")
            return None

    async def execute(self, opportunity: Opportunity) -> bool:
        """
        Execute statistical arbitrage trade.

        Args:
            opportunity: Statistical arbitrage opportunity

        Returns:
            True if executed successfully
        """
        dev: PriceDeviation = opportunity.metadata["deviation"]
        action = opportunity.metadata["action"]

        try:
            # Find the provider for this exchange
            provider = next(
                (p for p in self.providers if p.__class__.__name__ == dev.exchange),
                None
            )

            if not provider:
                logger.error(f"Provider not found for {dev.exchange}")
                return False

            logger.info(
                f"Executing statistical arbitrage: {action.upper()} {opportunity.size:.4f} "
                f"{self.pair} on {dev.exchange} @ ${dev.price:.2f}"
            )

            # Place order
            order = await self._place_order_async(
                provider,
                self.pair,
                opportunity.side,
                OrderType.MARKET,
                opportunity.size,
                None
            )

            if order:
                # Track position
                position_value = opportunity.size if action == "long" else -opportunity.size
                self.active_positions[dev.exchange] = position_value

                logger.info(
                    f"✅ Statistical arbitrage position opened: {dev.exchange} "
                    f"position={position_value:.4f}"
                )

                self.stats.total_trades += 1
                return True
            else:
                self.stats.total_trades += 1
                return False

        except Exception as e:
            logger.error(f"Error executing statistical arbitrage: {e}")
            self.stats.total_trades += 1
            return False

    async def _check_exit_positions(
        self,
        current_prices: Dict[str, float],
        mean_price: float,
        std_dev: float
    ):
        """Check if any positions should be closed (mean reversion occurred)."""
        for exchange, position in list(self.active_positions.items()):
            if exchange not in current_prices:
                continue

            current_price = current_prices[exchange]
            z_score = (current_price - mean_price) / std_dev if std_dev > 0 else 0

            # Exit if z-score has reverted to normal range
            if abs(z_score) <= self.exit_z_score:
                logger.info(
                    f"Closing position on {exchange}: z-score reverted to {z_score:.2f}"
                )

                # Find provider
                provider = next(
                    (p for p in self.providers if p.__class__.__name__ == exchange),
                    None
                )

                if provider:
                    # Close position (reverse the original trade)
                    side = OrderSide.SELL if position > 0 else OrderSide.BUY
                    size = abs(position)

                    order = await self._place_order_async(
                        provider, self.pair, side, OrderType.MARKET, size, None
                    )

                    if order:
                        logger.info(f"✅ Position closed on {exchange}")
                        del self.active_positions[exchange]
                        self.stats.winning_trades += 1

    async def _fetch_all_prices(self) -> Dict[str, float]:
        """Fetch current prices from all exchanges."""
        prices = {}

        tasks = []
        for provider in self.providers:
            tasks.append(self._fetch_price(provider))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for provider, result in zip(self.providers, results):
            if not isinstance(result, Exception) and result is not None:
                prices[provider.__class__.__name__] = result

        return prices

    async def _fetch_price(self, provider: BaseProvider) -> Optional[float]:
        """Fetch current price from a single exchange."""
        try:
            if hasattr(provider, 'get_ticker_price'):
                return await asyncio.get_event_loop().run_in_executor(
                    None, provider.get_ticker_price, self.pair
                )
            else:
                # Fallback to orderbook mid price
                orderbook = await asyncio.get_event_loop().run_in_executor(
                    None, provider.get_orderbook, self.pair, 1
                )
                return orderbook.mid_price if orderbook else None
        except Exception as e:
            logger.error(f"Error fetching price from {provider.__class__.__name__}: {e}")
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
            return None
