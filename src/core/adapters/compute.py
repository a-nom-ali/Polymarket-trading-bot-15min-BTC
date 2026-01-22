"""
GPU/Compute Domain Adapter

Demonstrates how the generic abstraction extends to GPU/compute capacity trading.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..asset import Asset, AssetType, AssetMetadata, AssetValuation, AssetState
from ..venue import (
    Venue, VenueType, VenueCapabilities, VenueStatus, VenueCredentials,
    ActionType, ActionRequest, ActionResult, AssetPosition
)


class GPUAssetAdapter(Asset):
    """
    Asset adapter for GPU/compute capacity.

    Treats GPU time as a tradeable asset where:
    - Price = $/hour rental rate
    - Quantity = hours of compute
    - Trading = deciding when to rent out vs keep for own workloads
    """

    def __init__(
        self,
        gpu_id: str,
        gpu_model: str,
        specs: Dict[str, Any]
    ):
        asset_id = f"gpu:{gpu_id}"
        metadata = AssetMetadata(
            display_name=gpu_model,
            description=f"{specs.get('vram', 'Unknown')} VRAM, {specs.get('cuda_cores', 'Unknown')} CUDA cores",
            tags=["compute", "gpu"],
            custom_fields={
                "gpu_model": gpu_model,
                "vram_gb": specs.get("vram"),
                "cuda_cores": specs.get("cuda_cores"),
                "power_watts": specs.get("power_watts"),
                "location": specs.get("location")
            },
            min_unit=0.1,  # Minimum 0.1 hour (6 minutes) rental
        )

        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.COMPUTE_CAPACITY,
            symbol=gpu_model,
            metadata=metadata
        )

        self.gpu_id = gpu_id
        self.gpu_model = gpu_model
        self.specs = specs

    async def fetch_current_valuation(self) -> AssetValuation:
        """
        Fetch current rental rate from compute marketplace.

        In real implementation, this would query Vast.ai, RunPod, or similar APIs.
        """
        # Placeholder: In reality, fetch from marketplace API
        # Example: GET https://api.vast.ai/pricing?gpu_model=RTX4090

        # Mock data for demonstration
        current_rate = 0.50  # $0.50/hour for this GPU model

        valuation = AssetValuation(
            current_value=current_rate,
            currency="USD",
            timestamp=datetime.utcnow(),
            # Quality score could factor in: reliability, bandwidth, location
            quality_score=85.0,
            # Demand score based on market rental activity
            demand_score=70.0,
            custom_metrics={
                "market_avg_rate": 0.45,
                "your_power_cost_per_hour": 0.12,
                "net_profit_per_hour": 0.38,
                "utilization_pct": 60.0
            }
        )

        self._valuation = valuation
        return valuation

    async def fetch_state(self) -> AssetState:
        """
        Check if GPU is available for rental.

        States:
        - ACTIVE: Available and online
        - INACTIVE: Offline or maintenance
        - SUSPENDED: Temporarily unavailable (busy with own workload)
        """
        # Placeholder: In reality, check GPU status via API or local daemon
        self._state = AssetState.ACTIVE
        return self._state

    def calculate_value(self, quantity: float) -> float:
        """Calculate total rental value for hours of compute"""
        if not self._valuation:
            raise ValueError("No valuation available")
        # quantity = hours, value = $/hour
        return quantity * self._valuation.current_value

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        """Validate rental duration"""
        if quantity < self.metadata.min_unit:
            return False, f"Minimum rental {self.metadata.min_unit} hours"

        if quantity > 720:  # Max 30 days
            return False, "Maximum rental 720 hours (30 days)"

        return True, None


class ComputeMarketplaceAdapter(Venue):
    """
    Venue adapter for compute marketplaces (Vast.ai, RunPod, etc.)

    Actions:
    - ALLOCATE: Make GPU available for rent at specified price
    - DEALLOCATE: Remove GPU from marketplace
    - SET_PRICE: Adjust rental rate
    - SET_CAPACITY: Set max concurrent rentals
    """

    def __init__(
        self,
        marketplace_name: str,
        api_key: str,
        owned_gpus: List[Dict[str, Any]]
    ):
        venue_id = f"compute:{marketplace_name}"
        credentials = VenueCredentials(
            credential_type="api_key",
            api_key=api_key,
            environment="production"
        )

        capabilities = VenueCapabilities(
            supported_actions={
                ActionType.ALLOCATE,
                ActionType.DEALLOCATE,
                ActionType.SET_PRICE,
                ActionType.SET_CAPACITY,
                ActionType.QUERY
            },
            supported_asset_types={
                AssetType.COMPUTE_CAPACITY
            },
            provides_realtime_updates=True,
            # Marketplace fee (e.g., Vast.ai takes 10%)
            taker_fee=0.10
        )

        super().__init__(
            venue_id=venue_id,
            venue_type=VenueType.COMPUTE_MARKETPLACE,
            name=marketplace_name,
            capabilities=capabilities,
            credentials=credentials
        )

        self.marketplace_name = marketplace_name
        self.owned_gpus = owned_gpus
        self._gpu_assets: Dict[str, GPUAssetAdapter] = {}

    async def connect(self) -> bool:
        """Connect to compute marketplace API"""
        # Placeholder: Initialize API client
        # Example: self.api_client = VastAIClient(api_key=self.credentials.api_key)

        self._connected = True
        self._status = VenueStatus.ONLINE
        return True

    async def disconnect(self) -> bool:
        """Disconnect from marketplace"""
        self._connected = False
        return True

    async def healthcheck(self) -> VenueStatus:
        """Check marketplace API health"""
        # Placeholder: ping marketplace API
        self._status = VenueStatus.ONLINE
        return self._status

    async def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Asset]:
        """List all owned GPUs"""
        assets = []

        for gpu_config in self.owned_gpus:
            asset = GPUAssetAdapter(
                gpu_id=gpu_config["gpu_id"],
                gpu_model=gpu_config["model"],
                specs=gpu_config.get("specs", {})
            )
            assets.append(asset)
            self._gpu_assets[gpu_config["gpu_id"]] = asset

        return assets

    async def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get GPU by ID or model"""
        # Check if it's a GPU ID
        if symbol in self._gpu_assets:
            return self._gpu_assets[symbol]

        # Check if it's a model name
        for asset in self._gpu_assets.values():
            if asset.gpu_model == symbol:
                return asset

        return None

    async def get_positions(self) -> List[AssetPosition]:
        """Get current GPU allocation status"""
        positions = []

        for gpu_id, asset in self._gpu_assets.items():
            # Fetch current rental status
            # Placeholder: query marketplace for active rentals

            position = AssetPosition(
                asset_id=asset.asset_id,
                quantity=1.0,  # You own 1 GPU
                available=1.0,  # Available to rent
                reserved=0.0,   # Currently rented hours
                metadata={
                    "status": "available",
                    "current_rate": 0.50,
                    "hours_rented_today": 8.5,
                    "revenue_today": 4.25
                }
            )
            positions.append(position)

        return positions

    async def get_position(self, asset: Asset) -> Optional[AssetPosition]:
        """Get position for specific GPU"""
        positions = await self.get_positions()
        for pos in positions:
            if pos.asset_id == asset.asset_id:
                return pos
        return None

    async def execute_action(self, request: ActionRequest) -> ActionResult:
        """Execute compute marketplace action"""
        is_valid, error = self.validate_action_request(request)
        if not is_valid:
            return ActionResult(
                request=request,
                success=False,
                error_message=error,
                status="failed"
            )

        started_at = datetime.utcnow()

        try:
            if request.action_type == ActionType.ALLOCATE:
                return await self._allocate_gpu(request)
            elif request.action_type == ActionType.DEALLOCATE:
                return await self._deallocate_gpu(request)
            elif request.action_type == ActionType.SET_PRICE:
                return await self._set_gpu_price(request)
            else:
                return ActionResult(
                    request=request,
                    success=False,
                    error_message=f"Unsupported action: {request.action_type}",
                    status="failed"
                )

        except Exception as e:
            return ActionResult(
                request=request,
                success=False,
                error_message=str(e),
                status="failed",
                submitted_at=started_at
            )

    async def _allocate_gpu(self, request: ActionRequest) -> ActionResult:
        """Make GPU available on marketplace"""
        # Placeholder: Call marketplace API
        # Example: POST /api/v1/listings with GPU specs and price

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"listing_{request.asset.asset_id}",
            status="active",
            completed_at=completed_at,
            metadata={
                "listing_url": f"https://vast.ai/listing/{request.asset.asset_id}",
                "hourly_rate": request.price,
                "estimated_revenue_per_day": request.price * 24 if request.price else 0
            }
        )

    async def _deallocate_gpu(self, request: ActionRequest) -> ActionResult:
        """Remove GPU from marketplace"""
        # Placeholder: Call marketplace API
        # Example: DELETE /api/v1/listings/{gpu_id}

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"delisting_{request.asset.asset_id}",
            status="inactive",
            completed_at=completed_at
        )

    async def _set_gpu_price(self, request: ActionRequest) -> ActionResult:
        """Update GPU rental rate"""
        # Placeholder: Call marketplace API
        # Example: PATCH /api/v1/listings/{gpu_id} with new price

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"price_update_{request.asset.asset_id}",
            status="updated",
            executed_price=request.price,
            completed_at=completed_at,
            metadata={
                "new_rate": request.price,
                "old_rate": request.metadata.get("old_price")
            }
        )

    async def query_action_status(self, transaction_id: str) -> ActionResult:
        """Query status of a listing or rental"""
        # Placeholder: GET /api/v1/listings/{id}/status

        dummy_request = ActionRequest(
            action_type=ActionType.QUERY,
            asset=None,
            quantity=0
        )

        return ActionResult(
            request=dummy_request,
            success=True,
            venue_transaction_id=transaction_id,
            status="active",
            metadata={
                "current_rate": 0.50,
                "hours_rented_total": 120.5,
                "revenue_total": 60.25
            }
        )


# Example strategy for GPU capacity optimization
class GPUCapacityStrategy:
    """
    Example strategy: Rent out GPU when market rate > (power cost + desired margin),
    keep for own workloads when market rate is low.
    """

    def __init__(
        self,
        gpu_asset: GPUAssetAdapter,
        marketplace: ComputeMarketplaceAdapter,
        power_cost_per_hour: float = 0.12,
        min_profit_margin: float = 0.25
    ):
        self.gpu_asset = gpu_asset
        self.marketplace = marketplace
        self.power_cost_per_hour = power_cost_per_hour
        self.min_profit_margin = min_profit_margin

    async def should_rent_out(self) -> tuple[bool, Optional[float]]:
        """
        Decide whether to rent out GPU.

        Returns:
            (should_rent, suggested_price)
        """
        # Fetch current market rate
        valuation = await self.gpu_asset.fetch_current_valuation()
        market_rate = valuation.current_value

        # Calculate minimum acceptable rate
        min_rate = self.power_cost_per_hour * (1 + self.min_profit_margin)

        if market_rate >= min_rate:
            # Market rate is profitable - rent out
            # Set our price slightly below market to be competitive
            suggested_price = market_rate * 0.98
            return True, suggested_price
        else:
            # Market rate too low - keep for own use
            return False, None

    async def execute(self):
        """Execute GPU allocation decision"""
        should_rent, price = await self.should_rent_out()

        if should_rent:
            # Allocate GPU to marketplace
            request = ActionRequest(
                action_type=ActionType.ALLOCATE,
                asset=self.gpu_asset,
                quantity=1.0,  # Make available
                price=price
            )
            result = await self.marketplace.execute_action(request)
            return result
        else:
            # Deallocate if currently listed
            request = ActionRequest(
                action_type=ActionType.DEALLOCATE,
                asset=self.gpu_asset,
                quantity=1.0
            )
            result = await self.marketplace.execute_action(request)
            return result
