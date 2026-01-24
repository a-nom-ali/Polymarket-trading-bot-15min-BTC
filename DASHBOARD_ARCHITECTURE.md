# Dashboard Architecture & Roadmap

## Executive Summary

This document addresses critical architectural decisions for the multi-domain automation platform's dashboard system, specifically:

1. **Bot vs Strategy relationship** - Are they the same thing or separate?
2. **Node diagrams** - For bot behavior or just strategies?
3. **Live execution visualization** - Real-time data on nodes
4. **Dashboard hierarchy** - Main dashboard → Bot dashboard → Strategy view
5. **Widget system** - Cards, graphs, metrics, live updates

**Key Decision**: Based on your vision and the abstraction layer architecture, **Bots and Strategies should be separate but composable entities**.

---

## Critical Architectural Questions

### Q1: Bot vs Strategy - Same or Separate?

**Answer: SEPARATE (but tightly integrated)**

```
┌─────────────────────────────────────────────────────────────┐
│                          BOT                                 │
│  (Orchestration Layer - What to run, when, with what risk)  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Strategy A  │  │ Strategy B  │  │ Strategy C  │         │
│  │ (Arbitrage) │  │ (Momentum)  │  │ (MM)        │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                  │
│         ▼                ▼                ▼                  │
│  ┌─────────────────────────────────────────────┐            │
│  │      Risk Manager (Shared)                  │            │
│  └─────────────────────────────────────────────┘            │
│                                                               │
│  ┌─────────────────────────────────────────────┐            │
│  │      Portfolio Tracker (Aggregated)         │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

**Why Separate:**

1. **A Bot can run multiple strategies simultaneously**
   - Example: GPU bot runs "GPU Capacity Optimizer" + "GPU Price Predictor"
   - Example: Trading bot runs "BTC Arbitrage" + "ETH Momentum" + "USDC Yield"

2. **Strategies can be reused across bots**
   - Same "Arbitrage" strategy works for BTC, ETH, GPU marketplaces
   - User creates strategy once, applies to multiple bots

3. **Different levels of control**
   - **Bot level**: When to run, which venues, global risk limits, capital allocation
   - **Strategy level**: How to find opportunities, execution logic, strategy-specific params

4. **Cleaner separation of concerns**
   - **Bot**: Orchestrator, scheduler, portfolio manager
   - **Strategy**: Alpha generator, opportunity detector, executor

**Proposed Data Model:**

```python
@dataclass
class Bot:
    bot_id: str
    name: str
    domain: str  # "trading", "gpu", "ads", "ecommerce"

    # Strategies this bot runs
    strategies: List[StrategyInstance]

    # Bot-level configuration
    risk_manager: RiskManager
    portfolio_tracker: PortfolioTracker
    schedule: BotSchedule  # When to run

    # Venues this bot has access to
    venues: List[Venue]

    # Bot-level metrics
    total_pnl: float
    active_positions: List[Position]

@dataclass
class StrategyInstance:
    strategy_id: str
    strategy_template: StrategyTemplate  # Reusable strategy definition

    # Instance-specific config
    enabled: bool
    weight: float  # Capital allocation weight (0-1)
    config_overrides: Dict[str, Any]

    # Instance metrics
    opportunities_found: int
    trades_executed: int
    pnl: float
```

**Example: Trading Bot with Multiple Strategies**

```python
bot = Bot(
    bot_id="trading_bot_001",
    name="Multi-Strategy BTC Bot",
    domain="trading",
    strategies=[
        StrategyInstance(
            strategy_template=ArbitrageStrategy,
            weight=0.5,  # 50% of capital
            config={"min_spread": 0.5}
        ),
        StrategyInstance(
            strategy_template=MomentumStrategy,
            weight=0.3,  # 30% of capital
            config={"momentum_window": 15}
        ),
        StrategyInstance(
            strategy_template=MarketMakingStrategy,
            weight=0.2,  # 20% of capital
            config={"spread_target": 0.1}
        )
    ],
    risk_manager=RiskManager([
        RiskConstraint(type=DAILY_LOSS, limit=500.0)
    ]),
    venues=[binance, coinbase]
)
```

---

### Q2: Does a Bot Need Its Own Node Diagram?

**Answer: YES - Bot-level orchestration diagram SEPARATE from strategy diagrams**

**Bot Diagram (Orchestration)**
- Controls WHEN strategies run
- HOW capital is allocated
- WHICH venues to use
- Risk management flow

**Strategy Diagram (Alpha Generation)**
- HOW to find opportunities
- WHAT conditions to check
- HOW to execute

**Visual Example:**

```
BOT DIAGRAM: "Trading Bot Orchestrator"
┌─────────────────────────────────────────────────────┐
│                                                      │
│  [Schedule Trigger]                                 │
│         │                                            │
│         ▼                                            │
│  [Check Portfolio State]                            │
│         │                                            │
│         ▼                                            │
│  [Risk Gate] ──────┐                                │
│         │          │ if risk OK                      │
│         │          ▼                                 │
│  (risk failed)  [Allocate Capital]                  │
│         │          │                                 │
│         │          ├──50%──▶ [Run Arbitrage Strategy]│
│         │          ├──30%──▶ [Run Momentum Strategy] │
│         │          └──20%──▶ [Run MM Strategy]       │
│         │                    │                       │
│         │                    ▼                       │
│         └──────────▶ [Aggregate Results]            │
│                              │                       │
│                              ▼                       │
│                      [Update Portfolio]             │
│                              │                       │
│                              ▼                       │
│                      [Notify if needed]             │
└─────────────────────────────────────────────────────┘


STRATEGY DIAGRAM: "Arbitrage Strategy"
┌─────────────────────────────────────────────────────┐
│                                                      │
│  [Get Price Binance] ──┐                            │
│                        │                             │
│  [Get Price Coinbase]──┤                            │
│                        │                             │
│                        ▼                             │
│                 [Calculate Spread]                   │
│                        │                             │
│                        ▼                             │
│                 [Spread > 0.5%?] ─No─▶ [Exit]       │
│                        │                             │
│                       Yes                            │
│                        ▼                             │
│                 [Calculate Profit]                   │
│                        │                             │
│                        ▼                             │
│                 [Place Orders]                       │
│                        │                             │
│                        ▼                             │
│                 [Monitor Execution]                  │
└─────────────────────────────────────────────────────┘
```

**Implementation:**

```python
# Bot has its own workflow
bot_workflow = BotOrchestrationWorkflow(
    graph_id="trading_bot_orchestrator",
    nodes=[
        ScheduleTriggerNode(...),
        PortfolioStateNode(...),
        RiskGateNode(...),
        CapitalAllocationNode(...),
        RunStrategyNode(strategy=arbitrage_strategy, weight=0.5),
        RunStrategyNode(strategy=momentum_strategy, weight=0.3),
        AggregateResultsNode(...),
        UpdatePortfolioNode(...),
    ]
)

# Each strategy has its own workflow
arbitrage_workflow = StrategyWorkflow(
    graph_id="arbitrage_strategy",
    nodes=[
        VenuePriceNode(venue=binance),
        VenuePriceNode(venue=coinbase),
        CalculateSpreadNode(),
        ThresholdCheckNode(threshold=0.5),
        ExecuteActionNode(),
    ]
)
```

---

### Q3: Live Execution Visualization

**Answer: YES - Nodes act as live dashboard widgets**

**Key Features:**

1. **Live Data Flow**
   - Each node shows current input/output values
   - Visual indication of data flowing through connections
   - Animated pulses when data passes

2. **Execution History**
   - Last 10 executions visible on timeline
   - Click to see detailed execution logs
   - Performance metrics per node (avg time, success rate)

3. **Real-time Metrics**
   - Running totals (opportunities found, trades executed)
   - Error counts with expandable error logs
   - Performance graphs (latency over time)

**Visual Mockup:**

```
┌────────────────────────────────────────────────────────┐
│  Strategy: BTC Arbitrage (RUNNING)                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐                ┌──────────────┐     │
│  │ Binance      │                │ Coinbase     │     │
│  │ Price        │                │ Price        │     │
│  ├──────────────┤                ├──────────────┤     │
│  │ $50,234.56   │──────┐   ┌────│ $50,487.23   │     │
│  │ ⏱ 45ms       │      │   │    │ ⏱ 52ms       │     │
│  │ ✓ 1,234 exec │      │   │    │ ✓ 1,234 exec │     │
│  └──────────────┘      │   │    └──────────────┘     │
│                        ▼   ▼                          │
│                   ┌──────────────┐                    │
│                   │ Calculate    │                    │
│                   │ Spread       │                    │
│                   ├──────────────┤                    │
│                   │ $252.67      │ ◄─ Current value   │
│                   │ 0.50%        │ ◄─ Percentage      │
│                   │ ⏱ 2ms        │ ◄─ Avg exec time   │
│                   │ ✓ 1,234 exec │ ◄─ Total execs     │
│                   └──────────────┘                    │
│                         │                              │
│                         ▼                              │
│                   ┌──────────────┐                    │
│                   │ Threshold?   │                    │
│                   │ >= 0.5%      │                    │
│                   ├──────────────┤                    │
│                   │ ✓ PASSED     │ ◄─ Live status     │
│                   │ 23/1234      │ ◄─ Pass rate       │
│                   └──────────────┘                    │
│                         │                              │
│                         ▼                              │
│                   ┌──────────────┐                    │
│                   │ Execute      │                    │
│                   │ Trade        │                    │
│                   ├──────────────┤                    │
│                   │ ⏳ EXECUTING │ ◄─ Current state   │
│                   │ 23 trades    │ ◄─ Total executed  │
│                   │ $145.67 avg  │ ◄─ Avg profit      │
│                   └──────────────┘                    │
│                                                         │
│  Execution Timeline:                                   │
│  ▓▓░░▓▓▓░▓▓░░░▓▓▓▓░░▓ ◄─ Last 100 executions         │
│  ▓ = Success  ░ = Skipped (no opportunity)            │
└────────────────────────────────────────────────────────┘
```

**Implementation Details:**

```typescript
// Node component receives live data via WebSocket
interface LiveNodeData {
  nodeId: string;
  currentInputs: Record<string, any>;
  currentOutputs: Record<string, any>;
  status: 'idle' | 'running' | 'success' | 'failed';
  metrics: {
    totalExecutions: number;
    successRate: number;
    avgExecutionTimeMs: number;
    lastExecutionAt: Date;
  };
  executionHistory: ExecutionRecord[];  // Last 10
}

// WebSocket updates flow through nodes
ws.on('node_execution', (data: LiveNodeData) => {
  // Animate data flow on connection
  animateDataFlow(data.nodeId, data.currentOutputs);

  // Update node widget display
  updateNodeWidget(data.nodeId, {
    values: data.currentOutputs,
    metrics: data.metrics,
    status: data.status
  });
});
```

---

## Dashboard Hierarchy

### 1. Main Dashboard (Overview)

**Purpose**: High-level view of all bots across all domains

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  🏠 Automation Platform Dashboard                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Global Metrics   │  │ Risk Dashboard   │               │
│  ├──────────────────┤  ├──────────────────┤               │
│  │ Total P&L: +$4.2k│  │ Daily Loss: $120 │               │
│  │ Active Bots: 5   │  │ Limit: $500      │               │
│  │ Running: 3       │  │ Remaining: $380  │               │
│  │ Paused: 2        │  │ ▓▓▓▓░░░░░░ 24%   │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                              │
│  Active Bots (Grid View):                                  │
│                                                              │
│  ┌────────────────────┐  ┌────────────────────┐           │
│  │ 🪙 BTC Trading     │  │ 🖥️ GPU Optimizer   │           │
│  │ ─────────────────  │  │ ─────────────────  │           │
│  │ Status: ● Running  │  │ Status: ● Running  │           │
│  │ P&L: +$1,234       │  │ P&L: +$432         │           │
│  │ Trades: 45         │  │ Hours: 156         │           │
│  │ Win%: 78%          │  │ Occupancy: 65%     │           │
│  │                    │  │                    │           │
│  │ [View Dashboard]   │  │ [View Dashboard]   │           │
│  └────────────────────┘  └────────────────────┘           │
│                                                              │
│  ┌────────────────────┐  ┌────────────────────┐           │
│  │ 📢 Ad Optimizer    │  │ 🛒 Ecommerce Arb   │           │
│  │ ─────────────────  │  │ ─────────────────  │           │
│  │ Status: ⏸ Paused   │  │ Status: ● Running  │           │
│  │ ROAS: 3.2x         │  │ P&L: +$2,145       │           │
│  │ Spend: $1,200      │  │ Items: 23          │           │
│  │ Revenue: $3,840    │  │ Margin: 42%        │           │
│  │                    │  │                    │           │
│  │ [View Dashboard]   │  │ [View Dashboard]   │           │
│  └────────────────────┘  └────────────────────┘           │
│                                                              │
│  ┌────────────────────┐                                    │
│  │ 💰 Yield Optimizer │                                    │
│  │ ─────────────────  │                                    │
│  │ Status: ⏸ Paused   │                                    │
│  │ APY: 12.4%         │                                    │
│  │ Allocated: $10k    │                                    │
│  │ Earned: $124       │                                    │
│  │                    │                                    │
│  │ [View Dashboard]   │                                    │
│  └────────────────────┘                                    │
│                                                              │
│  [+ Create New Bot]                                        │
└─────────────────────────────────────────────────────────────┘
```

**Widgets:**
- Global metrics card (total P&L, active bots)
- Risk dashboard (global limits usage)
- Bot cards (one per bot, double-click to open)
- Performance charts (P&L over time, all bots aggregated)
- Recent activity feed

### 2. Bot Dashboard (Detailed)

**Purpose**: Detailed view of a single bot's performance and strategies

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Main    🖥️ GPU Optimizer Bot                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ Bot Status   │ │ P&L          │ │ Risk         │       │
│  │ ● Running    │ │ +$432.18     │ │ ✓ Within     │       │
│  │ Uptime: 5d   │ │ Today: +$42  │ │   Limits     │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                              │
│  Bot Orchestration Diagram:                                │
│  ┌────────────────────────────────────────────────┐        │
│  │  [Schedule] → [Portfolio] → [Risk Gate]        │        │
│  │       ↓               ↓            ↓            │        │
│  │  [Strategy 1]   [Strategy 2]  [Aggregate]      │        │
│  │                                                  │        │
│  │  Click nodes to see live data ────────────┐    │        │
│  │  Double-click to open strategy view       │    │        │
│  └────────────────────────────────────────────────┘        │
│                                                              │
│  Active Strategies:                                         │
│  ┌────────────────────────┐  ┌────────────────────────┐   │
│  │ GPU Capacity Optimizer │  │ GPU Price Predictor     │   │
│  │ ──────────────────────│  │ ──────────────────────│   │
│  │ Status: ● Active       │  │ Status: ⏸ Paused        │   │
│  │ Opportunities: 23      │  │ Predictions: 156        │   │
│  │ Executed: 12           │  │ Accuracy: 78%           │   │
│  │ P&L: +$324             │  │ P&L: +$108              │   │
│  │ Weight: 70%            │  │ Weight: 30%             │   │
│  │                        │  │                         │   │
│  │ [View Strategy]        │  │ [View Strategy]         │   │
│  └────────────────────────┘  └────────────────────────┘   │
│                                                              │
│  Portfolio:                                                 │
│  ┌────────────────────────────────────────────────┐        │
│  │ GPU    │ Status   │ Rate    │ Hours │ Revenue │        │
│  │────────┼──────────┼─────────┼───────┼─────────│        │
│  │ 4090-1 │ ● Listed │ $0.48/h │ 45.2h │ $21.70  │        │
│  │ 4090-2 │ ○ Idle   │ -       │ -     │ -       │        │
│  │ 3090-1 │ ● Listed │ $0.32/h │ 62.8h │ $20.10  │        │
│  └────────────────────────────────────────────────┘        │
│                                                              │
│  Performance Charts:                                        │
│  [P&L Over Time] [Occupancy Rate] [Market Rates]          │
└─────────────────────────────────────────────────────────────┘
```

**Widgets:**
- Bot-level metrics (status, P&L, risk)
- **Bot orchestration diagram** (live, interactive)
- Strategy cards (one per strategy)
- Portfolio view (positions/assets)
- Performance charts (bot-specific)

### 3. Strategy View (Deep Dive)

**Purpose**: Detailed view of a single strategy's workflow and performance

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Bot    Strategy: GPU Capacity Optimizer          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ Status       │ │ Opportunities│ │ Success Rate │       │
│  │ ● Running    │ │ 23 found     │ │ 92.3%        │       │
│  │ Last: 2m ago │ │ 12 executed  │ │ 12/13 trades │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                              │
│  Strategy Workflow (LIVE):                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │                                                      │    │
│  │  ┌──────────────┐         ┌──────────────┐         │    │
│  │  │ Market Rate  │─────────│ Operating    │         │    │
│  │  │ $0.52/hr     │         │ Cost         │         │    │
│  │  │ ⏱ 125ms      │         │ $0.074/hr    │         │    │
│  │  │ ✓ Active     │         │ ⏱ 5ms        │         │    │
│  │  └──────────────┘         └──────────────┘         │    │
│  │         │                          │                │    │
│  │         └─────────┬────────────────┘                │    │
│  │                   ▼                                  │    │
│  │           ┌──────────────┐                          │    │
│  │           │ Profitability│                          │    │
│  │           │ Check        │                          │    │
│  │           ├──────────────┤                          │    │
│  │           │ ✓ PROFITABLE │ ◄─ Live result          │    │
│  │           │ Profit: $0.45│                          │    │
│  │           │ Margin: 608% │                          │    │
│  │           └──────────────┘                          │    │
│  │                   │                                  │    │
│  │                   ▼                                  │    │
│  │           ┌──────────────┐                          │    │
│  │           │ List GPU     │                          │    │
│  │           │ @ $0.51/hr   │                          │    │
│  │           ├──────────────┤                          │    │
│  │           │ ⏳ PENDING   │ ◄─ Current state         │    │
│  │           └──────────────┘                          │    │
│  │                                                      │    │
│  │  Execution Timeline:                                │    │
│  │  ▓▓░░▓▓▓░▓▓░░░▓▓▓▓░░▓ ◄─ Last 100 runs            │    │
│  │  ▓ = Success  ░ = No opportunity                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Recent Executions:                                         │
│  ┌────────┬──────────┬──────────┬──────────┬─────────┐    │
│  │ Time   │ Action   │ GPU      │ Profit   │ Status  │    │
│  │────────┼──────────┼──────────┼──────────┼─────────│    │
│  │ 2m ago │ List     │ 4090-1   │ +$0.45/h │ ✓       │    │
│  │ 7m ago │ Reprice  │ 3090-1   │ +$0.32/h │ ✓       │    │
│  │ 12m    │ Skip     │ 4090-2   │ -        │ -       │    │
│  └────────┴──────────┴──────────┴──────────┴─────────┘    │
│                                                              │
│  [Edit Strategy] [Pause] [Clone] [Backtest]               │
└─────────────────────────────────────────────────────────────┘
```

**Widgets:**
- Strategy-level metrics
- **Live workflow diagram** (nodes show current values)
- Execution timeline visualization
- Recent executions log
- Performance charts (strategy-specific)

---

## Technical Implementation Plan

### Phase 1: Data Architecture (Week 1)

**Objective**: Define data models and WebSocket infrastructure

**Tasks:**
1. Define Bot, Strategy, Portfolio models
2. Design WebSocket message protocol
3. Implement real-time data pipeline
4. Create event system for node executions

**Deliverables:**
```python
# Core models
class Bot(BaseModel):
    bot_id: str
    strategies: List[StrategyInstance]
    orchestration_workflow: WorkflowGraph

class StrategyInstance(BaseModel):
    strategy_id: str
    workflow: WorkflowGraph
    enabled: bool
    weight: float

# WebSocket protocol
{
  "type": "node_execution",
  "botId": "trading_001",
  "strategyId": "arb_strategy",
  "nodeId": "price_binance",
  "data": {
    "inputs": {...},
    "outputs": {...},
    "status": "success",
    "metrics": {...}
  }
}
```

### Phase 2: Dashboard Framework (Week 2)

**Objective**: Build reusable widget system and layout engine

**Tasks:**
1. Create base widget components
2. Implement grid layout system
3. Build live data binding
4. Add drag-and-drop customization

**Tech Stack:**
- React + TypeScript
- TailwindCSS for styling
- React Flow for node diagrams
- Socket.io for WebSocket
- Zustand for state management

**Components:**
```typescript
// Widget system
<DashboardGrid>
  <MetricCard title="Total P&L" value={pnl} />
  <ChartWidget type="line" data={pnlHistory} />
  <BotCard bot={bot} onDoubleClick={openBotDashboard} />
</DashboardGrid>

// Node diagram
<LiveNodeDiagram
  workflow={workflow}
  liveData={wsData}
  onNodeClick={showNodeDetails}
  onNodeDoubleClick={drillDown}
/>
```

### Phase 3: Main Dashboard (Week 3)

**Objective**: Implement overview dashboard

**Features:**
- Global metrics widget
- Risk dashboard widget
- Bot cards grid (all domains)
- Performance charts
- Activity feed

### Phase 4: Bot Dashboard (Week 4)

**Objective**: Implement per-bot detailed view

**Features:**
- Bot metrics
- Orchestration diagram (interactive)
- Strategy cards
- Portfolio widget
- Bot-specific charts

### Phase 5: Strategy View (Week 5)

**Objective**: Implement strategy deep-dive

**Features:**
- Live workflow diagram
- Node widgets showing current values
- Execution timeline
- Recent executions log
- Strategy performance charts

### Phase 6: Live Execution (Week 6)

**Objective**: Add real-time visualization

**Features:**
- Animated data flow on connections
- Node status indicators
- Execution history on timeline
- Performance metrics per node
- Error highlighting and logs

---

## Gap Analysis

### What We Have ✅

1. **Abstraction layer** - Complete
2. **Multi-domain support** - Trading + GPU working
3. **Risk management** - Cross-domain constraints
4. **Workflow system** - Node-based execution
5. **Strategy implementations** - Multiple examples

### What We Need 🔨

1. **Dashboard framework** - Not started
2. **WebSocket infrastructure** - Not started
3. **Bot orchestration layer** - Partial (MultiBotManager exists but needs enhancement)
4. **Live data pipeline** - Not started
5. **Widget system** - Not started
6. **Node diagram with live data** - Workflow executor exists but no UI

### Critical Decisions Needed ⚠️

1. **Frontend framework**: React vs Vue vs Svelte?
   - **Recommendation**: React (largest ecosystem for dashboard libraries)

2. **Node diagram library**: React Flow vs Rete.js vs custom?
   - **Recommendation**: React Flow (mature, performant, customizable)

3. **Charts library**: Recharts vs Chart.js vs D3?
   - **Recommendation**: Recharts (React-native, declarative)

4. **Real-time updates**: WebSocket vs Server-Sent Events vs Polling?
   - **Recommendation**: WebSocket (bidirectional, low latency)

5. **State management**: Redux vs Zustand vs Jotai?
   - **Recommendation**: Zustand (simpler than Redux, performant)

---

## Updated Roadmap

### Immediate (Weeks 1-2)
- [ ] Finalize bot vs strategy separation
- [ ] Design WebSocket message protocol
- [ ] Create dashboard wireframes/mockups
- [ ] Choose tech stack
- [ ] Set up frontend project structure

### Short-term (Weeks 3-6)
- [ ] Build widget framework
- [ ] Implement main dashboard
- [ ] Add bot dashboard
- [ ] Create strategy view with live nodes
- [ ] Test with trading + GPU bots

### Medium-term (Weeks 7-12)
- [ ] Add more domain bots (ads, ecommerce)
- [ ] Implement dashboard customization
- [ ] Add historical playback
- [ ] Build mobile-responsive views
- [ ] Add user authentication

### Long-term (Months 4-6)
- [ ] Multi-user support
- [ ] Shared strategy marketplace
- [ ] Advanced analytics
- [ ] AI-powered insights
- [ ] Mobile app

---

## Next Actions

1. **Review and approve** this architecture
2. **Create mockups** in Figma/Excalidraw
3. **Choose tech stack** definitively
4. **Build proof-of-concept** for one dashboard view
5. **Iterate based on feedback**

---

## Open Questions

1. Should users be able to **edit running workflows**? (Hot reload vs stop-edit-restart)
2. How to handle **conflicting strategies** in the same bot? (e.g., both want to trade the same asset)
3. **Permission system** - Can users share bots/strategies?
4. **Backtesting UI** - Integrated into strategy view or separate?
5. **Alerting system** - Email, Slack, push notifications?

---

This architecture document serves as the blueprint for the next phase of development. Let me know which parts you'd like to dive deeper into!
