# Project Context - Multi-Domain Automation Platform

**Last Updated**: 2026-01-24
**Current Phase**: Planning → Implementation (Week 1 starting)
**Active Branch**: `xenodochial-galileo`

---

## What This Project Is

A **multi-domain automation platform** that uses a generic abstraction layer to automate profit-generating activities across:
- 🪙 **Trading** (crypto, stocks, prediction markets) - WORKING
- 🖥️ **GPU Capacity** (Vast.ai marketplace optimization) - WORKING
- 📢 **Advertising** (Google/Meta Ads budget optimization) - Designed, not implemented
- 🛒 **Ecommerce** (Amazon/eBay arbitrage) - Designed, not implemented
- 💰 **Credit Yield** (DeFi/CeFi lending) - Designed, not implemented

**Key Insight**: Same strategy/risk/workflow engine works across all domains.

---

## Current State

### ✅ Completed (Production Ready)

1. **Core Abstraction Layer** (9,000+ lines)
   - `src/core/asset.py` - Generic asset abstraction
   - `src/core/venue.py` - Generic marketplace abstraction
   - `src/core/strategy.py` - Generic strategy abstraction
   - `src/core/risk.py` - Unified risk management
   - `src/core/graph_runtime.py` - Node-based workflow engine

2. **Domain Adapters**
   - `src/core/adapters/trading.py` - Wraps BaseProvider as Venue
   - `src/core/adapters/compute.py` - GPU marketplace adapter
   - `src/core/adapters/advertising.py` - Ad platform adapter (design)
   - `src/core/adapters/ecommerce.py` - Ecommerce marketplace adapter (design)

3. **Integration Bridge** (Legacy ↔ New)
   - `src/core/bridge.py` - Bidirectional compatibility
   - Existing BaseProvider works with new Venue interface
   - Existing BaseStrategy works with new Strategy interface

4. **Production Integrations**
   - `src/integrations/vastai.py` - Full Vast.ai API client + marketplace
   - `src/strategies/gpu_optimizer.py` - GPU capacity optimization strategy

5. **Workflow System**
   - `src/workflow/executor.py` - Node graph execution (existing)
   - `src/workflow/nodes.py` - Multi-domain workflow nodes
   - `src/workflow/gpu_nodes.py` - GPU-specific nodes

6. **Documentation** (Critical for New Sessions)
   - `ABSTRACTION_LAYER.md` - Architecture and design
   - `INTEGRATION_GUIDE.md` - How to integrate legacy code
   - `GPU_MARKETPLACE_GUIDE.md` - GPU implementation guide
   - `DASHBOARD_ARCHITECTURE.md` - Dashboard design decisions
   - `DASHBOARD_IMPLEMENTATION_PLAN.md` - 6-week implementation plan
   - `PROJECT_CONTEXT.md` - This file

### 🚧 In Progress

**Infrastructure Hardening** - Week 2 (PIVOTED FROM UI)

**Status**: Week 1 complete, Week 2 plan ready

**Critical Pivot Decision**: Based on pain points analysis, Week 2 pivots from WebSocket UI to infrastructure hardening. A beautiful dashboard on a fragile backend would hit the same "97% break under scale" problem as n8n.

**Week 2 Focus**:
1. State management abstraction (memory + Redis)
2. Event bus abstraction (memory + Redis pub/sub)
3. Structured logging with correlation IDs
4. Retry logic and circuit breakers
5. Emergency halt controls
6. Configuration system (.env support)

**See**: `WEEK_2_INFRASTRUCTURE_PLAN.md` and `PAIN_POINTS_ANALYSIS.md`

### ✅ Recently Completed

**Week 1: Wireframes & React Project Setup**
- ✅ Complete wireframes in `WIREFRAMES.md` (all 3 tiers)
- ✅ React + Vite + TypeScript project in `web/`
- ✅ TailwindCSS with custom design tokens
- ✅ Type-safe API and WebSocket services
- ✅ Component catalog template
- ✅ Folder structure established

### ❌ Not Started

- PostgreSQL for execution history (Week 3)
- Monitoring stack (Prometheus + Grafana) (Week 4)
- WebSocket infrastructure (Week 4)
- Main Dashboard UI (Week 5)
- Bot Dashboard UI (Week 5)
- Strategy View UI (Week 6)
- Ad platform integration
- Ecommerce integration

---

## Critical Architecture Decisions

### Bot vs Strategy (DECIDED)

**Bots and Strategies are SEPARATE entities:**

```
Bot (Orchestrator)
├── Strategy A (50% capital)
├── Strategy B (30% capital)
└── Strategy C (20% capital)
```

- **Bot**: Manages portfolio, enforces risk, allocates capital, schedules execution
- **Strategy**: Finds opportunities, executes trades, generates alpha

### Dashboard Hierarchy (DECIDED)

**Three-tier system:**

1. **Main Dashboard** - Overview of all bots
2. **Bot Dashboard** - Orchestration + strategies for one bot
3. **Strategy View** - Live workflow for one strategy

Each tier has its own node diagram:
- **Bot diagram**: Controls WHEN/HOW strategies run
- **Strategy diagram**: Controls HOW to find opportunities

### Tech Stack (APPROVED)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- TailwindCSS + shadcn/ui
- React Context + useReducer (state)
- ReactFlow (node diagrams)
- Recharts (charts)
- Socket.io client (WebSocket)

**Backend:**
- Python + FastAPI (existing)
- python-socketio (WebSocket server)
- Existing workflow executor enhanced

### Runtime Value Editing (DECIDED)

**Unity-style editing:**
- Users can edit node values while workflow runs
- Save button appears when value differs from default
- All changes logged with timestamp
- Can revert to saved values
- Visual indicator for "tweaked but not saved"

---

## File Structure

```
Polymarket-trading-bot-15min-BTC/
├── src/
│   ├── core/                    # Generic abstraction layer
│   │   ├── asset.py             # Asset abstraction
│   │   ├── venue.py             # Venue abstraction
│   │   ├── strategy.py          # Strategy abstraction
│   │   ├── risk.py              # Risk management
│   │   ├── graph_runtime.py     # Workflow engine
│   │   ├── bridge.py            # Legacy integration
│   │   └── adapters/            # Domain-specific adapters
│   ├── integrations/            # External service integrations
│   │   └── vastai.py            # Vast.ai GPU marketplace
│   ├── providers/               # Legacy trading providers
│   ├── strategies/              # Trading + GPU strategies
│   │   └── gpu_optimizer.py    # GPU capacity optimizer
│   ├── workflow/                # Workflow system
│   │   ├── executor.py          # Graph execution
│   │   ├── nodes.py             # Multi-domain nodes
│   │   └── gpu_nodes.py         # GPU-specific nodes
│   └── web/                     # (TO BE CREATED - Week 1)
│       └── src/                 # React dashboard app
├── examples/                    # Example scripts
│   ├── run_gpu_optimizer.py    # GPU bot example
│   └── gpu_optimization_workflow.json
├── tests/                       # Test suite
│   └── core/                    # Core tests
├── ABSTRACTION_LAYER.md         # Architecture guide
├── INTEGRATION_GUIDE.md         # Integration patterns
├── GPU_MARKETPLACE_GUIDE.md     # GPU implementation
├── DASHBOARD_ARCHITECTURE.md    # Dashboard design
├── DASHBOARD_IMPLEMENTATION_PLAN.md  # 6-week plan
└── PROJECT_CONTEXT.md           # This file (always current)
```

---

## WebSocket Event Protocol (Planned)

### Node Execution Event
```typescript
{
  type: 'node_execution',
  botId: 'trading_001',
  strategyId: 'arb_btc',
  nodeId: 'price_binance',
  timestamp: 1706140800000,
  data: {
    inputs: { /* ... */ },
    outputs: { price: 50234.56 },
    status: 'success' | 'failed' | 'running',
    executionTimeMs: 45,
    error?: string
  }
}
```

### Bot Metrics Update
```typescript
{
  type: 'bot_metrics',
  botId: 'trading_001',
  timestamp: 1706140800000,
  metrics: {
    pnl: 1234.56,
    activeTrades: 3,
    winRate: 0.78
  }
}
```

### Strategy Metrics Update
```typescript
{
  type: 'strategy_metrics',
  botId: 'trading_001',
  strategyId: 'arb_btc',
  timestamp: 1706140800000,
  metrics: {
    opportunitiesFound: 23,
    executed: 12,
    pnl: 324.18
  }
}
```

---

## Data Models (Current)

### Bot Model (To Be Implemented)
```python
@dataclass
class Bot:
    bot_id: str
    name: str
    domain: str  # "trading", "gpu", "ads", "ecommerce"
    strategies: List[StrategyInstance]
    risk_manager: RiskManager
    portfolio_tracker: PortfolioTracker
    schedule: BotSchedule
    venues: List[Venue]
    total_pnl: float
    active_positions: List[Position]
```

### StrategyInstance Model (To Be Implemented)
```python
@dataclass
class StrategyInstance:
    strategy_id: str
    strategy_template: StrategyTemplate
    enabled: bool
    weight: float  # Capital allocation (0-1)
    config_overrides: Dict[str, Any]
    opportunities_found: int
    trades_executed: int
    pnl: float
```

---

## Running Examples

### Trading Bot (Existing)
```bash
# Already working - uses BaseProvider + BaseStrategy
python examples/run_trading_bot.py
```

### GPU Optimizer (Production Ready)
```bash
# Set API key
export VAST_AI_API_KEY="your_key"

# Run optimizer
python examples/run_gpu_optimizer.py
```

### Dashboard (Not Yet Implemented)
```bash
# Will be available after Week 3
cd web
npm run dev
```

---

## Known Issues

1. **WebSocket not integrated** - Workflow executor doesn't emit events yet
2. **No dashboard UI** - Only backend and strategies exist
3. **Bot orchestration layer incomplete** - MultiBotManager exists but doesn't support multi-strategy bots yet
4. **No runtime value editing** - Workflows can't be tweaked during execution

---

## Development Workflow

### For New Claude Code Sessions

1. **Read this file first** (`PROJECT_CONTEXT.md`)
2. **Check implementation plan** (`DASHBOARD_IMPLEMENTATION_PLAN.md`)
3. **Review architecture** (`DASHBOARD_ARCHITECTURE.md`)
4. **Check wireframes** (`WIREFRAMES.md` - to be created)
5. **Update this file** when making changes

### Key Commands

```bash
# Run tests
pytest tests/ -v

# Run GPU optimizer
python examples/run_gpu_optimizer.py

# Lint/format (if configured)
black src/
mypy src/

# Git workflow (gitmoji format)
git add .
git commit -m "✨ feat: description"
```

### Commit Message Format (Gitmoji)

Use gitmoji for all commits:
- ✨ `:sparkles:` - New feature
- 🐛 `:bug:` - Bug fix
- 📚 `:books:` - Documentation
- 🎨 `:art:` - Code style/structure
- ⚡ `:zap:` - Performance
- ♻️ `:recycle:` - Refactoring
- 🔧 `:wrench:` - Configuration
- 🧪 `:test_tube:` - Tests

---

## Next Immediate Steps (Week 1)

**Priority**: Create wireframes and set up project

**Tasks** (in order):
1. [x] Create `WIREFRAMES.md` with ASCII art diagrams
2. [x] Set up React + Vite project in `web/` directory
3. [x] Install dependencies (see tech stack)
4. [x] Create folder structure (components, pages, services)
5. [x] Document design tokens (colors, spacing) - in Tailwind config
6. [x] Create `COMPONENT_CATALOG.md` template
7. [x] Set up TailwindCSS config
8. [ ] Install shadcn/ui components (optional - can add as needed)

**Status**: ✅ Week 1 Complete

**Deliverable**: ✅ Wireframes + React project ready for Week 2

---

## Success Metrics

### Phase 1: Abstraction Layer ✅
- [x] Works for trading domain
- [x] Works for GPU domain
- [x] Cross-domain risk management
- [x] Workflow system supports both

### Phase 2: Dashboard (In Progress)
- [ ] Main Dashboard shows all bots
- [ ] Bot Dashboard shows strategies
- [ ] Strategy View shows live workflow
- [ ] WebSocket updates work smoothly
- [ ] Runtime editing saves values

### Phase 3: Production (Future)
- [ ] Multi-user support
- [ ] Ad platform integration
- [ ] Ecommerce integration
- [ ] Mobile app
- [ ] Signal marketplace

---

## Contact & Resources

**Documentation Files** (Read in order):
1. `PROJECT_CONTEXT.md` ← You are here
2. `DASHBOARD_IMPLEMENTATION_PLAN.md` ← Detailed plan
3. `DASHBOARD_ARCHITECTURE.md` ← Design decisions
4. `ABSTRACTION_LAYER.md` ← Core architecture
5. `INTEGRATION_GUIDE.md` ← How to integrate

**API Documentation**:
- Vast.ai: https://docs.vast.ai/api-reference/

**Tech Stack Docs**:
- React: https://react.dev/
- TypeScript: https://www.typescriptlang.org/docs/
- Vite: https://vitejs.dev/
- TailwindCSS: https://tailwindcss.com/docs
- shadcn/ui: https://ui.shadcn.com/
- ReactFlow: https://reactflow.dev/
- Socket.io: https://socket.io/docs/

---

**This file is the source of truth for project state. Always keep it updated.**
