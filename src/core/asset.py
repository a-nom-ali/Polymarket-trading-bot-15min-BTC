"""
Generic Asset Abstraction Layer

This module defines the core abstraction for any tradeable/optimizable asset,
whether it's a financial instrument, GPU capacity, ad inventory, product SKU, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class AssetType(Enum):
    """Categories of assets the platform can handle"""
    FINANCIAL_SPOT = "financial_spot"              # Traditional spot trading (stocks, crypto, forex)
    FINANCIAL_DERIVATIVE = "financial_derivative"  # Futures, options, perpetuals
    FINANCIAL_BINARY = "financial_binary"          # Binary outcomes (Polymarket, Kalshi)
    COMPUTE_CAPACITY = "compute_capacity"          # GPU/CPU rental capacity
    AD_INVENTORY = "ad_inventory"                  # Ad impressions, clicks, conversions
    PRODUCT_SKU = "product_sku"                    # Physical/digital products for arbitrage
    CREDIT_YIELD = "credit_yield"                  # Lending/borrowing opportunities
    BANDWIDTH = "bandwidth"                        # Network capacity, CDN
    ENERGY = "energy"                              # Electricity, carbon credits
    CUSTOM = "custom"                              # User-defined asset types


class AssetState(Enum):
    """Current state of an asset"""
    ACTIVE = "active"           # Available for trading/optimization
    INACTIVE = "inactive"       # Temporarily unavailable
    DEPRECATED = "deprecated"   # Being phased out
    SUSPENDED = "suspended"     # Halted by venue
    DELISTED = "delisted"       # No longer available
    UNKNOWN = "unknown"         # State cannot be determined


@dataclass
class AssetMetadata:
    """Extended metadata for domain-specific asset information"""

    # Common fields across all asset types
    display_name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Domain-specific data (extensible)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    # Regulatory/compliance
    jurisdictions: List[str] = field(default_factory=list)  # Where asset is legal
    requires_kyc: bool = False

    # Technical specs (varies by asset type)
    min_unit: Optional[float] = None      # Minimum tradeable/allocatable unit
    max_unit: Optional[float] = None      # Maximum per transaction
    precision: Optional[int] = None        # Decimal places

    # Temporal properties
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # For time-limited assets

    # Links
    documentation_url: Optional[str] = None
    website_url: Optional[str] = None


@dataclass
class AssetValuation:
    """Current valuation/pricing of an asset"""

    # Core pricing
    current_value: float               # Current market price/value
    currency: str = "USD"              # Denomination currency
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Volatility indicators
    volatility_24h: Optional[float] = None      # 24h volatility percentage
    volume_24h: Optional[float] = None          # 24h trading volume

    # Derived metrics
    bid: Optional[float] = None                 # Best bid price
    ask: Optional[float] = None                 # Best ask price
    spread: Optional[float] = None              # Bid-ask spread
    mid_price: Optional[float] = None           # Mid-market price

    # Trend indicators
    change_24h: Optional[float] = None          # 24h price change %
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None

    # Quality metrics (for non-financial assets)
    quality_score: Optional[float] = None       # 0-100 quality rating
    demand_score: Optional[float] = None        # 0-100 demand indicator

    # Domain-specific valuations
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AssetPosition:
    """Current holdings/allocation of an asset"""

    asset_id: str
    quantity: float

    # Cost basis
    average_entry_price: Optional[float] = None
    total_cost: Optional[float] = None

    # Current value
    current_price: Optional[float] = None
    current_value: Optional[float] = None

    # P&L
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None

    # Availability
    available: float = 0.0          # Available for trading/allocation
    reserved: float = 0.0           # Locked in pending actions

    # Temporal
    opened_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Domain-specific
    metadata: Dict[str, Any] = field(default_factory=dict)


class Asset(ABC):
    """
    Abstract base class for any asset that can be traded, allocated, or optimized.

    This abstraction allows the same strategy/workflow engine to operate across
    financial markets, compute capacity, ad inventory, product arbitrage, etc.
    """

    def __init__(
        self,
        asset_id: str,
        asset_type: AssetType,
        symbol: str,
        metadata: AssetMetadata
    ):
        self.asset_id = asset_id
        self.asset_type = asset_type
        self.symbol = symbol
        self.metadata = metadata
        self._state = AssetState.UNKNOWN
        self._valuation: Optional[AssetValuation] = None

    @property
    def state(self) -> AssetState:
        """Current state of the asset"""
        return self._state

    @property
    def valuation(self) -> Optional[AssetValuation]:
        """Current valuation of the asset"""
        return self._valuation

    @abstractmethod
    async def fetch_current_valuation(self) -> AssetValuation:
        """
        Fetch the current valuation/price of this asset.

        Implementation varies by asset type:
        - Financial: market price, orderbook
        - GPU: current spot rate, demand
        - Ad inventory: CPM, CTR, ROAS
        - Product: buy cost, sell price, fees
        """
        pass

    @abstractmethod
    async def fetch_state(self) -> AssetState:
        """
        Fetch the current availability state of this asset.

        Returns whether the asset is tradeable, suspended, delisted, etc.
        """
        pass

    @abstractmethod
    def calculate_value(self, quantity: float) -> float:
        """
        Calculate the total value of a given quantity of this asset.

        Args:
            quantity: Amount of the asset

        Returns:
            Total value in the base currency
        """
        pass

    @abstractmethod
    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        """
        Validate if a quantity is valid for this asset.

        Args:
            quantity: Proposed quantity

        Returns:
            (is_valid, error_message)
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Serialize asset to dictionary"""
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type.value,
            "symbol": self.symbol,
            "state": self.state.value,
            "metadata": {
                "display_name": self.metadata.display_name,
                "description": self.metadata.description,
                "tags": self.metadata.tags,
                "custom_fields": self.metadata.custom_fields
            },
            "valuation": {
                "current_value": self._valuation.current_value if self._valuation else None,
                "currency": self._valuation.currency if self._valuation else None,
                "timestamp": self._valuation.timestamp.isoformat() if self._valuation else None
            } if self._valuation else None
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.symbol}, {self.asset_type.value})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} asset_id={self.asset_id} symbol={self.symbol}>"


# Domain-specific asset implementations

class FinancialAsset(Asset):
    """Financial instrument (spot, derivative, binary outcome)"""

    def __init__(
        self,
        asset_id: str,
        symbol: str,
        base_currency: str,
        quote_currency: str,
        asset_type: AssetType = AssetType.FINANCIAL_SPOT,
        metadata: Optional[AssetMetadata] = None
    ):
        if metadata is None:
            metadata = AssetMetadata(display_name=symbol)

        super().__init__(asset_id, asset_type, symbol, metadata)
        self.base_currency = base_currency
        self.quote_currency = quote_currency

    async def fetch_current_valuation(self) -> AssetValuation:
        # To be implemented by specific provider integration
        raise NotImplementedError("Must be implemented by provider-specific subclass")

    async def fetch_state(self) -> AssetState:
        # To be implemented by specific provider integration
        raise NotImplementedError("Must be implemented by provider-specific subclass")

    def calculate_value(self, quantity: float) -> float:
        if not self._valuation:
            raise ValueError("No valuation available")
        return quantity * self._valuation.current_value

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        if quantity <= 0:
            return False, "Quantity must be positive"

        if self.metadata.min_unit and quantity < self.metadata.min_unit:
            return False, f"Quantity below minimum unit {self.metadata.min_unit}"

        if self.metadata.max_unit and quantity > self.metadata.max_unit:
            return False, f"Quantity exceeds maximum unit {self.metadata.max_unit}"

        return True, None


class ComputeAsset(Asset):
    """GPU/CPU compute capacity"""

    def __init__(
        self,
        asset_id: str,
        symbol: str,  # e.g., "RTX4090", "A100-80GB"
        specs: Dict[str, Any],  # VRAM, CUDA cores, etc.
        metadata: Optional[AssetMetadata] = None
    ):
        if metadata is None:
            metadata = AssetMetadata(display_name=symbol)

        super().__init__(asset_id, AssetType.COMPUTE_CAPACITY, symbol, metadata)
        self.specs = specs

    async def fetch_current_valuation(self) -> AssetValuation:
        # Fetch current spot rate from compute marketplace
        raise NotImplementedError("Integrate with Vast.ai, RunPod, etc.")

    async def fetch_state(self) -> AssetState:
        # Check if capacity is available, rented, offline, etc.
        raise NotImplementedError()

    def calculate_value(self, quantity: float) -> float:
        """quantity = hours of compute time"""
        if not self._valuation:
            raise ValueError("No valuation available")
        return quantity * self._valuation.current_value  # $/hour

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        if quantity <= 0:
            return False, "Compute hours must be positive"
        return True, None


class AdInventoryAsset(Asset):
    """Ad impression/click inventory on a platform"""

    def __init__(
        self,
        asset_id: str,
        platform: str,  # "google", "meta", "tiktok"
        ad_format: str,  # "banner", "video", "sponsored"
        targeting: Dict[str, Any],
        metadata: Optional[AssetMetadata] = None
    ):
        symbol = f"{platform}:{ad_format}"
        if metadata is None:
            metadata = AssetMetadata(display_name=symbol)

        super().__init__(asset_id, AssetType.AD_INVENTORY, symbol, metadata)
        self.platform = platform
        self.ad_format = ad_format
        self.targeting = targeting

    async def fetch_current_valuation(self) -> AssetValuation:
        # Fetch current CPM, CPC, ROAS from ad platform
        raise NotImplementedError("Integrate with Google Ads, Meta Ads API, etc.")

    async def fetch_state(self) -> AssetState:
        # Check if inventory is available, saturated, etc.
        raise NotImplementedError()

    def calculate_value(self, quantity: float) -> float:
        """quantity = number of impressions or clicks"""
        if not self._valuation:
            raise ValueError("No valuation available")
        return quantity * self._valuation.current_value  # CPM or CPC

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        if quantity < 1000:  # Minimum 1k impressions
            return False, "Minimum 1000 impressions required"
        return True, None


class ProductSKU(Asset):
    """Physical or digital product for arbitrage/dropshipping"""

    def __init__(
        self,
        asset_id: str,
        sku: str,
        product_name: str,
        category: str,
        supplier_cost: float,
        metadata: Optional[AssetMetadata] = None
    ):
        if metadata is None:
            metadata = AssetMetadata(display_name=product_name)

        super().__init__(asset_id, AssetType.PRODUCT_SKU, sku, metadata)
        self.product_name = product_name
        self.category = category
        self.supplier_cost = supplier_cost

    async def fetch_current_valuation(self) -> AssetValuation:
        # Fetch current market price, fees, sales rank from marketplaces
        raise NotImplementedError("Integrate with Amazon, eBay, Shopify APIs")

    async def fetch_state(self) -> AssetState:
        # Check if in stock, restricted, IP flagged, etc.
        raise NotImplementedError()

    def calculate_value(self, quantity: float) -> float:
        """quantity = number of units"""
        if not self._valuation:
            raise ValueError("No valuation available")
        # Return potential profit margin
        return quantity * (self._valuation.current_value - self.supplier_cost)

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        if quantity < 1:
            return False, "Minimum 1 unit required"
        if not float(quantity).is_integer():
            return False, "Quantity must be whole number for physical products"
        return True, None
