"""
Ecommerce Domain Adapter

Demonstrates how the generic abstraction extends to product arbitrage and dropshipping.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..asset import Asset, AssetType, AssetMetadata, AssetValuation, AssetState
from ..venue import (
    Venue, VenueType, VenueCapabilities, VenueStatus, VenueCredentials,
    ActionType, ActionRequest, ActionResult, AssetPosition
)


class ProductSKUAdapter(Asset):
    """
    Asset adapter for physical/digital products.

    Treats products as assets where:
    - Price = market selling price
    - Quantity = units to buy/sell
    - Trading = arbitrage between suppliers and marketplaces
    """

    def __init__(
        self,
        sku: str,
        product_name: str,
        category: str,
        supplier_cost: float,
        supplier_info: Dict[str, Any]
    ):
        asset_id = f"sku:{sku}"
        metadata = AssetMetadata(
            display_name=product_name,
            description=f"{category} product",
            tags=["ecommerce", category],
            custom_fields={
                "sku": sku,
                "category": category,
                "supplier": supplier_info.get("name"),
                "supplier_cost": supplier_cost,
                "supplier_url": supplier_info.get("url"),
                "weight_kg": supplier_info.get("weight"),
                "dimensions_cm": supplier_info.get("dimensions")
            },
            min_unit=1.0  # Minimum 1 unit
        )

        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.PRODUCT_SKU,
            symbol=sku,
            metadata=metadata
        )

        self.sku = sku
        self.product_name = product_name
        self.category = category
        self.supplier_cost = supplier_cost
        self.supplier_info = supplier_info

    async def fetch_current_valuation(self) -> AssetValuation:
        """
        Fetch current market price and demand indicators.

        Valuation factors:
        - Market price on Amazon, eBay, Walmart
        - Sales rank (demand indicator)
        - Competition level
        - Fees and shipping costs
        - Profit margin potential
        """
        # Placeholder: In reality, scrape/fetch from Keepa, SellerAssistant, etc.
        # Example: GET https://api.keepa.com/product?key=X&domain=1&asin=Y

        # Mock data for demonstration
        market_price = 29.99
        amazon_fees = 4.50  # 15% referral fee
        shipping_cost = 3.25
        sales_rank = 15234  # Lower = better

        # Calculate net profit
        net_profit = market_price - self.supplier_cost - amazon_fees - shipping_cost
        roi = (net_profit / self.supplier_cost) * 100 if self.supplier_cost > 0 else 0

        valuation = AssetValuation(
            current_value=market_price,
            currency="USD",
            timestamp=datetime.utcnow(),
            # Quality score based on reviews, return rate, defect rate
            quality_score=82.0,
            # Demand score based on sales rank and velocity
            demand_score=self._calculate_demand_score(sales_rank),
            custom_metrics={
                "market_price": market_price,
                "supplier_cost": self.supplier_cost,
                "amazon_fees": amazon_fees,
                "shipping_cost": shipping_cost,
                "net_profit": net_profit,
                "roi_pct": roi,
                "sales_rank": sales_rank,
                "monthly_sales_estimate": self._estimate_monthly_sales(sales_rank),
                "competition_level": "medium",
                "in_stock": True,
                "has_ip_risk": False,
                "hazmat": False
            }
        )

        self._valuation = valuation
        return valuation

    def _calculate_demand_score(self, sales_rank: int) -> float:
        """Convert sales rank to demand score (0-100)"""
        # Lower rank = higher demand
        # This is simplified - real calculation would be category-specific
        if sales_rank < 1000:
            return 95.0
        elif sales_rank < 10000:
            return 75.0
        elif sales_rank < 100000:
            return 50.0
        elif sales_rank < 500000:
            return 25.0
        else:
            return 10.0

    def _estimate_monthly_sales(self, sales_rank: int) -> int:
        """Estimate monthly sales from rank"""
        # Simplified estimation - real tools use historical data
        if sales_rank < 1000:
            return 1000
        elif sales_rank < 10000:
            return 200
        elif sales_rank < 100000:
            return 50
        elif sales_rank < 500000:
            return 10
        else:
            return 2

    async def fetch_state(self) -> AssetState:
        """
        Check product availability and restrictions.

        States:
        - ACTIVE: Available to sell
        - SUSPENDED: IP complaint, policy violation
        - RESTRICTED: Gated category, requires approval
        - DELISTED: No longer available from supplier
        """
        # Placeholder: Check supplier stock and marketplace restrictions
        self._state = AssetState.ACTIVE
        return self._state

    def calculate_value(self, quantity: float) -> float:
        """Calculate total potential profit"""
        if not self._valuation:
            raise ValueError("No valuation available")

        # Return profit potential (not revenue)
        net_profit_per_unit = self._valuation.custom_metrics.get("net_profit", 0)
        return quantity * net_profit_per_unit

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        """Validate order quantity"""
        if not float(quantity).is_integer():
            return False, "Quantity must be whole number"

        if quantity < 1:
            return False, "Minimum 1 unit"

        # Check supplier stock availability (would fetch in real implementation)
        max_available = 1000  # Placeholder
        if quantity > max_available:
            return False, f"Only {max_available} units available"

        return True, None


class EcommerceMarketplaceAdapter(Venue):
    """
    Venue adapter for ecommerce marketplaces (Amazon, eBay, Shopify, etc.)

    Actions:
    - CREATE_LISTING: List product for sale
    - UPDATE_LISTING: Update price, quantity, description
    - DELETE_LISTING: Remove listing
    - REBALANCE: Adjust inventory allocation across warehouses/FBA
    """

    def __init__(
        self,
        marketplace_name: str,
        seller_id: str,
        api_credentials: Dict[str, str]
    ):
        venue_id = f"ecommerce:{marketplace_name}:{seller_id}"
        credentials = VenueCredentials(
            credential_type="api_key",
            api_key=api_credentials.get("api_key"),
            api_secret=api_credentials.get("api_secret"),
            environment="production"
        )

        capabilities = VenueCapabilities(
            supported_actions={
                ActionType.CREATE_LISTING,
                ActionType.UPDATE_LISTING,
                ActionType.DELETE_LISTING,
                ActionType.REBALANCE,
                ActionType.QUERY
            },
            supported_asset_types={
                AssetType.PRODUCT_SKU
            },
            # Marketplace fees (e.g., Amazon 15% referral fee)
            taker_fee=0.15
        )

        super().__init__(
            venue_id=venue_id,
            venue_type=VenueType.ECOMMERCE_MARKETPLACE,
            name=marketplace_name,
            capabilities=capabilities,
            credentials=credentials
        )

        self.marketplace_name = marketplace_name
        self.seller_id = seller_id
        self._product_assets: Dict[str, ProductSKUAdapter] = {}

    async def connect(self) -> bool:
        """Connect to marketplace API"""
        # Placeholder: Initialize API client
        # Example: self.api_client = AmazonSPAPI(credentials=...)

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
        """List all products in inventory"""
        # Placeholder: GET /inventory from marketplace API

        # Mock data
        mock_products = [
            {
                "sku": "SKU-001-BLU",
                "name": "Bluetooth Headphones - Blue",
                "category": "Electronics",
                "supplier_cost": 15.50,
                "supplier_info": {"name": "AliExpress Supplier A", "weight": 0.3}
            },
            {
                "sku": "SKU-002-RED",
                "name": "Yoga Mat - Red",
                "category": "Sports",
                "supplier_cost": 8.25,
                "supplier_info": {"name": "Alibaba Supplier B", "weight": 1.2}
            }
        ]

        assets = []
        for product in mock_products:
            asset = ProductSKUAdapter(
                sku=product["sku"],
                product_name=product["name"],
                category=product["category"],
                supplier_cost=product["supplier_cost"],
                supplier_info=product.get("supplier_info", {})
            )
            assets.append(asset)
            self._product_assets[product["sku"]] = asset

        return assets

    async def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get product by SKU"""
        if symbol in self._product_assets:
            return self._product_assets[symbol]

        # Try to fetch from API
        # Placeholder: GET /products/{sku}
        return None

    async def get_positions(self) -> List[AssetPosition]:
        """Get current inventory positions"""
        positions = []

        for sku, asset in self._product_assets.items():
            # Fetch inventory levels
            # Placeholder: GET /inventory/{sku}/quantity

            position = AssetPosition(
                asset_id=asset.asset_id,
                quantity=50.0,  # Units in stock
                available=45.0,  # Available to sell
                reserved=5.0,    # Reserved for pending orders
                current_price=29.99,
                current_value=1499.50,  # 50 units * $29.99
                metadata={
                    "status": "active",
                    "listing_price": 29.99,
                    "units_sold_30d": 23,
                    "revenue_30d": 689.77,
                    "profit_30d": 327.25,
                    "sales_rank": 15234,
                    "fulfillment_method": "FBA"  # Fulfilled by Amazon
                }
            )
            positions.append(position)

        return positions

    async def get_position(self, asset: Asset) -> Optional[AssetPosition]:
        """Get position for specific product"""
        positions = await self.get_positions()
        for pos in positions:
            if pos.asset_id == asset.asset_id:
                return pos
        return None

    async def execute_action(self, request: ActionRequest) -> ActionResult:
        """Execute marketplace action"""
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
            if request.action_type == ActionType.CREATE_LISTING:
                return await self._create_listing(request)
            elif request.action_type == ActionType.UPDATE_LISTING:
                return await self._update_listing(request)
            elif request.action_type == ActionType.DELETE_LISTING:
                return await self._delete_listing(request)
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

    async def _create_listing(self, request: ActionRequest) -> ActionResult:
        """Create product listing"""
        # Placeholder: POST /listings with product details
        # Example: Amazon SP-API - create listing with ASIN/SKU

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"listing_{request.asset.asset_id}",
            status="active",
            executed_quantity=request.quantity,
            executed_price=request.price,
            completed_at=completed_at,
            metadata={
                "listing_url": f"https://amazon.com/dp/EXAMPLE",
                "price": request.price,
                "quantity": request.quantity,
                "fulfillment": "FBA"
            }
        )

    async def _update_listing(self, request: ActionRequest) -> ActionResult:
        """Update listing price or quantity"""
        # Placeholder: PATCH /listings/{sku}

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"update_{request.asset.asset_id}",
            status="updated",
            executed_price=request.price,
            completed_at=completed_at,
            metadata={
                "new_price": request.price,
                "old_price": request.metadata.get("old_price"),
                "new_quantity": request.quantity
            }
        )

    async def _delete_listing(self, request: ActionRequest) -> ActionResult:
        """Remove product listing"""
        # Placeholder: DELETE /listings/{sku}

        completed_at = datetime.utcnow()

        return ActionResult(
            request=request,
            success=True,
            venue_transaction_id=f"delete_{request.asset.asset_id}",
            status="deleted",
            completed_at=completed_at
        )

    async def query_action_status(self, transaction_id: str) -> ActionResult:
        """Query listing status"""
        # Placeholder: GET /listings/{sku}/status

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
                "listing_price": 29.99,
                "quantity_available": 45,
                "units_sold_7d": 8,
                "revenue_7d": 239.92,
                "sales_rank": 15234
            }
        )


# Example strategy for product arbitrage
class ProductArbitrageStrategy:
    """
    Example strategy: Find products where market price > supplier cost + fees + margin,
    create listings for profitable products.
    """

    def __init__(
        self,
        products: List[ProductSKUAdapter],
        marketplace: EcommerceMarketplaceAdapter,
        min_roi_pct: float = 30.0,
        min_monthly_sales: int = 20
    ):
        self.products = products
        self.marketplace = marketplace
        self.min_roi_pct = min_roi_pct
        self.min_monthly_sales = min_monthly_sales

    async def find_opportunities(self) -> List[Dict[str, Any]]:
        """Find profitable products to list"""
        opportunities = []

        for product in self.products:
            # Fetch current market data
            valuation = await product.fetch_current_valuation()

            roi = valuation.custom_metrics.get("roi_pct", 0)
            monthly_sales = valuation.custom_metrics.get("monthly_sales_estimate", 0)
            net_profit = valuation.custom_metrics.get("net_profit", 0)

            # Check if profitable and has demand
            if roi >= self.min_roi_pct and monthly_sales >= self.min_monthly_sales:
                opportunities.append({
                    "product": product,
                    "market_price": valuation.current_value,
                    "roi": roi,
                    "net_profit": net_profit,
                    "monthly_sales": monthly_sales,
                    "suggested_quantity": min(monthly_sales * 2, 100)  # 2 months supply, max 100
                })

        # Sort by ROI
        opportunities.sort(key=lambda x: x["roi"], reverse=True)

        return opportunities

    async def execute_top_opportunity(self):
        """List the most profitable product"""
        opportunities = await self.find_opportunities()

        if not opportunities:
            return None

        # Take top opportunity
        opp = opportunities[0]

        # Create listing
        request = ActionRequest(
            action_type=ActionType.CREATE_LISTING,
            asset=opp["product"],
            quantity=opp["suggested_quantity"],
            price=opp["market_price"],
            metadata={
                "fulfillment": "FBA",
                "condition": "new",
                "expected_roi": opp["roi"],
                "expected_profit": opp["net_profit"] * opp["suggested_quantity"]
            }
        )

        result = await self.marketplace.execute_action(request)
        return result
