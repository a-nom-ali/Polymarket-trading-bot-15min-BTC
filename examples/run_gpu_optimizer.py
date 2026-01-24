"""
Example: Running the GPU Capacity Optimizer

This script demonstrates how to use the GPU optimization strategy
to automatically manage GPU rentals on Vast.ai.

This is the FIRST production implementation of a non-trading strategy
using the generic abstraction layer.
"""

import asyncio
import logging
import os
from datetime import timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.integrations.vastai import VastAIMarketplace
from src.strategies.gpu_optimizer import GPUCapacityOptimizer, GPUConfig
from src.core.strategy import StrategyConfig
from src.core.risk import DefaultRiskManager, RiskConstraint, ConstraintType


async def main():
    """Run GPU capacity optimizer"""

    # ==================== Configuration ====================

    # Get Vast.ai API key from environment
    api_key = os.getenv("VAST_AI_API_KEY")
    if not api_key:
        print("❌ Error: VAST_AI_API_KEY environment variable not set")
        print("Get your API key from: https://console.vast.ai/account/")
        return

    # Define your GPUs
    gpus = [
        GPUConfig(
            gpu_id="gpu_001",
            gpu_model="RTX_4090",
            vram_gb=24,
            cuda_cores=16384,
            power_watts=450,
            power_cost_per_kwh=0.12,  # $/kWh (adjust for your location)
            maintenance_cost_per_hour=0.02  # Amortized maintenance costs
        ),
        GPUConfig(
            gpu_id="gpu_002",
            gpu_model="RTX_4090",
            vram_gb=24,
            cuda_cores=16384,
            power_watts=450,
            power_cost_per_kwh=0.12,
            maintenance_cost_per_hour=0.02
        ),
        # Add more GPUs as needed
    ]

    # ==================== Initialize Marketplace ====================

    print("🔗 Connecting to Vast.ai marketplace...")
    marketplace = VastAIMarketplace(
        api_key=api_key,
        owned_gpus=[{
            "gpu_id": gpu.gpu_id,
            "model": gpu.gpu_model,
            "specs": {
                "vram": f"{gpu.vram_gb}GB",
                "cuda_cores": gpu.cuda_cores,
                "power_watts": gpu.power_watts
            }
        } for gpu in gpus]
    )

    # ==================== Configure Risk Management ====================

    print("🛡️  Setting up risk management...")
    risk_manager = DefaultRiskManager(constraints=[
        RiskConstraint(
            constraint_type=ConstraintType.DAILY_LOSS,
            name="max_daily_operating_loss",
            limit=50.0,  # Max $50 loss per day
            enforce=True,
            time_window=timedelta(days=1)
        ),
        RiskConstraint(
            constraint_type=ConstraintType.FREQUENCY,
            name="listing_frequency",
            limit=20,  # Max 20 listing changes per hour
            enforce=True,
            time_window=timedelta(hours=1)
        )
    ])

    # ==================== Configure Strategy ====================

    print("⚙️  Configuring GPU optimizer...")
    strategy_config = StrategyConfig(
        scan_interval_ms=300000,  # 5 minutes
        min_expected_profit=0.10,  # $0.10/hour minimum profit
        min_roi=0.25,  # 25% profit margin minimum
        enable_auto_execution=True,
        dry_run_mode=False,  # Set to True for testing without real actions
        custom_params={
            "unlist_on_shutdown": True  # Unlist all GPUs when stopping
        }
    )

    # ==================== Initialize Strategy ====================

    print("🚀 Initializing GPU Capacity Optimizer...")
    optimizer = GPUCapacityOptimizer(
        gpu_configs=gpus,
        marketplace=marketplace,
        config=strategy_config,
        risk_manager=risk_manager
    )

    # Initialize
    if not await optimizer.initialize():
        print("❌ Failed to initialize optimizer")
        return

    print("\n" + "="*60)
    print("GPU CAPACITY OPTIMIZER - RUNNING")
    print("="*60)
    print(f"📊 Managing {len(gpus)} GPUs")
    print(f"⏱️  Scan interval: {strategy_config.scan_interval_ms / 1000} seconds")
    print(f"💰 Min profit: ${strategy_config.min_expected_profit}/hour")
    print(f"📈 Min ROI: {strategy_config.min_roi * 100}%")
    print(f"🧪 Dry run mode: {strategy_config.dry_run_mode}")
    print("="*60 + "\n")

    # ==================== Main Loop ====================

    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"\n🔄 Iteration {iteration} - {asyncio.get_event_loop().time()}")

            # Find opportunities
            opportunities = await optimizer.find_opportunities()

            if opportunities:
                print(f"✨ Found {len(opportunities)} opportunities:")

                for opp in opportunities:
                    action = opp.metadata.get("action_type", "unknown")
                    gpu_id = opp.metadata.get("gpu_id", "unknown")
                    profit = opp.expected_profit

                    print(f"  - {action.upper()} {gpu_id}: ${profit:.3f}/hr profit")

                    # Validate opportunity
                    if await optimizer.validate_opportunity(opp):
                        # Execute opportunity
                        result = await optimizer.execute_opportunity(opp)

                        if result.success:
                            print(f"    ✅ Success!")
                        else:
                            print(f"    ❌ Failed: {result.error_message}")
                    else:
                        print(f"    ⚠️  Skipped (validation failed)")

            else:
                print("  No opportunities found (GPUs in optimal state)")

            # Show statistics
            stats = optimizer.get_statistics()
            print(f"\n📊 Statistics:")
            print(f"  Total executions: {stats['total_executions']}")
            print(f"  Success rate: {stats['success_rate']:.1%}")
            print(f"  Total revenue: ${optimizer.total_rental_revenue:.2f}")
            print(f"  Hours rented: {optimizer.total_hours_rented:.1f}")

            # Wait for next iteration
            await asyncio.sleep(strategy_config.scan_interval_ms / 1000)

    except KeyboardInterrupt:
        print("\n\n⚠️  Received shutdown signal...")

    finally:
        # Graceful shutdown
        print("🛑 Shutting down optimizer...")
        await optimizer.shutdown()
        print("✅ Optimizer stopped cleanly")


if __name__ == "__main__":
    # Run the optimizer
    asyncio.run(main())
