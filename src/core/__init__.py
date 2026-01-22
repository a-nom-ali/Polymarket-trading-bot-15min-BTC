"""
Core Abstraction Layer

This package provides the generic abstraction layer that enables the platform
to work across multiple domains: trading, GPU allocation, ad optimization,
ecommerce arbitrage, and more.

Key Modules:
- asset: Asset abstraction (tradeable/optimizable resources)
- venue: Venue abstraction (marketplaces/platforms)
- strategy: Strategy abstraction (automated decision logic)
- risk: Risk management and constraint enforcement
- graph_runtime: Node-graph execution engine
- adapters: Domain-specific implementations
"""

from .asset import (
    Asset,
    AssetType,
    AssetState,
    AssetMetadata,
    AssetValuation,
    AssetPosition,
    FinancialAsset,
    ComputeAsset,
    AdInventoryAsset,
    ProductSKU
)

from .venue import (
    Venue,
    VenueType,
    VenueStatus,
    VenueCapabilities,
    VenueCredentials,
    ActionType,
    ActionRequest,
    ActionResult
)

from .strategy import (
    Strategy,
    OpportunityType,
    OpportunityStatus,
    Opportunity,
    ExecutionResult,
    StrategyStatus,
    StrategyExecutionMode,
    StrategyConfig
)

from .risk import (
    RiskManager,
    RiskLevel,
    RiskConstraint,
    RiskAssessment,
    PortfolioMetrics,
    ConstraintType,
    DefaultRiskManager
)

from .graph_runtime import (
    Node,
    NodeCategory,
    NodeStatus,
    NodeInput,
    NodeOutput,
    NodeConnection,
    NodeExecutionContext,
    NodeExecutionResult,
    StrategyGraph,
    GraphRuntime,
    GraphExecutionStatus,
    GraphExecutionResult,
    register_node_type,
    create_node
)

__all__ = [
    # Asset
    'Asset',
    'AssetType',
    'AssetState',
    'AssetMetadata',
    'AssetValuation',
    'AssetPosition',
    'FinancialAsset',
    'ComputeAsset',
    'AdInventoryAsset',
    'ProductSKU',
    # Venue
    'Venue',
    'VenueType',
    'VenueStatus',
    'VenueCapabilities',
    'VenueCredentials',
    'ActionType',
    'ActionRequest',
    'ActionResult',
    # Strategy
    'Strategy',
    'OpportunityType',
    'OpportunityStatus',
    'Opportunity',
    'ExecutionResult',
    'StrategyStatus',
    'StrategyExecutionMode',
    'StrategyConfig',
    # Risk
    'RiskManager',
    'RiskLevel',
    'RiskConstraint',
    'RiskAssessment',
    'PortfolioMetrics',
    'ConstraintType',
    'DefaultRiskManager',
    # Graph Runtime
    'Node',
    'NodeCategory',
    'NodeStatus',
    'NodeInput',
    'NodeOutput',
    'NodeConnection',
    'NodeExecutionContext',
    'NodeExecutionResult',
    'StrategyGraph',
    'GraphRuntime',
    'GraphExecutionStatus',
    'GraphExecutionResult',
    'register_node_type',
    'create_node',
]
