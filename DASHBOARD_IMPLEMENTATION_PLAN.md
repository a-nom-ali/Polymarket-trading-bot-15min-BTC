# Dashboard Implementation Plan (Revised)

## Executive Summary

This document outlines the concrete implementation plan for the multi-domain automation dashboard, incorporating the architectural decisions and user feedback.

**Approach**: Hybrid (Option C) - Wireframes → Prototype → Iterate
**Priority**: Unified, intuitive UX across all three dashboard tiers
**Stack**: Optimized for Claude Code development
**Timeline**: 6 weeks, starting with Main Dashboard

---

## User Feedback Integration

### 1. Runtime Value Editing (Unity-style)

**Implementation:**
```typescript
// Node input field with save capability
<NodeInputField
  value={currentValue}
  runtimeValue={runtimeTweakedValue}
  onChange={(val) => setRuntimeTweaked(val)}
  onSave={(val) => {
    saveValueAsPermanent(val);
    logChange({
      nodeId,
      field,
      oldValue: currentValue,
      newValue: val,
      timestamp: Date.now(),
      savedDuringRuntime: true
    });
  }}
  showSaveButton={runtimeTweakedValue !== currentValue}
/>
```

**Features:**
- Edit values while workflow runs
- Save icon appears when value differs from saved
- All changes logged with timestamp
- Can revert to saved value
- Visual indicator for "tweaked but not saved" state

**Change Log UI:**
```
┌────────────────────────────────────────────────┐
│ Runtime Changes Log                            │
├────────────────────────────────────────────────┤
│ 2m ago: Threshold changed 0.5% → 0.3% (saved) │
│ 5m ago: Min profit $0.10 → $0.15 (saved)      │
│ 12m ago: Scan interval 5min → 3min (reverted) │
└────────────────────────────────────────────────┘
```

### 2. Tech Stack - Optimized for Claude Code

**Original Stack Review:**
- React + TypeScript ✅ (Claude Code excels with TypeScript)
- React Flow ⚠️ (Complex API, might need alternatives)
- Recharts ✅ (Declarative, easy for Claude)
- WebSocket ✅ (Standard, well-documented)
- Zustand ⚠️ (Less common, consider alternatives)
- TailwindCSS ✅ (Utility-first, perfect for Claude)

**Revised Stack (Claude Code Optimized):**

```typescript
{
  // Frontend Framework
  "framework": "React 18 + TypeScript",
  "reasoning": "Claude Code has extensive React training data, TypeScript provides safety",

  // Styling
  "styling": "TailwindCSS + shadcn/ui",
  "reasoning": "Utility-first + pre-built components = fast iteration for Claude",

  // Node Diagrams
  "diagrams": "ReactFlow", // Keep this - mature, well-documented
  "alternative": "Custom SVG-based (simpler, more control if needed)",

  // State Management
  "state": "React Context + useReducer", // Changed from Zustand
  "reasoning": "Built-in React features = no external library, easier for Claude to reason about",

  // Charts
  "charts": "Recharts",
  "reasoning": "Declarative API, excellent for Claude Code generation",

  // Real-time
  "realtime": "Socket.io (client + server)",
  "reasoning": "Well-documented, handles reconnection, fallback to polling",

  // Build Tool
  "build": "Vite",
  "reasoning": "Fast HMR, simple config, modern standards",

  // Testing (future)
  "testing": "Vitest + React Testing Library",
  "reasoning": "Vite-native, similar API to Jest"
}
```

**Approved Stack:**
✅ React 18 + TypeScript
✅ Vite (build tool)
✅ TailwindCSS + shadcn/ui (styling + components)
✅ React Context + useReducer (state)
✅ ReactFlow (node diagrams)
✅ Recharts (charts)
✅ Socket.io (WebSocket)

**Why This Stack for Claude Code:**
1. **All standard technologies** - extensive training data
2. **Minimal external dependencies** - easier to reason about
3. **Type-safe** - TypeScript catches errors early
4. **Component-based** - shadcn/ui provides copy-paste components
5. **Well-documented** - React, TypeScript, Socket.io have excellent docs

### 3. Priority: Main Dashboard First

**Goal**: Establish the UX foundation that cascades to Bot and Strategy tiers

**Why Main Dashboard First:**
- Sets the design system (colors, spacing, typography)
- Establishes widget patterns (cards, metrics, charts)
- Defines navigation UX (how to drill down)
- Tests WebSocket integration at simplest level

**Deliverable**: Unified design language for all tiers

### 4. Wireframes + Documentation

**Approach**: Lightweight wireframes in Markdown + ASCII art

**Why:**
- Version-controllable (Git)
- Easy for Claude Code to reference
- No external tools needed
- Quick to update

**Example:**
```markdown
## Main Dashboard Wireframe

┌─────────────────────────────────────────┐
│ Header: Logo | Search | Notifications  │
├─────────────────────────────────────────┤
│ Metrics Row:                            │
│ [Total P&L] [Active Bots] [Risk]       │
├─────────────────────────────────────────┤
│ Bot Cards (Grid):                       │
│ [Bot A] [Bot B] [Bot C]                 │
│ [Bot D] [Bot E] [+ New]                 │
└─────────────────────────────────────────┘

Interactions:
- Double-click bot card → Navigate to Bot Dashboard
- Click metrics → Show expanded view
- Hover bot card → Show quick stats tooltip
```

### 5. WebSocket Integration

**Architecture:**

```
┌─────────────────────────────────────────────────┐
│              Frontend (React)                   │
│  ┌───────────────────────────────────────┐     │
│  │  Socket.io Client                      │     │
│  │  - Auto-reconnect                      │     │
│  │  - Event handlers                      │     │
│  │  - State sync                          │     │
│  └───────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
                     ↕ WebSocket
┌─────────────────────────────────────────────────┐
│         Backend (Python + FastAPI)              │
│  ┌───────────────────────────────────────┐     │
│  │  Socket.io Server (python-socketio)   │     │
│  │  - Room management (per bot)          │     │
│  │  - Event broadcasting                  │     │
│  │  - Authentication                      │     │
│  └───────────────────────────────────────┘     │
│                    ↕                            │
│  ┌───────────────────────────────────────┐     │
│  │  Workflow Executor                     │     │
│  │  - Emit events on node execution       │     │
│  │  - Send metrics updates                │     │
│  └───────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

**Event Protocol:**

```typescript
// Node execution event
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

// Bot metrics update
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

// Strategy metrics update
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

**Implementation Priorities:**
1. **Smooth as butter** - sub-100ms latency for events
2. **Reliable** - auto-reconnect, buffering on disconnect
3. **Scalable** - room-based broadcasting (only send to subscribers)
4. **Secure** - authentication, rate limiting

---

## Implementation Plan (6 Weeks)

### Week 1: Foundation + Wireframes

**Goals:**
- Create wireframes for all three tiers
- Set up project structure
- Document component architecture
- Establish design tokens

**Deliverables:**

1. **Project Structure**
```
web/
├── src/
│   ├── components/
│   │   ├── ui/           # shadcn/ui components
│   │   ├── widgets/      # Dashboard widgets
│   │   └── diagrams/     # Node diagram components
│   ├── contexts/         # React contexts
│   ├── hooks/            # Custom hooks
│   ├── services/         # API, WebSocket
│   ├── types/            # TypeScript types
│   └── pages/
│       ├── MainDashboard.tsx
│       ├── BotDashboard.tsx
│       └── StrategyView.tsx
├── tailwind.config.js
├── vite.config.ts
└── package.json
```

2. **Wireframes Document** (`WIREFRAMES.md`)
3. **Component Catalog** (`COMPONENT_CATALOG.md`)
4. **Design Tokens** (colors, spacing, typography)

**Tasks:**
- [ ] Create React + Vite project
- [ ] Install dependencies (TypeScript, Tailwind, shadcn/ui)
- [ ] Set up folder structure
- [ ] Create wireframes for Main Dashboard
- [ ] Create wireframes for Bot Dashboard
- [ ] Create wireframes for Strategy View
- [ ] Document design tokens
- [ ] Document component patterns

### Week 2: WebSocket Infrastructure

**Goals:**
- Implement Socket.io on backend
- Integrate with workflow executor
- Create frontend WebSocket service
- Test real-time updates

**Backend Deliverables:**

```python
# src/web/websocket_server.py
class DashboardWebSocket:
    """WebSocket server for real-time dashboard updates"""

    def __init__(self, app):
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*'
        )
        self.app = socketio.ASGIApp(self.sio, app)
        self._setup_handlers()

    async def emit_node_execution(self, bot_id, strategy_id, node_data):
        """Emit node execution event to subscribers"""
        await self.sio.emit('node_execution', {
            'botId': bot_id,
            'strategyId': strategy_id,
            **node_data
        }, room=f'bot_{bot_id}')

    async def emit_bot_metrics(self, bot_id, metrics):
        """Emit bot metrics update"""
        await self.sio.emit('bot_metrics', {
            'botId': bot_id,
            'metrics': metrics
        }, room=f'bot_{bot_id}')
```

```python
# src/workflow/executor.py (enhanced)
class WorkflowExecutor:
    def __init__(self, workflow, websocket=None):
        self.workflow = workflow
        self.websocket = websocket  # Inject WebSocket server

    async def execute_node(self, node):
        start = time.time()

        # Execute node
        result = await node.execute(context)

        # Emit to WebSocket
        if self.websocket:
            await self.websocket.emit_node_execution(
                bot_id=self.bot_id,
                strategy_id=self.strategy_id,
                node_data={
                    'nodeId': node.node_id,
                    'timestamp': int(start * 1000),
                    'data': {
                        'outputs': result.outputs,
                        'status': result.status.value,
                        'executionTimeMs': (time.time() - start) * 1000
                    }
                }
            )

        return result
```

**Frontend Deliverables:**

```typescript
// src/services/websocket.ts
import io from 'socket.io-client';

export class DashboardWebSocket {
  private socket: Socket;

  constructor() {
    this.socket = io('http://localhost:8000', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    this.setupHandlers();
  }

  // Subscribe to bot updates
  subscribeToBotfinal(botId: string, handler: (data: BotMetrics) => void) {
    this.socket.emit('subscribe', { botId });
    this.socket.on('bot_metrics', (data) => {
      if (data.botId === botId) handler(data.metrics);
    });
  }

  // Subscribe to node executions
  subscribeToNodeExecutions(
    botId: string,
    strategyId: string,
    handler: (data: NodeExecution) => void
  ) {
    this.socket.on('node_execution', (data) => {
      if (data.botId === botId && data.strategyId === strategyId) {
        handler(data);
      }
    });
  }
}
```

**Tasks:**
- [ ] Install python-socketio in backend
- [ ] Create WebSocket server class
- [ ] Integrate with workflow executor
- [ ] Create frontend WebSocket service
- [ ] Test connection and reconnection
- [ ] Document event protocol
- [ ] Add authentication (basic)

### Week 3: Main Dashboard

**Goals:**
- Implement main dashboard UI
- Create reusable widget components
- Integrate WebSocket for live updates
- Polish UX interactions

**Components to Build:**

1. **MetricCard**
```typescript
// Reusable metric display card
<MetricCard
  title="Total P&L"
  value={4234.56}
  format="currency"
  trend={+12.3}
  trendPeriod="24h"
  icon={<TrendingUpIcon />}
/>
```

2. **BotCard**
```typescript
// Bot card with live metrics
<BotCard
  bot={bot}
  onDoubleClick={() => navigate(`/bot/${bot.id}`)}
  liveMetrics={wsMetrics}
  showQuickStats
/>
```

3. **RiskDashboard**
```typescript
// Risk limit visualization
<RiskDashboard
  limits={globalRiskLimits}
  currentUsage={currentUsage}
  showBreakdown
/>
```

4. **DashboardGrid**
```typescript
// Responsive grid layout
<DashboardGrid
  columns={{ sm: 1, md: 2, lg: 3 }}
  gap={4}
>
  {botCards}
</DashboardGrid>
```

**Tasks:**
- [ ] Create shadcn/ui base components
- [ ] Build MetricCard widget
- [ ] Build BotCard widget
- [ ] Build RiskDashboard widget
- [ ] Implement DashboardGrid layout
- [ ] Connect WebSocket for live metrics
- [ ] Add navigation to bot dashboard
- [ ] Polish animations and transitions
- [ ] Test with multiple bots

### Week 4: Bot Dashboard

**Goals:**
- Implement bot dashboard UI
- Create orchestration diagram (basic)
- Build strategy cards
- Add portfolio widget

**Components to Build:**

1. **OrchestrationDiagram**
```typescript
// Bot-level workflow diagram
<OrchestrationDiagram
  workflow={botWorkflow}
  liveData={wsData}
  onNodeClick={showNodeDetails}
  onNodeDoubleClick={drillDownToStrategy}
/>
```

2. **StrategyCard**
```typescript
// Strategy instance card
<StrategyCard
  strategy={strategyInstance}
  metrics={liveMetrics}
  onView={() => navigate(`/strategy/${strategy.id}`)}
  onPause={toggleStrategyPause}
/>
```

3. **PortfolioWidget**
```typescript
// Portfolio/position display
<PortfolioWidget
  positions={positions}
  totalValue={totalValue}
  showBreakdown
  onAssetClick={showAssetDetails}
/>
```

**Tasks:**
- [ ] Build bot dashboard layout
- [ ] Implement orchestration diagram (basic ReactFlow)
- [ ] Create strategy card component
- [ ] Build portfolio widget
- [ ] Add performance charts
- [ ] Connect WebSocket for bot-level updates
- [ ] Implement breadcrumb navigation
- [ ] Test with multiple strategies

### Week 5: Strategy View

**Goals:**
- Implement strategy view UI
- Create live workflow diagram
- Add execution timeline
- Implement runtime value editing

**Components to Build:**

1. **LiveWorkflowDiagram**
```typescript
// Strategy workflow with live data
<LiveWorkflowDiagram
  workflow={strategyWorkflow}
  liveNodeData={wsNodeData}
  onNodeClick={showNodeDetails}
  runtimeEditable
  onValueSave={saveRuntimeValue}
/>
```

2. **NodeWidget** (within diagram)
```typescript
// Node with live data display
<NodeWidget
  node={node}
  liveData={currentData}
  editable={runtimeEditable}
  onValueChange={handleValueChange}
  onSave={saveAsDefault}
  showChangeIndicator
/>
```

3. **ExecutionTimeline**
```typescript
// Visual execution history
<ExecutionTimeline
  executions={recentExecutions}
  maxDisplay={100}
  onClick={showExecutionDetails}
/>
```

4. **RuntimeValueEditor**
```typescript
// Edit node values during runtime
<RuntimeValueEditor
  nodeId={nodeId}
  field={field}
  currentValue={savedValue}
  runtimeValue={tweakedValue}
  onChange={setTweaked}
  onSave={saveAndLog}
  showSaveButton={hasChanges}
/>
```

**Tasks:**
- [ ] Build strategy view layout
- [ ] Implement live workflow diagram
- [ ] Create node widget with live data
- [ ] Add runtime value editing (Unity-style)
- [ ] Build execution timeline
- [ ] Create change log display
- [ ] Add execution details modal
- [ ] Connect WebSocket for node updates
- [ ] Test runtime editing and saving

### Week 6: Polish + Integration

**Goals:**
- Unify UX across all tiers
- Add animations and transitions
- Implement error handling
- Performance optimization
- Documentation

**Tasks:**
- [ ] Unified navigation (breadcrumbs, back buttons)
- [ ] Consistent color scheme and spacing
- [ ] Smooth transitions between tiers
- [ ] Loading states for all async operations
- [ ] Error boundaries and error displays
- [ ] WebSocket reconnection handling
- [ ] Performance audit (React DevTools)
- [ ] Optimize re-renders
- [ ] Write component documentation
- [ ] Create usage examples
- [ ] Record demo video

---

## Documentation Strategy

### For New Claude Code Sessions

**Critical Documents** (always keep updated):

1. **PROJECT_CONTEXT.md** (NEW)
   - Current state of implementation
   - Active features
   - Known issues
   - Next immediate tasks

2. **COMPONENT_CATALOG.md** (NEW)
   - All React components
   - Props, usage examples
   - Dependencies

3. **WEBSOCKET_PROTOCOL.md** (NEW)
   - Event types
   - Message schemas
   - Usage examples

4. **DASHBOARD_ARCHITECTURE.md** (EXISTS)
   - High-level decisions
   - Data models
   - System design

5. **WIREFRAMES.md** (NEW)
   - Visual layouts
   - User flows
   - Interaction patterns

**Update Cadence:**
- **PROJECT_CONTEXT.md**: Every session
- **COMPONENT_CATALOG.md**: When adding components
- **WEBSOCKET_PROTOCOL.md**: When changing events
- **WIREFRAMES.md**: When finalizing designs

---

## Success Criteria

### Week 3 (Main Dashboard)
- [ ] Can view all bots at a glance
- [ ] Live metrics update via WebSocket
- [ ] Can double-click to navigate to bot
- [ ] Consistent design language established

### Week 4 (Bot Dashboard)
- [ ] Can see bot-level orchestration
- [ ] Can view all strategies in bot
- [ ] Can navigate to strategy view
- [ ] Portfolio and charts display correctly

### Week 5 (Strategy View)
- [ ] Can see live workflow execution
- [ ] Nodes update in real-time
- [ ] Can edit values during runtime
- [ ] Can save tweaked values (Unity-style)
- [ ] Change log displays all edits

### Week 6 (Polish)
- [ ] Smooth navigation across all tiers
- [ ] No visual inconsistencies
- [ ] WebSocket handles disconnects gracefully
- [ ] Performance is acceptable (<100ms lag)

---

## Next Immediate Actions

1. ✅ **Approve tech stack** (already approved above)
2. 📝 **Create wireframes** for Main Dashboard (Week 1 task)
3. 🏗️ **Set up React + Vite project** (Week 1 task)
4. 📚 **Document design tokens** (Week 1 task)
5. 🔌 **Prototype WebSocket connection** (Week 2 task)

**Ready to proceed with Week 1?**
