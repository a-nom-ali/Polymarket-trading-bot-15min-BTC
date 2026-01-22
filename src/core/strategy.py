"""
Generic Strategy Abstraction Layer

This module defines the core abstraction for any automated strategy that can
find opportunities and execute actions across different domains.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime

from .asset import Asset
from .venue import Venue, ActionRequest, ActionResult


class OpportunityType(Enum):
    """Categories of opportunities"""
    ARBITRAGE = "arbitrage"              # Price differential across venues
    MARKET_MAKING = "market_making"      # Provide liquidity for spread
    MOMENTUM = "momentum"                # Ride trend/momentum
    MEAN_REVERSION = "mean_reversion"    # Revert to mean price
    YIELD_OPTIMIZATION = "yield_optimization"  # Maximize yield/return
    COST_OPTIMIZATION = "cost_optimization"    # Minimize cost
    CAPACITY_OPTIMIZATION = "capacity_optimization"  # Optimize resource allocation
    CUSTOM = "custom"


class OpportunityStatus(Enum):
    """Status of an opportunity"""
    DETECTED = "detected"        # Just found
    VALIDATED = "validated"      # Passed validation checks
    EXECUTING = "executing"      # Currently being executed
    COMPLETED = "completed"      # Successfully executed
    FAILED = "failed"            # Execution failed
    EXPIRED = "expired"          # Opportunity window closed
    CANCELLED = "cancelled"      # Manually cancelled


@dataclass
class Opportunity:
    """
    Represents a detected opportunity for profit/optimization.

    This abstraction works across domains:
    - Trading: arbitrage between exchanges
    - GPU: rent out when spot rate high, keep when low
    - Ads: reallocate budget to high-ROAS campaigns
    - Products: buy where cheap, sell where expensive
    """

    opportunity_id: str
    opportunity_type: OpportunityType

    # Strategy context
    strategy_name: str
    strategy_version: str = "1.0.0"

    # Confidence and expected outcome
    confidence: float  # 0.0 to 1.0
    expected_profit: float
    expected_cost: float
    expected_roi: float  # Return on investment as decimal

    # Risk metrics
    risk_score: float = 0.5  # 0.0 (safe) to 1.0 (risky)
    max_loss: Optional[float] = None
    sharpe_ratio: Optional[float] = None

    # Temporal constraints
    detected_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    estimated_execution_time_ms: Optional[int] = None

    # Asset and venue context
    primary_asset: Optional[Asset] = None
    primary_venue: Optional[Venue] = None
    secondary_asset: Optional[Asset] = None
    secondary_venue: Optional[Venue] = None

    # Actions to execute (populated by strategy)
    actions: List[ActionRequest] = field(default_factory=list)

    # Status
    status: OpportunityStatus = OpportunityStatus.DETECTED

    # Domain-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize opportunity to dictionary"""
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_type": self.opportunity_type.value,
            "strategy_name": self.strategy_name,
            "confidence": self.confidence,
            "expected_profit": self.expected_profit,
            "expected_cost": self.expected_cost,
            "expected_roi": self.expected_roi,
            "risk_score": self.risk_score,
            "detected_at": self.detected_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "metadata": self.metadata
        }


@dataclass
class ExecutionResult:
    """Result of executing an opportunity"""

    opportunity: Opportunity
    success: bool

    # Actual outcomes
    actual_profit: Optional[float] = None
    actual_cost: Optional[float] = None
    actual_roi: Optional[float] = None

    # Action results
    action_results: List[ActionResult] = field(default_factory=list)

    # Error tracking
    error_message: Optional[str] = None
    failed_actions: List[ActionRequest] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None

    # Performance metrics
    slippage: Optional[float] = None  # (expected - actual) / expected
    slippage_pct: Optional[float] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_slippage(self):
        """Calculate slippage from expected vs actual profit"""
        if self.actual_profit is not None:
            expected = self.opportunity.expected_profit
            if expected != 0:
                self.slippage = expected - self.actual_profit
                self.slippage_pct = (self.slippage / abs(expected)) * 100


class StrategyExecutionMode(Enum):
    """How the strategy executes"""
    POLLING = "polling"              # Scan at regular intervals
    EVENT_DRIVEN = "event_driven"    # React to real-time events
    HYBRID = "hybrid"                # Both polling and events
    ON_DEMAND = "on_demand"          # Execute only when triggered


class StrategyStatus(Enum):
    """Current status of a strategy"""
    IDLE = "idle"                # Not running
    INITIALIZING = "initializing"  # Starting up
    SCANNING = "scanning"        # Looking for opportunities
    EXECUTING = "executing"      # Executing opportunity
    WAITING = "waiting"          # Waiting for cooldown/rate limit
    PAUSED = "paused"            # Temporarily paused
    STOPPED = "stopped"          # Stopped by user
    ERROR = "error"              # In error state


@dataclass
class StrategyConfig:
    """Configuration for a strategy"""

    # Execution settings
    execution_mode: StrategyExecutionMode = StrategyExecutionMode.POLLING
    scan_interval_ms: int = 5000  # For polling mode
    max_concurrent_opportunities: int = 1

    # Thresholds
    min_confidence: float = 0.7
    min_expected_profit: float = 0.0
    min_roi: float = 0.0
    max_risk_score: float = 1.0

    # Resource limits
    max_position_size: Optional[float] = None
    max_capital_per_opportunity: Optional[float] = None
    max_daily_trades: Optional[int] = None

    # Execution constraints
    enable_auto_execution: bool = True
    require_manual_approval: bool = False
    dry_run_mode: bool = False

    # Custom parameters (strategy-specific)
    custom_params: Dict[str, Any] = field(default_factory=dict)


class Strategy(ABC):
    """
    Abstract base class for any automated strategy.

    This abstraction allows the same workflow/orchestration engine to run
    strategies across trading, GPU allocation, ad optimization, inventory
    management, etc.
    """

    def __init__(
        self,
        strategy_id: str,
        strategy_name: str,
        venues: List[Venue],
        config: StrategyConfig
    ):
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.venues = venues
        self.config = config

        self._status = StrategyStatus.IDLE
        self._active_opportunities: List[Opportunity] = []
        self._execution_history: List[ExecutionResult] = []

        # Callbacks
        self._on_opportunity_detected: Optional[Callable] = None
        self._on_execution_complete: Optional[Callable] = None

    @property
    def status(self) -> StrategyStatus:
        """Current status"""
        return self._status

    @property
    def active_opportunities(self) -> List[Opportunity]:
        """Currently active opportunities"""
        return self._active_opportunities

    @property
    def execution_history(self) -> List[ExecutionResult]:
        """History of executed opportunities"""
        return self._execution_history

    # Lifecycle methods

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the strategy.

        This is called once when the strategy starts. Use it to:
        - Connect to venues
        - Load historical data
        - Initialize models/indicators
        - Set up event listeners

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the strategy gracefully.

        This is called when the strategy stops. Use it to:
        - Close positions
        - Disconnect from venues
        - Save state
        - Clean up resources

        Returns:
            True if shutdown successful
        """
        pass

    # Core strategy methods

    @abstractmethod
    async def find_opportunities(self) -> List[Opportunity]:
        """
        Scan for opportunities.

        This is the main "alpha generation" method where the strategy
        implements its logic to find profitable opportunities.

        Implementation varies by domain:
        - Trading: find arbitrage, momentum, mean reversion
        - GPU: find times to rent vs keep
        - Ads: find campaigns to scale up/down
        - Products: find buy/sell price differentials

        Returns:
            List of detected opportunities
        """
        pass

    @abstractmethod
    async def validate_opportunity(self, opportunity: Opportunity) -> bool:
        """
        Validate an opportunity before execution.

        Check:
        - Still viable (prices haven't moved)
        - Risk constraints satisfied
        - Sufficient capital/resources
        - No conflicts with active opportunities

        Args:
            opportunity: Opportunity to validate

        Returns:
            True if opportunity is still valid
        """
        pass

    @abstractmethod
    async def execute_opportunity(self, opportunity: Opportunity) -> ExecutionResult:
        """
        Execute an opportunity.

        This method:
        1. Validates the opportunity
        2. Executes all required actions
        3. Tracks the results
        4. Handles errors/rollback

        Args:
            opportunity: Opportunity to execute

        Returns:
            Execution result
        """
        pass

    # Event-driven hooks (optional)

    async def on_market_data_update(self, asset: Asset, data: Any):
        """
        Handle real-time market data updates.

        Override this for event-driven strategies.
        """
        pass

    async def on_venue_event(self, venue: Venue, event: Dict[str, Any]):
        """
        Handle venue-specific events.

        Override this for event-driven strategies.
        """
        pass

    # Callback registration

    def set_on_opportunity_detected(self, callback: Callable):
        """Register callback for when opportunity is detected"""
        self._on_opportunity_detected = callback

    def set_on_execution_complete(self, callback: Callable):
        """Register callback for when execution completes"""
        self._on_execution_complete = callback

    # Helper methods

    async def _execute_actions(
        self,
        actions: List[ActionRequest],
        venue: Venue
    ) -> List[ActionResult]:
        """
        Execute a list of actions on a venue.

        Args:
            actions: Actions to execute
            venue: Target venue

        Returns:
            List of action results
        """
        results = []
        for action in actions:
            try:
                result = await venue.execute_action(action)
                results.append(result)

                if not result.success:
                    # Stop on first failure
                    break
            except Exception as e:
                # Create failed result
                result = ActionResult(
                    request=action,
                    success=False,
                    error_message=str(e)
                )
                results.append(result)
                break

        return results

    def _should_execute_opportunity(self, opportunity: Opportunity) -> tuple[bool, Optional[str]]:
        """
        Check if opportunity meets execution criteria.

        Returns:
            (should_execute, reason_if_not)
        """
        # Check confidence threshold
        if opportunity.confidence < self.config.min_confidence:
            return False, f"Confidence {opportunity.confidence} below minimum {self.config.min_confidence}"

        # Check profit threshold
        if opportunity.expected_profit < self.config.min_expected_profit:
            return False, f"Expected profit {opportunity.expected_profit} below minimum"

        # Check ROI threshold
        if opportunity.expected_roi < self.config.min_roi:
            return False, f"Expected ROI {opportunity.expected_roi} below minimum"

        # Check risk threshold
        if opportunity.risk_score > self.config.max_risk_score:
            return False, f"Risk score {opportunity.risk_score} exceeds maximum"

        # Check concurrent opportunity limit
        if len(self._active_opportunities) >= self.config.max_concurrent_opportunities:
            return False, "Max concurrent opportunities reached"

        return True, None

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy performance statistics"""
        if not self._execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "total_profit": 0.0,
                "avg_profit": 0.0,
                "avg_roi": 0.0
            }

        successful = [r for r in self._execution_history if r.success]
        total_profit = sum(r.actual_profit or 0 for r in successful)
        total_executions = len(self._execution_history)

        return {
            "total_executions": total_executions,
            "successful_executions": len(successful),
            "success_rate": len(successful) / total_executions,
            "total_profit": total_profit,
            "avg_profit": total_profit / len(successful) if successful else 0,
            "avg_roi": sum(r.actual_roi or 0 for r in successful) / len(successful) if successful else 0,
            "avg_execution_time_ms": sum(r.execution_time_ms or 0 for r in self._execution_history) / total_executions
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize strategy to dictionary"""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "status": self.status.value,
            "venues": [v.name for v in self.venues],
            "config": {
                "execution_mode": self.config.execution_mode.value,
                "scan_interval_ms": self.config.scan_interval_ms,
                "min_confidence": self.config.min_confidence,
                "min_expected_profit": self.config.min_expected_profit,
                "enable_auto_execution": self.config.enable_auto_execution
            },
            "active_opportunities": len(self._active_opportunities),
            "statistics": self.get_statistics()
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.strategy_name}, {self.status.value})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} strategy_id={self.strategy_id} name={self.strategy_name}>"
