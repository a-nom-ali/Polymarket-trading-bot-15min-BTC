"""
Manual Resilience Integration Tests

Tests the integration of resilience patterns without pytest
"""

import asyncio
import sys
from unittest.mock import AsyncMock, patch
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor
from src.infrastructure.factory import Infrastructure
from src.infrastructure.emergency import EmergencyHalted, RiskLimitExceeded


SIMPLE_WORKFLOW = {
    "blocks": [
        {
            "id": "node1",
            "name": "Test Node",
            "category": "providers",
            "type": "api_call",
            "properties": {},
            "config": {},
            "inputs": {},
            "outputs": ["result"]
        }
    ]
}


async def test_workflow_emits_events():
    """Test that workflow executor emits events to event bus"""
    print("\n🧪 Test: Workflow emits events during execution")

    infra = await Infrastructure.create("development")
    events_received = []

    async def capture_event(event):
        events_received.append(event)

    await infra.events.subscribe("workflow_events", capture_event)

    executor = EnhancedWorkflowExecutor(
        workflow=SIMPLE_WORKFLOW,
        infra=infra,
        workflow_id="test_events",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()

    # Mock successful node execution
    async def successful_node(*args, **kwargs):
        return {"status": "success", "data": 42}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=successful_node
    ):
        result = await executor.execute()
        await asyncio.sleep(0.2)  # Wait for events

        # Verify events
        assert len(events_received) >= 3, f"Expected >=3 events, got {len(events_received)}"

        event_types = [e["type"] for e in events_received]
        assert "execution_started" in event_types
        assert "node_started" in event_types
        assert "node_completed" in event_types

        print("   ✅ Events emitted correctly")

    # Infrastructure cleanup not needed for memory backend
    return True


async def test_emergency_halt():
    """Test that emergency halt stops workflow execution"""
    print("\n🧪 Test: Emergency halt stops execution")

    infra = await Infrastructure.create("development")

    executor = EnhancedWorkflowExecutor(
        workflow=SIMPLE_WORKFLOW,
        infra=infra,
        workflow_id="test_emergency",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()
    await infra.emergency.halt("Manual emergency halt for testing")

    try:
        await executor.execute()
        print("   ❌ Should have raised EmergencyHalted")
        # Infrastructure cleanup not needed for memory backend
        return False
    except EmergencyHalted as e:
        assert e.state.value == "halt"
        assert "Manual emergency halt" in str(e)
        print("   ✅ Emergency halt working correctly")
        # Infrastructure cleanup not needed for memory backend
        return True


async def test_risk_limit_check():
    """Test that exceeding risk limits triggers emergency halt"""
    print("\n🧪 Test: Risk limit check triggers halt")

    infra = await Infrastructure.create("development")

    executor = EnhancedWorkflowExecutor(
        workflow=SIMPLE_WORKFLOW,
        infra=infra,
        workflow_id="test_risk",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()

    daily_loss_limit = -500.0
    current_daily_pnl = -550.0

    try:
        await infra.emergency.check_risk_limit(
            "daily_loss",
            current_daily_pnl,
            daily_loss_limit,
            auto_halt=True
        )
        print("   ❌ Should have raised RiskLimitExceeded")
        # Infrastructure cleanup not needed for memory backend
        return False
    except RiskLimitExceeded as e:
        assert e.limit_type == "daily_loss"
        assert e.current == current_daily_pnl
        assert e.limit == daily_loss_limit
        assert infra.emergency.is_halted
        print("   ✅ Risk limit check working correctly")
        # Infrastructure cleanup not needed for memory backend
        return True


async def test_timeout_handling():
    """Test that timeout handling prevents nodes from hanging"""
    print("\n🧪 Test: Timeout handling prevents hanging")

    infra = await Infrastructure.create("development")

    workflow = {
        "blocks": [
            {
                "id": "slow_node",
                "name": "Slow Node",
                "category": "providers",
                "type": "slow_api",
                "properties": {},
                "config": {},
                "inputs": {},
                "outputs": ["result"],
                "timeout": 1.0
            }
        ]
    }

    executor = EnhancedWorkflowExecutor(
        workflow=workflow,
        infra=infra,
        workflow_id="test_timeout",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()

    async def slow_api_call(*args, **kwargs):
        await asyncio.sleep(10)  # Sleep much longer than 1s timeout
        return {"data": "too slow"}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=slow_api_call
    ):
        try:
            result = await executor.execute()
            # Timeout will cause node_failed, but workflow completes with errors
            if "errors" in result and len(result["errors"]) > 0:
                error_msg = result["errors"][0].get("error", "")
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    print("   ✅ Timeout handling working correctly (node failed with timeout)")
                    # Infrastructure cleanup not needed for memory backend
                    return True
            print(f"   ❌ Expected timeout error, got: {result}")
            # Infrastructure cleanup not needed for memory backend
            return False
        except (TimeoutError, asyncio.TimeoutError, Exception) as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                print("   ✅ Timeout handling working correctly")
                # Infrastructure cleanup not needed for memory backend
                return True
            print(f"   ❌ Unexpected error: {e}")
            # Infrastructure cleanup not needed for memory backend
            return False


async def test_correlation_id_tracking():
    """Test that correlation IDs are tracked throughout execution"""
    print("\n🧪 Test: Correlation ID tracking")

    from src.infrastructure.logging import get_correlation_id

    infra = await Infrastructure.create("development")

    executor = EnhancedWorkflowExecutor(
        workflow=SIMPLE_WORKFLOW,
        infra=infra,
        workflow_id="test_correlation",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()

    correlation_found = False

    async def check_correlation(*args, **kwargs):
        nonlocal correlation_found
        corr_id = get_correlation_id()
        if corr_id and corr_id.startswith("exec_test_correlation_"):
            correlation_found = True
        return {"data": 42}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=check_correlation
    ):
        result = await executor.execute()
        assert correlation_found, "Correlation ID not set during execution"
        print("   ✅ Correlation ID tracking working correctly")

    # Infrastructure cleanup not needed for memory backend
    return True


async def test_state_persistence():
    """Test that execution state is persisted to state store"""
    print("\n🧪 Test: State persistence during execution")

    infra = await Infrastructure.create("development")

    executor = EnhancedWorkflowExecutor(
        workflow=SIMPLE_WORKFLOW,
        infra=infra,
        workflow_id="test_persistence",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()

    async def successful_node(*args, **kwargs):
        return {"data": 42}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=successful_node
    ):
        result = await executor.execute()
        execution_id = executor.execution_id

        # Verify state persistence
        status = await infra.state.get(
            f"workflow:test_persistence:execution:{execution_id}:status"
        )
        assert status in ["completed", "completed_with_errors"]

        latest = await infra.state.get(
            f"workflow:test_persistence:latest_execution"
        )
        assert latest == execution_id

        print("   ✅ State persistence working correctly")

    # Infrastructure cleanup not needed for memory backend
    return True


async def test_circuit_breaker():
    """Test that circuit breaker protects against repeated failures"""
    print("\n🧪 Test: Circuit breaker protects against failures")

    infra = await Infrastructure.create("development")

    executor = EnhancedWorkflowExecutor(
        workflow=SIMPLE_WORKFLOW,
        infra=infra,
        workflow_id="test_circuit",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()

    failure_count = 0

    async def failing_api_call(*args, **kwargs):
        nonlocal failure_count
        failure_count += 1
        raise ConnectionError("API connection failed")

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=failing_api_call
    ):
        try:
            await executor.execute()
        except ConnectionError:
            pass  # Expected

        # Check circuit breaker state
        stats = executor.api_breaker.get_stats()
        assert stats["failure_count"] > 0
        print(f"   ✅ Circuit breaker tracked {stats['failure_count']} failures")

    # Infrastructure cleanup not needed for memory backend
    return True


async def test_retry_logic():
    """Test that retry logic handles transient failures"""
    print("\n🧪 Test: Retry logic with transient failures")

    infra = await Infrastructure.create("development")

    executor = EnhancedWorkflowExecutor(
        workflow=SIMPLE_WORKFLOW,
        infra=infra,
        workflow_id="test_retry",
        bot_id="bot_test",
        strategy_id="strategy_test"
    )

    await executor.initialize()

    call_count = 0

    async def flaky_api_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:  # Fail once, succeed on second attempt
            raise ConnectionError("Transient failure")
        return {"status": "success", "data": 42}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=flaky_api_call
    ):
        result = await executor.execute()
        assert result["status"] in ["completed", "completed_with_errors"]
        assert call_count == 2  # Development config uses max_attempts=2
        print(f"   ✅ Retry logic succeeded after {call_count} attempts")

    # Infrastructure cleanup not needed for memory backend
    return True


async def main():
    """Run all resilience tests"""
    print("=" * 70)
    print("Manual Resilience Integration Tests")
    print("=" * 70)

    tests = [
        test_workflow_emits_events,
        test_correlation_id_tracking,
        test_state_persistence,
        test_emergency_halt,
        test_risk_limit_check,
        test_timeout_handling,
        test_retry_logic,
        test_circuit_breaker,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'=' * 70}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
