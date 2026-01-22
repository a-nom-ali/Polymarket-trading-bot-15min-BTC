"""
Generic Venue Abstraction Layer

This module defines the core abstraction for any venue/marketplace/platform
where assets can be traded, allocated, or optimized.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from enum import Enum
from datetime import datetime

from .asset import Asset, AssetType, AssetPosition


class VenueType(Enum):
    """Categories of venues the platform can interact with"""
    EXCHANGE_SPOT = "exchange_spot"                # Spot trading exchange
    EXCHANGE_DERIVATIVE = "exchange_derivative"    # Futures/options exchange
    PREDICTION_MARKET = "prediction_market"        # Binary outcome markets
    COMPUTE_MARKETPLACE = "compute_marketplace"    # GPU/CPU rental platforms
    AD_PLATFORM = "ad_platform"                    # Ad networks
    ECOMMERCE_MARKETPLACE = "ecommerce_marketplace"  # Amazon, eBay, Shopify
    LENDING_PLATFORM = "lending_platform"          # DeFi/CeFi lending
    CUSTOM = "custom"


class VenueStatus(Enum):
    """Current operational status of a venue"""
    ONLINE = "online"              # Fully operational
    DEGRADED = "degraded"          # Operating with issues
    MAINTENANCE = "maintenance"    # Scheduled downtime
    OFFLINE = "offline"            # Not accessible
    RESTRICTED = "restricted"      # Limited functionality
    UNKNOWN = "unknown"


class ActionType(Enum):
    """Types of actions that can be performed on a venue"""
    # Trading actions
    PLACE_ORDER = "place_order"
    CANCEL_ORDER = "cancel_order"
    MODIFY_ORDER = "modify_order"

    # Allocation actions
    ALLOCATE = "allocate"
    DEALLOCATE = "deallocate"
    REBALANCE = "rebalance"

    # Listing actions
    CREATE_LISTING = "create_listing"
    UPDATE_LISTING = "update_listing"
    DELETE_LISTING = "delete_listing"

    # Capacity actions
    SET_CAPACITY = "set_capacity"
    SET_PRICE = "set_price"

    # Budget actions
    SET_BUDGET = "set_budget"
    ADJUST_BID = "adjust_bid"

    # Generic
    EXECUTE = "execute"
    QUERY = "query"


@dataclass
class VenueCapabilities:
    """Capabilities and constraints of a venue"""

    # Supported action types
    supported_actions: Set[ActionType] = field(default_factory=set)

    # Supported asset types
    supported_asset_types: Set[AssetType] = field(default_factory=set)

    # Rate limits
    max_requests_per_second: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    max_orders_per_day: Optional[int] = None

    # Order constraints
    supports_limit_orders: bool = True
    supports_market_orders: bool = True
    supports_stop_loss: bool = False
    supports_take_profit: bool = False
    supports_iceberg_orders: bool = False

    # Data access
    provides_orderbook: bool = True
    provides_trade_history: bool = True
    provides_ohlcv: bool = True
    provides_realtime_updates: bool = False
    websocket_available: bool = False

    # Fees
    maker_fee: Optional[float] = None  # As decimal (0.001 = 0.1%)
    taker_fee: Optional[float] = None
    withdrawal_fee: Optional[float] = None

    # Timing
    settlement_time_ms: Optional[int] = None
    typical_latency_ms: Optional[int] = None

    # Custom capabilities
    custom_features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRequest:
    """Request to perform an action on a venue"""

    action_type: ActionType
    asset: Asset
    quantity: float

    # Optional parameters (usage depends on action type)
    price: Optional[float] = None
    side: Optional[str] = None  # "buy", "sell", "long", "short"
    order_type: Optional[str] = None  # "limit", "market", "stop_loss"
    time_in_force: Optional[str] = None  # "GTC", "IOC", "FOK"

    # Metadata
    client_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Constraints
    max_slippage: Optional[float] = None
    timeout_ms: Optional[int] = None


@dataclass
class ActionResult:
    """Result of an action performed on a venue"""

    request: ActionRequest
    success: bool

    # Identifiers
    venue_transaction_id: Optional[str] = None
    client_transaction_id: Optional[str] = None

    # Execution details
    executed_quantity: Optional[float] = None
    executed_price: Optional[float] = None
    total_cost: Optional[float] = None
    fees_paid: Optional[float] = None

    # Status
    status: str = "pending"  # pending, completed, failed, partial
    error_message: Optional[str] = None

    # Timing
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VenueCredentials:
    """Authentication credentials for a venue"""

    credential_type: str  # "api_key", "private_key", "oauth", "wallet"

    # API-based auth
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # Wallet-based auth
    wallet_address: Optional[str] = None
    private_key: Optional[str] = None

    # OAuth
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    # Additional fields
    passphrase: Optional[str] = None
    extra_headers: Dict[str, str] = field(default_factory=dict)

    # Metadata
    is_testnet: bool = False
    environment: str = "production"  # "production", "staging", "testnet"


class Venue(ABC):
    """
    Abstract base class for any venue where assets can be traded or allocated.

    This abstraction allows the same strategy/workflow engine to interact with
    cryptocurrency exchanges, prediction markets, ad platforms, compute marketplaces,
    ecommerce platforms, etc.
    """

    def __init__(
        self,
        venue_id: str,
        venue_type: VenueType,
        name: str,
        capabilities: VenueCapabilities,
        credentials: Optional[VenueCredentials] = None
    ):
        self.venue_id = venue_id
        self.venue_type = venue_type
        self.name = name
        self.capabilities = capabilities
        self.credentials = credentials
        self._status = VenueStatus.UNKNOWN
        self._connected = False

    @property
    def status(self) -> VenueStatus:
        """Current operational status"""
        return self._status

    @property
    def is_connected(self) -> bool:
        """Whether the venue connection is active"""
        return self._connected

    # Connection lifecycle

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the venue.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the venue.

        Returns:
            True if disconnection successful
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> VenueStatus:
        """
        Check the current health/status of the venue.

        Returns:
            Current venue status
        """
        pass

    # Asset discovery

    @abstractmethod
    async def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Asset]:
        """
        List all available assets on this venue.

        Args:
            asset_type: Filter by asset type
            filters: Additional filters (e.g., {"category": "crypto"})

        Returns:
            List of available assets
        """
        pass

    @abstractmethod
    async def get_asset(self, symbol: str) -> Optional[Asset]:
        """
        Get a specific asset by symbol.

        Args:
            symbol: Asset symbol/identifier

        Returns:
            Asset if found, None otherwise
        """
        pass

    # Position management

    @abstractmethod
    async def get_positions(self) -> List[AssetPosition]:
        """
        Get all current positions/holdings on this venue.

        Returns:
            List of current positions
        """
        pass

    @abstractmethod
    async def get_position(self, asset: Asset) -> Optional[AssetPosition]:
        """
        Get current position for a specific asset.

        Args:
            asset: The asset to query

        Returns:
            Position if exists, None otherwise
        """
        pass

    # Action execution

    @abstractmethod
    async def execute_action(self, request: ActionRequest) -> ActionResult:
        """
        Execute an action on this venue.

        This is the core method that handles all venue interactions:
        - Trading: place/cancel/modify orders
        - Allocation: allocate/deallocate resources
        - Listing: create/update/delete listings
        - Budget: set budgets, adjust bids

        Args:
            request: Action request details

        Returns:
            Result of the action
        """
        pass

    @abstractmethod
    async def query_action_status(self, transaction_id: str) -> ActionResult:
        """
        Query the status of a previously submitted action.

        Args:
            transaction_id: Venue transaction ID

        Returns:
            Current status of the action
        """
        pass

    # Market data (for venues that support it)

    async def get_orderbook(self, asset: Asset) -> Optional[Any]:
        """
        Get current orderbook for an asset.

        Returns:
            Orderbook data (format depends on venue type)
        """
        return None  # Default: not supported

    async def get_ticker(self, asset: Asset) -> Optional[Dict[str, Any]]:
        """
        Get current ticker/price data for an asset.

        Returns:
            Ticker data
        """
        return None  # Default: not supported

    async def get_ohlcv(
        self,
        asset: Asset,
        interval: str,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical OHLCV (candlestick) data.

        Args:
            asset: Asset to query
            interval: Time interval (e.g., "1m", "1h", "1d")
            limit: Number of candles

        Returns:
            List of OHLCV data points
        """
        return None  # Default: not supported

    # Utility methods

    def supports_action(self, action_type: ActionType) -> bool:
        """Check if venue supports a specific action type"""
        return action_type in self.capabilities.supported_actions

    def supports_asset_type(self, asset_type: AssetType) -> bool:
        """Check if venue supports a specific asset type"""
        return asset_type in self.capabilities.supported_asset_types

    def validate_action_request(self, request: ActionRequest) -> tuple[bool, Optional[str]]:
        """
        Validate an action request before execution.

        Returns:
            (is_valid, error_message)
        """
        # Check if action is supported
        if not self.supports_action(request.action_type):
            return False, f"Action {request.action_type.value} not supported by {self.name}"

        # Check if asset type is supported
        if not self.supports_asset_type(request.asset.asset_type):
            return False, f"Asset type {request.asset.asset_type.value} not supported by {self.name}"

        # Validate quantity
        is_valid, error = request.asset.validate_quantity(request.quantity)
        if not is_valid:
            return False, error

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize venue to dictionary"""
        return {
            "venue_id": self.venue_id,
            "venue_type": self.venue_type.value,
            "name": self.name,
            "status": self.status.value,
            "is_connected": self.is_connected,
            "capabilities": {
                "supported_actions": [a.value for a in self.capabilities.supported_actions],
                "supported_asset_types": [t.value for t in self.capabilities.supported_asset_types],
                "max_requests_per_second": self.capabilities.max_requests_per_second,
                "supports_limit_orders": self.capabilities.supports_limit_orders,
                "supports_market_orders": self.capabilities.supports_market_orders,
                "maker_fee": self.capabilities.maker_fee,
                "taker_fee": self.capabilities.taker_fee
            }
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.venue_type.value})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} venue_id={self.venue_id} name={self.name}>"
