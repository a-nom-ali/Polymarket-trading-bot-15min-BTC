"""
Advertising Domain Adapter

Demonstrates how the generic abstraction extends to ad inventory and budget optimization.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..asset import Asset, AssetType, AssetMetadata, AssetValuation, AssetState
from ..venue import (
    Venue, VenueType, VenueCapabilities, VenueStatus, VenueCredentials,
    ActionType, ActionRequest, ActionResult, AssetPosition
)


class AdInventoryAdapter(Asset):
    """
    Asset adapter for advertising inventory/campaigns.

    Treats ad campaigns as assets where:
    - Price = CPC (cost per click) or CPM (cost per thousand impressions)
    - Quantity = impressions or clicks to purchase
    - Trading = reallocating budget to high-ROI campaigns
    """

    def __init__(
        self,
        campaign_id: str,
        campaign_name: str,
        platform: str,
        targeting: Dict[str, Any]
    ):
        asset_id = f"ad:{platform}:{campaign_id}"
        metadata = AssetMetadata(
            display_name=campaign_name,
            description=f"{platform} ad campaign",
            tags=["advertising", platform, targeting.get("objective", "conversions")],
            custom_fields={
                "platform": platform,
                "targeting": targeting,
                "ad_format": targeting.get("ad_format", "unknown"),
                "objective": targeting.get("objective", "conversions")
            }
        )

        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.AD_INVENTORY,
            symbol=f"{platform}:{campaign_name}",
            metadata=metadata
        )

        self.campaign_id = campaign_id
        self.campaign_name = campaign_name
        self.platform = platform
        self.targeting = targeting

    async def fetch_current_valuation(self) -> AssetValuation:
        """
        Fetch current ad performance metrics.

        Valuation factors:
        - CPC/CPM (cost)
        - CTR (click-through rate)
        - Conversion rate
        - ROAS (return on ad spend)
        """
        # Placeholder: In reality, fetch from Meta Ads API, Google Ads API, etc.
        # Example: GET https://graph.facebook.com/v18.0/{campaign_id}/insights

        # Mock data for demonstration
        cpc = 0.75  # $0.75 per click
        ctr = 2.5   # 2.5% click-through rate
        conversion_rate = 5.0  # 5% of clicks convert
        roas = 4.2  # $4.20 revenue per $1 spent

        # "Current value" = CPC (the price to acquire one unit)
        valuation = AssetValuation(
            current_value=cpc,
            currency="USD",
            timestamp=datetime.utcnow(),
            # Quality score = combination of CTR, conversion rate, ad relevance
            quality_score=75.0,
            # Demand score = how saturated the auction is
            demand_score=60.0,
            custom_metrics={
                "cpc": cpc,
                "cpm": cpc * 10 * ctr,  # CPM approximation
                "ctr": ctr,
                "conversion_rate": conversion_rate,
                "roas": roas,
                "impressions_last_7d": 125000,
                "clicks_last_7d": 3125,
                "conversions_last_7d": 156,
                "cost_last_7d": 2343.75,
                "revenue_last_7d": 9843.75
            }
        )

        self._valuation = valuation
        return valuation

    async def fetch_state(self) -> AssetState:
        """
        Check campaign status.

        States:
        - ACTIVE: Campaign running
        - INACTIVE: Paused
        - SUSPENDED: Platform flagged (policy violation, payment issue)
        """
        # Placeholder: Check via API
        self._state = AssetState.ACTIVE
        return self._state

    def calculate_value(self, quantity: float) -> float:
        """Calculate total cost for clicks/impressions"""
        if not self._valuation:
            raise ValueError("No valuation available")
        # quantity = clicks, value = CPC
        return quantity * self._valuation.current_value

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        """Validate ad quantity (clicks or impressions)"""
        if quantity < 100:
            return False, "Minimum 100 clicks/impressions"

        return True, None


class AdPlatformAdapter(Venue):
    """
    Venue adapter for ad platforms (Google Ads, Meta Ads, TikTok Ads, etc.)

    Actions:
    - SET_BUDGET: Set daily/lifetime budget for campaign
    - ADJUST_BID: Adjust bid amount
    - ALLOCATE: Enable campaign
    - DEALLOCATE: Pause campaign
    """

    def __init__(
        self,
        platform_name: str,
        account_id: str,
        access_token: str
    ):
        venue_id = f"ads:{platform_name}:{account_id}"
        credentials = VenueCredentials(
            credential_type="oauth",
            access_token=access_token,
            environment="production"
        )

        capabilities = VenueCapabilities(
            supported_actions={
                ActionType.SET_BUDGET,
                ActionType.ADJUST_BID,
                ActionType.ALLOCATE,
                ActionType.DEALLOCATE,
                ActionType.QUERY
            },
            supported_asset_types={
                AssetType.AD_INVENTORY
            },
            provides_realtime_updates=False,
            # Platform fee is built into auction pricing
        )

        super().__init__(
            venue_id=venue_id,
            venue_type=VenueType.AD_PLATFORM,
            name=platform_name,
            capabilities=capabilities,
            credentials=credentials
        )

        self.platform_name = platform_name
        self.account_id = account_id
        self._campaign_assets: Dict[str, AdInventoryAdapter] = {}

    async def connect(self) -> bool:
        """Connect to ad platform API"""
        # Placeholder: Initialize API client
        # Example for Meta: self.api_client = FacebookAdsApi.init(access_token=...)

        self._connected = True
        self._status = VenueStatus.ONLINE
        return True

    async def disconnect(self) -> bool:
        """Disconnect from ad platform"""
        self._connected = False
        return True

    async def healthcheck(self) -> VenueStatus:
        """Check ad platform API health"""
        # Placeholder: ping platform API
        self._status = VenueStatus.ONLINE
        return self._status

    async def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Asset]:
        """List all campaigns in the ad account"""
        # Placeholder: GET /campaigns from platform API

        # Mock data
        mock_campaigns = [
            {
                "campaign_id": "camp_001",
                "name": "Brand Awareness Q1",
                "targeting": {"objective": "awareness", "ad_format": "video"}
            },
            {
                "campaign_id": "camp_002",
                "name": "Product Launch Conversion",
                "targeting": {"objective": "conversions", "ad_format": "carousel"}
            }
        ]

        assets = []
        for campaign in mock_campaigns:
            asset = AdInventoryAdapter(
                campaign_id=campaign["campaign_id"],
                campaign_name=campaign["name"],
                platform=self.platform_name,
                targeting=campaign.get("targeting", {})
            )
            assets.append(asset)
            self._campaign_assets[campaign["campaign_id"]] = asset

        return assets

    async def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get campaign by ID"""
        if symbol in self._campaign_assets:
            return self._campaign_assets[symbol]

        # Try to fetch from API
        # Placeholder: GET /campaigns/{campaign_id}
        return None

    async def get_positions(self) -> List[AssetPosition]:
        """Get current campaign allocations and performance"""
        positions = []

        for campaign_id, asset in self._campaign_assets.items():
            # Fetch performance metrics
            valuation = await asset.fetch_current_valuation()

            position = AssetPosition(
                asset_id=asset.asset_id,
                quantity=valuation.custom_metrics.get("clicks_last_7d", 0),
                current_value=valuation.custom_metrics.get("cost_last_7d", 0),
                metadata={
                    "status": "active",
                    "daily_budget": 500.0,
                    "lifetime_budget": 10000.0,
                    "spent_today": 425.30,
                    "spent_lifetime": 8543.20,
                    "roas": valuation.custom_metrics.get("roas", 0),
                    "conversions_today": 12
                }
            )
            positions.append(position)

        return positions

    async def get_position(self, asset: Asset) -> Optional[AssetPosition]:
        """Get position for specific campaign"""
        positions = await self.get_positions()
        for pos in positions:
            if pos.asset_id == asset.asset_id:
                return pos
        return None

    async def execute_action(self, request: ActionRequest) -> ActionResult:
        """Execute ad platform action"""
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
            if request.action_type == ActionType.SET_BUDGET:
                return await self._set_campaign_budget(request)
            elif request.action_type == ActionType.ADJUST_BID:
                return await self._adjust_campaign_bid(request)
            elif request.action_type == ActionType.ALLOCATE:
                return await self._enable_campaign(request)
            elif request.action_type == ActionType.DEALLOCATE:
                return await self._pause_campaign(request)
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

    async def _set_campaign_budget(self, request: ActionRequest) -> ActionResult:
        """Set campaign daily budget"""
        # Placeholder: PATCH /campaigns/{id} with new budget
        # Example: Meta API - update campaign.daily_budget

        budget_amount = request.metadata.get("daily_budget", request.quantity)

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"budget_{request.asset.asset_id}",
            status="updated",
            completed_at=completed_at,
            metadata={
                "new_daily_budget": budget_amount,
                "old_daily_budget": request.metadata.get("old_budget"),
                "budget_type": "daily"
            }
        )

    async def _adjust_campaign_bid(self, request: ActionRequest) -> ActionResult:
        """Adjust campaign bid amount"""
        # Placeholder: Update bid strategy
        # Example: Google Ads - update target_cpa or target_roas

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"bid_{request.asset.asset_id}",
            status="updated",
            executed_price=request.price,
            completed_at=completed_at,
            metadata={
                "new_bid": request.price,
                "old_bid": request.metadata.get("old_bid"),
                "bid_strategy": request.metadata.get("strategy", "manual_cpc")
            }
        )

    async def _enable_campaign(self, request: ActionRequest) -> ActionResult:
        """Enable/start campaign"""
        # Placeholder: PATCH /campaigns/{id} status=ACTIVE

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"enable_{request.asset.asset_id}",
            status="active",
            completed_at=completed_at
        )

    async def _pause_campaign(self, request: ActionRequest) -> ActionResult:
        """Pause campaign"""
        # Placeholder: PATCH /campaigns/{id} status=PAUSED

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"pause_{request.asset.asset_id}",
            status="paused",
            completed_at=completed_at
        )

    async def query_action_status(self, transaction_id: str) -> ActionResult:
        """Query campaign status"""
        # Placeholder: GET /campaigns/{id}

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
                "daily_budget": 500.0,
                "spent_today": 425.30,
                "impressions_today": 35000,
                "clicks_today": 875,
                "conversions_today": 44
            }
        )


# Example strategy for ad budget optimization
class AdBudgetOptimizer:
    """
    Example strategy: Reallocate budget to campaigns with highest ROAS,
    pause underperforming campaigns.
    """

    def __init__(
        self,
        campaigns: List[AdInventoryAdapter],
        platform: AdPlatformAdapter,
        total_budget: float,
        min_roas: float = 2.0
    ):
        self.campaigns = campaigns
        self.platform = platform
        self.total_budget = total_budget
        self.min_roas = min_roas

    async def optimize(self):
        """Optimize budget allocation across campaigns"""
        # Fetch performance for all campaigns
        campaign_performance = []

        for campaign in self.campaigns:
            valuation = await campaign.fetch_current_valuation()
            roas = valuation.custom_metrics.get("roas", 0)

            campaign_performance.append({
                "campaign": campaign,
                "roas": roas,
                "current_budget": 500.0  # Would fetch from position
            })

        # Sort by ROAS (best first)
        campaign_performance.sort(key=lambda x: x["roas"], reverse=True)

        # Allocate budget proportionally to ROAS
        total_roas = sum(c["roas"] for c in campaign_performance if c["roas"] >= self.min_roas)

        results = []

        for perf in campaign_performance:
            if perf["roas"] < self.min_roas:
                # Pause underperforming campaign
                request = ActionRequest(
                    action_type=ActionType.DEALLOCATE,
                    asset=perf["campaign"],
                    quantity=0
                )
                result = await self.platform.execute_action(request)
                results.append(result)
            else:
                # Allocate budget proportionally to ROAS
                budget_share = (perf["roas"] / total_roas) * self.total_budget

                request = ActionRequest(
                    action_type=ActionType.SET_BUDGET,
                    asset=perf["campaign"],
                    quantity=budget_share,
                    metadata={
                        "daily_budget": budget_share,
                        "old_budget": perf["current_budget"]
                    }
                )
                result = await self.platform.execute_action(request)
                results.append(result)

        return results
