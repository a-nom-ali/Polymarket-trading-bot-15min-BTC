"""
GPU-Specific Workflow Nodes

Specialized nodes for GPU capacity optimization workflows.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..core.graph_runtime import (
    Node,
    NodeCategory,
    NodeInput,
    NodeOutput,
    NodeExecutionContext,
    NodeExecutionResult,
    NodeStatus,
    register_node_type
)
from ..integrations.vastai import VastAIMarketplace


@register_node_type("gpu_market_rate")
class GPUMarketRateNode(Node):
    """
    Fetch current market rental rate for a GPU model from Vast.ai.

    Outputs:
    - median_rate: Median market rate ($/hour)
    - min_rate: Minimum available rate
    - max_rate: Maximum rate
    - offer_count: Number of available offers
    """

    def __init__(
        self,
        node_id: str,
        marketplace: VastAIMarketplace,
        gpu_model: str,
        **kwargs
    ):
        super().__init__(
            node_id=node_id,
            node_type="gpu_market_rate",
            category=NodeCategory.SOURCE,
            inputs=[],
            outputs=[
                NodeOutput(name="median_rate", data_type="number"),
                NodeOutput(name="min_rate", data_type="number"),
                NodeOutput(name="max_rate", data_type="number"),
                NodeOutput(name="mean_rate", data_type="number"),
                NodeOutput(name="offer_count", data_type="number")
            ],
            config={"gpu_model": gpu_model}
        )
        self.marketplace = marketplace
        self.gpu_model = gpu_model

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Fetch GPU market rates"""
        start_time = datetime.utcnow()

        try:
            # Get market prices from Vast.ai
            stats = await self.marketplace.client.get_market_prices(
                gpu_name=self.gpu_model,
                limit=50
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "median_rate": stats["median"],
                    "min_rate": stats["min"],
                    "max_rate": stats["max"],
                    "mean_rate": stats["mean"],
                    "offer_count": stats["count"]
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


@register_node_type("gpu_operating_cost")
class GPUOperatingCostNode(Node):
    """
    Calculate GPU operating costs (power + maintenance).

    Inputs:
    - power_watts: GPU power consumption in watts
    - power_cost_per_kwh: Electricity cost ($/kWh)

    Outputs:
    - power_cost_per_hour: Power cost in $/hour
    - maintenance_cost_per_hour: Maintenance cost
    - total_cost_per_hour: Total operating cost
    """

    def __init__(
        self,
        node_id: str,
        maintenance_cost_per_hour: float = 0.02,
        **kwargs
    ):
        super().__init__(
            node_id=node_id,
            node_type="gpu_operating_cost",
            category=NodeCategory.TRANSFORM,
            inputs=[
                NodeInput(name="power_watts", data_type="number", required=True),
                NodeInput(name="power_cost_per_kwh", data_type="number", required=True)
            ],
            outputs=[
                NodeOutput(name="power_cost_per_hour", data_type="number"),
                NodeOutput(name="maintenance_cost_per_hour", data_type="number"),
                NodeOutput(name="total_cost_per_hour", data_type="number")
            ],
            config={"maintenance_cost_per_hour": maintenance_cost_per_hour}
        )
        self.maintenance_cost_per_hour = maintenance_cost_per_hour

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Calculate operating costs"""
        start_time = datetime.utcnow()

        try:
            power_watts = context.inputs.get("power_watts", 0)
            power_cost_per_kwh = context.inputs.get("power_cost_per_kwh", 0.12)

            # Calculate power cost
            kwh = power_watts / 1000.0
            power_cost_per_hour = kwh * power_cost_per_kwh

            # Total cost
            total_cost_per_hour = power_cost_per_hour + self.maintenance_cost_per_hour

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "power_cost_per_hour": power_cost_per_hour,
                    "maintenance_cost_per_hour": self.maintenance_cost_per_hour,
                    "total_cost_per_hour": total_cost_per_hour
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


@register_node_type("gpu_profitability")
class GPUProfitabilityNode(Node):
    """
    Determine if renting out a GPU is profitable.

    Inputs:
    - market_rate: Current market rental rate ($/hour)
    - operating_cost: Total operating cost ($/hour)
    - min_margin_pct: Minimum profit margin percentage

    Outputs:
    - is_profitable: Boolean indicating if profitable
    - profit_per_hour: Expected profit ($/hour)
    - margin_pct: Profit margin percentage
    - suggested_price: Suggested listing price
    """

    def __init__(self, node_id: str, **kwargs):
        super().__init__(
            node_id=node_id,
            node_type="gpu_profitability",
            category=NodeCategory.SCORER,
            inputs=[
                NodeInput(name="market_rate", data_type="number", required=True),
                NodeInput(name="operating_cost", data_type="number", required=True),
                NodeInput(name="min_margin_pct", data_type="number", required=False, default_value=25.0)
            ],
            outputs=[
                NodeOutput(name="is_profitable", data_type="boolean"),
                NodeOutput(name="profit_per_hour", data_type="number"),
                NodeOutput(name="margin_pct", data_type="number"),
                NodeOutput(name="suggested_price", data_type="number")
            ]
        )

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Determine profitability"""
        start_time = datetime.utcnow()

        try:
            market_rate = context.inputs.get("market_rate", 0)
            operating_cost = context.inputs.get("operating_cost", 0)
            min_margin_pct = context.inputs.get("min_margin_pct", 25.0)

            # Calculate profit
            profit_per_hour = market_rate - operating_cost

            # Calculate margin
            margin_pct = (profit_per_hour / operating_cost * 100) if operating_cost > 0 else 0

            # Determine if profitable
            is_profitable = margin_pct >= min_margin_pct

            # Suggested price (slightly below market to be competitive)
            suggested_price = market_rate * 0.98

            # Ensure suggested price still meets minimum margin
            min_price = operating_cost * (1 + min_margin_pct / 100)
            if suggested_price < min_price:
                suggested_price = min_price

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "is_profitable": is_profitable,
                    "profit_per_hour": profit_per_hour,
                    "margin_pct": margin_pct,
                    "suggested_price": suggested_price
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


@register_node_type("gpu_list_action")
class GPUListActionNode(Node):
    """
    List a GPU on Vast.ai marketplace.

    Inputs:
    - gpu_id: GPU identifier
    - price: Listing price ($/hour)

    Outputs:
    - success: Whether listing succeeded
    - instance_id: Vast.ai instance ID
    """

    def __init__(
        self,
        node_id: str,
        marketplace: VastAIMarketplace,
        **kwargs
    ):
        super().__init__(
            node_id=node_id,
            node_type="gpu_list_action",
            category=NodeCategory.EXECUTOR,
            inputs=[
                NodeInput(name="gpu_id", data_type="string", required=True),
                NodeInput(name="price", data_type="number", required=True)
            ],
            outputs=[
                NodeOutput(name="success", data_type="boolean"),
                NodeOutput(name="instance_id", data_type="string"),
                NodeOutput(name="message", data_type="string")
            ]
        )
        self.marketplace = marketplace

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """List GPU on marketplace"""
        start_time = datetime.utcnow()

        try:
            gpu_id = context.inputs.get("gpu_id")
            price = context.inputs.get("price")

            # In production, this would call Vast.ai API to list the GPU
            # For now, simulate success
            success = True
            instance_id = f"instance_{gpu_id}_{int(datetime.utcnow().timestamp())}"
            message = f"Listed GPU {gpu_id} at ${price:.3f}/hr"

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "success": success,
                    "instance_id": instance_id,
                    "message": message
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


# Export all GPU node types
__all__ = [
    'GPUMarketRateNode',
    'GPUOperatingCostNode',
    'GPUProfitabilityNode',
    'GPUListActionNode',
]
