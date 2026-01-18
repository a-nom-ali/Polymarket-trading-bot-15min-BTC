"""
Backtesting Engine

Simulates strategy execution on historical data to evaluate performance.

Features:
- Historical data replay
- Trade simulation with fees
- Performance metrics calculation
- Parameter optimization
- Multi-timeframe support
- Slippage modeling

Usage:
    from src.backtesting import BacktestEngine

    engine = BacktestEngine(strategy, historical_data)
    result = await engine.run()
    print(f"Sharpe Ratio: {result.sharpe_ratio}")
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import statistics

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Backtest trade record."""
    timestamp: datetime
    pair: str
    side: str
    price: float
    size: float
    fee: float = 0.0
    profit: float = 0.0
    strategy: str = ""


@dataclass
class BacktestResult:
    """Backtest results."""
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # Profit metrics
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0

    # Advanced metrics
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    recovery_factor: float = 0.0

    # Timing
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: float = 0.0

    # Trade list
    trades: List[Trade] = field(default_factory=list)

    # Equity curve
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "net_profit": self.net_profit,
            "avg_profit": self.avg_profit,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "recovery_factor": self.recovery_factor,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "duration_days": self.duration_days,
            "trades_count": len(self.trades)
        }


class BacktestEngine:
    """Backtesting engine for strategy evaluation."""

    def __init__(
        self,
        strategy_class,
        historical_data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ):
        """
        Initialize backtest engine.

        Args:
            strategy_class: Strategy class to test
            historical_data: Historical market data
            config: Backtest configuration
        """
        self.strategy_class = strategy_class
        self.historical_data = sorted(historical_data, key=lambda x: x['timestamp'])
        self.config = config

        # Config
        self.initial_balance = config.get('initial_balance', 10000.0)
        self.fee_pct = config.get('fee_pct', 0.1)
        self.slippage_pct = config.get('slippage_pct', 0.05)

        # State
        self.balance = self.initial_balance
        self.position = 0.0  # Current position size
        self.position_price = 0.0  # Entry price
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []

        logger.info(f"Backtest engine initialized (initial balance: ${self.initial_balance})")

    async def run(self) -> BacktestResult:
        """
        Run backtest.

        Returns:
            Backtest results
        """
        logger.info(f"Starting backtest on {len(self.historical_data)} data points")

        # Initialize strategy (mock provider)
        from .data_provider import HistoricalDataProvider
        provider = HistoricalDataProvider(self.historical_data)
        strategy = self.strategy_class(provider, self.config)

        # Track start time
        start_time = datetime.now()

        # Iterate through historical data
        for i, data_point in enumerate(self.historical_data):
            current_time = data_point['timestamp']
            current_price = data_point['price']

            # Update provider with current data
            provider.set_current_index(i)

            # Let strategy find opportunities
            try:
                opportunity = await strategy.find_opportunity()

                if opportunity:
                    # Execute trade
                    await self._execute_trade(opportunity, current_price, current_time)

            except Exception as e:
                logger.warning(f"Error in strategy at {current_time}: {e}")

            # Record equity
            equity = self._calculate_equity(current_price)
            self.equity_curve.append({
                'timestamp': current_time,
                'equity': equity,
                'balance': self.balance,
                'position_value': self.position * current_price if self.position else 0.0
            })

        # Calculate final results
        result = self._calculate_results()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Backtest completed in {elapsed:.2f}s - Net profit: ${result.net_profit:.2f}")

        return result

    async def _execute_trade(self, opportunity, current_price: float, timestamp):
        """Execute a trade."""
        # Apply slippage
        if opportunity.side.value == 'BUY':
            execution_price = current_price * (1 + self.slippage_pct / 100)
        else:
            execution_price = current_price * (1 - self.slippage_pct / 100)

        # Calculate size
        size = opportunity.size

        # Calculate fee
        trade_value = size * execution_price
        fee = trade_value * (self.fee_pct / 100)

        # Execute trade
        if opportunity.side.value == 'BUY':
            # Check if we have enough balance
            total_cost = trade_value + fee
            if total_cost > self.balance:
                logger.warning(f"Insufficient balance: ${self.balance:.2f} < ${total_cost:.2f}")
                return

            # Execute buy
            self.balance -= total_cost
            self.position += size
            self.position_price = execution_price

            # Record trade
            trade = Trade(
                timestamp=timestamp,
                pair=opportunity.market_pair,
                side='BUY',
                price=execution_price,
                size=size,
                fee=fee,
                profit=0.0,
                strategy=self.strategy_class.__name__
            )
            self.trades.append(trade)

        else:  # SELL
            # Check if we have position
            if self.position <= 0:
                logger.warning("No position to sell")
                return

            # Calculate profit
            sell_value = size * execution_price
            buy_value = size * self.position_price
            profit = sell_value - buy_value - fee

            # Execute sell
            self.balance += sell_value - fee
            self.position -= size

            # Record trade
            trade = Trade(
                timestamp=timestamp,
                pair=opportunity.market_pair,
                side='SELL',
                price=execution_price,
                size=size,
                fee=fee,
                profit=profit,
                strategy=self.strategy_class.__name__
            )
            self.trades.append(trade)

            logger.debug(f"Trade executed: {trade.side} {trade.size} @ ${trade.price:.2f} (profit: ${profit:.2f})")

    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current equity."""
        position_value = self.position * current_price if self.position else 0.0
        return self.balance + position_value

    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest results."""
        result = BacktestResult()

        if not self.trades:
            logger.warning("No trades executed")
            return result

        # Basic metrics
        sell_trades = [t for t in self.trades if t.side == 'SELL']
        result.total_trades = len(sell_trades)
        result.winning_trades = len([t for t in sell_trades if t.profit > 0])
        result.losing_trades = len([t for t in sell_trades if t.profit < 0])
        result.win_rate = (result.winning_trades / result.total_trades * 100) if result.total_trades > 0 else 0.0

        # Profit metrics
        profits = [t.profit for t in sell_trades if t.profit > 0]
        losses = [abs(t.profit) for t in sell_trades if t.profit < 0]

        result.total_profit = sum(profits) if profits else 0.0
        result.total_loss = sum(losses) if losses else 0.0
        result.net_profit = sum(t.profit for t in sell_trades)
        result.avg_profit = statistics.mean(profits) if profits else 0.0
        result.avg_loss = statistics.mean(losses) if losses else 0.0
        result.profit_factor = (result.total_profit / result.total_loss) if result.total_loss > 0 else 0.0

        # Timing
        result.start_date = self.historical_data[0]['timestamp']
        result.end_date = self.historical_data[-1]['timestamp']
        result.duration_days = (result.end_date - result.start_date).total_seconds() / 86400

        # Sharpe ratio
        if sell_trades:
            returns = [t.profit / self.initial_balance for t in sell_trades]
            if len(returns) > 1:
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                result.sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0.0
            else:
                result.sharpe_ratio = 0.0

        # Drawdown
        result.max_drawdown, result.max_drawdown_pct = self._calculate_drawdown()

        # Recovery factor
        if result.max_drawdown != 0:
            result.recovery_factor = result.net_profit / abs(result.max_drawdown)
        else:
            result.recovery_factor = 0.0

        # Store trades and equity curve
        result.trades = self.trades
        result.equity_curve = self.equity_curve

        return result

    def _calculate_drawdown(self) -> tuple[float, float]:
        """Calculate maximum drawdown."""
        if not self.equity_curve:
            return 0.0, 0.0

        peak = self.initial_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0

        for point in self.equity_curve:
            equity = point['equity']

            # Update peak
            if equity > peak:
                peak = equity

            # Calculate drawdown
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0.0

            # Update max
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct

        return max_drawdown, max_drawdown_pct


class ParameterOptimizer:
    """Optimize strategy parameters using grid search."""

    def __init__(self, strategy_class, historical_data: List[Dict[str, Any]]):
        """
        Initialize parameter optimizer.

        Args:
            strategy_class: Strategy class to optimize
            historical_data: Historical market data
        """
        self.strategy_class = strategy_class
        self.historical_data = historical_data

    async def optimize(
        self,
        param_grid: Dict[str, List[Any]],
        metric: str = 'sharpe_ratio'
    ) -> Dict[str, Any]:
        """
        Optimize parameters using grid search.

        Args:
            param_grid: Parameter grid {param_name: [values]}
            metric: Metric to optimize

        Returns:
            Best parameters and result
        """
        logger.info(f"Starting parameter optimization (metric: {metric})")

        best_params = None
        best_score = float('-inf')
        best_result = None

        # Generate parameter combinations
        param_combinations = self._generate_combinations(param_grid)

        logger.info(f"Testing {len(param_combinations)} parameter combinations")

        # Test each combination
        for i, params in enumerate(param_combinations):
            logger.info(f"Testing combination {i+1}/{len(param_combinations)}: {params}")

            # Run backtest
            engine = BacktestEngine(self.strategy_class, self.historical_data, params)
            result = await engine.run()

            # Get score
            score = getattr(result, metric, 0.0)

            # Update best
            if score > best_score:
                best_score = score
                best_params = params
                best_result = result

                logger.info(f"New best {metric}: {score:.4f}")

        logger.info(f"Optimization complete - Best {metric}: {best_score:.4f}")

        return {
            'best_params': best_params,
            'best_score': best_score,
            'best_result': best_result
        }

    def _generate_combinations(self, param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """Generate all parameter combinations."""
        import itertools

        keys = param_grid.keys()
        values = param_grid.values()

        combinations = []
        for combo in itertools.product(*values):
            combinations.append(dict(zip(keys, combo)))

        return combinations
