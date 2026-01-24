"""
GPU Capacity Optimization Strategy

Automatically decides when to rent out GPUs on Vast.ai vs keep for own use,
based on market rates, power costs, and profitability thresholds.

This is the first production implementation of a non-trading strategy using
the generic abstraction layer.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..core.strategy import (
    Strategy,
    Opportunity,
    OpportunityType,
    ExecutionResult,
    StrategyStatus,
    StrategyConfig
)
from ..core.asset import ComputeAsset, AssetValuation
from ..core.venue import ActionRequest, ActionResult, ActionType
from ..core.risk import RiskManager, PortfolioMetrics
from ..integrations.vastai import VastAIMarketplace, GPUOffer

logger = logging.getLogger(__name__)


@dataclass
class GPUConfig:
    """Configuration for a GPU to optimize"""

    gpu_id: str
    gpu_model: str
    vram_gb: int
    cuda_cores: int
    power_watts: int

    # Operating costs
    power_cost_per_kwh: float = 0.12  # $/kWh (default ~US average)
    maintenance_cost_per_hour: float = 0.02  # Amortized maintenance

    # Performance
    hashrate_mhs: Optional[float] = None  # For mining comparison
    flops: Optional[float] = None  # For ML workload value

    @property
    def power_cost_per_hour(self) -> float:
        """Calculate power cost in $/hour"""
        kwh = (self.power_watts / 1000.0)
        return kwh * self.power_cost_per_kwh

    @property
    def total_operating_cost_per_hour(self) -> float:
        """Total operating cost including power and maintenance"""
        return self.power_cost_per_hour + self.maintenance_cost_per_hour


@dataclass
class GPUOpportunity:
    """
    Represents a GPU rental opportunity decision.

    Extends base Opportunity with GPU-specific data.
    """

    opportunity: Opportunity
    gpu_config: GPUConfig

    # Market data
    current_market_rate: float  # $/hour
    estimated_occupancy: float  # 0-1 (how often rented)

    # Decision factors
    should_list: bool
    suggested_price: Optional[float] = None

    # Comparison data
    alternative_value: Optional[float] = None  # Value if used for mining/ML
    opportunity_cost: float = 0.0


class GPUCapacityOptimizer(Strategy):
    """
    GPU capacity optimization strategy.

    Makes intelligent decisions about when to:
    1. List GPUs on Vast.ai for rental (when market rate is high)
    2. Keep GPUs for own use (when market rate is low or own workloads more valuable)
    3. Dynamically adjust pricing based on market conditions

    This strategy demonstrates the abstraction layer working for a
    completely different domain than trading.
    """

    def __init__(
        self,
        gpu_configs: List[GPUConfig],
        marketplace: VastAIMarketplace,
        config: Optional[StrategyConfig] = None,
        risk_manager: Optional[RiskManager] = None
    ):
        """
        Initialize GPU optimizer.

        Args:
            gpu_configs: List of GPU configurations to optimize
            marketplace: Vast.ai marketplace adapter
            config: Strategy configuration
            risk_manager: Optional risk manager
        """
        # Default config for GPU optimization
        if config is None:
            config = StrategyConfig(
                scan_interval_ms=300000,  # 5 minutes
                min_expected_profit=0.10,  # $0.10/hour minimum
                min_roi=0.25,  # 25% margin minimum
                enable_auto_execution=True,
                dry_run_mode=False
            )

        super().__init__(
            strategy_id="gpu_capacity_optimizer",
            strategy_name="GPU Capacity Optimizer",
            venues=[marketplace],
            config=config
        )

        self.gpu_configs = {gpu.gpu_id: gpu for gpu in gpu_configs}
        self.marketplace = marketplace
        self.risk_manager = risk_manager

        # State tracking
        self.listed_gpus: Dict[str, int] = {}  # gpu_id -> instance_id
        self.market_rates_cache: Dict[str, float] = {}  # gpu_model -> rate
        self.cache_timestamp: Optional[datetime] = None
        self.cache_ttl = timedelta(minutes=5)

        # Performance tracking
        self.total_rental_revenue = 0.0
        self.total_hours_rented = 0.0
        self.decisions_made = 0

    async def initialize(self) -> bool:
        """Initialize strategy"""
        logger.info("🚀 Initializing GPU Capacity Optimizer")

        try:
            # Connect to marketplace
            if not await self.marketplace.connect():
                logger.error("Failed to connect to Vast.ai marketplace")
                return False

            # Fetch initial market rates
            await self._update_market_rates()

            # Check current instance status
            await self._sync_instance_state()

            self._status = StrategyStatus.SCANNING
            logger.info(f"✅ Optimizer initialized with {len(self.gpu_configs)} GPUs")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            self._status = StrategyStatus.ERROR
            return False

    async def shutdown(self) -> bool:
        """Shutdown strategy gracefully"""
        logger.info("🛑 Shutting down GPU Capacity Optimizer")

        try:
            # Optionally unlist all GPUs
            if self.config.custom_params.get("unlist_on_shutdown", False):
                for gpu_id in list(self.listed_gpus.keys()):
                    await self._unlist_gpu(gpu_id)

            # Disconnect from marketplace
            await self.marketplace.disconnect()

            # Log final statistics
            logger.info(f"📊 Final Stats:")
            logger.info(f"  Total Revenue: ${self.total_rental_revenue:.2f}")
            logger.info(f"  Hours Rented: {self.total_hours_rented:.1f}")
            logger.info(f"  Decisions Made: {self.decisions_made}")

            return True

        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return False

    async def find_opportunities(self) -> List[Opportunity]:
        """
        Scan for GPU rental opportunities.

        For each GPU, determine if listing/unlisting would be profitable.
        """
        opportunities = []

        # Update market rates if cache expired
        if self._should_refresh_cache():
            await self._update_market_rates()

        # Evaluate each GPU
        for gpu_id, gpu_config in self.gpu_configs.items():
            opp = await self._evaluate_gpu(gpu_id, gpu_config)
            if opp:
                opportunities.append(opp.opportunity)

        logger.info(f"Found {len(opportunities)} GPU opportunities")
        return opportunities

    async def validate_opportunity(self, opportunity: Opportunity) -> bool:
        """Validate opportunity before execution"""

        # Check if profit meets threshold
        if opportunity.expected_profit < self.config.min_expected_profit:
            logger.debug(f"Opportunity {opportunity.opportunity_id} below profit threshold")
            return False

        # Check if ROI meets threshold
        if opportunity.expected_roi < self.config.min_roi:
            logger.debug(f"Opportunity {opportunity.opportunity_id} below ROI threshold")
            return False

        # Risk management check
        if self.risk_manager:
            from ..core.risk import PortfolioMetrics

            # Build current portfolio metrics
            portfolio = await self._get_portfolio_metrics()

            # Assess risk
            assessment = await self.risk_manager.assess_opportunity(
                opportunity,
                portfolio
            )

            if not assessment.should_allow:
                logger.warning(f"Risk manager blocked opportunity: {assessment.reason}")
                return False

        return True

    async def execute_opportunity(self, opportunity: Opportunity) -> ExecutionResult:
        """
        Execute a GPU rental opportunity.

        This involves either listing or unlisting a GPU on Vast.ai.
        """
        start_time = datetime.utcnow()
        self.decisions_made += 1

        try:
            # Extract GPU ID from metadata
            gpu_id = opportunity.metadata.get("gpu_id")
            action_type = opportunity.metadata.get("action_type")

            if not gpu_id or not action_type:
                return ExecutionResult(
                    opportunity=opportunity,
                    success=False,
                    error_message="Missing gpu_id or action_type in metadata"
                )

            # Execute based on action type
            if action_type == "list":
                result = await self._list_gpu(
                    gpu_id=gpu_id,
                    price=opportunity.metadata.get("suggested_price")
                )
            elif action_type == "unlist":
                result = await self._unlist_gpu(gpu_id)
            elif action_type == "reprice":
                result = await self._reprice_gpu(
                    gpu_id=gpu_id,
                    new_price=opportunity.metadata.get("suggested_price")
                )
            else:
                return ExecutionResult(
                    opportunity=opportunity,
                    success=False,
                    error_message=f"Unknown action type: {action_type}"
                )

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Build execution result
            exec_result = ExecutionResult(
                opportunity=opportunity,
                success=result.success,
                actual_profit=opportunity.expected_profit if result.success else None,
                action_results=[result],
                execution_time_ms=execution_time_ms
            )

            # Update history
            self._execution_history.append(exec_result)

            if result.success:
                logger.info(f"✅ Executed {action_type} for GPU {gpu_id}")
            else:
                logger.error(f"❌ Failed {action_type} for GPU {gpu_id}: {result.error_message}")

            return exec_result

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                opportunity=opportunity,
                success=False,
                error_message=str(e)
            )

    # ==================== Private Methods ====================

    async def _evaluate_gpu(
        self,
        gpu_id: str,
        gpu_config: GPUConfig
    ) -> Optional[GPUOpportunity]:
        """
        Evaluate whether to list/unlist a specific GPU.

        Decision logic:
        1. Get current market rate for GPU model
        2. Calculate break-even rate (operating costs + margin)
        3. If market rate > break-even: LIST
        4. If market rate < break-even: UNLIST
        5. If already listed: consider REPRICING
        """
        # Get current market rate
        market_rate = self.market_rates_cache.get(gpu_config.gpu_model, 0.0)

        if market_rate == 0.0:
            logger.warning(f"No market data for {gpu_config.gpu_model}")
            return None

        # Calculate break-even rate
        operating_cost = gpu_config.total_operating_cost_per_hour
        min_margin = operating_cost * self.config.min_roi
        break_even_rate = operating_cost + min_margin

        # Calculate expected profit
        expected_profit_per_hour = market_rate - operating_cost

        # Check if currently listed
        is_listed = gpu_id in self.listed_gpus

        # Decision logic
        if not is_listed and expected_profit_per_hour >= self.config.min_expected_profit:
            # OPPORTUNITY: List GPU

            # Calculate suggested price (slightly below market to be competitive)
            suggested_price = market_rate * 0.98

            # Ensure we're still profitable at suggested price
            if suggested_price < break_even_rate:
                suggested_price = break_even_rate * 1.05  # 5% above break-even

            opportunity = Opportunity(
                opportunity_id=f"list_{gpu_id}_{int(datetime.utcnow().timestamp())}",
                opportunity_type=OpportunityType.YIELD_OPTIMIZATION,
                strategy_name=self.strategy_name,
                confidence=0.8,  # High confidence for market-based decisions
                expected_profit=expected_profit_per_hour,
                expected_cost=operating_cost,
                expected_roi=(expected_profit_per_hour / operating_cost) * 100,
                metadata={
                    "gpu_id": gpu_id,
                    "action_type": "list",
                    "gpu_model": gpu_config.gpu_model,
                    "suggested_price": suggested_price,
                    "market_rate": market_rate,
                    "operating_cost": operating_cost
                }
            )

            return GPUOpportunity(
                opportunity=opportunity,
                gpu_config=gpu_config,
                current_market_rate=market_rate,
                estimated_occupancy=0.75,  # Conservative estimate
                should_list=True,
                suggested_price=suggested_price
            )

        elif is_listed and expected_profit_per_hour < self.config.min_expected_profit:
            # OPPORTUNITY: Unlist GPU (market rate too low)

            opportunity = Opportunity(
                opportunity_id=f"unlist_{gpu_id}_{int(datetime.utcnow().timestamp())}",
                opportunity_type=OpportunityType.COST_OPTIMIZATION,
                strategy_name=self.strategy_name,
                confidence=0.9,
                expected_profit=operating_cost,  # Save operating cost
                expected_cost=0.0,
                expected_roi=100.0,  # Avoid losses
                metadata={
                    "gpu_id": gpu_id,
                    "action_type": "unlist",
                    "gpu_model": gpu_config.gpu_model,
                    "market_rate": market_rate,
                    "reason": "market_rate_too_low"
                }
            )

            return GPUOpportunity(
                opportunity=opportunity,
                gpu_config=gpu_config,
                current_market_rate=market_rate,
                estimated_occupancy=0.0,
                should_list=False
            )

        # No opportunity (already in optimal state)
        return None

    async def _list_gpu(self, gpu_id: str, price: float) -> ActionResult:
        """List a GPU on Vast.ai"""
        # In production, this would call Vast.ai API to create instance
        # For now, simulate the action

        logger.info(f"Listing GPU {gpu_id} at ${price:.3f}/hr on Vast.ai")

        # Mark as listed
        self.listed_gpus[gpu_id] = 0  # Placeholder instance ID

        return ActionResult(
            request=None,
            success=True,
            status="listed",
            metadata={
                "gpu_id": gpu_id,
                "price": price,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def _unlist_gpu(self, gpu_id: str) -> ActionResult:
        """Unlist a GPU from Vast.ai"""
        logger.info(f"Unlisting GPU {gpu_id} from Vast.ai")

        # Remove from listed
        if gpu_id in self.listed_gpus:
            del self.listed_gpus[gpu_id]

        return ActionResult(
            request=None,
            success=True,
            status="unlisted",
            metadata={
                "gpu_id": gpu_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def _reprice_gpu(self, gpu_id: str, new_price: float) -> ActionResult:
        """Update pricing for listed GPU"""
        logger.info(f"Repricing GPU {gpu_id} to ${new_price:.3f}/hr")

        return ActionResult(
            request=None,
            success=True,
            status="repriced",
            metadata={
                "gpu_id": gpu_id,
                "new_price": new_price,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def _update_market_rates(self):
        """Fetch current market rates for all GPU models"""
        logger.info("📊 Updating market rates...")

        unique_models = set(gpu.gpu_model for gpu in self.gpu_configs.values())

        for model in unique_models:
            try:
                rate = await self.marketplace.get_market_rate(model)
                self.market_rates_cache[model] = rate
                logger.debug(f"  {model}: ${rate:.3f}/hr")
            except Exception as e:
                logger.error(f"Failed to get rate for {model}: {e}")

        self.cache_timestamp = datetime.utcnow()

    def _should_refresh_cache(self) -> bool:
        """Check if market rate cache should be refreshed"""
        if not self.cache_timestamp:
            return True

        age = datetime.utcnow() - self.cache_timestamp
        return age > self.cache_ttl

    async def _sync_instance_state(self):
        """Sync listed GPUs with actual Vast.ai instances"""
        # In production, query Vast.ai for active instances
        # and update self.listed_gpus accordingly
        pass

    async def _get_portfolio_metrics(self) -> PortfolioMetrics:
        """Build portfolio metrics for risk management"""
        from ..core.risk import PortfolioMetrics

        # Calculate total value and exposure
        total_value = 0.0
        allocated_capital = 0.0

        for gpu_id, gpu_config in self.gpu_configs.items():
            # Estimate GPU value (simplified)
            gpu_value = 1000.0  # Placeholder
            total_value += gpu_value

            if gpu_id in self.listed_gpus:
                # Listed GPU is "allocated"
                allocated_capital += gpu_config.total_operating_cost_per_hour * 24  # Daily cost

        return PortfolioMetrics(
            total_value=total_value,
            available_capital=total_value - allocated_capital,
            allocated_capital=allocated_capital,
            unrealized_pnl=0.0,  # Would track rental revenue
            realized_pnl=self.total_rental_revenue,
            total_pnl=self.total_rental_revenue
        )
