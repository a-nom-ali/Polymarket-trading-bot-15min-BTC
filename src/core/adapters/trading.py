"""
Trading Domain Adapter

Bridges the generic abstraction layer with cryptocurrency/financial trading.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..asset import Asset, AssetType, AssetMetadata, AssetValuation, AssetState
from ..venue import (
    Venue, VenueType, VenueCapabilities, VenueStatus, VenueCredentials,
    ActionType, ActionRequest, ActionResult, AssetPosition
)
from ...providers.base import BaseProvider, Orderbook, Order, Balance


class FinancialAssetAdapter(Asset):
    """
    Adapter that wraps a financial instrument and integrates with BaseProvider.

    This shows how existing trading infrastructure maps to the generic Asset abstraction.
    """

    def __init__(
        self,
        provider: BaseProvider,
        symbol: str,
        base_currency: str,
        quote_currency: str
    ):
        asset_id = f"{provider.__class__.__name__}:{symbol}"
        metadata = AssetMetadata(
            display_name=symbol,
            description=f"{base_currency}/{quote_currency} trading pair"
        )

        super().__init__(
            asset_id=asset_id,
            asset_type=AssetType.FINANCIAL_SPOT,
            symbol=symbol,
            metadata=metadata
        )

        self.provider = provider
        self.base_currency = base_currency
        self.quote_currency = quote_currency

    async def fetch_current_valuation(self) -> AssetValuation:
        """Fetch current price from provider's orderbook"""
        try:
            orderbook = await self.provider.get_orderbook(self.symbol)

            valuation = AssetValuation(
                current_value=orderbook.mid_price,
                currency=self.quote_currency,
                bid=orderbook.best_bid,
                ask=orderbook.best_ask,
                spread=orderbook.spread,
                mid_price=orderbook.mid_price
            )

            self._valuation = valuation
            return valuation

        except Exception as e:
            raise ValueError(f"Failed to fetch valuation for {self.symbol}: {e}")

    async def fetch_state(self) -> AssetState:
        """Check if asset is tradeable on the provider"""
        try:
            markets = await self.provider.get_markets()
            if self.symbol in markets:
                self._state = AssetState.ACTIVE
            else:
                self._state = AssetState.DELISTED

            return self._state

        except Exception:
            self._state = AssetState.UNKNOWN
            return self._state

    def calculate_value(self, quantity: float) -> float:
        """Calculate value in quote currency"""
        if not self._valuation:
            raise ValueError("No valuation available")
        return quantity * self._valuation.current_value

    def validate_quantity(self, quantity: float) -> tuple[bool, Optional[str]]:
        """Validate quantity for trading"""
        if quantity <= 0:
            return False, "Quantity must be positive"

        # Provider-specific minimum order size could be checked here
        return True, None


class TradingVenueAdapter(Venue):
    """
    Adapter that wraps a BaseProvider and implements the generic Venue interface.

    This shows how existing exchange integrations (Binance, Coinbase, etc.)
    map to the generic Venue abstraction.
    """

    def __init__(
        self,
        provider: BaseProvider,
        credentials: Optional[VenueCredentials] = None
    ):
        venue_id = f"trading:{provider.__class__.__name__}"
        venue_type = VenueType.EXCHANGE_SPOT

        # Define capabilities based on provider
        capabilities = VenueCapabilities(
            supported_actions={
                ActionType.PLACE_ORDER,
                ActionType.CANCEL_ORDER,
                ActionType.QUERY
            },
            supported_asset_types={
                AssetType.FINANCIAL_SPOT,
                AssetType.FINANCIAL_DERIVATIVE,
                AssetType.FINANCIAL_BINARY
            },
            supports_limit_orders=True,
            supports_market_orders=True,
            provides_orderbook=True,
            provides_trade_history=True,
            # Fees would come from provider config
            maker_fee=0.001,  # Example: 0.1%
            taker_fee=0.002   # Example: 0.2%
        )

        super().__init__(
            venue_id=venue_id,
            venue_type=venue_type,
            name=provider.__class__.__name__,
            capabilities=capabilities,
            credentials=credentials
        )

        self.provider = provider
        self._asset_cache: Dict[str, FinancialAssetAdapter] = {}

    async def connect(self) -> bool:
        """Connect to the trading provider"""
        try:
            await self.provider.connect()
            self._connected = True
            self._status = VenueStatus.ONLINE
            return True
        except Exception as e:
            self._status = VenueStatus.OFFLINE
            return False

    async def disconnect(self) -> bool:
        """Disconnect from the trading provider"""
        try:
            await self.provider.disconnect()
            self._connected = False
            return True
        except Exception:
            return False

    async def healthcheck(self) -> VenueStatus:
        """Check provider health"""
        try:
            # Attempt to fetch markets as health check
            await self.provider.get_markets()
            self._status = VenueStatus.ONLINE
        except Exception:
            self._status = VenueStatus.OFFLINE

        return self._status

    async def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Asset]:
        """List all tradeable assets on this provider"""
        try:
            markets = await self.provider.get_markets()
            assets = []

            for symbol in markets:
                # Parse symbol to get base/quote currencies
                # This is simplified - real implementation would parse correctly
                if '/' in symbol:
                    base, quote = symbol.split('/')
                elif '-' in symbol:
                    base, quote = symbol.split('-')
                else:
                    continue

                asset = FinancialAssetAdapter(
                    provider=self.provider,
                    symbol=symbol,
                    base_currency=base,
                    quote_currency=quote
                )
                assets.append(asset)

            return assets

        except Exception:
            return []

    async def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get a specific asset by symbol"""
        # Check cache first
        if symbol in self._asset_cache:
            return self._asset_cache[symbol]

        # Parse and create new asset
        if '/' in symbol:
            base, quote = symbol.split('/')
        elif '-' in symbol:
            base, quote = symbol.split('-')
        else:
            return None

        asset = FinancialAssetAdapter(
            provider=self.provider,
            symbol=symbol,
            base_currency=base,
            quote_currency=quote
        )

        # Cache it
        self._asset_cache[symbol] = asset

        return asset

    async def get_positions(self) -> List[AssetPosition]:
        """Get all current positions (balances) on this provider"""
        try:
            positions = []

            # Get all balances
            # Note: BaseProvider.get_balance() takes an asset parameter
            # In real implementation, we'd need to iterate through all assets
            # For now, this is a simplified example

            # This would need to be enhanced based on BaseProvider interface
            # Placeholder implementation:
            return positions

        except Exception:
            return []

    async def get_position(self, asset: Asset) -> Optional[AssetPosition]:
        """Get current position for a specific asset"""
        try:
            if not isinstance(asset, FinancialAssetAdapter):
                return None

            # Get balance for base currency
            balance_result = await self.provider.get_balance(asset.base_currency)

            if not balance_result:
                return None

            # Extract balance (BaseProvider returns Dict[str, Balance])
            if asset.base_currency in balance_result:
                balance = balance_result[asset.base_currency]

                # Fetch current price
                valuation = await asset.fetch_current_valuation()

                position = AssetPosition(
                    asset_id=asset.asset_id,
                    quantity=balance.total,
                    available=balance.available,
                    reserved=balance.reserved,
                    current_price=valuation.current_value,
                    current_value=balance.total * valuation.current_value
                )

                return position

            return None

        except Exception:
            return None

    async def execute_action(self, request: ActionRequest) -> ActionResult:
        """Execute a trading action"""
        # Validate request
        is_valid, error = self.validate_action_request(request)
        if not is_valid:
            return ActionResult(
                request=request,
                success=False,
                error_message=error,
                status="failed"
            )

        try:
            if request.action_type == ActionType.PLACE_ORDER:
                return await self._place_order(request)
            elif request.action_type == ActionType.CANCEL_ORDER:
                return await self._cancel_order(request)
            else:
                return ActionResult(
                    request=request,
                    success=False,
                    error_message=f"Unsupported action type: {request.action_type}",
                    status="failed"
                )

        except Exception as e:
            return ActionResult(
                request=request,
                success=False,
                error_message=str(e),
                status="failed"
            )

    async def _place_order(self, request: ActionRequest) -> ActionResult:
        """Place an order via the provider"""
        started_at = datetime.utcnow()

        # Extract parameters
        symbol = request.asset.symbol
        side = request.side or "buy"
        order_type = request.order_type or "limit"
        quantity = request.quantity
        price = request.price

        try:
            # Place order via provider
            order = await self.provider.place_order(
                pair=symbol,
                side=side,
                type=order_type,
                size=quantity,
                price=price
            )

            completed_at = datetime.utcnow()
            execution_time_ms = (completed_at - started_at).total_seconds() * 1000

            return ActionResult(
                request=request,
                success=True,
                venue_transaction_id=order.order_id,
                client_transaction_id=request.client_id,
                executed_quantity=quantity,
                executed_price=price,
                status=order.status.value,
                submitted_at=started_at,
                completed_at=completed_at,
                execution_time_ms=execution_time_ms
            )

        except Exception as e:
            return ActionResult(
                request=request,
                success=False,
                error_message=str(e),
                status="failed",
                submitted_at=started_at
            )

    async def _cancel_order(self, request: ActionRequest) -> ActionResult:
        """Cancel an order via the provider"""
        started_at = datetime.utcnow()

        order_id = request.metadata.get("order_id")
        if not order_id:
            return ActionResult(
                request=request,
                success=False,
                error_message="Missing order_id in metadata",
                status="failed"
            )

        try:
            success = await self.provider.cancel_order(order_id)

            completed_at = datetime.utcnow()
            execution_time_ms = (completed_at - started_at).total_seconds() * 1000

            return ActionResult(
                request=request,
                success=success,
                venue_transaction_id=order_id,
                status="cancelled" if success else "failed",
                submitted_at=started_at,
                completed_at=completed_at,
                execution_time_ms=execution_time_ms
            )

        except Exception as e:
            return ActionResult(
                request=request,
                success=False,
                error_message=str(e),
                status="failed",
                submitted_at=started_at
            )

    async def query_action_status(self, transaction_id: str) -> ActionResult:
        """Query order status"""
        try:
            order = await self.provider.get_order(transaction_id)

            # Create a placeholder ActionRequest (we don't have the original)
            dummy_request = ActionRequest(
                action_type=ActionType.PLACE_ORDER,
                asset=None,  # We don't have the asset reference
                quantity=0
            )

            return ActionResult(
                request=dummy_request,
                success=True,
                venue_transaction_id=transaction_id,
                status=order.status.value,
                metadata={"order": order.__dict__}
            )

        except Exception as e:
            dummy_request = ActionRequest(
                action_type=ActionType.QUERY,
                asset=None,
                quantity=0
            )

            return ActionResult(
                request=dummy_request,
                success=False,
                error_message=str(e),
                status="failed"
            )

    async def get_orderbook(self, asset: Asset) -> Optional[Orderbook]:
        """Get orderbook for an asset"""
        try:
            return await self.provider.get_orderbook(asset.symbol)
        except Exception:
            return None

    async def get_ticker(self, asset: Asset) -> Optional[Dict[str, Any]]:
        """Get ticker data"""
        try:
            orderbook = await self.provider.get_orderbook(asset.symbol)
            return {
                "symbol": asset.symbol,
                "bid": orderbook.best_bid,
                "ask": orderbook.best_ask,
                "mid": orderbook.mid_price,
                "spread": orderbook.spread
            }
        except Exception:
            return None
