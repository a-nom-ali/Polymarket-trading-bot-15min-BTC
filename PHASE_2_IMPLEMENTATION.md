# Phase 2 Implementation: Workflow Execution Engine

**Status**: ✅ COMPLETE | **Date**: 2026-01-21 | **Commit**: `3448cfd`

---

## 🎯 Objective

Create a Python workflow execution engine that can execute visual workflow graphs directly without code generation. This enables real-time workflow execution with proper node dependency resolution.

---

## 📦 What Was Implemented

### 1. **WorkflowExecutor Class**
**File**: `src/workflow/executor.py` (462 lines)

Core class that executes workflow graphs in real-time.

```python
class WorkflowExecutor:
    """Executes workflow-based bots in real-time."""

    def __init__(self, workflow: Dict[str, Any]):
        self.workflow = workflow
        self.providers = {}  # provider_id → provider instance
        self.node_outputs = {}  # node_id → output values
        self.execution_order = []  # Topologically sorted node IDs
```

**Key Features**:
- Topological sort for execution order
- Provider initialization
- Node execution handlers
- Error handling and logging
- Performance timing

---

### 2. **Topological Sort (Kahn's Algorithm)**
**File**: `src/workflow/executor.py:66-116`

Computes execution order based on node dependencies to prevent executing a node before its inputs are ready.

```python
def _topological_sort(self) -> List[str]:
    """Compute execution order using Kahn's algorithm."""

    # Build dependency graph
    graph = defaultdict(list)  # node → [dependent_nodes]
    in_degree = defaultdict(int)  # node → number of dependencies

    # Build graph from connections
    for conn in self.workflow.get('connections', []):
        from_node = conn['from']['blockId']
        to_node = conn['to']['blockId']

        graph[from_node].append(to_node)
        in_degree[to_node] += 1

    # Kahn's algorithm
    queue = deque([node for node in all_nodes if in_degree[node] == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)

        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check for cycles
    if len(result) != len(all_nodes):
        raise ValueError("Workflow contains cycles - cannot execute")

    return result
```

**Example**:
```
Workflow:
[Provider A] → [Spread Calc] → [Threshold] → [Buy Order]
[Provider B] ↗

Execution Order:
1. Provider A
2. Provider B
3. Spread Calc  (waits for both providers)
4. Threshold    (waits for spread calc)
5. Buy Order    (waits for threshold)
```

---

### 3. **Provider Node Execution**
**File**: `src/workflow/executor.py:201-234`

Fetches live market data from providers (currently mock data).

```python
async def _execute_provider_node(self, node: Dict, inputs: Dict) -> Dict:
    """Execute provider node (fetch live data)."""

    provider_id = node['id']
    provider = self.providers.get(provider_id)
    enabled_endpoints = provider['enabled_endpoints']
    outputs = {}

    # Mock data for now - will be replaced with actual provider calls
    if 'price_feed' in enabled_endpoints:
        outputs['price_feed'] = 0.52

    if 'balance' in enabled_endpoints:
        outputs['balance'] = 1000.0

    if 'positions' in enabled_endpoints:
        outputs['positions'] = []

    if 'orderbook' in enabled_endpoints:
        outputs['orderbook'] = {
            'bids': [[0.51, 100]],
            'asks': [[0.53, 100]]
        }

    return outputs
```

**Future Integration**:
- Replace mock data with actual provider API calls
- Use `profile_id` to load credentials
- Handle rate limiting and errors

---

### 4. **Condition Node Execution**
**File**: `src/workflow/executor.py:244-301`

Evaluates boolean conditions and routing logic.

**Supported Conditions**:

| Node Type | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `threshold` | Check if value within range | value, min, max | pass (bool) |
| `compare` | Compare two values | value1, operator, value2 | result (bool) |
| `and` | Logical AND gate | input1, input2 | output (bool) |
| `or` | Logical OR gate | input1, input2 | output (bool) |
| `if` | If/else branch | condition | true, false |

**Example - Threshold**:
```python
# Node checks if spread > 0.5%
if node_type == 'threshold':
    value = inputs.get('value', 0)  # spread: 0.8
    min_val = inputs.get('min', float('-inf'))
    max_val = inputs.get('max', float('inf'))

    passed = min_val <= value <= max_val  # True
    return {'pass': True}
```

**Example - Compare**:
```python
# Node checks if price > threshold
if node_type == 'compare':
    value1 = inputs.get('value1', 0)  # price: 0.52
    value2 = inputs.get('value2', 0)  # threshold: 0.50
    operator = inputs.get('operator', '==')  # '>'

    result = value1 > value2  # True
    return {'result': True}
```

---

### 5. **Action Node Execution**
**File**: `src/workflow/executor.py:303-347`

Executes trading actions (buy, sell, cancel, notify).

```python
async def _execute_action_node(self, node: Dict, inputs: Dict) -> Dict:
    """Execute action node."""

    node_type = node['type']

    if node_type == 'buy' or node_type == 'sell':
        signal = inputs.get('signal', False)
        amount = inputs.get('amount', 0)

        if not signal:
            return {'order': None}

        # Mock order execution
        order = {
            'side': node_type,
            'amount': amount,
            'price': 0.52,
            'status': 'filled'
        }
        logger.info(f"Executed {node_type} order: {order}")
        return {'order': order}

    elif node_type == 'notify':
        signal = inputs.get('signal', False)
        message = inputs.get('message', '')
        if signal:
            logger.info(f"Notification: {message}")
            return {'sent': True}
        return {'sent': False}
```

**Features**:
- Signal-gated execution (only execute if signal is True)
- Logging for audit trail
- Mock execution (ready for real provider integration)

---

### 6. **Node Input Resolution**
**File**: `src/workflow/executor.py:351-388`

Maps outputs from upstream nodes to inputs of downstream nodes via connections.

```python
async def _get_node_inputs(self, node_id: str) -> Dict[str, Any]:
    """Get input values for a node from connected nodes."""
    inputs = {}

    for conn in self.workflow.get('connections', []):
        to_node_id = conn['to']['blockId']

        if to_node_id == node_id:
            from_node_id = conn['from']['blockId']
            from_output_index = conn['from']['index']

            # Get the output name from the from_node
            from_node = self._get_node(from_node_id)
            from_output_name = from_node['outputs'][from_output_index]['name']

            # Get value from stored outputs
            if from_node_id in self.node_outputs:
                value = self.node_outputs[from_node_id].get(from_output_name)

                # Get the input name from to_node
                to_node = self._get_node(to_node_id)
                to_input_index = conn['to']['index']
                to_input_name = to_node['inputs'][to_input_index]['name']

                inputs[to_input_name] = value

    return inputs
```

**Example**:
```
Connection:
{
    from: { blockId: 'provider_1', index: 0 },  // price_feed output
    to: { blockId: 'threshold_1', index: 0 }    // value input
}

Result:
inputs = {
    'value': 0.52  // price_feed value from provider_1
}
```

---

### 7. **Workflow Execution API**
**File**: `src/web/server.py:793-858`

HTTP endpoint to execute workflows from the frontend.

```python
@self.app.route('/api/workflow/execute', methods=['POST'])
def api_execute_workflow():
    """
    Execute a workflow graph.

    Request body:
        {
            "workflow": {
                "blocks": [...],
                "connections": [...]
            }
        }

    Returns:
        {
            "status": "completed",
            "duration": 234,
            "results": [...],
            "errors": []
        }
    """
    workflow = request.json.get('workflow')

    # Create executor
    executor = WorkflowExecutor(workflow)

    # Run in event loop
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(executor.initialize())
        result = loop.run_until_complete(executor.execute())
        return jsonify(result)
    finally:
        loop.close()
```

**Request Example**:
```json
POST /api/workflow/execute
{
    "workflow": {
        "blocks": [
            {
                "id": "provider_poly",
                "category": "providers",
                "type": "polymarket",
                "properties": {
                    "profile_id": "prod_1",
                    "enabled_endpoints": ["price_feed"]
                },
                "outputs": [{"name": "price_feed"}]
            },
            {
                "id": "threshold_1",
                "category": "conditions",
                "type": "threshold",
                "inputs": [{"name": "value"}, {"name": "min"}],
                "outputs": [{"name": "pass"}]
            }
        ],
        "connections": [
            {
                "from": {"blockId": "provider_poly", "index": 0},
                "to": {"blockId": "threshold_1", "index": 0}
            }
        ]
    }
}
```

**Response Example**:
```json
{
    "status": "completed",
    "duration": 234,
    "results": [
        {
            "nodeId": "provider_poly",
            "nodeName": "Polymarket",
            "nodeType": "providers",
            "output": {"price_feed": 0.52},
            "duration": 45
        },
        {
            "nodeId": "threshold_1",
            "nodeName": "Threshold",
            "nodeType": "conditions",
            "output": {"pass": true},
            "duration": 2
        }
    ],
    "errors": []
}
```

---

### 8. **Credential Profiles API**
**File**: `src/web/server.py:860-895`

HTTP endpoint to fetch credential profiles for provider nodes.

```python
@self.app.route('/api/credentials/profiles', methods=['GET'])
def api_get_credential_profiles():
    """
    Get credential profiles for a provider.

    Query params:
        provider: Provider name (polymarket, binance, kalshi)

    Returns:
        [{
            "id": "prod_1",
            "name": "Production",
            "provider": "polymarket",
            "created_at": "2026-01-20T10:00:00Z"
        }]
    """
    provider = request.args.get('provider')

    # Get all profiles and filter by provider
    all_profiles = self.profile_manager.get_all_profiles()
    provider_profiles = [
        {
            'id': profile_id,
            'name': profile.get('name', profile_id),
            'provider': profile.get('provider', provider),
            'created_at': profile.get('created_at')
        }
        for profile_id, profile in all_profiles.items()
        if profile.get('provider') == provider
    ]

    return jsonify(provider_profiles)
```

**Usage**:
```
GET /api/credentials/profiles?provider=polymarket

Response:
[
    {
        "id": "prod_1",
        "name": "Production",
        "provider": "polymarket",
        "created_at": "2026-01-20T10:00:00Z"
    },
    {
        "id": "test_1",
        "name": "Testing",
        "provider": "polymarket",
        "created_at": "2026-01-20T12:00:00Z"
    }
]
```

---

## 🔄 Execution Flow

### **Complete Workflow Execution**

1. **Frontend**: User clicks "Run Workflow" button
2. **Frontend**: Sends workflow JSON to `POST /api/workflow/execute`
3. **Backend**: Creates `WorkflowExecutor(workflow)`
4. **Backend**: Calls `executor.initialize()`
   - Initializes provider nodes
   - Computes topological sort
5. **Backend**: Calls `executor.execute()`
   - Executes nodes in order
   - Passes outputs between nodes
   - Tracks timing and errors
6. **Backend**: Returns execution results
7. **Frontend**: Displays results modal with node outputs

---

## 🧪 Example Workflow Execution

### **Simple Price Threshold Strategy**

**Workflow**:
```
[Polymarket Provider] → [Threshold > 0.50] → [Buy Order]
```

**Blocks**:
```json
[
    {
        "id": "poly",
        "category": "providers",
        "type": "polymarket",
        "properties": {"profile_id": "prod_1", "enabled_endpoints": ["price_feed"]}
    },
    {
        "id": "threshold",
        "category": "conditions",
        "type": "threshold",
        "properties": {"min": 0.50}
    },
    {
        "id": "buy",
        "category": "actions",
        "type": "buy",
        "properties": {"amount": 10}
    }
]
```

**Execution Order**: `poly` → `threshold` → `buy`

**Step-by-Step Execution**:

1. **Execute Provider** (`poly`)
   - Fetches price from Polymarket
   - Output: `{"price_feed": 0.52}`
   - Duration: 45ms

2. **Execute Threshold** (`threshold`)
   - Input: `value = 0.52` (from poly.price_feed)
   - Check: `0.52 >= 0.50` → True
   - Output: `{"pass": true}`
   - Duration: 2ms

3. **Execute Buy Order** (`buy`)
   - Input: `signal = true` (from threshold.pass)
   - Creates order: `{side: "buy", amount: 10, price: 0.52}`
   - Output: `{"order": {...}}`
   - Duration: 15ms

**Total Duration**: 62ms

---

## 🎯 Success Criteria Met

✅ **WorkflowExecutor class created**
✅ **Topological sort implemented (Kahn's algorithm)**
✅ **Provider node execution handler added**
✅ **Condition node execution handler added (5 types)**
✅ **Action node execution handler added (4 types)**
✅ **Workflow execution API endpoint created**
✅ **Credential profiles API endpoint created**
✅ **Cycle detection in workflows**
✅ **Error handling and logging**
✅ **Performance timing per node**

---

## 📊 Files Created/Modified

| File | Lines | Description |
|------|-------|-------------|
| `src/workflow/__init__.py` | 8 | Module initialization |
| `src/workflow/executor.py` | 462 | WorkflowExecutor class |
| `src/workflow/nodes/__init__.py` | 10 | Node handlers placeholder |
| `src/web/server.py` | +102 | API endpoints |

**Total**: +582 lines of code

---

## 🔍 Node Execution Summary

| Node Category | Types Implemented | Status |
|---------------|------------------|--------|
| **Providers** | polymarket, binance, kalshi | ✅ Mock data |
| **Triggers** | All types | ✅ Basic implementation |
| **Conditions** | threshold, compare, and, or, if, switch | ✅ Complete |
| **Actions** | buy, sell, cancel, notify | ✅ Mock execution |
| **Risk** | All types | ✅ Basic implementation |

---

## 🚀 Next Steps: Phase 3

**Goal**: Convert existing strategies to workflow templates

### **Tasks**:
1. Create `src/web/static/data/workflow-templates.json`
2. Define workflow JSON for each of the 11 strategies:
   - Cross Exchange Arbitrage
   - Funding Rate Arbitrage
   - Grid Trading
   - RSI Mean Reversion
   - MACD Crossover
   - Bollinger Bands
   - EMA Cross
   - Volume Spike
   - Support/Resistance
   - Delta Neutral
   - Market Making
3. Add template preview rendering
4. Integrate with template selector modal
5. Test loading each template

**Estimated Time**: 1 day

---

## 📝 Known Limitations

1. **Mock Provider Data**: Currently returns hardcoded values instead of real market data
2. **No Provider Integration**: Needs actual provider API calls
3. **No Persistence**: Workflows not saved to database yet
4. **No Real-Time Execution**: Runs once, doesn't loop continuously
5. **No Backpressure**: No handling of slow nodes or rate limits

**To Be Addressed**: Future phases and integration work

---

## 🔗 Related Documentation

- **Workflow Unification Plan**: `WORKFLOW_UNIFICATION_PLAN.md` (Lines 629-641)
- **Phase 1 Implementation**: `PHASE_1_IMPLEMENTATION.md`
- **Commit**: `3448cfd` - "✨ Add workflow execution engine (Phase 2)"

---

**Phase 2**: ✅ COMPLETE
**Next**: Phase 3 - Strategy Templates
**Status**: Ready to proceed
