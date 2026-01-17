"""
Momentum Trading Strategy.

Strategy: Follow strong price trends in prediction markets
Returns: Variable (5-30% per trade in trending markets)
Risk: Medium (requires quick exits, stop losses)

How it works:
1. Detect strong momentum in one direction
2. Enter position following the trend
3. Exit when momentum weakens or reverses
4. Use stop-loss to limit downside

Example (Polymarket):
- Trump odds moving: 45% → 55% → 65% in 1 hour
- Enter LONG at 65%
- Momentum continues: 65% → 75%
- Exit at 75%
- Profit: 10 percentage points

Indicators used:
- Price velocity (rate of change)
- Volume surge detection
- Moving average crossovers

Reference: Successful Polymarket traders focus on momentum
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Deque
from collections import deque
from dataclasses import dataclass

from .base import EventDrivenStrategy, Opportunity, TradeResult
from ..providers.base import BaseProvider, OrderSide, OrderType, Orderbook


logger = logging.getLogger(__name__)


@dataclass
class PricePoint:
    """Price data point for momentum calculation."""
    timestamp: float
    price: float
    volume: float = 0.0


class MomentumTradingStrategy(EventDrivenStrategy):
    """
    Momentum trading strategy for prediction markets.

    Follows strong price trends with momentum indicators.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: Dict[str, Any],
        market_pair: str,
        name: Optional[str] = None
    ):
        """
        Initialize momentum trading strategy.

        Args:
            provider: Trading provider
            config: Strategy configuration with:
                - lookback_period: Periods for momentum calculation (default: 20)
                - momentum_threshold: Min % change to trigger (default: 5.0)
                - volume_surge_multiplier: Volume surge detection (default: 2.0)
                - ma_fast: Fast moving average period (default: 5)
                - ma_slow: Slow moving average period (default: 20)
                - stop_loss_pct: Stop loss percentage (default: 3.0)
                - take_profit_pct: Take profit percentage (default: 15.0)
                - order_size: Position size
                - max_positions: Maximum concurrent positions (default: 3)
                - scan_interval: Seconds between scans (default: 10)
            market_pair: Trading pair or token ID
            name: Optional custom name
        """
        super().__init__(provider, config, name or "MomentumTrading")

        self.market_pair = market_pair

        # Strategy-specific config
        self.lookback_period = config.get("lookback_period", 20)
        self.momentum_threshold = config.get("momentum_threshold", 5.0)  # 5% move
        self.volume_surge_multiplier = config.get("volume_surge_multiplier", 2.0)
        self.ma_fast = config.get("ma_fast", 5)
        self.ma_slow = config.get("ma_slow", 20)
        self.stop_loss_pct = config.get("stop_loss_pct", 3.0)
        self.take_profit_pct = config.get("take_profit_pct", 15.0)
        self.order_size = config.get("order_size", 100.0)
        self.max_positions = config.get("max_positions", 3)

        # Price history
        self.price_history: Deque[PricePoint] = deque(maxlen=max(self.lookback_period, self.ma_slow) * 2)

        # Active positions
        self.positions: List[Dict[str, Any]] = []

        self.logger.info(f"Momentum trading configured:")
        self.logger.info(f"  Market: {self.market_pair}")
        self.logger.info(f"  Momentum threshold: {self.momentum_threshold}%")
        self.logger.info(f"  Lookback period: {self.lookback_period}")
        self.logger.info(f"  MA: {self.ma_fast}/{self.ma_slow}")
        self.logger.info(f"  Stop loss: {self.stop_loss_pct}%")
        self.logger.info(f"  Take profit: {self.take_profit_pct}%")
        self.logger.info(f"  Max positions: {self.max_positions}")

    async def run(self):
        """
        Main momentum trading loop.

        Monitors price action and manages positions.
        """
        self.logger.info(f"🚀 Starting momentum trading on {self.market_pair}")

        while self.running:
            try:
                # Get current orderbook
                orderbook = self.provider.get_orderbook(self.market_pair, depth=10)

                # Update price history
                if orderbook.best_bid and orderbook.best_ask:
                    mid_price = (orderbook.best_bid.price + orderbook.best_ask.price) / 2
                    volume = orderbook.best_bid.volume + orderbook.best_ask.volume

                    self.price_history.append(PricePoint(
                        timestamp=time.time(),
                        price=mid_price,
                        volume=volume
                    ))

                # Check for momentum signals (only if we have enough history)
                if len(self.price_history) >= self.lookback_period:
                    opportunity = await self._detect_momentum()
                    if opportunity and len(self.positions) < self.max_positions:
                        should_execute, reason = self.should_execute(opportunity)
                        if should_execute:
                            result = await self._execute_with_tracking(opportunity)

                # Manage existing positions
                await self._manage_positions(orderbook)

                # Wait before next scan
                await asyncio.sleep(self.scan_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in momentum loop: {e}", exc_info=True)
                await asyncio.sleep(5)

        # Close all positions on stop
        await self._close_all_positions()
        self.logger.info("Momentum trading stopped")

    async def _detect_momentum(self) -> Optional[Opportunity]:
        """
        Detect momentum using multiple indicators.

        Returns:
            Opportunity if strong momentum detected, None otherwise
        """
        try:
            if len(self.price_history) < self.lookback_period:
                return None

            current_price = self.price_history[-1].price
            old_price = self.price_history[-self.lookback_period].price

            # Calculate price change
            price_change = current_price - old_price
            price_change_pct = (price_change / old_price) * 100

            # Check momentum threshold
            if abs(price_change_pct) < self.momentum_threshold:
                return None

            # Determine direction
            direction = "LONG" if price_change > 0 else "SHORT"

            # Check moving average crossover
            if not self._check_ma_crossover(direction):
                self.logger.debug(f"MA crossover not confirmed for {direction}")
                return None

            # Check volume surge
            volume_surge = self._check_volume_surge()

            # Calculate confidence based on indicators
            confidence = 0.5  # Base confidence

            # Strong momentum adds confidence
            if abs(price_change_pct) > self.momentum_threshold * 1.5:
                confidence += 0.2

            # Volume surge adds confidence
            if volume_surge:
                confidence += 0.2
                self.logger.info(f"📊 Volume surge detected ({volume_surge:.1f}x normal)")

            # MA alignment adds confidence
            if self._check_ma_alignment(direction):
                confidence += 0.1

            confidence = min(1.0, confidence)

            # Calculate expected profit (estimate based on recent moves)
            avg_move = self._calculate_average_move()
            expected_move_pct = min(avg_move * 1.5, self.take_profit_pct)  # Conservative estimate
            expected_profit = (expected_move_pct / 100) * current_price * self.order_size

            # Create opportunity
            opportunity = Opportunity(
                strategy_name=self.name,
                timestamp=int(time.time() * 1000),
                confidence=confidence,
                expected_profit=expected_profit,
                metadata={
                    "market_pair": self.market_pair,
                    "direction": direction,
                    "entry_price": current_price,
                    "price_change_pct": price_change_pct,
                    "volume_surge": volume_surge,
                    "stop_loss": current_price * (1 - self.stop_loss_pct / 100) if direction == "LONG" else current_price * (1 + self.stop_loss_pct / 100),
                    "take_profit": current_price * (1 + self.take_profit_pct / 100) if direction == "LONG" else current_price * (1 - self.take_profit_pct / 100),
                    "order_size": self.order_size,
                }
            )

            self.logger.info(
                f"🎯 Momentum signal: {direction} @ ${current_price:.4f} "
                f"({price_change_pct:+.2f}% momentum, {confidence:.0%} confidence)"
            )

            return opportunity

        except Exception as e:
            self.logger.error(f"Error detecting momentum: {e}", exc_info=True)
            return None

    def _check_ma_crossover(self, direction: str) -> bool:
        """
        Check if moving averages confirm the direction.

        Args:
            direction: "LONG" or "SHORT"

        Returns:
            True if MAs confirm direction
        """
        try:
            if len(self.price_history) < self.ma_slow:
                return False

            # Calculate fast MA
            fast_prices = [p.price for p in list(self.price_history)[-self.ma_fast:]]
            ma_fast = sum(fast_prices) / len(fast_prices)

            # Calculate slow MA
            slow_prices = [p.price for p in list(self.price_history)[-self.ma_slow:]]
            ma_slow = sum(slow_prices) / len(slow_prices)

            # Check crossover
            if direction == "LONG":
                return ma_fast > ma_slow
            else:
                return ma_fast < ma_slow

        except Exception as e:
            self.logger.error(f"Error checking MA crossover: {e}")
            return False

    def _check_ma_alignment(self, direction: str) -> bool:
        """
        Check if price, fast MA, and slow MA are aligned with direction.

        Args:
            direction: "LONG" or "SHORT"

        Returns:
            True if aligned
        """
        try:
            if len(self.price_history) < self.ma_slow:
                return False

            current_price = self.price_history[-1].price

            fast_prices = [p.price for p in list(self.price_history)[-self.ma_fast:]]
            ma_fast = sum(fast_prices) / len(fast_prices)

            slow_prices = [p.price for p in list(self.price_history)[-self.ma_slow:]]
            ma_slow = sum(slow_prices) / len(slow_prices)

            if direction == "LONG":
                return current_price > ma_fast > ma_slow
            else:
                return current_price < ma_fast < ma_slow

        except Exception as e:
            self.logger.error(f"Error checking MA alignment: {e}")
            return False

    def _check_volume_surge(self) -> float:
        """
        Check for volume surge.

        Returns:
            Volume surge multiplier, or 0 if no surge
        """
        try:
            if len(self.price_history) < self.lookback_period:
                return 0.0

            # Recent volume
            recent_volumes = [p.volume for p in list(self.price_history)[-5:]]
            avg_recent_volume = sum(recent_volumes) / len(recent_volumes)

            # Historical average volume
            historical_volumes = [p.volume for p in list(self.price_history)[-self.lookback_period:-5]]
            if not historical_volumes:
                return 0.0

            avg_historical_volume = sum(historical_volumes) / len(historical_volumes)

            # Calculate surge
            if avg_historical_volume > 0:
                surge = avg_recent_volume / avg_historical_volume
                if surge >= self.volume_surge_multiplier:
                    return surge

            return 0.0

        except Exception as e:
            self.logger.error(f"Error checking volume surge: {e}")
            return 0.0

    def _calculate_average_move(self) -> float:
        """
        Calculate average price move in recent history.

        Returns:
            Average move percentage
        """
        try:
            if len(self.price_history) < 10:
                return 5.0  # Default estimate

            moves = []
            prices = [p.price for p in self.price_history]

            for i in range(1, min(10, len(prices))):
                move_pct = abs((prices[-i] - prices[-i-1]) / prices[-i-1]) * 100
                moves.append(move_pct)

            return sum(moves) / len(moves) if moves else 5.0

        except Exception as e:
            self.logger.error(f"Error calculating average move: {e}")
            return 5.0

    async def _manage_positions(self, orderbook: Orderbook):
        """
        Manage open positions (stop loss, take profit).

        Args:
            orderbook: Current orderbook
        """
        if not orderbook.best_bid or not orderbook.best_ask:
            return

        current_price = (orderbook.best_bid.price + orderbook.best_ask.price) / 2

        for position in self.positions[:]:  # Copy list to allow removal
            direction = position["direction"]
            entry_price = position["entry_price"]
            stop_loss = position["stop_loss"]
            take_profit = position["take_profit"]

            # Check stop loss
            if direction == "LONG" and current_price <= stop_loss:
                self.logger.warning(f"⛔ Stop loss hit: ${current_price:.4f} <= ${stop_loss:.4f}")
                await self._close_position(position, current_price, "STOP_LOSS")
                continue

            if direction == "SHORT" and current_price >= stop_loss:
                self.logger.warning(f"⛔ Stop loss hit: ${current_price:.4f} >= ${stop_loss:.4f}")
                await self._close_position(position, current_price, "STOP_LOSS")
                continue

            # Check take profit
            if direction == "LONG" and current_price >= take_profit:
                self.logger.info(f"✅ Take profit hit: ${current_price:.4f} >= ${take_profit:.4f}")
                await self._close_position(position, current_price, "TAKE_PROFIT")
                continue

            if direction == "SHORT" and current_price <= take_profit:
                self.logger.info(f"✅ Take profit hit: ${current_price:.4f} <= ${take_profit:.4f}")
                await self._close_position(position, current_price, "TAKE_PROFIT")
                continue

    async def _close_position(self, position: Dict[str, Any], exit_price: float, reason: str):
        """
        Close a position.

        Args:
            position: Position to close
            exit_price: Exit price
            reason: Reason for closing
        """
        try:
            direction = position["direction"]
            entry_price = position["entry_price"]
            size = position["size"]

            # Calculate P&L
            if direction == "LONG":
                pnl = (exit_price - entry_price) * size
            else:
                pnl = (entry_price - exit_price) * size

            self.logger.info(
                f"📉 Closing {direction} position: "
                f"Entry ${entry_price:.4f} → Exit ${exit_price:.4f} "
                f"= ${pnl:+.2f} ({reason})"
            )

            # Place exit order
            if not self.dry_run:
                side = OrderSide.SELL if direction == "LONG" else OrderSide.BUY
                order = self.provider.place_order(
                    pair=self.market_pair,
                    side=side,
                    order_type=OrderType.IOC,
                    size=size,
                    price=exit_price,
                )
                self.logger.info(f"✅ Exit order placed: {order.order_id}")

            # Update stats
            self.total_profit += pnl
            if pnl > 0:
                self.trades_executed += 1

            # Remove position
            self.positions.remove(position)

        except Exception as e:
            self.logger.error(f"Error closing position: {e}", exc_info=True)

    async def _close_all_positions(self):
        """Close all open positions."""
        self.logger.info("Closing all positions...")
        for position in self.positions[:]:
            try:
                # Get current price
                orderbook = self.provider.get_orderbook(self.market_pair)
                if orderbook.best_bid and orderbook.best_ask:
                    current_price = (orderbook.best_bid.price + orderbook.best_ask.price) / 2
                    await self._close_position(position, current_price, "SHUTDOWN")
            except Exception as e:
                self.logger.error(f"Error closing position on shutdown: {e}")

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute momentum trade.

        Args:
            opportunity: Momentum opportunity

        Returns:
            TradeResult with execution details
        """
        metadata = opportunity.metadata
        direction = metadata["direction"]
        entry_price = metadata["entry_price"]
        order_size = metadata["order_size"]

        self.logger.info("=" * 70)
        self.logger.info(f"🎯 EXECUTING MOMENTUM TRADE: {direction}")
        self.logger.info("=" * 70)
        self.logger.info(f"Entry price:     ${entry_price:.4f}")
        self.logger.info(f"Order size:      {order_size} shares")
        self.logger.info(f"Stop loss:       ${metadata['stop_loss']:.4f}")
        self.logger.info(f"Take profit:     ${metadata['take_profit']:.4f}")
        self.logger.info(f"Momentum:        {metadata['price_change_pct']:+.2f}%")
        self.logger.info("=" * 70)

        if self.dry_run:
            self.logger.info("🔸 DRY RUN MODE - No real orders placed")

            # Track position even in dry run
            self.positions.append({
                "direction": direction,
                "entry_price": entry_price,
                "size": order_size,
                "stop_loss": metadata["stop_loss"],
                "take_profit": metadata["take_profit"],
                "entry_time": time.time(),
            })

            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,
                orders=[],
            )

        try:
            # Place entry order
            side = OrderSide.BUY if direction == "LONG" else OrderSide.SELL
            order = self.provider.place_order(
                pair=self.market_pair,
                side=side,
                order_type=OrderType.FOK,
                size=order_size,
                price=entry_price,
            )

            self.logger.info(f"✅ Order placed: {order.order_id}")

            # Track position
            self.positions.append({
                "direction": direction,
                "entry_price": entry_price,
                "size": order_size,
                "stop_loss": metadata["stop_loss"],
                "take_profit": metadata["take_profit"],
                "entry_time": time.time(),
                "order_id": order.order_id,
            })

            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=0.0,  # Won't know until exit
                orders=[order],
            )

        except Exception as e:
            self.logger.error(f"Error executing momentum trade: {e}", exc_info=True)
            return TradeResult(
                opportunity=opportunity,
                success=False,
                error=str(e)
            )
