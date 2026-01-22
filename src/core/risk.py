"""
Risk and Constraint Layer Abstraction

This module provides unified risk management and constraint enforcement
across all domains (trading, GPU allocation, ad spend, inventory, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict

from .asset import Asset, AssetPosition
from .venue import Venue, ActionRequest
from .strategy import Opportunity


class RiskLevel(Enum):
    """Risk severity levels"""
    NONE = "none"          # No risk
    LOW = "low"            # Acceptable risk
    MEDIUM = "medium"      # Moderate risk, caution advised
    HIGH = "high"          # High risk, limits should apply
    CRITICAL = "critical"  # Unacceptable risk, block action


class ConstraintType(Enum):
    """Types of constraints"""
    POSITION_SIZE = "position_size"        # Max position size per asset
    CAPITAL_ALLOCATION = "capital_allocation"  # Max capital per action
    DAILY_LOSS = "daily_loss"              # Max loss per day
    TOTAL_EXPOSURE = "total_exposure"      # Max total exposure
    LEVERAGE = "leverage"                  # Max leverage
    CONCENTRATION = "concentration"        # Max % in single asset/venue
    FREQUENCY = "frequency"                # Max actions per time period
    CORRELATION = "correlation"            # Correlation limits
    VOLATILITY = "volatility"              # Volatility thresholds
    DRAWDOWN = "drawdown"                  # Max drawdown
    CUSTOM = "custom"                      # Domain-specific constraints


@dataclass
class RiskConstraint:
    """A single risk constraint"""

    constraint_type: ConstraintType
    name: str
    description: Optional[str] = None

    # Threshold values
    limit: Optional[float] = None
    warning_threshold: Optional[float] = None  # Warn when approaching limit

    # Temporal scope
    time_window: Optional[timedelta] = None  # e.g., daily, hourly

    # Applicability
    applies_to_assets: Optional[List[str]] = None  # Asset IDs
    applies_to_venues: Optional[List[str]] = None  # Venue IDs
    applies_to_strategies: Optional[List[str]] = None  # Strategy IDs

    # Enforcement
    enforce: bool = True  # If false, only warn
    block_on_breach: bool = True  # Block action if breached

    # Custom validation
    custom_validator: Optional[Callable] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    enabled: bool = True


@dataclass
class RiskAssessment:
    """Result of risk assessment for an action"""

    action_id: str
    overall_risk_level: RiskLevel

    # Constraint violations
    violated_constraints: List[RiskConstraint] = field(default_factory=list)
    warning_constraints: List[RiskConstraint] = field(default_factory=list)

    # Quantitative risk metrics
    risk_score: float = 0.0  # 0.0 (safe) to 1.0 (max risk)
    expected_loss: Optional[float] = None  # Worst-case loss
    value_at_risk: Optional[float] = None  # VaR estimate
    sharpe_ratio: Optional[float] = None

    # Position impact
    current_exposure: float = 0.0
    new_exposure: float = 0.0
    exposure_change_pct: float = 0.0

    # Capital impact
    current_capital_used: float = 0.0
    new_capital_used: float = 0.0
    available_capital: float = 0.0

    # Action recommendation
    should_allow: bool = True
    reason: Optional[str] = None

    # Suggestions
    suggested_size_reduction: Optional[float] = None
    suggested_adjustments: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioMetrics:
    """Current portfolio/position metrics for risk calculation"""

    total_value: float
    available_capital: float
    allocated_capital: float

    # Positions
    positions: List[AssetPosition] = field(default_factory=list)
    total_exposure: float = 0.0

    # Performance
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0

    # Risk metrics
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    var_95: Optional[float] = None  # 95% Value at Risk

    # Asset concentration
    largest_position_pct: float = 0.0
    top_5_concentration_pct: float = 0.0

    # Venue concentration
    venue_exposures: Dict[str, float] = field(default_factory=dict)

    # Temporal metrics
    trades_today: int = 0
    pnl_today: float = 0.0

    # Metadata
    calculated_at: datetime = field(default_factory=datetime.utcnow)


class RiskManager(ABC):
    """
    Abstract base class for risk management.

    Implementations handle domain-specific risk assessment:
    - Trading: position limits, loss limits, leverage
    - GPU: capacity limits, cost caps, utilization
    - Ads: budget limits, ROAS thresholds, frequency caps
    - Ecommerce: inventory limits, capital allocation
    """

    def __init__(self, constraints: Optional[List[RiskConstraint]] = None):
        self.constraints = constraints or []
        self._assessment_history: List[RiskAssessment] = []
        self._metrics_history: List[PortfolioMetrics] = []

    @abstractmethod
    async def assess_action(
        self,
        action: ActionRequest,
        current_portfolio: PortfolioMetrics
    ) -> RiskAssessment:
        """
        Assess the risk of a proposed action.

        Args:
            action: Proposed action
            current_portfolio: Current portfolio state

        Returns:
            Risk assessment with allow/block recommendation
        """
        pass

    @abstractmethod
    async def assess_opportunity(
        self,
        opportunity: Opportunity,
        current_portfolio: PortfolioMetrics
    ) -> RiskAssessment:
        """
        Assess the risk of an opportunity before execution.

        Args:
            opportunity: Detected opportunity
            current_portfolio: Current portfolio state

        Returns:
            Risk assessment
        """
        pass

    @abstractmethod
    async def calculate_position_size(
        self,
        asset: Asset,
        confidence: float,
        current_portfolio: PortfolioMetrics
    ) -> float:
        """
        Calculate appropriate position size for an asset.

        Uses Kelly criterion, fixed fractional, or custom method.

        Args:
            asset: Asset to size
            confidence: Strategy confidence (0.0-1.0)
            current_portfolio: Current portfolio state

        Returns:
            Suggested position size
        """
        pass

    # Constraint management

    def add_constraint(self, constraint: RiskConstraint):
        """Add a risk constraint"""
        self.constraints.append(constraint)

    def remove_constraint(self, constraint_name: str):
        """Remove a constraint by name"""
        self.constraints = [c for c in self.constraints if c.name != constraint_name]

    def get_constraint(self, constraint_name: str) -> Optional[RiskConstraint]:
        """Get a constraint by name"""
        for constraint in self.constraints:
            if constraint.name == constraint_name:
                return constraint
        return None

    def enable_constraint(self, constraint_name: str):
        """Enable a constraint"""
        constraint = self.get_constraint(constraint_name)
        if constraint:
            constraint.enabled = True

    def disable_constraint(self, constraint_name: str):
        """Disable a constraint"""
        constraint = self.get_constraint(constraint_name)
        if constraint:
            constraint.enabled = False

    # Common risk checks (implemented by base class)

    def check_position_size_constraint(
        self,
        asset: Asset,
        quantity: float,
        current_portfolio: PortfolioMetrics
    ) -> tuple[bool, Optional[str]]:
        """Check if position size is within limits"""
        for constraint in self.constraints:
            if not constraint.enabled or constraint.constraint_type != ConstraintType.POSITION_SIZE:
                continue

            if constraint.applies_to_assets and asset.asset_id not in constraint.applies_to_assets:
                continue

            if constraint.limit and quantity > constraint.limit:
                return False, f"Position size {quantity} exceeds limit {constraint.limit}"

        return True, None

    def check_daily_loss_constraint(
        self,
        current_portfolio: PortfolioMetrics
    ) -> tuple[bool, Optional[str]]:
        """Check if daily loss limit is breached"""
        for constraint in self.constraints:
            if not constraint.enabled or constraint.constraint_type != ConstraintType.DAILY_LOSS:
                continue

            daily_pnl = current_portfolio.pnl_today

            if constraint.limit and daily_pnl < -abs(constraint.limit):
                return False, f"Daily loss {abs(daily_pnl)} exceeds limit {constraint.limit}"

            if constraint.warning_threshold and daily_pnl < -abs(constraint.warning_threshold):
                return True, f"Approaching daily loss limit"

        return True, None

    def check_frequency_constraint(
        self,
        asset: Optional[Asset] = None
    ) -> tuple[bool, Optional[str]]:
        """Check if action frequency is within limits"""
        for constraint in self.constraints:
            if not constraint.enabled or constraint.constraint_type != ConstraintType.FREQUENCY:
                continue

            # Count recent actions within time window
            if constraint.time_window:
                cutoff = datetime.utcnow() - constraint.time_window
                recent_assessments = [
                    a for a in self._assessment_history
                    if a.assessed_at >= cutoff
                ]

                if constraint.limit and len(recent_assessments) >= constraint.limit:
                    return False, f"Frequency limit exceeded: {len(recent_assessments)} actions in {constraint.time_window}"

        return True, None

    def check_capital_allocation_constraint(
        self,
        required_capital: float,
        current_portfolio: PortfolioMetrics
    ) -> tuple[bool, Optional[str]]:
        """Check if capital allocation is within limits"""
        for constraint in self.constraints:
            if not constraint.enabled or constraint.constraint_type != ConstraintType.CAPITAL_ALLOCATION:
                continue

            if constraint.limit and required_capital > constraint.limit:
                return False, f"Required capital {required_capital} exceeds limit {constraint.limit}"

            available = current_portfolio.available_capital
            if required_capital > available:
                return False, f"Insufficient capital: need {required_capital}, have {available}"

        return True, None

    # Portfolio analysis

    def calculate_risk_score(
        self,
        action: ActionRequest,
        current_portfolio: PortfolioMetrics
    ) -> float:
        """
        Calculate overall risk score (0.0-1.0) for an action.

        Factors:
        - Position concentration
        - Volatility
        - Correlation with existing positions
        - Capital utilization
        """
        score = 0.0
        factors = 0

        # Factor 1: Capital utilization
        required_capital = action.quantity * (action.price or 0)
        if current_portfolio.total_value > 0:
            utilization = required_capital / current_portfolio.total_value
            score += min(utilization, 1.0)
            factors += 1

        # Factor 2: Concentration
        if current_portfolio.largest_position_pct > 0.5:
            score += 0.3
            factors += 1

        # Factor 3: Volatility
        if current_portfolio.volatility:
            # Normalize volatility to 0-1 scale (assume max 100% volatility)
            vol_score = min(current_portfolio.volatility / 1.0, 1.0)
            score += vol_score
            factors += 1

        # Average the factors
        return score / factors if factors > 0 else 0.0

    # History and statistics

    def get_assessment_history(self) -> List[RiskAssessment]:
        """Get risk assessment history"""
        return self._assessment_history

    def get_statistics(self) -> Dict[str, Any]:
        """Get risk management statistics"""
        if not self._assessment_history:
            return {
                "total_assessments": 0,
                "blocked_actions": 0,
                "block_rate": 0.0
            }

        total = len(self._assessment_history)
        blocked = sum(1 for a in self._assessment_history if not a.should_allow)

        return {
            "total_assessments": total,
            "allowed_actions": total - blocked,
            "blocked_actions": blocked,
            "block_rate": blocked / total,
            "avg_risk_score": sum(a.risk_score for a in self._assessment_history) / total,
            "constraints_enabled": sum(1 for c in self.constraints if c.enabled),
            "constraints_total": len(self.constraints)
        }


class DefaultRiskManager(RiskManager):
    """
    Default risk manager implementation with common risk checks.

    Works across all domains with sensible defaults.
    """

    async def assess_action(
        self,
        action: ActionRequest,
        current_portfolio: PortfolioMetrics
    ) -> RiskAssessment:
        """Assess risk of an action"""
        assessment = RiskAssessment(
            action_id=f"action_{datetime.utcnow().timestamp()}",
            overall_risk_level=RiskLevel.LOW
        )

        # Check all constraints
        violated = []
        warnings = []

        # Position size check
        is_valid, msg = self.check_position_size_constraint(
            action.asset,
            action.quantity,
            current_portfolio
        )
        if not is_valid:
            violated.append(self.get_constraint("position_size_limit"))

        # Daily loss check
        is_valid, msg = self.check_daily_loss_constraint(current_portfolio)
        if not is_valid:
            violated.append(self.get_constraint("daily_loss_limit"))

        # Frequency check
        is_valid, msg = self.check_frequency_constraint(action.asset)
        if not is_valid:
            violated.append(self.get_constraint("frequency_limit"))

        # Capital check
        required_capital = action.quantity * (action.price or 0)
        is_valid, msg = self.check_capital_allocation_constraint(
            required_capital,
            current_portfolio
        )
        if not is_valid:
            violated.append(self.get_constraint("capital_limit"))

        # Set violations
        assessment.violated_constraints = [c for c in violated if c]
        assessment.warning_constraints = [c for c in warnings if c]

        # Calculate risk score
        assessment.risk_score = self.calculate_risk_score(action, current_portfolio)

        # Determine if should allow
        if assessment.violated_constraints:
            assessment.should_allow = False
            assessment.overall_risk_level = RiskLevel.CRITICAL
            assessment.reason = f"Violated {len(assessment.violated_constraints)} constraints"
        elif assessment.risk_score > 0.8:
            assessment.overall_risk_level = RiskLevel.HIGH
        elif assessment.risk_score > 0.5:
            assessment.overall_risk_level = RiskLevel.MEDIUM

        # Store assessment
        self._assessment_history.append(assessment)

        return assessment

    async def assess_opportunity(
        self,
        opportunity: Opportunity,
        current_portfolio: PortfolioMetrics
    ) -> RiskAssessment:
        """Assess risk of an opportunity"""
        assessment = RiskAssessment(
            action_id=opportunity.opportunity_id,
            overall_risk_level=RiskLevel.LOW
        )

        # Use opportunity's risk score
        assessment.risk_score = opportunity.risk_score

        # Map risk score to risk level
        if assessment.risk_score > 0.8:
            assessment.overall_risk_level = RiskLevel.HIGH
        elif assessment.risk_score > 0.5:
            assessment.overall_risk_level = RiskLevel.MEDIUM
        elif assessment.risk_score > 0.2:
            assessment.overall_risk_level = RiskLevel.LOW
        else:
            assessment.overall_risk_level = RiskLevel.NONE

        # Check daily loss
        is_valid, msg = self.check_daily_loss_constraint(current_portfolio)
        if not is_valid:
            assessment.should_allow = False
            assessment.reason = msg

        self._assessment_history.append(assessment)
        return assessment

    async def calculate_position_size(
        self,
        asset: Asset,
        confidence: float,
        current_portfolio: PortfolioMetrics
    ) -> float:
        """
        Calculate position size using fixed fractional method.

        Allocates a fixed percentage of capital based on confidence.
        """
        # Default: use 2% of capital per trade
        base_fraction = 0.02

        # Scale by confidence
        adjusted_fraction = base_fraction * confidence

        # Calculate size
        position_size = current_portfolio.available_capital * adjusted_fraction

        # Check against constraints
        for constraint in self.constraints:
            if constraint.enabled and constraint.constraint_type == ConstraintType.POSITION_SIZE:
                if constraint.limit:
                    position_size = min(position_size, constraint.limit)

        return position_size
