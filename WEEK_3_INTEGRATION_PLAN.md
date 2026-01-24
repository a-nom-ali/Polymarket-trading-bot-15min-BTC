# Week 3: Infrastructure Integration & WebSocket Events

**Duration:** 5 Days
**Goal:** Integrate Week 2 infrastructure with existing workflow system and enable real-time UI updates
**Status:** Ready to Start

---

## Overview

Week 2 delivered production-ready infrastructure components. Week 3 focuses on **integration** - wiring the new infrastructure into the existing workflow executor to enable real-time monitoring, emergency controls, and reliable execution.

**Key Objective:** Enable the dashboard UI to receive real-time updates from running workflows through WebSocket events.

---

## Architecture Integration Points

### Current State (Before Week 3)

```
Workflow Executor (Existing)
├── Executes nodes sequentially
├── No event emission
├── No correlation ID tracking
├── No emergency halt checks
├── No state persistence
└── No resilience patterns

Infrastructure (Week 2 - Isolated)
├── State management ✅
├── Event bus ✅
├── Structured logging ✅
├── Resilience patterns ✅
├── Emergency controls ✅
└── Configuration ✅
```

### Target State (After Week 3)

```
Enhanced Workflow Executor
├── Uses infrastructure factory for initialization
├── Emits events to event bus on each node execution
├── Sets correlation ID for each workflow execution
├── Checks emergency controller before each execution
├── Persists workflow state to state store
├── Uses circuit breakers for external calls
├── Retries with exponential backoff
└── Logs with structured logging

WebSocket Server
├── Subscribes to event bus
├── Forwards events to connected clients
├── Sends real-time node execution updates
├── Sends bot/strategy metrics
└── Handles client subscriptions by bot/strategy ID
```

---

## Day-by-Day Plan

### Day 1: Workflow Executor Enhancement

**Goal:** Integrate infrastructure into workflow executor

**Tasks:**

1. **Add Infrastructure Initialization**
   ```python
   # src/workflow/executor.py
   from src.infrastructure.factory import create_infrastructure

   class WorkflowExecutor:
       async def __init__(self, config_env="development"):
           self.infra = await create_infrastructure(config_env)
           self.state = self.infra.state
           self.events = self.infra.events
           self.emergency = self.infra.emergency
           self.logger = get_logger(__name__)
   ```

2. **Add Correlation ID Tracking**
   ```python
   async def execute_workflow(self, workflow_id: str, workflow: Dict):
       execution_id = f"exec_{workflow_id}_{uuid.uuid4().hex[:8]}"
       set_correlation_id(execution_id)

       self.logger.info(
           "workflow_execution_started",
           workflow_id=workflow_id,
           execution_id=execution_id,
           node_count=len(workflow['nodes'])
       )
   ```

3. **Add Event Emission**
   ```python
   async def execute_node(self, node_id: str, node: Dict):
       # Emit node_started event
       await self.events.publish("workflow_events", {
           "type": "node_started",
           "execution_id": get_correlation_id(),
           "node_id": node_id,
           "timestamp": datetime.utcnow().isoformat()
       })

       # Execute node
       start_time = time.time()
       try:
           result = await self._run_node(node)
           duration_ms = (time.time() - start_time) * 1000

           # Emit node_completed event
           await self.events.publish("workflow_events", {
               "type": "node_completed",
               "execution_id": get_correlation_id(),
               "node_id": node_id,
               "timestamp": datetime.utcnow().isoformat(),
               "duration_ms": duration_ms,
               "status": "success",
               "outputs": result
           })
       except Exception as e:
           # Emit node_failed event
           await self.events.publish("workflow_events", {
               "type": "node_failed",
               "execution_id": get_correlation_id(),
               "node_id": node_id,
               "error": str(e),
               "error_type": type(e).__name__
           })
           raise
   ```

4. **Add Emergency Checks**
   ```python
   async def execute_workflow(self, workflow_id: str, workflow: Dict):
       # Check emergency state before starting
       await self.infra.emergency.assert_can_operate()

       # Execute workflow
       for node_id, node in workflow['nodes'].items():
           # Check before each node
           await self.infra.emergency.assert_can_trade()
           await self.execute_node(node_id, node)
   ```

5. **Add State Persistence**
   ```python
   async def execute_workflow(self, workflow_id: str, workflow: Dict):
       # Save initial state
       await self.state.set(
           f"workflow:{workflow_id}:status",
           "running"
       )

       # Execute nodes...

       # Save completion state
       await self.state.set(
           f"workflow:{workflow_id}:status",
           "completed"
       )
   ```

**Deliverable:** Enhanced workflow executor with full infrastructure integration

**Tests:**
- Workflow executor initializes infrastructure
- Events are emitted for each node execution
- Correlation IDs are tracked
- Emergency checks are enforced
- State is persisted

---

### Day 2: WebSocket Server Implementation

**Goal:** Create WebSocket server that forwards workflow events to clients

**Tasks:**

1. **Install Socket.IO**
   ```bash
   pip install python-socketio aiohttp
   ```

2. **Create WebSocket Server**
   ```python
   # src/web/websocket_server.py
   import socketio
   from src.infrastructure.factory import create_infrastructure

   class WorkflowWebSocketServer:
       def __init__(self, infra):
           self.infra = infra
           self.sio = socketio.AsyncServer(
               async_mode='aiohttp',
               cors_allowed_origins='*'
           )
           self.app = None

       async def setup(self):
           # Subscribe to workflow events
           await self.infra.events.subscribe(
               "workflow_events",
               self.handle_workflow_event
           )

       async def handle_workflow_event(self, event: dict):
           # Forward event to all connected clients
           await self.sio.emit('workflow_event', event)
   ```

3. **Add Client Management**
   ```python
   @self.sio.event
   async def connect(sid, environ):
       logger.info("client_connected", sid=sid)

   @self.sio.event
   async def disconnect(sid):
       logger.info("client_disconnected", sid=sid)

   @self.sio.event
   async def subscribe_workflow(sid, data):
       workflow_id = data.get('workflow_id')
       # Add client to workflow-specific room
       await self.sio.enter_room(sid, f"workflow:{workflow_id}")
   ```

4. **Create Server Startup Script**
   ```python
   # src/web/run_websocket_server.py
   async def main():
       infra = await create_infrastructure("development")

       server = WorkflowWebSocketServer(infra)
       await server.setup()
       await server.run(host='0.0.0.0', port=8001)
   ```

5. **Test WebSocket Connection**
   - Create simple HTML client for testing
   - Verify events are received
   - Test reconnection logic

**Deliverable:** Working WebSocket server that broadcasts workflow events

**Tests:**
- WebSocket server starts successfully
- Clients can connect
- Events are forwarded to clients
- Client subscriptions work
- Reconnection works

---

### Day 3: Resilience Integration

**Goal:** Add resilience patterns to workflow executor

**Tasks:**

1. **Add Circuit Breakers for External Calls**
   ```python
   class WorkflowExecutor:
       def __init__(self):
           # Create circuit breakers for common services
           self.api_breaker = self.infra.create_circuit_breaker(
               "exchange_api",
               failure_threshold=5
           )
   ```

2. **Add Retry Logic to Node Execution**
   ```python
   from src.infrastructure.resilience import with_retry, with_timeout

   @with_retry(
       max_attempts=3,
       retry_on=(ConnectionError, TimeoutError)
   )
   @with_timeout(30.0)
   async def execute_api_node(self, node: Dict):
       return await self.api_breaker.call(
           self._call_external_api,
           node['config']
       )
   ```

3. **Add Timeout Handling**
   ```python
   async def execute_node(self, node_id: str, node: Dict):
       timeout_seconds = node.get('timeout', 30.0)

       try:
           result = await with_timeout_async(
               self._run_node,
               node,
               timeout_seconds=timeout_seconds,
               operation_name=f"node_{node_id}"
           )
       except TimeoutError as e:
           self.logger.error(
               "node_timeout",
               node_id=node_id,
               timeout_seconds=timeout_seconds
           )
           raise
   ```

4. **Add Risk Limit Checks**
   ```python
   async def check_trade_risk(self, trade: Dict):
       # Check daily loss limit
       daily_pnl = await self.state.get("daily_pnl") or 0.0

       await self.infra.emergency.check_risk_limit(
           "daily_loss",
           daily_pnl,
           self.infra.config.emergency.daily_loss_limit,
           auto_halt=True
       )
   ```

**Deliverable:** Resilient workflow executor with retry, circuit breakers, and timeout

**Tests:**
- Circuit breakers protect against API failures
- Retries work with exponential backoff
- Timeouts prevent hanging nodes
- Risk limits trigger emergency halt

---

### Day 4: Testing & Examples

**Goal:** Comprehensive testing and example workflows

**Tasks:**

1. **Create Integration Tests**
   ```python
   # tests/integration/test_workflow_infrastructure.py

   async def test_workflow_execution_with_events():
       """Test that workflow executor emits events"""
       infra = await create_infrastructure("memory")
       executor = WorkflowExecutor(infra)

       events_received = []
       async def capture_event(event):
           events_received.append(event)

       await infra.events.subscribe("workflow_events", capture_event)

       # Execute simple workflow
       workflow = {
           "nodes": {
               "node1": {"type": "constant", "value": 42}
           }
       }

       await executor.execute_workflow("test_workflow", workflow)

       # Verify events
       assert len(events_received) >= 2  # started + completed
       assert events_received[0]['type'] == 'node_started'
       assert events_received[-1]['type'] == 'node_completed'
   ```

2. **Create Example: Real-time Trading Workflow**
   ```python
   # examples/realtime_trading_workflow.py

   async def main():
       # Initialize infrastructure
       infra = await create_infrastructure("development")

       # Create workflow executor
       executor = WorkflowExecutor(infra)

       # Subscribe to events
       async def log_event(event):
           print(f"Event: {event['type']} - {event.get('node_id')}")

       await infra.events.subscribe("workflow_events", log_event)

       # Execute trading workflow
       workflow = load_workflow("trading_arb_btc.json")
       await executor.execute_workflow("arb_btc_001", workflow)
   ```

3. **Create Example: Emergency Halt Scenario**
   ```python
   # examples/emergency_halt_demo.py

   async def simulate_loss_limit_exceeded():
       infra = await create_infrastructure("development")
       executor = WorkflowExecutor(infra)

       # Subscribe to emergency events
       async def on_emergency(event):
           print(f"EMERGENCY: {event.reason}")

       await infra.emergency.subscribe(on_emergency)

       # Simulate daily loss
       await infra.state.set("daily_pnl", -550.0)

       # Try to execute trade (should halt)
       try:
           await executor.execute_workflow("trade", trade_workflow)
       except EmergencyHalted as e:
           print(f"Trading halted: {e}")
   ```

4. **Performance Testing**
   - Benchmark workflow execution with infrastructure
   - Measure event emission overhead
   - Test with multiple concurrent workflows

**Deliverable:** Complete test suite and working examples

**Tests:**
- Integration tests for all infrastructure components
- Performance benchmarks
- Emergency halt scenarios
- WebSocket event flow

---

### Day 5: Documentation & Polish

**Goal:** Complete documentation and prepare for UI development

**Tasks:**

1. **Create Integration Guide**
   ```markdown
   # INFRASTRUCTURE_INTEGRATION.md

   ## How to Use Infrastructure in Workflows

   ### Basic Usage

   ### Event System

   ### Emergency Controls

   ### Configuration
   ```

2. **Update Existing Docs**
   - Add infrastructure section to `DASHBOARD_ARCHITECTURE.md`
   - Update `INTEGRATION_GUIDE.md` with new patterns
   - Add WebSocket protocol to `PROJECT_CONTEXT.md`

3. **Create Migration Guide**
   ```markdown
   # MIGRATION_TO_INFRASTRUCTURE.md

   ## Migrating Existing Workflows

   1. Update workflow executor initialization
   2. Add event emission
   3. Add emergency checks
   4. Add resilience patterns
   ```

4. **Polish & Cleanup**
   - Ensure all code has docstrings
   - Run linters/formatters
   - Update type hints
   - Fix any deprecation warnings

5. **Create Week 3 Summary**
   - Document all changes
   - List benefits for UI development
   - Identify any issues for Week 4

**Deliverable:** Complete documentation for infrastructure integration

---

## Event Schema

### Node Execution Events

**node_started**
```typescript
{
  type: 'node_started',
  execution_id: 'exec_abc123',
  workflow_id: 'arb_btc_001',
  node_id: 'price_binance',
  timestamp: '2024-01-24T10:15:23.456Z'
}
```

**node_completed**
```typescript
{
  type: 'node_completed',
  execution_id: 'exec_abc123',
  workflow_id: 'arb_btc_001',
  node_id: 'price_binance',
  timestamp: '2024-01-24T10:15:23.501Z',
  duration_ms: 45,
  status: 'success',
  outputs: {
    price: 50234.56,
    volume: 1234.56
  }
}
```

**node_failed**
```typescript
{
  type: 'node_failed',
  execution_id: 'exec_abc123',
  workflow_id: 'arb_btc_001',
  node_id: 'price_binance',
  timestamp: '2024-01-24T10:15:23.501Z',
  error: 'Connection timeout',
  error_type: 'TimeoutError'
}
```

### Emergency Events

**emergency_state_changed**
```typescript
{
  type: 'emergency_state_changed',
  controller_id: 'bot_001',
  previous_state: 'normal',
  new_state: 'halt',
  reason: 'Daily loss limit exceeded',
  timestamp: '2024-01-24T10:15:23.456Z'
}
```

---

## Benefits for Week 4+ (UI Development)

### Real-Time Updates
- Dashboard receives live node execution updates
- No polling required
- Instant notification of failures

### Correlation ID Tracking
- Track single execution across all logs
- Debug issues by execution ID
- Filter events by workflow/bot/strategy

### Emergency Controls
- UI can trigger emergency halt
- Display current emergency state
- Show risk limit utilization

### Resilience
- Workflow doesn't crash on API failures
- Automatic retries reduce false failures
- Circuit breakers prevent cascading failures

### State Persistence
- Resume workflows after restart
- Track historical executions
- Restore emergency state on startup

---

## Migration Checklist

- [ ] Day 1: Workflow executor enhanced
- [ ] Day 2: WebSocket server implemented
- [ ] Day 3: Resilience integrated
- [ ] Day 4: Tests and examples complete
- [ ] Day 5: Documentation complete

**Success Criteria:**
- Workflow executor emits events for every node execution
- WebSocket server forwards events to connected clients
- Circuit breakers and retries protect against failures
- Emergency halt stops trading when limits exceeded
- Complete test coverage (integration tests)
- Working examples demonstrate all features

---

## Next: Week 4 - Dashboard UI Components

With infrastructure integrated, Week 4 can focus on building React components that consume the real-time events:

- Real-time node execution visualization
- Bot metrics dashboard
- Strategy performance charts
- Emergency control panel
- Execution history viewer

All powered by the infrastructure built in Weeks 2-3!
