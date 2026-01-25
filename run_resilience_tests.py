"""
Simple test runner for resilience integration tests
Bypasses pytest plugin system to avoid web3 conflicts
"""

import asyncio
import sys
from tests.integration.test_workflow_resilience import (
    TestWorkflowResilience,
    TestResilienceConfiguration
)


async def run_test(test_class, test_method_name):
    """Run a single test method"""
    test_instance = test_class()

    # Get fixtures
    infra = None
    simple_workflow = None

    try:
        if hasattr(test_instance, 'infra'):
            infra_gen = test_instance.infra()
            infra = await infra_gen.__anext__()

        if hasattr(test_instance, 'simple_workflow'):
            simple_workflow = test_instance.simple_workflow()

        # Get test method
        test_method = getattr(test_instance, test_method_name)

        # Call with appropriate arguments
        if simple_workflow and infra:
            await test_method(infra, simple_workflow)
        elif infra:
            await test_method(infra)
        else:
            await test_method()

        print(f"✅ {test_class.__name__}.{test_method_name} PASSED")
        return True

    except Exception as e:
        print(f"❌ {test_class.__name__}.{test_method_name} FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if infra:
            try:
                await infra_gen.aclose()
            except:
                pass


async def main():
    """Run all resilience tests"""
    print("=" * 70)
    print("Running Resilience Integration Tests")
    print("=" * 70)

    tests = [
        (TestWorkflowResilience, "test_workflow_emits_events_during_execution"),
        (TestWorkflowResilience, "test_correlation_id_tracking"),
        (TestWorkflowResilience, "test_state_persistence_during_execution"),
        (TestWorkflowResilience, "test_emergency_halt_stops_execution"),
        (TestWorkflowResilience, "test_risk_limit_triggers_emergency_halt"),
        (TestWorkflowResilience, "test_timeout_handling_prevents_hanging"),
        (TestWorkflowResilience, "test_retry_logic_with_transient_failures"),
        (TestWorkflowResilience, "test_circuit_breaker_protects_against_failures"),
        (TestWorkflowResilience, "test_node_failure_emits_failed_event"),
        (TestWorkflowResilience, "test_multiple_concurrent_workflows"),
        (TestResilienceConfiguration, "test_custom_retry_configuration"),
        (TestResilienceConfiguration, "test_custom_circuit_breaker_threshold"),
    ]

    passed = 0
    failed = 0

    for test_class, test_method in tests:
        print(f"\n{'─' * 70}")
        print(f"Running: {test_class.__name__}.{test_method}")
        print(f"{'─' * 70}")

        try:
            result = await run_test(test_class, test_method)
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test runner error: {e}")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'=' * 70}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
