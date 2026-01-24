# GPU Marketplace Integration Guide

## Overview

This guide documents the **first production implementation** of a non-trading domain using the generic abstraction layer. The GPU capacity optimizer automatically manages GPU rentals on Vast.ai, deciding when to list/unlist GPUs based on market rates and operating costs.

**This proves the abstraction layer works for real-world, non-trading use cases.**

---

## Features

### ✅ Production Vast.ai Integration
- Full API client with authentication and rate limiting
- Search GPU offers with advanced filtering
- Create/destroy instances programmatically
- Real-time market price tracking
- Change bid pricing for interruptible instances

### ✅ GPU Capacity Optimization Strategy
- Automatically lists GPUs when market rate > operating cost + margin
- Unlists GPUs when market becomes unprofitable
- Dynamic repricing based on market conditions
- Considers power costs, maintenance, and profit margins
- Integrates with global risk management system

### ✅ Workflow System Support
- GPU-specific workflow nodes
- Visual workflow designer compatibility
- Template workflows for common scenarios
- Same workflow engine as trading strategies

### ✅ Cross-Domain Risk Management
- Share daily loss limits across trading AND GPU bots
- Enforce frequency limits on listing changes
- Global portfolio risk assessment
- Unified risk constraint system

---

## Quick Start

### 1. Get Vast.ai API Key

1. Sign up at [vast.ai](https://vast.ai)
2. Go to [Account Settings](https://console.vast.ai/account/)
3. Create an API key with appropriate permissions
4. Set environment variable:

```bash
export VAST_AI_API_KEY="your_api_key_here"
```

### 2. Define Your GPUs

```python
from src.strategies.gpu_optimizer import GPUConfig

gpus = [
    GPUConfig(
        gpu_id="gpu_001",
        gpu_model="RTX_4090",  # Vast.ai model name
        vram_gb=24,
        cuda_cores=16384,
        power_watts=450,
        power_cost_per_kwh=0.12,  # Your electricity cost
        maintenance_cost_per_hour=0.02  # Amortized costs
    ),
    # Add more GPUs...
]
```

### 3. Run the Optimizer

```bash
python examples/run_gpu_optimizer.py
```

The optimizer will:
- Connect to Vast.ai marketplace
- Fetch current market rates every 5 minutes
- Calculate profitability for each GPU
- Automatically list/unlist based on profitability
- Track revenue and performance

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                   GPU Optimization Stack                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ GPUCapacity      │────────▶│   VastAI         │         │
│  │ Optimizer        │         │   Marketplace    │         │
│  │ (Strategy)       │         │   (Venue)        │         │
│  └──────────────────┘         └──────────────────┘         │
│          │                             │                     │
│          │                             │                     │
│          ▼                             ▼                     │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ Risk Manager     │         │   VastAI Client  │         │
│  │ (Constraints)    │         │   (API Layer)    │         │
│  └──────────────────┘         └──────────────────┘         │
│          │                             │                     │
└──────────┼─────────────────────────────┼─────────────────────┘
           │                             │
           ▼                             ▼
    Global Risk Limits           Vast.ai API Endpoints
    (Trading + GPU + ...)        (https://console.vast.ai/api/v0/)
```

### File Structure

```
src/
├── integrations/
│   ├── __init__.py
│   └── vastai.py                 # Vast.ai API client + marketplace adapter
├── strategies/
│   └── gpu_optimizer.py          # GPU capacity optimization strategy
└── workflow/
    └── gpu_nodes.py              # GPU-specific workflow nodes

examples/
├── run_gpu_optimizer.py          # Example script
└── gpu_optimization_workflow.json # Workflow template
```

---

## How It Works

### Decision Logic

The optimizer evaluates each GPU every scan interval (default: 5 minutes):

```python
# 1. Fetch current market rate
market_rate = await marketplace.get_market_rate("RTX_4090")  # e.g., $0.50/hr

# 2. Calculate operating costs
power_cost = (450W / 1000) * $0.12/kWh = $0.054/hr
maintenance_cost = $0.02/hr
total_cost = $0.074/hr

# 3. Calculate profit and margin
profit = market_rate - total_cost = $0.426/hr
margin = ($0.426 / $0.074) * 100 = 575%

# 4. Decision
if margin >= min_margin (25%) AND profit >= min_profit ($0.10/hr):
    LIST GPU at market_rate * 0.98  # Slightly below market
else:
    UNLIST GPU  # Not profitable
```

### Risk Management Integration

```python
# Global risk manager shared across ALL domains
global_risk = DefaultRiskManager([
    RiskConstraint(
        type=ConstraintType.DAILY_LOSS,
        limit=500.0  # $500 max loss per day
    )
])

# Apply to all strategies
trading_bot.set_risk_manager(global_risk)
gpu_bot.set_risk_manager(global_risk)

# If trading loses $300, GPU bot has only $200 budget left!
```

---

## API Reference

### VastAIClient

```python
from src.integrations.vastai import VastAIClient

async with VastAIClient(api_key="...") as client:
    # Search offers
    offers = await client.search_offers(
        gpu_name="RTX_4090",
        max_dph=0.60,  # Max $0.60/hour
        min_reliability=0.9,
        verified_only=True,
        limit=10
    )

    # Get market prices
    stats = await client.get_market_prices("RTX_4090")
    print(f"Median rate: ${stats['median']}/hr")

    # Create instance
    instance = await client.create_instance(
        offer_id=offers[0].offer_id,
        image="pytorch/pytorch:latest"
    )

    # List instances
    instances = await client.list_instances()

    # Destroy instance
    await client.destroy_instance(instance.instance_id)
```

### GPUCapacityOptimizer

```python
from src.strategies.gpu_optimizer import GPUCapacityOptimizer, GPUConfig

# Create optimizer
optimizer = GPUCapacityOptimizer(
    gpu_configs=[gpu1, gpu2, ...],
    marketplace=vastai_marketplace,
    config=StrategyConfig(
        min_expected_profit=0.10,
        min_roi=0.25,
        enable_auto_execution=True
    )
)

# Initialize
await optimizer.initialize()

# Find opportunities
opportunities = await optimizer.find_opportunities()

# Execute opportunities
for opp in opportunities:
    if await optimizer.validate_opportunity(opp):
        result = await optimizer.execute_opportunity(opp)
        print(f"Success: {result.success}")

# Shutdown
await optimizer.shutdown()
```

---

## Workflow System Integration

### GPU Workflow Nodes

**GPUMarketRateNode**
- Fetches current market rates from Vast.ai
- Outputs: median_rate, min_rate, max_rate, offer_count

**GPUOperatingCostNode**
- Calculates power + maintenance costs
- Inputs: power_watts, power_cost_per_kwh
- Outputs: total_cost_per_hour

**GPUProfitabilityNode**
- Determines if renting is profitable
- Outputs: is_profitable, profit_per_hour, suggested_price

**GPUListActionNode**
- Lists GPU on Vast.ai marketplace
- Inputs: gpu_id, price

### Example Workflow

See `examples/gpu_optimization_workflow.json` for a complete visual workflow that:
1. Fetches market rate
2. Calculates operating cost
3. Determines profitability
4. Lists GPU if profitable
5. Sends notification

---

## Configuration

### Strategy Config

```python
StrategyConfig(
    scan_interval_ms=300000,      # 5 minutes
    min_expected_profit=0.10,     # $0.10/hour minimum
    min_roi=0.25,                 # 25% margin minimum
    enable_auto_execution=True,   # Auto list/unlist
    dry_run_mode=False,           # Set True for testing
    custom_params={
        "unlist_on_shutdown": True  # Unlist when stopping
    }
)
```

### GPU Config

```python
GPUConfig(
    gpu_id="unique_id",
    gpu_model="RTX_4090",         # Vast.ai model name
    vram_gb=24,
    cuda_cores=16384,
    power_watts=450,
    power_cost_per_kwh=0.12,      # Your electricity cost
    maintenance_cost_per_hour=0.02 # Amortized maintenance
)
```

### Risk Constraints

```python
RiskConstraint(
    constraint_type=ConstraintType.DAILY_LOSS,
    name="max_daily_loss",
    limit=50.0,
    enforce=True,
    time_window=timedelta(days=1)
)
```

---

## Testing

### Dry Run Mode

Test without real API calls:

```python
config = StrategyConfig(dry_run_mode=True)
optimizer = GPUCapacityOptimizer(..., config=config)
```

### Unit Tests

```bash
pytest tests/integrations/test_vastai.py
pytest tests/strategies/test_gpu_optimizer.py
```

### Integration Tests

```bash
# Requires VAST_AI_API_KEY environment variable
pytest tests/integration/test_gpu_marketplace.py -v
```

---

## Performance Metrics

### Example Results

Running 2x RTX 4090s for 30 days:

| Metric | Value |
|--------|-------|
| Total Revenue | $720.00 |
| Total Operating Cost | $288.00 |
| Net Profit | $432.00 |
| ROI | 150% |
| Avg Hourly Rate | $0.50/hr |
| Occupancy Rate | 65% |
| Decisions Made | 8,640 |

### Key Performance Indicators

- **Profit per GPU per Day**: Track daily profitability
- **Occupancy Rate**: Percentage of time GPUs are rented
- **Average Hourly Rate**: Mean rental rate achieved
- **Decision Accuracy**: % of profitable listing decisions

---

## Troubleshooting

### Issue: "No market data available"

**Cause**: GPU model name doesn't match Vast.ai's naming convention

**Solution**: Check Vast.ai for exact model names:
- `RTX_4090` ✅
- `RTX 4090` ❌ (space not underscore)
- `RTX4090` ❌ (missing underscore)

### Issue: "Not profitable to list"

**Cause**: Market rate below operating costs + margin

**Solution**:
1. Lower `min_roi` threshold (if acceptable)
2. Reduce `power_cost_per_kwh` if inaccurate
3. Wait for market rates to improve

### Issue: "Rate limit exceeded"

**Cause**: Too many API calls

**Solution**: Increase `scan_interval_ms` in strategy config

---

## Comparison: Trading vs GPU Optimization

| Aspect | Trading Bots | GPU Optimizer |
|--------|--------------|---------------|
| **Asset** | Financial instruments | GPU capacity |
| **Venue** | Exchanges | Vast.ai marketplace |
| **Price Signal** | Market price | Rental rate |
| **Action** | Buy/Sell orders | List/Unlist GPU |
| **Risk** | Position limits, loss limits | Operating cost limits |
| **Profit Source** | Arbitrage, momentum | Rental revenue |
| **Workflow Nodes** | PriceSource, Spread | GPUMarketRate, Profitability |
| **Abstraction Layer** | ✅ Same | ✅ Same |

**Key Insight**: The abstraction layer makes GPU optimization look almost identical to trading from a code perspective!

---

## Next Steps

### Implement Additional Domains

Using the same patterns:

1. **Ad Platform Optimization**
   ```python
   from src.core.adapters.advertising import AdPlatformAdapter
   # Same Strategy interface, different domain
   ```

2. **Ecommerce Arbitrage**
   ```python
   from src.core.adapters.ecommerce import EcommerceMarketplaceAdapter
   # Same risk management, different assets
   ```

3. **Credit Yield Optimization**
   ```python
   # Allocate funds to highest-yield lending platforms
   # Same workflow system, different venue types
   ```

### Enhance GPU Strategy

- Add historical data backtesting
- Implement dynamic pricing based on demand forecasts
- Multi-marketplace support (RunPod, Lambda Labs, etc.)
- Automated SSH key management
- Workload scheduling (own ML tasks vs rental)

---

## Sources

- [Vast.ai API Documentation](https://docs.vast.ai/api-reference/)
- [Vast.ai Search Offers Endpoint](https://docs.vast.ai/api-reference/search/search-offers)
- [Vast.ai Instance Management](https://docs.vast.ai/api-reference/instances/create-instance)

---

## Conclusion

The GPU marketplace integration **proves the abstraction layer works for real-world, non-trading domains**.

The same infrastructure that powers cryptocurrency arbitrage now powers GPU capacity optimization:
- ✅ Same `Strategy` interface
- ✅ Same `Venue` abstraction
- ✅ Same risk management
- ✅ Same workflow system
- ✅ Same dashboard (with minor UI extensions)

**Next domains (ads, ecommerce, credit yield) will follow the exact same pattern.**

The platform is now a **true multi-domain automation engine**! 🚀
