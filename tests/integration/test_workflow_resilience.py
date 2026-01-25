"""
Integration Tests for Workflow Resilience Patterns

Tests the integration of resilience patterns in the enhanced workflow executor:
- Circuit breakers for external API calls
- Retry logic with exponential backoff
- Timeout handling for node execution
- Risk limit checks before trade execution
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.workflow.enhanced_executor import EnhancedWorkflowExecutor
from src.infrastructure.factory import Infrastructure
from src.infrastructure.emergency import EmergencyHalted, RiskLimitExceeded
from src.infrastructure.resilience import CircuitBreakerOpen


class TestWorkflowResilience:
    """Test suite for workflow resilience patterns"""

    @pytest.fixture
    async def infra(self):
        """Create test infrastructure"""
        infra = await Infrastructure.create("memory")
        yield infra
        await infra.cleanup()

    @pytest.fixture
    def simple_workflow(self):
        """Simple workflow for testing"""
        return {
            "blocks": [
                {
                    "id": "node1",
                    "name": "Test Node",
                    "category": "providers",
                    "type": "api_call",
                    "config": {},
                    "inputs": {},
                    "outputs": ["result"]
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_circuit_breaker_protects_against_failures(self, infra, simple_workflow):
        """Test that circuit breaker protects against repeated API failures"""
        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
            infra=infra,
            workflow_id="test_circuit_breaker",
            bot_id="bot_test",
            strategy_id="strategy_test"
        )

        await executor.initialize()

        # Mock the base executor's node execution to fail
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
            # First few calls should retry
            with pytest.raises(ConnectionError):
                await executor.execute()

            # Circuit breaker should open after threshold failures
            assert executor.api_breaker.state.name in ["OPEN", "HALF_OPEN"]

            # Get breaker stats
            stats = executor.api_breaker.get_stats()
            assert stats["failure_count"] >= infra.config.resilience.circuit_failure_threshold

    @pytest.mark.asyncio
    async def test_retry_logic_with_transient_failures(self, infra, simple_workflow):
        """Test that retry logic handles transient failures"""
        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
            infra=infra,
            workflow_id="test_retry",
            bot_id="bot_test",
            strategy_id="strategy_test"
        )

        await executor.initialize()

        # Mock API that fails twice then succeeds
        call_count = 0
        async def flaky_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient failure")
            return {"status": "success", "data": 42}

        with patch.object(
            executor.__class__.__bases__[0],
            '_execute_provider_node',
            side_effect=flaky_api_call
        ):
            result = await executor.execute()

            # Should succeed after retries
            assert result["status"] in ["completed", "completed_with_errors"]
            assert call_count == 3  # Failed twice, succeeded on third

    @pytest.mark.asyncio
    async def test_timeout_handling_prevents_hanging(self, infra):
        """Test that timeout handling prevents nodes from hanging"""
        workflow = {
            "blocks": [
                {
                    "id": "slow_node",
                    "name": "Slow Node",
                    "category": "providers",
                    "type": "slow_api",
                    "config": {},
                    "inputs": {},
                    "outputs": ["result"],
                    "timeout": 1.0  # 1 second timeout
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

        # Mock slow API call
        async def slow_api_call(*args, **kwargs):
            await asyncio.sleep(5)  # Sleep longer than timeout
            return {"data": "too slow"}

        with patch.object(
            executor.__class__.__bases__[0],
            '_execute_provider_node',
            side_effect=slow_api_call
        ):
            with pytest.raises(TimeoutError):
                await executor.execute()

    @pytest.mark.asyncio
    async def test_emergency_halt_stops_execution(self, infra, simple_workflow):
        """Test that emergency halt stops workflow execution"""
        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
            infra=infra,
            workflow_id="test_emergency",
            bot_id="bot_test",
            strategy_id="strategy_test"
        )

        await executor.initialize()

        # Trigger emergency halt
        await infra.emergency.halt("Manual emergency halt for testing")

        # Execution should raise EmergencyHalted
        with pytest.raises(EmergencyHalted) as exc_info:
            await executor.execute()

        assert exc_info.value.state.value == "halt"
        assert "Manual emergency halt" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_risk_limit_triggers_emergency_halt(self, infra, simple_workflow):
        """Test that exceeding risk limits triggers emergency halt"""
        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
            infra=infra,
            workflow_id="test_risk_limit",
            bot_id="bot_test",
            strategy_id="strategy_test"
        )

        await executor.initialize()

        # Set daily loss to exceed limit
        daily_loss_limit = -500.0
        current_daily_pnl = -550.0

        # Check risk limit (should auto-halt)
        with pytest.raises(RiskLimitExceeded) as exc_info:
            await infra.emergency.check_risk_limit(
                "daily_loss",
                current_daily_pnl,
                daily_loss_limit,
                auto_halt=True
            )

        # Verify limit exceeded
        assert exc_info.value.limit_type == "daily_loss"
        assert exc_info.value.current == current_daily_pnl
        assert exc_info.value.limit == daily_loss_limit

        # Verify emergency controller is halted
        assert infra.emergency.is_halted

    @pytest.mark.asyncio
    async def test_workflow_emits_events_during_execution(self, infra, simple_workflow):
        """Test that workflow executor emits events to event bus"""
        events_received = []

        async def capture_event(event):
            events_received.append(event)

        # Subscribe to workflow events
        await infra.events.subscribe("workflow_events", capture_event)

        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
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

            # Wait for events to be processed
            await asyncio.sleep(0.1)

            # Verify events were emitted
            assert len(events_received) >= 3  # execution_started, node_started, node_completed, execution_completed

            # Check event types
            event_types = [e["type"] for e in events_received]
            assert "execution_started" in event_types
            assert "node_started" in event_types
            assert "node_completed" in event_types
            assert "execution_completed" in event_types

            # Verify execution_started event
            start_event = next(e for e in events_received if e["type"] == "execution_started")
            assert start_event["workflow_id"] == "test_events"
            assert start_event["bot_id"] == "bot_test"
            assert start_event["strategy_id"] == "strategy_test"
            assert "execution_id" in start_event

    @pytest.mark.asyncio
    async def test_correlation_id_tracking(self, infra, simple_workflow):
        """Test that correlation IDs are tracked throughout execution"""
        from src.infrastructure.logging import get_correlation_id

        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
            infra=infra,
            workflow_id="test_correlation",
            bot_id="bot_test",
            strategy_id="strategy_test"
        )

        await executor.initialize()

        # Mock successful node execution
        async def check_correlation(*args, **kwargs):
            # Correlation ID should be set during execution
            corr_id = get_correlation_id()
            assert corr_id is not None
            assert corr_id.startswith("exec_test_correlation_")
            return {"data": 42}

        with patch.object(
            executor.__class__.__bases__[0],
            '_execute_provider_node',
            side_effect=check_correlation
        ):
            result = await executor.execute()
            assert result["status"] in ["completed", "completed_with_errors"]

    @pytest.mark.asyncio
    async def test_state_persistence_during_execution(self, infra, simple_workflow):
        """Test that execution state is persisted to state store"""
        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
            infra=infra,
            workflow_id="test_persistence",
            bot_id="bot_test",
            strategy_id="strategy_test"
        )

        await executor.initialize()

        # Mock successful node execution
        async def successful_node(*args, **kwargs):
            return {"data": 42}

        with patch.object(
            executor.__class__.__bases__[0],
            '_execute_provider_node',
            side_effect=successful_node
        ):
            result = await executor.execute()

            # Verify execution state was persisted
            execution_id = executor.execution_id

            # Check execution status
            status = await infra.state.get(
                f"workflow:test_persistence:execution:{execution_id}:status"
            )
            assert status in ["completed", "completed_with_errors"]

            # Check latest execution
            latest = await infra.state.get(
                f"workflow:test_persistence:latest_execution"
            )
            assert latest == execution_id

            # Check execution result
            persisted_result = await infra.state.get(
                f"workflow:test_persistence:execution:{execution_id}:result"
            )
            assert persisted_result is not None
            assert persisted_result["status"] in ["completed", "completed_with_errors"]

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows(self, infra, simple_workflow):
        """Test that multiple workflows can execute concurrently"""
        executors = []

        for i in range(3):
            executor = EnhancedWorkflowExecutor(
                workflow=simple_workflow,
                infra=infra,
                workflow_id=f"test_concurrent_{i}",
                bot_id=f"bot_{i}",
                strategy_id="strategy_test"
            )
            await executor.initialize()
            executors.append(executor)

        # Mock successful node execution
        async def successful_node(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate some work
            return {"data": 42}

        # Execute all workflows concurrently
        with patch.object(
            executors[0].__class__.__bases__[0],
            '_execute_provider_node',
            side_effect=successful_node
        ):
            results = await asyncio.gather(
                *[executor.execute() for executor in executors],
                return_exceptions=True
            )

            # All should complete successfully
            for result in results:
                if isinstance(result, Exception):
                    raise result
                assert result["status"] in ["completed", "completed_with_errors"]

    @pytest.mark.asyncio
    async def test_node_failure_emits_failed_event(self, infra, simple_workflow):
        """Test that node failures emit node_failed events"""
        events_received = []

        async def capture_event(event):
            events_received.append(event)

        await infra.events.subscribe("workflow_events", capture_event)

        executor = EnhancedWorkflowExecutor(
            workflow=simple_workflow,
            infra=infra,
            workflow_id="test_node_failure",
            bot_id="bot_test",
            strategy_id="strategy_test"
        )

        await executor.initialize()

        # Mock failing node
        async def failing_node(*args, **kwargs):
            raise ValueError("Node execution failed")

        with patch.object(
            executor.__class__.__bases__[0],
            '_execute_provider_node',
            side_effect=failing_node
        ):
            # Execute should complete but with errors
            result = await executor.execute()

            # Wait for events
            await asyncio.sleep(0.1)

            # Check for node_failed event
            failed_events = [e for e in events_received if e["type"] == "node_failed"]
            assert len(failed_events) >= 1

            failed_event = failed_events[0]
            assert failed_event["node_id"] == "node1"
            assert "error" in failed_event
            assert failed_event["error_type"] == "ValueError"


class TestResilienceConfiguration:
    """Test resilience configuration and customization"""

    @pytest.mark.asyncio
    async def test_custom_retry_configuration(self):
        """Test that custom retry configuration is respected"""
        from src.infrastructure.config import InfrastructureConfig, ResilienceConfig

        config = InfrastructureConfig(
            resilience=ResilienceConfig(
                retry_max_attempts=5,
                retry_min_wait_seconds=0.1,
                retry_max_wait_seconds=2.0
            )
        )

        infra = await Infrastructure.create("memory", config=config)

        try:
            assert infra.config.resilience.retry_max_attempts == 5
            assert infra.config.resilience.retry_min_wait_seconds == 0.1
        finally:
            await infra.cleanup()

    @pytest.mark.asyncio
    async def test_custom_circuit_breaker_threshold(self):
        """Test that custom circuit breaker threshold is respected"""
        from src.infrastructure.config import InfrastructureConfig, ResilienceConfig

        config = InfrastructureConfig(
            resilience=ResilienceConfig(
                circuit_failure_threshold=10
            )
        )

        infra = await Infrastructure.create("memory", config=config)

        try:
            # Create circuit breaker with custom threshold
            breaker = infra.create_circuit_breaker("test_breaker", failure_threshold=10)

            stats = breaker.get_stats()
            assert stats["failure_threshold"] == 10
        finally:
            await infra.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
