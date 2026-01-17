"""
High-Probability Bond Strategy for Polymarket.

Strategy: Buy near-certain outcomes (>95% probability) close to resolution
Returns: 1-5% per trade, ~1800% annualized when compounded
Risk: Low (high confidence, short duration)

Based on proven Polymarket strategy from 2025:
- Target markets priced at 95 cents or higher
- Resolution must be close (within hours/days)
- Earn spread between entry price and $1.00 payout

Example:
- Buy YES token at $0.97 (97% probability)
- Market resolves YES → Receive $1.00
- Profit: $0.03 per share (3.1% return)
- If done daily: ~1800% annualized

Reference: https://www.chaincatcher.com/en/article/2233047
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .base import PollingStrategy, Opportunity, TradeResult
from ..providers.base import BaseProvider, OrderSide, OrderType


logger = logging.getLogger(__name__)


class HighProbabilityBondStrategy(PollingStrategy):
    """
    High-Probability Bond Strategy for Polymarket.

    Targets near-certain outcomes with imminent resolution for low-risk returns.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: Dict[str, Any],
        name: Optional[str] = None
    ):
        """
        Initialize high-probability bond strategy.

        Args:
            provider: Trading provider (Polymarket)
            config: Strategy configuration with:
                - min_probability: Minimum probability to enter (default: 0.95)
                - max_probability: Maximum probability to enter (default: 0.99)
                - max_hours_to_resolution: Max hours until market closes (default: 48)
                - order_size: Number of tokens to buy
                - order_type: FOK, GTC, etc.
                - scan_interval: Seconds between scans (default: 60)
                - min_expected_return: Minimum expected return % (default: 1.0)
                - market_categories: Categories to scan (default: ["crypto", "politics", "sports"])
            name: Optional custom name
        """
        super().__init__(provider, config, name or "HighProbabilityBond")

        # Strategy-specific config
        self.min_probability = config.get("min_probability", 0.95)
        self.max_probability = config.get("max_probability", 0.99)
        self.max_hours_to_resolution = config.get("max_hours_to_resolution", 48)
        self.order_size = config.get("order_size", 100.0)
        self.order_type_str = config.get("order_type", "FOK")
        self.min_expected_return = config.get("min_expected_return", 1.0)  # 1%
        self.market_categories = config.get("market_categories", ["crypto", "politics", "sports"])

        # Map string to OrderType enum
        order_type_map = {
            "FOK": OrderType.FOK,
            "GTC": OrderType.GTC,
            "IOC": OrderType.IOC,
        }
        self.order_type = order_type_map.get(self.order_type_str.upper(), OrderType.FOK)

        # Track entered positions
        self.active_positions: List[Dict[str, Any]] = []

        self.logger.info(f"High-Probability Bond configured:")
        self.logger.info(f"  Probability range: {self.min_probability:.1%} - {self.max_probability:.1%}")
        self.logger.info(f"  Max hours to resolution: {self.max_hours_to_resolution}h")
        self.logger.info(f"  Min expected return: {self.min_expected_return:.1%}")
        self.logger.info(f"  Order size: {self.order_size} shares")

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan Polymarket for high-probability markets near resolution.

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            # Get available markets
            # Note: This requires the provider to implement get_markets() method
            if not hasattr(self.provider, 'get_markets'):
                self.logger.warning("Provider does not support get_markets()")
                return None

            markets = self.provider.get_markets(categories=self.market_categories)

            best_opportunity = None
            best_expected_return = self.min_expected_return / 100.0

            for market in markets:
                # Check if market is near resolution
                if not self._is_near_resolution(market):
                    continue

                # Get market orderbook
                # For binary markets, we check both YES and NO sides
                if market.get("type") == "binary":
                    yes_token_id = market.get("yes_token_id")
                    no_token_id = market.get("no_token_id")

                    if not yes_token_id or not no_token_id:
                        continue

                    # Check YES side
                    yes_opportunity = await self._check_token_opportunity(
                        market, yes_token_id, "YES"
                    )
                    if yes_opportunity:
                        expected_return = yes_opportunity.expected_profit / (
                            yes_opportunity.metadata["entry_price"] * self.order_size
                        )
                        if expected_return > best_expected_return:
                            best_expected_return = expected_return
                            best_opportunity = yes_opportunity

                    # Check NO side
                    no_opportunity = await self._check_token_opportunity(
                        market, no_token_id, "NO"
                    )
                    if no_opportunity:
                        expected_return = no_opportunity.expected_profit / (
                            no_opportunity.metadata["entry_price"] * self.order_size
                        )
                        if expected_return > best_expected_return:
                            best_expected_return = expected_return
                            best_opportunity = no_opportunity

            return best_opportunity

        except Exception as e:
            self.logger.error(f"Error finding opportunity: {e}", exc_info=True)
            return None

    async def _check_token_opportunity(
        self, market: Dict[str, Any], token_id: str, side: str
    ) -> Optional[Opportunity]:
        """
        Check if a specific token presents a high-probability bond opportunity.

        Args:
            market: Market data
            token_id: Token ID to check
            side: "YES" or "NO"

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            orderbook = self.provider.get_orderbook(token_id, depth=10)

            if not orderbook.best_ask:
                return None

            price = orderbook.best_ask.price
            probability = price  # In prediction markets, price = probability

            # Check probability range
            if probability < self.min_probability or probability > self.max_probability:
                return None

            # Check liquidity
            if orderbook.best_ask.volume < self.order_size:
                return None

            # Calculate expected return
            profit_per_share = 1.0 - price
            expected_profit = profit_per_share * self.order_size
            expected_return_pct = (profit_per_share / price) * 100

            # Check minimum return
            if expected_return_pct < self.min_expected_return:
                return None

            # Calculate annualized return (approximate)
            hours_to_resolution = self._hours_until_resolution(market)
            if hours_to_resolution > 0:
                periods_per_year = (365 * 24) / hours_to_resolution
                annualized_return = ((1 + profit_per_share / price) ** periods_per_year - 1) * 100
            else:
                annualized_return = 0.0

            # Create opportunity
            opportunity = Opportunity(
                strategy_name=self.name,
                timestamp=int(time.time() * 1000),
                confidence=probability,
                expected_profit=expected_profit,
                metadata={
                    "market_id": market.get("id"),
                    "market_name": market.get("name"),
                    "token_id": token_id,
                    "side": side,
                    "entry_price": price,
                    "probability": probability,
                    "profit_per_share": profit_per_share,
                    "expected_return_pct": expected_return_pct,
                    "annualized_return_pct": annualized_return,
                    "hours_to_resolution": hours_to_resolution,
                    "resolution_time": market.get("end_date"),
                    "order_size": self.order_size,
                }
            )

            self.logger.info(
                f"📊 Found high-probability bond: {market.get('name')} - "
                f"{side} @ {price:.2%} → {expected_return_pct:.2f}% return "
                f"(~{annualized_return:.0f}% annualized)"
            )

            return opportunity

        except Exception as e:
            self.logger.error(f"Error checking token opportunity: {e}", exc_info=True)
            return None

    def _is_near_resolution(self, market: Dict[str, Any]) -> bool:
        """
        Check if market is close to resolution.

        Args:
            market: Market data with end_date

        Returns:
            True if market resolves within max_hours_to_resolution
        """
        try:
            end_date = market.get("end_date")
            if not end_date:
                return False

            # Parse end_date (format may vary by provider)
            if isinstance(end_date, str):
                # Try parsing ISO format
                try:
                    end_time = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except:
                    # Try parsing Unix timestamp
                    try:
                        end_time = datetime.fromtimestamp(int(end_date))
                    except:
                        return False
            elif isinstance(end_date, (int, float)):
                # Unix timestamp
                end_time = datetime.fromtimestamp(end_date)
            else:
                return False

            # Check if within time window
            now = datetime.now()
            hours_until = (end_time - now).total_seconds() / 3600

            return 0 < hours_until <= self.max_hours_to_resolution

        except Exception as e:
            self.logger.error(f"Error checking resolution time: {e}")
            return False

    def _hours_until_resolution(self, market: Dict[str, Any]) -> float:
        """
        Get hours until market resolution.

        Args:
            market: Market data

        Returns:
            Hours until resolution, 0 if unknown or past
        """
        try:
            end_date = market.get("end_date")
            if not end_date:
                return 0.0

            if isinstance(end_date, str):
                try:
                    end_time = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except:
                    try:
                        end_time = datetime.fromtimestamp(int(end_date))
                    except:
                        return 0.0
            elif isinstance(end_date, (int, float)):
                end_time = datetime.fromtimestamp(end_date)
            else:
                return 0.0

            now = datetime.now()
            hours = (end_time - now).total_seconds() / 3600

            return max(0.0, hours)

        except Exception as e:
            self.logger.error(f"Error calculating hours: {e}")
            return 0.0

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute high-probability bond trade.

        Args:
            opportunity: Bond opportunity

        Returns:
            TradeResult with execution details
        """
        metadata = opportunity.metadata

        token_id = metadata["token_id"]
        side = metadata["side"]
        price = metadata["entry_price"]
        order_size = metadata["order_size"]
        market_name = metadata["market_name"]

        self.logger.info("=" * 70)
        self.logger.info("🎯 EXECUTING HIGH-PROBABILITY BOND")
        self.logger.info("=" * 70)
        self.logger.info(f"Market:          {market_name}")
        self.logger.info(f"Side:            {side}")
        self.logger.info(f"Entry price:     ${price:.4f} ({metadata['probability']:.2%} probability)")
        self.logger.info(f"Order size:      {order_size} shares")
        self.logger.info(f"Expected return: {metadata['expected_return_pct']:.2f}%")
        self.logger.info(f"Annualized:      ~{metadata['annualized_return_pct']:.0f}%")
        self.logger.info(f"Time to resolution: {metadata['hours_to_resolution']:.1f}h")
        self.logger.info("=" * 70)

        if self.dry_run:
            self.logger.info("🔸 DRY RUN MODE - No real orders placed")
            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,
                orders=[],
            )

        try:
            # Place order
            self.logger.info(f"📤 Placing {side} order: BUY {order_size} @ ${price:.4f}")
            order = self.provider.place_order(
                pair=token_id,
                side=OrderSide.BUY,
                order_type=self.order_type,
                size=order_size,
                price=price,
            )

            self.logger.info(f"✅ Order placed: {order.order_id}")

            # For FOK orders, verify fill
            if self.order_type == OrderType.FOK:
                await asyncio.sleep(1.0)
                order_status = self.provider.get_order(order.order_id)

                if order_status.is_complete:
                    self.logger.info("✅ Order filled successfully")

                    # Track position
                    self.active_positions.append({
                        "market_id": metadata["market_id"],
                        "market_name": market_name,
                        "token_id": token_id,
                        "side": side,
                        "entry_price": price,
                        "shares": order_size,
                        "entry_time": datetime.now(),
                        "resolution_time": metadata["resolution_time"],
                        "expected_profit": opportunity.expected_profit,
                    })

                    return TradeResult(
                        opportunity=opportunity,
                        success=True,
                        actual_profit=opportunity.expected_profit,
                        orders=[order],
                    )
                else:
                    self.logger.warning("⚠️ Order not filled")
                    return TradeResult(
                        opportunity=opportunity,
                        success=False,
                        orders=[order],
                        error="Order not filled"
                    )

            # For GTC/IOC, assume success
            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,
                orders=[order],
            )

        except Exception as e:
            self.logger.error(f"Error executing bond: {e}", exc_info=True)
            return TradeResult(
                opportunity=opportunity,
                success=False,
                error=str(e)
            )

    def get_active_positions(self) -> List[Dict[str, Any]]:
        """
        Get list of active bond positions.

        Returns:
            List of position dictionaries
        """
        return self.active_positions

    def print_positions(self):
        """Print active positions to console."""
        if not self.active_positions:
            self.logger.info("No active bond positions")
            return

        self.logger.info("\n" + "=" * 70)
        self.logger.info("📊 ACTIVE BOND POSITIONS")
        self.logger.info("=" * 70)

        total_invested = 0.0
        total_expected_profit = 0.0

        for pos in self.active_positions:
            invested = pos["entry_price"] * pos["shares"]
            total_invested += invested
            total_expected_profit += pos["expected_profit"]

            hours_remaining = (
                (pos["resolution_time"] - datetime.now()).total_seconds() / 3600
                if isinstance(pos["resolution_time"], datetime)
                else 0.0
            )

            self.logger.info(f"\n{pos['market_name']}")
            self.logger.info(f"  Side: {pos['side']}")
            self.logger.info(f"  Entry: ${pos['entry_price']:.4f} × {pos['shares']} shares")
            self.logger.info(f"  Invested: ${invested:.2f}")
            self.logger.info(f"  Expected profit: ${pos['expected_profit']:.2f}")
            self.logger.info(f"  Time remaining: {hours_remaining:.1f}h")

        self.logger.info("\n" + "-" * 70)
        self.logger.info(f"Total invested: ${total_invested:.2f}")
        self.logger.info(f"Total expected profit: ${total_expected_profit:.2f}")
        self.logger.info(f"Expected return: {(total_expected_profit / total_invested * 100):.2f}%")
        self.logger.info("=" * 70 + "\n")
