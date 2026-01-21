# Workflow Unification Plan

**Vision**: Unify bots and workflows into a single concept where every bot IS a workflow.

**Status**: 📋 Planning Phase | **Priority**: HIGH | **Estimated Effort**: 5-7 days

---

## 🎯 Core Concept

### Current Architecture (Separated)
- **Bots**: Configured via dropdown (provider + strategy + params)
- **Workflows**: Visual builder that generates Python code
- **Problem**: Disconnected systems, manual deployment, limited flexibility

### Unified Architecture (Proposed)
- **Every bot IS a workflow**
- **Providers are nodes** (not dropdowns)
- **Strategies are workflow templates**
- **Direct execution** (no Python code generation needed)

---

## 💡 Key Benefits

### 1. No More Code Generation Disconnect
**Current Flow**:
```
Build Workflow → Generate Python → Save to file → Deploy → Create Bot
```

**Unified Flow**:
```
Build/Load Workflow → Save as Bot → Start Execution
```

### 2. Provider as Node
```
[Polymarket Provider] → [Price Feed] → [RSI > 70?] → [Market Order]
     ↓
[Binance Provider]   → [Price Feed] →
```

**Benefits**:
- Multiple providers in one workflow (cross-exchange arbitrage!)
- Provider swapping = just change the node
- Provider becomes a configurable block like any other

### 3. Strategy Templates = Workflow Templates
All 11 current strategies become pre-built workflow templates:
- Cross Exchange Arbitrage → Template with 2 provider nodes
- Funding Rate Arbitrage → Template with funding node
- Grid Trading → Template with price levels

### 4. Live Workflow Editing
- Edit running bot's workflow in real-time
- Clone profitable bot workflows
- A/B test by changing single nodes

### 5. Better Visualization
- Bot cards show miniature workflow preview
- Understand what each bot does at a glance
- Group bots by workflow pattern

---

## 🏗️ Architecture Design

### New Node Types

#### 1. Provider Nodes (Input Source)
```javascript
{
    id: 'provider_polymarket',
    type: 'provider',
    subtype: 'polymarket',
    config: {
        profile_id: 'production',  // Links to credential profile
        enabled_endpoints: ['price', 'orderbook', 'balance', 'positions']
    },
    outputs: {
        'price_feed': { type: 'stream', format: 'float' },
        'balance': { type: 'value', format: 'float' },
        'positions': { type: 'list', format: 'position[]' },
        'orderbook': { type: 'stream', format: 'orderbook' }
    }
}
```

**Visual Representation**:
```
┌─────────────────────┐
│  📊 Polymarket      │
│  Profile: Prod      │
├─────────────────────┤
│ ○ Price Feed       │──→
│ ○ Balance          │──→
│ ○ Positions        │──→
│ ○ Order Book       │──→
└─────────────────────┘
```

#### 2. Data Flow Nodes
```javascript
{
    id: 'price_monitor',
    type: 'data',
    subtype: 'price_feed',
    inputs: {
        'source': 'provider_polymarket.price_feed'
    },
    outputs: {
        'current_price': { type: 'value', format: 'float' },
        'bid': { type: 'value', format: 'float' },
        'ask': { type: 'value', format: 'float' },
        'spread': { type: 'value', format: 'float' }
    }
}
```

#### 3. Multi-Provider Comparison
```javascript
{
    id: 'spread_calc',
    type: 'comparison',
    subtype: 'price_spread',
    inputs: {
        'price_a': 'provider_polymarket.price_feed',
        'price_b': 'provider_binance.price_feed'
    },
    config: {
        'min_spread_pct': 0.5,  // 0.5% minimum spread
        'include_fees': true
    },
    outputs: {
        'spread_pct': { type: 'value', format: 'float' },
        'profitable': { type: 'boolean', format: 'bool' },
        'expected_profit': { type: 'value', format: 'float' }
    }
}
```

#### 4. Conditional Branching
```javascript
{
    id: 'spread_check',
    type: 'condition',
    subtype: 'threshold',
    inputs: {
        'value': 'spread_calc.spread_pct',
        'threshold': 0.5
    },
    outputs: {
        'true_branch': { type: 'signal', format: 'trigger' },
        'false_branch': { type: 'signal', format: 'trigger' }
    }
}
```

#### 5. Order Execution Nodes
```javascript
{
    id: 'buy_polymarket',
    type: 'action',
    subtype: 'market_order',
    inputs: {
        'provider': 'provider_polymarket',
        'trigger': 'spread_check.true_branch',
        'size': 'config.position_size'
    },
    config: {
        'side': 'buy',
        'position_size': 10,  // $10
        'max_slippage': 0.5   // 0.5%
    }
}
```

---

## 📊 Database Schema

### Bot Collection (Unified)
```json
{
    "bot_id": "bot_abc123",
    "name": "Cross Exchange Arb - BTC",
    "status": "running",
    "created_at": "2026-01-21T10:00:00Z",
    "updated_at": "2026-01-21T10:05:00Z",

    "workflow": {
        "id": "workflow_xyz789",
        "name": "Cross Exchange Arbitrage",
        "version": "1.0.0",

        "blocks": [
            {
                "id": "poly_provider",
                "type": "provider",
                "subtype": "polymarket",
                "profile_id": "production",
                "position": { "x": 100, "y": 200 }
            },
            {
                "id": "binance_provider",
                "type": "provider",
                "subtype": "binance",
                "profile_id": "production",
                "position": { "x": 100, "y": 400 }
            },
            {
                "id": "spread_calc",
                "type": "comparison",
                "subtype": "price_spread",
                "config": { "min_spread_pct": 0.5 },
                "position": { "x": 400, "y": 300 }
            },
            {
                "id": "profitable_check",
                "type": "condition",
                "subtype": "threshold",
                "config": { "threshold": 0.5 },
                "position": { "x": 700, "y": 300 }
            },
            {
                "id": "buy_low",
                "type": "action",
                "subtype": "market_order",
                "config": { "side": "buy", "position_size": 10 },
                "position": { "x": 1000, "y": 200 }
            },
            {
                "id": "sell_high",
                "type": "action",
                "subtype": "market_order",
                "config": { "side": "sell", "position_size": 10 },
                "position": { "x": 1000, "y": 400 }
            }
        ],

        "connections": [
            {
                "from": "poly_provider.price_feed",
                "to": "spread_calc.price_a"
            },
            {
                "from": "binance_provider.price_feed",
                "to": "spread_calc.price_b"
            },
            {
                "from": "spread_calc.spread_pct",
                "to": "profitable_check.value"
            },
            {
                "from": "profitable_check.true_branch",
                "to": "buy_low.trigger"
            },
            {
                "from": "profitable_check.true_branch",
                "to": "sell_high.trigger"
            }
        ]
    },

    "execution": {
        "interval_seconds": 60,
        "last_execution": "2026-01-21T10:04:30Z",
        "next_execution": "2026-01-21T10:05:30Z",
        "execution_count": 1247
    },

    "metrics": {
        "total_profit": 145.32,
        "total_trades": 89,
        "win_rate": 0.73,
        "error_rate": 0.02,
        "avg_execution_time_ms": 234
    }
}
```

---

## 🔧 Workflow Execution Engine

### WorkflowExecutor Class
```python
class WorkflowExecutor:
    """Executes workflow-based bots in real-time."""

    def __init__(self, workflow: Dict[str, Any]):
        self.workflow = workflow
        self.providers = {}          # provider_id → provider instance
        self.node_outputs = {}       # node_id → output values
        self.execution_order = []    # Topologically sorted node IDs

    async def initialize(self):
        """Initialize all provider nodes and compute execution order."""
        # 1. Initialize provider nodes
        for block in self.workflow['blocks']:
            if block['type'] == 'provider':
                profile = await self.get_profile(block['profile_id'])
                provider = create_provider(
                    block['subtype'],
                    profile['credentials']
                )
                self.providers[block['id']] = provider
                await provider.initialize()

        # 2. Compute topological execution order
        self.execution_order = self.topological_sort()

    def topological_sort(self) -> List[str]:
        """Compute execution order based on node dependencies."""
        graph = {}
        in_degree = {}

        # Build dependency graph
        for conn in self.workflow['connections']:
            from_node = conn['from'].split('.')[0]
            to_node = conn['to'].split('.')[0]

            if from_node not in graph:
                graph[from_node] = []
            graph[from_node].append(to_node)

            in_degree[to_node] = in_degree.get(to_node, 0) + 1
            if from_node not in in_degree:
                in_degree[from_node] = 0

        # Kahn's algorithm for topological sort
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    async def execute(self):
        """Execute workflow once."""
        try:
            # Execute nodes in topological order
            for node_id in self.execution_order:
                node = self.get_node(node_id)

                # Get inputs from connected nodes
                inputs = await self.get_node_inputs(node_id)

                # Execute node based on type
                outputs = await self.execute_node(node, inputs)

                # Store outputs for downstream nodes
                self.node_outputs[node_id] = outputs

                # Log execution
                logger.debug(f"Executed node {node_id}: {outputs}")

            return True

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return False

    async def execute_node(self, node: Dict, inputs: Dict) -> Dict:
        """Execute a single node based on its type."""
        node_type = node['type']

        if node_type == 'provider':
            return await self.execute_provider_node(node)
        elif node_type == 'comparison':
            return await self.execute_comparison_node(node, inputs)
        elif node_type == 'condition':
            return await self.execute_condition_node(node, inputs)
        elif node_type == 'action':
            return await self.execute_action_node(node, inputs)
        else:
            raise ValueError(f"Unknown node type: {node_type}")

    async def execute_provider_node(self, node: Dict) -> Dict:
        """Execute provider node (fetch live data)."""
        provider = self.providers[node['id']]

        outputs = {}
        if 'price_feed' in node['outputs']:
            outputs['price_feed'] = await provider.get_current_price()
        if 'balance' in node['outputs']:
            outputs['balance'] = await provider.get_balance()
        if 'positions' in node['outputs']:
            outputs['positions'] = await provider.get_positions()

        return outputs

    async def execute_comparison_node(self, node: Dict, inputs: Dict) -> Dict:
        """Execute comparison node (e.g., spread calculation)."""
        subtype = node['subtype']

        if subtype == 'price_spread':
            price_a = inputs.get('price_a')
            price_b = inputs.get('price_b')

            if price_a and price_b:
                spread_pct = abs(price_a - price_b) / price_a * 100
                min_spread = node['config'].get('min_spread_pct', 0)

                return {
                    'spread_pct': spread_pct,
                    'profitable': spread_pct >= min_spread,
                    'expected_profit': spread_pct * 0.8  # Rough estimate
                }

        return {}

    async def execute_condition_node(self, node: Dict, inputs: Dict) -> Dict:
        """Execute condition node (boolean check)."""
        subtype = node['subtype']

        if subtype == 'threshold':
            value = inputs.get('value', 0)
            threshold = node['config'].get('threshold', 0)

            if value >= threshold:
                return {'true_branch': True, 'false_branch': False}
            else:
                return {'true_branch': False, 'false_branch': True}

        return {}

    async def execute_action_node(self, node: Dict, inputs: Dict) -> Dict:
        """Execute action node (e.g., place order)."""
        # Only execute if trigger input is True
        trigger = inputs.get('trigger', False)
        if not trigger:
            return {'executed': False}

        subtype = node['subtype']

        if subtype == 'market_order':
            provider_id = inputs.get('provider')
            provider = self.providers.get(provider_id)

            if provider:
                order = await provider.create_market_order(
                    side=node['config']['side'],
                    size=node['config']['position_size']
                )
                return {'executed': True, 'order': order}

        return {'executed': False}

    async def get_node_inputs(self, node_id: str) -> Dict:
        """Get input values for a node from connected nodes."""
        inputs = {}

        for conn in self.workflow['connections']:
            to_node, to_port = conn['to'].split('.')

            if to_node == node_id:
                from_node, from_port = conn['from'].split('.')

                # Get value from stored outputs
                if from_node in self.node_outputs:
                    value = self.node_outputs[from_node].get(from_port)
                    inputs[to_port] = value

        return inputs

    def get_node(self, node_id: str) -> Dict:
        """Get node definition by ID."""
        for block in self.workflow['blocks']:
            if block['id'] == node_id:
                return block
        return None
```

---

## 🎨 UI Changes

### 1. Bot Creation Flow (New)

**Old Way**:
```
Click "Create Bot" → Modal with dropdowns → Fill form → Create
```

**New Way**:
```
Click "Create Bot" → Strategy Builder opens → Choose template or build → Save as bot
```

**Implementation**:
```javascript
function createBot() {
    // Open strategy builder in "create mode"
    window.location.href = '/strategy-builder?mode=create';
}

// In strategy builder
if (urlParams.get('mode') === 'create') {
    // Show template selection first
    showTemplateLibrary();
}
```

### 2. Bot Card Enhancements

**Add Workflow Preview**:
```html
<div class="bot-card">
    <div class="bot-card__workflow-preview">
        <!-- Mini canvas showing workflow diagram -->
        <canvas id="workflow-mini-{{ bot.id }}"
                width="300" height="100"></canvas>
    </div>

    <div class="bot-card__providers">
        <!-- Show all providers used in workflow -->
        <span class="provider-badge">📊 Polymarket</span>
        <span class="provider-badge">🔗 Binance</span>
    </div>

    <div class="bot-card__actions">
        <button onclick="editBotWorkflow('{{ bot.id }}')">
            ✏️ Edit Workflow
        </button>
        <button onclick="cloneBotWorkflow('{{ bot.id }}')">
            📋 Clone
        </button>
    </div>
</div>
```

**Mini Workflow Renderer**:
```javascript
function renderMiniWorkflow(canvasId, workflow) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');

    // Simple node rendering at small scale
    const scale = 0.2;  // 20% of full size

    workflow.blocks.forEach(block => {
        const x = block.position.x * scale;
        const y = block.position.y * scale;

        // Draw tiny node
        ctx.fillStyle = getNodeColor(block.type);
        ctx.fillRect(x, y, 20, 15);
    });

    // Draw connections
    workflow.connections.forEach(conn => {
        // ... simple line rendering
    });
}
```

### 3. Template Library Modal

```html
<div id="templateLibrary" class="modal">
    <div class="modal-header">
        <h2>Choose Strategy Template</h2>
    </div>

    <div class="template-grid">
        <!-- Cross Exchange Arb -->
        <div class="template-card" onclick="loadTemplate('cross_exchange')">
            <div class="template-preview">
                <!-- Mini workflow preview -->
                <canvas id="template-cross-exchange"></canvas>
            </div>
            <h3>Cross Exchange Arbitrage</h3>
            <p>Trade price differences between exchanges</p>
            <div class="template-stats">
                <span>2 Providers</span>
                <span>Avg Return: 2.3%/day</span>
            </div>
        </div>

        <!-- Funding Rate Arb -->
        <div class="template-card" onclick="loadTemplate('funding_rate')">
            <div class="template-preview">
                <canvas id="template-funding-rate"></canvas>
            </div>
            <h3>Funding Rate Arbitrage</h3>
            <p>Capture funding rate differentials</p>
            <div class="template-stats">
                <span>1 Provider</span>
                <span>Avg Return: 1.8%/day</span>
            </div>
        </div>

        <!-- More templates... -->
    </div>

    <button onclick="startFromScratch()">
        Or Start from Scratch
    </button>
</div>
```

---

## 🗓️ Implementation Phases

### Phase 1: Provider Nodes (2 days)
**Goal**: Add provider nodes to strategy builder

**Tasks**:
- [ ] Create provider node type definition
- [ ] Add provider node to block library
- [ ] Implement provider node rendering
- [ ] Add profile selection to provider config
- [ ] Test dragging provider nodes onto canvas

**Files to Modify**:
- `src/web/static/js/components/strategy-builder.js`
- `src/web/static/css/strategy-builder.css`

### Phase 2: Workflow Execution Engine (3 days)
**Goal**: Execute workflows directly without code generation

**Tasks**:
- [ ] Create `WorkflowExecutor` class in Python
- [ ] Implement topological sort for node dependencies
- [ ] Add provider node execution
- [ ] Add comparison node execution
- [ ] Add condition node execution
- [ ] Add action node execution
- [ ] Test full workflow execution

**Files to Create**:
- `src/workflow/executor.py`
- `src/workflow/nodes/` (provider, comparison, condition, action)

### Phase 3: Convert Strategies to Templates (1 day)
**Goal**: Convert existing 11 strategies to workflow templates

**Tasks**:
- [ ] Define workflow JSON for each strategy
- [ ] Create template library JSON file
- [ ] Add template preview images/canvases
- [ ] Test loading each template

**Files to Create**:
- `src/web/static/data/workflow-templates.json`

### Phase 4: Update Bot Creation Flow (1 day)
**Goal**: Replace dropdown-based bot creation with workflow-based

**Tasks**:
- [ ] Modify "Create Bot" button to open strategy builder
- [ ] Add template selection modal
- [ ] Implement "Save as Bot" functionality
- [ ] Update bot database schema
- [ ] Migrate existing bots to workflow format

**Files to Modify**:
- `src/web/templates/dashboard.html`
- `src/web/static/js/components/bot-config-modal.js`
- `src/web/server.py` (bot creation endpoints)

### Phase 5: Bot Card Workflow Preview (1-2 days)
**Goal**: Show mini workflow on each bot card

**Tasks**:
- [ ] Create mini workflow renderer
- [ ] Add canvas to bot card template
- [ ] Render workflow on card load
- [ ] Add "Edit Workflow" button
- [ ] Add "Clone Workflow" button
- [ ] Implement workflow editing from bot card

**Files to Modify**:
- `src/web/templates/dashboard.html`
- `src/web/static/js/dashboard.js`
- `src/web/static/css/bot-card.css`

---

## 🔥 Killer Features This Enables

### 1. Visual Debugging
See execution state on workflow in real-time:
```
[Provider] ✅ → [Spread Calc] ✅ → [Check] ❌ → [Order] ⏸️
                    2.3%              Failed       Not executed
```

### 2. A/B Testing
```
Bot A: [RSI < 30] → [Buy]
Bot B: [RSI < 25] → [Buy]  ← Changed threshold

Compare performance side-by-side
```

### 3. Multi-Provider Arbitrage
```
[Polymarket] ──┐
               ├─→ [Spread] → [Profitable?] → [Execute Both]
[Binance]   ──┘
```

### 4. Conditional Execution
```
[Time] → [Market Hours?] ──True──→ [Aggressive Strategy]
                        └─False─→ [Conservative Strategy]
```

### 5. Risk Management Chains
```
[Order] → [Position Monitor] → [Profit > 5%?] ──True──→ [Take Profit]
                              └─────────────────False─→ [Continue]
```

### 6. Workflow Marketplace
- Share profitable workflows
- Rate/review workflows
- One-click clone and deploy
- Track workflow performance statistics

---

## 📝 Template Examples

### Template 1: Cross Exchange Arbitrage
```json
{
    "name": "Cross Exchange Arbitrage",
    "description": "Trade price differences between Polymarket and Binance",
    "category": "arbitrage",
    "difficulty": "medium",
    "avg_return_pct": 2.3,

    "workflow": {
        "blocks": [
            {
                "id": "poly", "type": "provider", "subtype": "polymarket",
                "position": { "x": 100, "y": 200 }
            },
            {
                "id": "binance", "type": "provider", "subtype": "binance",
                "position": { "x": 100, "y": 400 }
            },
            {
                "id": "spread", "type": "comparison", "subtype": "price_spread",
                "config": { "min_spread_pct": 0.5 },
                "position": { "x": 400, "y": 300 }
            },
            {
                "id": "check", "type": "condition", "subtype": "threshold",
                "position": { "x": 700, "y": 300 }
            },
            {
                "id": "buy_low", "type": "action", "subtype": "market_order",
                "config": { "side": "buy", "position_size": 10 },
                "position": { "x": 1000, "y": 200 }
            },
            {
                "id": "sell_high", "type": "action", "subtype": "market_order",
                "config": { "side": "sell", "position_size": 10 },
                "position": { "x": 1000, "y": 400 }
            }
        ],
        "connections": [
            { "from": "poly.price_feed", "to": "spread.price_a" },
            { "from": "binance.price_feed", "to": "spread.price_b" },
            { "from": "spread.spread_pct", "to": "check.value" },
            { "from": "check.true_branch", "to": "buy_low.trigger" },
            { "from": "check.true_branch", "to": "sell_high.trigger" }
        ]
    }
}
```

### Template 2: RSI Mean Reversion
```json
{
    "name": "RSI Mean Reversion",
    "description": "Buy when oversold (RSI < 30), sell when overbought (RSI > 70)",
    "category": "momentum",
    "difficulty": "easy",
    "avg_return_pct": 1.5,

    "workflow": {
        "blocks": [
            {
                "id": "provider", "type": "provider", "subtype": "polymarket",
                "position": { "x": 100, "y": 300 }
            },
            {
                "id": "rsi", "type": "indicator", "subtype": "rsi",
                "config": { "period": 14 },
                "position": { "x": 400, "y": 300 }
            },
            {
                "id": "oversold", "type": "condition", "subtype": "threshold",
                "config": { "threshold": 30, "operator": "<" },
                "position": { "x": 700, "y": 200 }
            },
            {
                "id": "overbought", "type": "condition", "subtype": "threshold",
                "config": { "threshold": 70, "operator": ">" },
                "position": { "x": 700, "y": 400 }
            },
            {
                "id": "buy", "type": "action", "subtype": "market_order",
                "config": { "side": "buy", "position_size": 10 },
                "position": { "x": 1000, "y": 200 }
            },
            {
                "id": "sell", "type": "action", "subtype": "market_order",
                "config": { "side": "sell", "position_size": 10 },
                "position": { "x": 1000, "y": 400 }
            }
        ],
        "connections": [
            { "from": "provider.price_feed", "to": "rsi.input" },
            { "from": "rsi.value", "to": "oversold.value" },
            { "from": "rsi.value", "to": "overbought.value" },
            { "from": "oversold.true_branch", "to": "buy.trigger" },
            { "from": "overbought.true_branch", "to": "sell.trigger" }
        ]
    }
}
```

---

## 🎯 Success Metrics

### User Experience
- **Bot creation time**: <3 minutes (vs 15 minutes with code)
- **Template adoption**: >80% users start from template
- **Workflow editing**: >60% users edit running bot workflows
- **Clone rate**: >40% new bots are clones of existing ones

### Technical Performance
- **Workflow execution latency**: <200ms average
- **Node execution time**: <50ms per node
- **Topological sort time**: <10ms for 50-node workflows
- **Memory usage**: <50MB per active bot

### Feature Adoption
- **Multi-provider workflows**: >30% bots use 2+ providers
- **Visual debugging usage**: >50% users check execution state
- **A/B testing**: >25% users run parallel bot experiments

---

## 🚨 Challenges & Solutions

### Challenge 1: Backward Compatibility
**Problem**: Existing bots use old config format

**Solution**: Migration script
```python
def migrate_old_bot_to_workflow(old_bot: Dict) -> Dict:
    """Convert old bot config to workflow format."""
    strategy_name = old_bot['strategy']
    template = load_template(strategy_name)

    # Inject provider node with old credentials
    for block in template['blocks']:
        if block['type'] == 'provider':
            block['profile_id'] = create_profile_from_old_config(old_bot)

    return {
        'bot_id': old_bot['bot_id'],
        'workflow': template,
        'migrated_from': 'legacy'
    }
```

### Challenge 2: Execution Performance
**Problem**: Workflow execution might be slower than compiled code

**Solution**:
- Cache topological sort
- Lazy evaluation of unused branches
- Parallel execution of independent nodes
- Node result caching for identical inputs

### Challenge 3: Complex Workflows
**Problem**: Very large workflows (100+ nodes) might be hard to navigate

**Solution**:
- Subworkflow nodes (nested workflows)
- Minimap in corner
- Search/filter nodes
- Collapse node groups

---

## 📚 Related Documentation

- **Current Implementation**: See `UX_FEATURES.md` for existing strategy builder
- **Code Generation**: See `IMPLEMENTATION_GUIDE.md` for current code gen approach
- **Provider System**: See `src/providers/` for provider architecture
- **Bot Management**: See `src/web/server.py` for current bot management

---

## ✅ Next Steps for New Session

1. **Review this document** - Understand the unified architecture vision
2. **Start with Phase 1** - Add provider nodes to strategy builder
3. **Prototype executor** - Create minimal WorkflowExecutor with 2-3 node types
4. **Test end-to-end** - Create simple workflow → Execute → Verify results
5. **Iterate** - Expand node types and features based on testing

---

**Status**: 📋 Ready for Implementation
**Priority**: HIGH - This is a fundamental architectural improvement
**Estimated Timeline**: 5-7 days for full implementation
**Risk Level**: MEDIUM - Requires careful migration of existing bots

This design document should be used as the primary reference for implementing the workflow unification in a fresh session.
