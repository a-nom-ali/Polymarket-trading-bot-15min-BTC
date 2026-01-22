# Generic Abstraction Layer: Multi-Domain Automation Platform

## Overview

This abstraction layer transforms the trading bot platform into a **universal automation-for-profit engine** that works across any domain where there is:

1. **A definable asset** (financial instrument, GPU capacity, ad inventory, product SKU)
2. **A price/quality signal** (market price, rental rate, ROAS, profit margin)
3. **An executable action** (buy/sell, allocate/deallocate, enable/pause, list/unlist)

The same node-graph infrastructure, workflow engine, and risk management system now power automation across **trading, GPU marketplaces, ad platforms, ecommerce arbitrage, and beyond**.

---

## Architecture

### Core Abstractions

The abstraction layer consists of **four core interfaces** that generalize across all domains:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Asset    │────▶│    Venue    │────▶│  Strategy   │────▶│    Risk     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                   │                    │                    │
     │                   │                    │                    │
  Financial         Exchanges           Arbitrage          Position Limits
  GPU Capacity      Marketplaces        Momentum           Loss Limits
  Ad Inventory      Ad Platforms        Optimization       Budget Caps
  Product SKU       Ecommerce           Mean Reversion     Frequency Limits
```

### 1. Asset Abstraction (`src/core/asset.py`)

**Purpose**: Represents any tradeable or optimizable asset.

**Key Concepts**:
- `Asset` base class with domain-agnostic operations
- `AssetValuation` for pricing/quality metrics
- `AssetPosition` for current holdings
- Domain-specific implementations: `FinancialAsset`, `ComputeAsset`, `AdInventoryAsset`, `ProductSKU`

**Example**:
```python
# Financial asset
btc = FinancialAsset(
    asset_id="binance:BTC-USDT",
    symbol="BTC-USDT",
    base_currency="BTC",
    quote_currency="USDT"
)

# GPU capacity asset
gpu = ComputeAsset(
    asset_id="gpu:rtx4090-001",
    symbol="RTX4090",
    specs={"vram": "24GB", "cuda_cores": 16384}
)

# Both use the same interface
valuation = await btc.fetch_current_valuation()  # Returns market price
valuation = await gpu.fetch_current_valuation()  # Returns rental rate $/hour
```

**Cross-Domain Asset Types**:
- `FINANCIAL_SPOT` - Stocks, crypto, forex
- `FINANCIAL_DERIVATIVE` - Futures, options, perpetuals
- `FINANCIAL_BINARY` - Binary outcome markets (Polymarket, Kalshi)
- `COMPUTE_CAPACITY` - GPU/CPU rental (Vast.ai, RunPod)
- `AD_INVENTORY` - Ad impressions/clicks (Google, Meta, TikTok)
- `PRODUCT_SKU` - Physical/digital products (Amazon, eBay)
- `CREDIT_YIELD` - Lending/borrowing opportunities
- `ENERGY` - Electricity, carbon credits

---

### 2. Venue Abstraction (`src/core/venue.py`)

**Purpose**: Represents any marketplace or platform where assets can be traded or allocated.

**Key Concepts**:
- `Venue` base class with standardized action execution
- `VenueCapabilities` defines what actions are supported
- `ActionRequest` / `ActionResult` for unified action handling
- Domain-specific implementations: `TradingVenueAdapter`, `ComputeMarketplaceAdapter`, `AdPlatformAdapter`, `EcommerceMarketplaceAdapter`

**Example**:
```python
# Trading exchange
binance = TradingVenueAdapter(
    provider=binance_provider,
    credentials=VenueCredentials(api_key=..., api_secret=...)
)

# GPU marketplace
vastai = ComputeMarketplaceAdapter(
    marketplace_name="vast.ai",
    api_key="...",
    owned_gpus=[...]
)

# Both use the same interface
await binance.connect()
await vastai.connect()

# Execute actions with the same pattern
action = ActionRequest(
    action_type=ActionType.PLACE_ORDER,  # or ALLOCATE for GPU
    asset=btc,
    quantity=0.1,
    price=50000
)
result = await binance.execute_action(action)
```

**Cross-Domain Venue Types**:
- `EXCHANGE_SPOT` - Spot trading exchanges
- `EXCHANGE_DERIVATIVE` - Futures/options exchanges
- `PREDICTION_MARKET` - Binary outcome markets
- `COMPUTE_MARKETPLACE` - GPU/CPU rental platforms
- `AD_PLATFORM` - Advertising networks
- `ECOMMERCE_MARKETPLACE` - Product marketplaces
- `LENDING_PLATFORM` - DeFi/CeFi lending

**Cross-Domain Action Types**:
- `PLACE_ORDER` / `CANCEL_ORDER` - Trading
- `ALLOCATE` / `DEALLOCATE` - Resource allocation
- `CREATE_LISTING` / `UPDATE_LISTING` - Ecommerce
- `SET_BUDGET` / `ADJUST_BID` - Advertising
- `SET_PRICE` / `SET_CAPACITY` - Dynamic pricing

---

### 3. Strategy Abstraction (`src/core/strategy.py`)

**Purpose**: Automated strategy that finds opportunities and executes actions across domains.

**Key Concepts**:
- `Strategy` base class for all automation logic
- `Opportunity` represents detected profit/optimization potential
- `OpportunityType` enum: arbitrage, market making, yield optimization, cost optimization, etc.
- `ExecutionResult` tracks actual vs expected outcomes

**Example**:
```python
class CrossDomainArbitrageStrategy(Strategy):
    async def find_opportunities(self) -> List[Opportunity]:
        # Works across ANY domain that implements Asset/Venue interfaces
        opportunities = []

        for venue_a in self.venues:
            for venue_b in self.venues:
                if venue_a == venue_b:
                    continue

                # Price differential = opportunity
                asset_a = await venue_a.get_asset(self.symbol)
                asset_b = await venue_b.get_asset(self.symbol)

                val_a = await asset_a.fetch_current_valuation()
                val_b = await asset_b.fetch_current_valuation()

                if val_a.current_value < val_b.current_value:
                    profit = val_b.current_value - val_a.current_value

                    opp = Opportunity(
                        opportunity_id=f"arb_{time.time()}",
                        opportunity_type=OpportunityType.ARBITRAGE,
                        expected_profit=profit,
                        confidence=0.9,
                        primary_asset=asset_a,
                        primary_venue=venue_a,
                        secondary_asset=asset_b,
                        secondary_venue=venue_b
                    )
                    opportunities.append(opp)

        return opportunities
```

**Strategy Execution Modes**:
- `POLLING` - Scan at regular intervals (traditional algo trading)
- `EVENT_DRIVEN` - React to real-time events (high-frequency trading)
- `HYBRID` - Both polling and events
- `ON_DEMAND` - Execute only when manually triggered

---

### 4. Risk Management Abstraction (`src/core/risk.py`)

**Purpose**: Unified risk assessment and constraint enforcement across all domains.

**Key Concepts**:
- `RiskManager` base class with domain-agnostic checks
- `RiskConstraint` defines limits (position size, daily loss, frequency, etc.)
- `RiskAssessment` evaluates actions before execution
- `PortfolioMetrics` tracks current exposure and performance

**Example**:
```python
# Works the same across trading, GPU, ads, ecommerce
risk_manager = DefaultRiskManager(constraints=[
    RiskConstraint(
        constraint_type=ConstraintType.POSITION_SIZE,
        name="max_position",
        limit=10000.0  # Max $10k per position
    ),
    RiskConstraint(
        constraint_type=ConstraintType.DAILY_LOSS,
        name="daily_loss_limit",
        limit=500.0  # Max $500 loss per day
    ),
    RiskConstraint(
        constraint_type=ConstraintType.FREQUENCY,
        name="trade_frequency",
        limit=50,  # Max 50 actions per day
        time_window=timedelta(days=1)
    )
])

# Assess any action
assessment = await risk_manager.assess_action(action, current_portfolio)

if assessment.should_allow:
    await venue.execute_action(action)
else:
    print(f"Blocked: {assessment.reason}")
```

**Cross-Domain Constraint Types**:
- `POSITION_SIZE` - Max allocation per asset
- `CAPITAL_ALLOCATION` - Max capital per action
- `DAILY_LOSS` - Max loss per day
- `TOTAL_EXPOSURE` - Max total exposure across all positions
- `FREQUENCY` - Max actions per time period
- `CONCENTRATION` - Max % in single asset/venue
- `VOLATILITY` - Volatility thresholds
- `DRAWDOWN` - Max drawdown percentage

---

### 5. Graph Runtime (`src/core/graph_runtime.py`)

**Purpose**: Execute node-based strategy graphs across all domains.

**Key Concepts**:
- `StrategyGraph` - DAG of nodes and connections
- `Node` - Discrete operation (data fetch, transform, condition, action)
- `GraphRuntime` - Execution engine with topological ordering
- `NodeCategory` - SOURCE, TRANSFORM, CONDITION, SCORER, RISK, OPTIMIZER, EXECUTOR, MONITOR, GATE

**Example**:
```python
# Create a strategy graph
graph = StrategyGraph(
    graph_id="multi_asset_arb",
    name="Multi-Asset Arbitrage"
)

# Add nodes (same pattern for trading, GPU, ads, ecommerce)
source_a = PriceSourceNode(venue=binance, asset=btc)
source_b = PriceSourceNode(venue=coinbase, asset=btc)
comparator = CompareNode(operation="spread")
risk_check = RiskNode(risk_manager=risk_mgr)
executor = ExecutorNode(action_type=ActionType.PLACE_ORDER)

graph.add_node(source_a)
graph.add_node(source_b)
graph.add_node(comparator)
graph.add_node(risk_check)
graph.add_node(executor)

# Connect nodes
graph.add_connection(NodeConnection(
    from_node_id=source_a.node_id, from_output_index=0,
    to_node_id=comparator.node_id, to_input_index=0
))
# ... more connections

# Execute graph
runtime = GraphRuntime(graph)
result = await runtime.execute()
```

**Node Types** (all work across domains):
- **SOURCE**: Fetch data from venues/APIs
- **TRANSFORM**: Calculate indicators, spreads, ratios
- **CONDITION**: If/then, compare, filter logic
- **SCORER**: Rank opportunities by profitability
- **RISK**: Check constraints before execution
- **OPTIMIZER**: Position sizing, portfolio allocation
- **EXECUTOR**: Execute actions on venues
- **MONITOR**: Track results, send alerts
- **GATE**: Human approval for high-risk actions

---

## Domain Adapters

Adapters bridge the generic abstractions with domain-specific APIs and logic.

### Trading Adapter (`src/core/adapters/trading.py`)

**Maps**:
- `BaseProvider` (Binance, Coinbase, etc.) → `Venue`
- Trading pairs → `FinancialAsset`
- Orders → `ActionRequest`/`ActionResult`

**Example**:
```python
from src.providers.binance import BinanceProvider
from src.core.adapters.trading import TradingVenueAdapter

provider = BinanceProvider(api_key=..., api_secret=...)
venue = TradingVenueAdapter(provider=provider)

await venue.connect()
assets = await venue.list_assets()  # All trading pairs as FinancialAsset
```

---

### GPU/Compute Adapter (`src/core/adapters/compute.py`)

**Maps**:
- GPU capacity → `ComputeAsset`
- Vast.ai / RunPod API → `ComputeMarketplaceAdapter`
- Rental actions → `ActionRequest` with `ALLOCATE`/`DEALLOCATE`/`SET_PRICE`

**Example Strategy**:
```python
# Rent out GPU when market rate > power cost + margin
strategy = GPUCapacityStrategy(
    gpu_asset=rtx4090,
    marketplace=vastai,
    power_cost_per_hour=0.12,
    min_profit_margin=0.25
)

await strategy.execute()  # Automatically lists or delists GPU
```

---

### Advertising Adapter (`src/core/adapters/advertising.py`)

**Maps**:
- Ad campaigns → `AdInventoryAsset`
- Google Ads / Meta Ads API → `AdPlatformAdapter`
- Budget/bid actions → `ActionRequest` with `SET_BUDGET`/`ADJUST_BID`

**Example Strategy**:
```python
# Reallocate budget to high-ROAS campaigns
optimizer = AdBudgetOptimizer(
    campaigns=[awareness_campaign, conversion_campaign],
    platform=meta_ads,
    total_budget=5000.0,
    min_roas=2.0  # Pause campaigns with ROAS < 2.0
)

await optimizer.optimize()  # Automatically adjusts budgets
```

---

### Ecommerce Adapter (`src/core/adapters/ecommerce.py`)

**Maps**:
- Product SKUs → `ProductSKUAdapter`
- Amazon / eBay API → `EcommerceMarketplaceAdapter`
- Listing actions → `ActionRequest` with `CREATE_LISTING`/`UPDATE_LISTING`

**Example Strategy**:
```python
# Find and list profitable products
arbitrage = ProductArbitrageStrategy(
    products=[headphones, yoga_mat],
    marketplace=amazon,
    min_roi_pct=30.0,
    min_monthly_sales=20
)

result = await arbitrage.execute_top_opportunity()  # Lists most profitable product
```

---

## Integration with Existing System

### How It Works with Current Architecture

The abstraction layer **wraps and extends** the existing system:

```
┌──────────────────────────────────────────────────────────────┐
│                   Existing System                            │
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ BaseProvider│    │BaseStrategy │    │ RiskManager │     │
│  │   (8 impl)  │    │  (11 impl)  │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │            │
└─────────┼───────────────────┼───────────────────┼────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────┐
│              Abstraction Layer (NEW)                         │
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │    Asset    │    │   Strategy   │    │    Risk     │     │
│  │   Venue     │    │Opportunity   │    │  Constraint │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │            │
└─────────┼───────────────────┼───────────────────┼────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────┐
│           Domain Adapters (NEW)                              │
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Trading   │    │     GPU     │    │     Ads     │     │
│  │  Ecommerce  │    │   Credit    │    │   Energy    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

**Migration Path**:

1. **Phase 1** (Current): Trading domain uses abstraction layer
   - Existing `BaseProvider` wrapped by `TradingVenueAdapter`
   - Existing strategies can extend `Strategy` base class
   - Existing risk manager wrapped by `RiskManager` interface

2. **Phase 2**: Add new domains one at a time
   - Implement GPU adapter → instant access to all existing infrastructure
   - Implement Ad adapter → reuse same workflow engine, risk system, UI
   - Implement Ecommerce adapter → same patterns, minimal new code

3. **Phase 3**: Unified dashboard
   - All bots (trading, GPU, ads, ecommerce) in same UI
   - Cross-domain portfolio view
   - Unified P&L tracking across all domains

---

## Workflow System Integration

The existing workflow system (`src/workflow/executor.py`) **already supports** the abstraction layer:

**Current Workflow Blocks**:
```json
{
  "blocks": [
    {"category": "providers", "type": "binance"},
    {"category": "triggers", "type": "price_cross"},
    {"category": "actions", "type": "buy"}
  ]
}
```

**Extended for Multi-Domain**:
```json
{
  "blocks": [
    {"category": "providers", "type": "vastai", "asset_type": "compute_capacity"},
    {"category": "triggers", "type": "price_cross"},
    {"category": "actions", "type": "allocate"}
  ]
}
```

**Universal Workflow**:
```json
{
  "name": "Universal Arbitrage",
  "blocks": [
    {
      "id": "source_1",
      "category": "source",
      "type": "venue_price",
      "config": {"venue_id": "binance", "asset_id": "BTC-USDT"}
    },
    {
      "id": "source_2",
      "category": "source",
      "type": "venue_price",
      "config": {"venue_id": "coinbase", "asset_id": "BTC-USD"}
    },
    {
      "id": "compare",
      "category": "condition",
      "type": "compare",
      "config": {"operation": "spread_pct", "threshold": 0.5}
    },
    {
      "id": "risk",
      "category": "risk",
      "type": "assess_action"
    },
    {
      "id": "execute",
      "category": "executor",
      "type": "arbitrage"
    }
  ],
  "connections": [
    {"from": "source_1", "to": "compare"},
    {"from": "source_2", "to": "compare"},
    {"from": "compare", "to": "risk"},
    {"from": "risk", "to": "execute"}
  ]
}
```

Same workflow template works for:
- Trading arbitrage (Binance ↔ Coinbase)
- GPU arbitrage (Rent out when Vast.ai rate > RunPod rate)
- Ad arbitrage (Shift budget from low-ROAS to high-ROAS campaigns)
- Ecommerce arbitrage (Buy from AliExpress, sell on Amazon)

---

## Concrete Use Cases

### 1. Multi-Asset Trading + GPU Optimization

**Scenario**: Run trading bots during market hours, rent out GPUs when market is quiet.

```python
# Morning: Trade crypto
trading_strategy = BinaryArbitrageStrategy(
    venues=[polymarket, kalshi],
    config=StrategyConfig(scan_interval_ms=5000)
)

# Afternoon: Market slows down, GPUs sit idle
# Automatically rent them out on Vast.ai
gpu_strategy = GPUCapacityStrategy(
    gpu_asset=rtx4090,
    marketplace=vastai,
    power_cost_per_hour=0.12
)

# Combined orchestration
orchestrator = MultiDomainOrchestrator(strategies=[
    (trading_strategy, {"active_hours": "9am-5pm"}),
    (gpu_strategy, {"active_hours": "6pm-8am"})
])

await orchestrator.run()  # Switches between domains automatically
```

---

### 2. Cross-Domain Risk Management

**Scenario**: Enforce global daily loss limit across ALL domains.

```python
# One risk manager for everything
global_risk = DefaultRiskManager(constraints=[
    RiskConstraint(
        constraint_type=ConstraintType.DAILY_LOSS,
        name="global_daily_loss",
        limit=1000.0,  # $1000 max loss across trading, GPU, ads, ecommerce
        enforce=True
    )
])

# All domains share the same risk manager
trading_bot.set_risk_manager(global_risk)
gpu_bot.set_risk_manager(global_risk)
ad_bot.set_risk_manager(global_risk)
ecommerce_bot.set_risk_manager(global_risk)

# If trading loses $600, GPU/ads/ecommerce only have $400 budget left
```

---

### 3. Signal Marketplace

**Scenario**: Package strategies as reusable signals that others can subscribe to.

```python
# Create a signal (opportunity detector)
signal = OpportunitySignal(
    signal_id="btc_funding_arb",
    name="BTC Funding Rate Arbitrage",
    strategy=FundingRateStrategy(...)
)

# Publish signal
marketplace = SignalMarketplace()
await marketplace.publish_signal(signal, price_per_month=50.0)

# Others subscribe
subscriber = SignalSubscriber(api_key="...")
signals = await subscriber.subscribe(signal_id="btc_funding_arb")

# When signal fires, subscriber's bot executes
for opportunity in signals:
    await my_bot.execute_opportunity(opportunity)
```

---

## Benefits

### 1. **Code Reuse**
- Write a strategy once, run it across domains
- Same risk management for trading, GPU, ads, ecommerce
- Same workflow engine for all automation

### 2. **Rapid Domain Expansion**
- Adding GPU marketplace support: ~500 lines of adapter code
- Adding ad platform support: ~600 lines of adapter code
- No changes to core strategy, risk, or workflow engine

### 3. **Cross-Domain Intelligence**
- Learn from trading signals to optimize ad budget allocation
- Use GPU market data to inform crypto mining profitability
- Correlate ecommerce demand with social media ad performance

### 4. **Unified User Experience**
- One dashboard for all bots (trading, GPU, ads, ecommerce)
- One risk management interface
- One workflow designer

### 5. **Future-Proof**
- New asset classes (NFTs, carbon credits, bandwidth) → just add adapter
- New venues (new exchanges, marketplaces, platforms) → implement Venue interface
- New strategies → extend Strategy base class

---

## Next Steps

### Immediate (Week 1-2)
1. ✅ **Core abstractions implemented** (Asset, Venue, Strategy, Risk, GraphRuntime)
2. ✅ **Domain adapters created** (Trading, GPU, Ads, Ecommerce)
3. ⏳ **Integrate with existing providers** (wrap `BaseProvider` with `TradingVenueAdapter`)

### Short-term (Week 3-4)
4. **Extend workflow system** to support multi-domain blocks
5. **Add domain-specific node types** (GPUSourceNode, AdMetricsNode, ProductScannerNode)
6. **Build cross-domain dashboard** (unified bot list, P&L across domains)

### Medium-term (Month 2)
7. **Implement first non-trading domain** (GPU marketplace integration)
8. **Create domain-specific strategies** (GPU capacity optimizer, ad budget allocator)
9. **Test cross-domain risk management** (global loss limits, portfolio correlation)

### Long-term (Month 3+)
10. **Signal marketplace** (publish/subscribe to opportunities)
11. **Backtesting across domains** (test GPU strategies on historical spot rates)
12. **AI-powered optimization** (learn optimal allocation across domains)

---

## Technical Reference

### File Structure
```
src/core/
├── asset.py               # Asset abstraction + domain implementations
├── venue.py               # Venue abstraction + action framework
├── strategy.py            # Strategy abstraction + opportunity framework
├── risk.py                # Risk management + constraint enforcement
├── graph_runtime.py       # Node-graph execution engine
└── adapters/
    ├── __init__.py
    ├── trading.py         # Trading domain adapter
    ├── compute.py         # GPU/compute domain adapter
    ├── advertising.py     # Ad platform domain adapter
    └── ecommerce.py       # Ecommerce marketplace adapter
```

### Key Classes

| Class | Purpose | Domain-Agnostic? |
|-------|---------|------------------|
| `Asset` | Tradeable/optimizable asset | ✅ Yes |
| `Venue` | Marketplace/platform | ✅ Yes |
| `Strategy` | Automated decision logic | ✅ Yes |
| `RiskManager` | Constraint enforcement | ✅ Yes |
| `StrategyGraph` | Node-based workflow | ✅ Yes |
| `GraphRuntime` | Execution engine | ✅ Yes |
| `TradingVenueAdapter` | Trading-specific | ❌ Domain |
| `ComputeMarketplaceAdapter` | GPU-specific | ❌ Domain |
| `AdPlatformAdapter` | Advertising-specific | ❌ Domain |
| `EcommerceMarketplaceAdapter` | Ecommerce-specific | ❌ Domain |

---

## FAQ

**Q: Does this replace the existing system?**
A: No, it wraps and extends it. Existing `BaseProvider` and `BaseStrategy` can be used as-is or wrapped with adapters.

**Q: Do I need to rewrite all strategies?**
A: No. Existing strategies work unchanged. New strategies can optionally extend the generic `Strategy` base class for cross-domain support.

**Q: How does this affect performance?**
A: Minimal overhead. The abstraction layer is a thin wrapper that delegates to domain-specific implementations. Most calls are async pass-throughs.

**Q: Can I mix domains in one strategy?**
A: Yes! A strategy can interact with multiple venues across different domains (e.g., trade crypto on Binance while optimizing GPU allocation on Vast.ai).

**Q: What about domain-specific features?**
A: The abstraction provides common operations. Domain-specific features are accessible via `metadata` fields or by accessing the underlying adapter directly.

**Q: How do I add a new domain?**
A: Implement three classes: `<Domain>Asset`, `<Domain>Adapter`, and optionally domain-specific strategies. See `src/core/adapters/compute.py` for reference.

---

## Contributing

To add a new domain:

1. **Create asset adapter** in `src/core/adapters/<domain>.py`
2. **Implement `Asset` interface** for your domain's assets
3. **Implement `Venue` interface** for your domain's marketplaces
4. **Add example strategy** demonstrating domain-specific optimization
5. **Update `src/core/adapters/__init__.py`** to export new adapters
6. **Add tests** in `tests/core/adapters/test_<domain>.py`
7. **Document** in this file under "Domain Adapters"

---

## Conclusion

This abstraction layer transforms a **trading bot platform** into a **universal automation-for-profit engine**. The same infrastructure that powers cryptocurrency arbitrage now powers GPU capacity trading, ad budget optimization, ecommerce arbitrage, and any future domain where profit can be automated.

**The key insight**: Trading is just one instance of a more general pattern—**wherever there's an asset, a price signal, and an executable action, this system can automate it for profit**.
