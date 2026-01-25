# Architecture Documentation

This document describes the multi-provider, multi-strategy trading bot architecture.

## 🏗️ System Architecture

### Overview

The bot is built with **three distinct layers** for maximum flexibility and extensibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Trading Bot System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │   Provider   │─────▶│   Strategy   │─────▶│     Bot      │   │
│  │    Layer     │      │    Layer     │      │ Orchestrator │   │
│  └──────────────┘      └──────────────┘      └──────────────┘   │
│         │                     │                      │          │
│         ▼                     ▼                      ▼          │
│  • Polymarket          • Binary Arb          • Single           │
│  • Luno (REST+WS)      • Copy Trading        • Multi            │
│  • Extensible          • Cross-Exchange      • Risk Mgmt        │
│                        • Market Making                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns** - Each layer has a single responsibility
2. **Provider Agnostic** - Strategies work across any provider
3. **Strategy Reusability** - Same strategy, different providers
4. **Easy Extensibility** - Add new providers/strategies without modifying existing code
5. **Testability** - Mock providers for testing strategies
6. **Type Safety** - Strong typing with dataclasses and enums

---

## 📦 Layer 1: Provider Layer

**Location**: `src/providers/`

**Purpose**: Abstract exchange/platform-specific APIs into a common interface.

### Base Interface (`providers/base.py`)

```python
class BaseProvider(ABC):
    def connect() -> None
    def disconnect() -> None
    def get_balance(asset: str) -> Dict[str, Balance]
    def get_orderbook(pair: str) -> Orderbook
    def place_order(pair, side, type, size, price) -> Order
    def get_order(order_id: str) -> Order
    def cancel_order(order_id: str) -> bool
    def get_markets() -> List[str]
```

### Data Models

```python
@dataclass
class Balance:
    asset: str
    available: float
    reserved: float
    total: float

@dataclass
class Orderbook:
    pair: str
    bids: List[OrderbookEntry]
    asks: List[OrderbookEntry]
    timestamp: int

@dataclass
class Order:
    order_id: str
    pair: str
    side: OrderSide
    type: OrderType
    price: Optional[float]
    size: float
    filled_size: float
    status: OrderStatus
```

### Implemented Providers

#### 1. **PolymarketProvider** (`providers/polymarket.py`)

- **Type**: Prediction market
- **Pairs**: Binary outcome tokens (YES/NO, UP/DOWN)
- **Prices**: Probabilities (0.00 to 1.00)
- **Payout**: $1.00 per winning token
- **Auth**: Ethereum private key, Magic.link support
- **Features**:
  - Balance in USDC
  - Orderbook for outcome tokens
  - FOK/GTC order types
  - Negative risk markets support

**Example**:
```python
provider = PolymarketProvider({
    "private_key": "0x...",
    "signature_type": 1,
    "yes_token_id": "...",
    "no_token_id": "..."
})
```

#### 2. **LunoProvider** (`providers/luno.py`)

- **Type**: Cryptocurrency exchange (spot)
- **Pairs**: XBTZAR, ETHZAR, XRPZAR, etc.
- **Prices**: Fiat currency (ZAR)
- **Auth**: API key ID + secret (Basic Auth)
- **Features**:
  - REST API (300 calls/min)
  - WebSocket streaming (50 sessions)
  - Market orders, Limit orders (GTC/FOK/IOC)
  - Real-time orderbook updates

**Example**:
```python
provider = LunoProvider({
    "api_key_id": "...",
    "api_key_secret": "...",
    "default_pair": "XBTZAR"
})
```

#### 3. **KalshiProvider** (`providers/kalshi.py`)

- **Type**: US-regulated prediction market
- **Volume**: $23.8B in 2025 (1,100% YoY growth)
- **Pairs**: Event markets (political, economic, crypto)
- **Prices**: Cents (0-100, converted to 0.00-1.00)
- **Auth**: Email/password or API key (JWT tokens)
- **Features**:
  - Cross-platform arbitrage with Polymarket
  - KYC required (CFTC-regulated)
  - 7% profit commission (no loss commission)
  - Market discovery by event name

**Example**:
```python
provider = KalshiProvider({
    "api_key": "...",  # or email/password
    "default_pair": "KXBTC-23JAN31-T95000"
})
```

#### 4. **BinanceProvider** (`providers/binance.py`)

- **Type**: Cryptocurrency exchange (spot)
- **Size**: World's largest exchange by volume
- **Pairs**: 600+ trading pairs (BTC, ETH, altcoins)
- **Prices**: USDT, BUSD, BTC quoted
- **Auth**: API key + HMAC SHA256 signature
- **Features**:
  - Unmatched global liquidity
  - Cross-exchange arbitrage opportunities
  - Triangular arbitrage within Binance
  - Testnet available
  - 0.1% fees (0.075% with BNB)

**Example**:
```python
provider = BinanceProvider({
    "api_key": "...",
    "api_secret": "...",
    "default_pair": "BTCUSDT",
    "testnet": False
})
```

#### 5. **CoinbaseProvider** (`providers/coinbase.py`)

- **Type**: Cryptocurrency exchange (spot)
- **Size**: Largest US-based exchange
- **Pairs**: Major cryptocurrencies (BTC, ETH, SOL)
- **Prices**: USD, EUR quoted
- **Auth**: API key + HMAC SHA256 signature
- **Features**:
  - US regulatory compliance
  - Strong USD liquidity
  - Cross-exchange arbitrage (often premium vs Binance)
  - Sandbox for testing
  - 0.4-0.6% fees (volume-based)

**Example**:
```python
provider = CoinbaseProvider({
    "api_key": "...",
    "api_secret": "...",
    "default_pair": "BTC-USD",
    "sandbox": False
})
```

#### 6. **BybitProvider** (`providers/bybit.py`)

- **Type**: Derivatives exchange (perpetuals, futures, options)
- **Size**: Leading derivatives platform
- **Pairs**: 200+ perpetual contracts
- **Prices**: USDT-margined, Coin-margined
- **Auth**: API key + HMAC SHA256 signature (v5 API)
- **Features**:
  - High leverage (up to 100x)
  - Funding rate arbitrage opportunities
  - Unified trading account
  - Testnet available
  - 0.02% maker, 0.055% taker

**Example**:
```python
provider = BybitProvider({
    "api_key": "...",
    "api_secret": "...",
    "default_pair": "BTCUSDT",
    "category": "linear",  # linear, inverse, spot
    "testnet": False
})
```

#### 7. **KrakenProvider** (`providers/kraken.py`)

- **Type**: Cryptocurrency exchange (spot)
- **Size**: One of the oldest and most trusted exchanges
- **Pairs**: Major cryptocurrencies with fiat pairs
- **Prices**: USD, EUR, GBP, CAD, JPY quoted
- **Auth**: API key + HMAC SHA512 signature (base64-encoded secret)
- **Features**:
  - Deep liquidity for fiat pairs
  - Strong regulatory compliance
  - Fiat on-ramps (bank wires)
  - Cross-exchange arbitrage opportunities
  - 0.16-0.36% fees (volume-based)

**Example**:
```python
provider = KrakenProvider({
    "api_key": "...",
    "api_secret": "...",  # base64-encoded
    "default_pair": "XXBTZUSD"
})
```

#### 8. **DydxProvider** (`providers/dydx.py`)

- **Type**: Decentralized perpetuals exchange
- **Volume**: $1.5T+ all-time volume
- **Pairs**: Major perpetual contracts
- **Prices**: USDC collateral (cross-margin)
- **Auth**: Wallet address + mnemonic (on-chain signing)
- **Features**:
  - Fully decentralized (non-custodial)
  - No KYC required
  - Funding rate arbitrage vs CEX
  - Hourly funding (vs 8-hour on CEX)
  - 0.02% maker, 0.05% taker
  - Smart contract risk instead of counterparty risk

**Note**: Order placement requires the official dYdX v4 Python client for transaction signing.

**Example**:
```python
provider = DydxProvider({
    "address": "dydx1...",
    "mnemonic": "word1 word2...",
    "default_pair": "BTC-USD",
    "testnet": False
})
```

#### 9. **LunoWebSocket** (`providers/luno_websocket.py`)

- **Market Stream**: Real-time orderbook updates
  - Sequence-numbered updates (must apply in order)
  - Create/Delete/Trade/Status updates
  - Automatic reconnection with backoff

- **User Stream**: Order fills and balance updates
  - Order status changes
  - Fill notifications with deltas
  - 5-minute message cache on reconnect

**Example**:
```python
market_stream = LunoMarketStream(
    pair="XBTZAR",
    api_key_id="...",
    api_key_secret="...",
    on_update=lambda orderbook: handle_update(orderbook)
)
await market_stream.run()
```

### Provider Factory

```python
from src.providers import create_provider

# Polymarket (Prediction Market)
poly_provider = create_provider("polymarket", {
    "private_key": "0x...",
    "signature_type": 1
})

# Luno (South African Exchange)
luno_provider = create_provider("luno", {
    "api_key_id": "...",
    "api_key_secret": "..."
})

# Kalshi (US Prediction Market)
kalshi_provider = create_provider("kalshi", {
    "api_key": "...",
})

# Binance (Global Crypto Exchange)
binance_provider = create_provider("binance", {
    "api_key": "...",
    "api_secret": "...",
    "testnet": False
})

# Coinbase (US Crypto Exchange)
coinbase_provider = create_provider("coinbase", {
    "api_key": "...",
    "api_secret": "...",
    "sandbox": False
})

# Bybit (Derivatives Exchange)
bybit_provider = create_provider("bybit", {
    "api_key": "...",
    "api_secret": "...",
    "category": "linear"
})

# Kraken (Trusted Crypto Exchange)
kraken_provider = create_provider("kraken", {
    "api_key": "...",
    "api_secret": "..."  # base64-encoded
})

# dYdX (DeFi Derivatives)
dydx_provider = create_provider("dydx", {
    "address": "dydx1...",
    "mnemonic": "..."
})
```

**Supported Providers**:
- `polymarket` - Prediction market (binary outcomes)
- `luno` - Cryptocurrency exchange (ZAR pairs)
- `kalshi` - US-regulated prediction market ($23.8B volume)
- `binance` - World's largest cryptocurrency exchange
- `coinbase` - Largest US-based exchange
- `bybit` - Leading derivatives exchange (perpetuals)
- `kraken` - Trusted exchange with fiat pairs
- `dydx` - Decentralized perpetuals ($1.5T+ volume)

---

## 🎯 Layer 2: Strategy Layer

**Location**: `src/strategies/`

**Purpose**: Implement trading logic independent of exchange/platform.

### Base Interface (`strategies/base.py`)

```python
class BaseStrategy(ABC):
    async def start()
    async def stop()
    async def run()  # Main strategy loop

    # Polling mode
    async def find_opportunity() -> Optional[Opportunity]

    # Event-driven mode
    def on_orderbook_update(pair, orderbook)
    def on_trade(pair, trade)
    def on_balance_update(balance)

    # Execution
    async def execute(opportunity) -> TradeResult

    # Validation
    def should_execute(opportunity) -> (bool, str)
```

### Execution Modes

#### 1. **Polling Strategy** (`PollingStrategy`)

Scans for opportunities at regular intervals.

```python
class PollingStrategy(BaseStrategy):
    async def run(self):
        while self.running:
            opportunity = await self.find_opportunity()
            if opportunity and self.should_execute(opportunity):
                await self.execute(opportunity)
            await asyncio.sleep(self.scan_interval)
```

**Use Cases**: Arbitrage, periodic market scans

#### 2. **Event-Driven Strategy** (`EventDrivenStrategy`)

Reacts to real-time market events.

```python
class EventDrivenStrategy(BaseStrategy):
    def on_orderbook_update(self, pair, orderbook):
        opportunity = self.analyze_orderbook(orderbook)
        if opportunity:
            asyncio.create_task(self.execute(opportunity))
```

**Use Cases**: High-frequency trading, market making

### Implemented Strategies

#### 1. **BinaryArbitrageStrategy** (`strategies/binary_arbitrage.py`)

**Description**: Polymarket binary outcome arbitrage

**Logic**:
1. Fetch YES and NO orderbooks
2. Calculate: `total_cost = best_ask_yes + best_ask_no`
3. If `total_cost < target_threshold` (e.g., $0.99)
4. Buy both sides simultaneously
5. Profit: `$1.00 - total_cost` per share

**Configuration**:
```python
{
    "target_pair_cost": 0.99,  # Buy when total < $0.99
    "order_size": 50,          # 50 shares per side
    "order_type": "FOK",       # Fill-or-Kill
    "scan_interval": 1.0,      # Scan every second
    "dry_run": False
}
```

**Example**:
```python
strategy = BinaryArbitrageStrategy(
    provider=poly_provider,
    config=config,
    yes_token_id="...",
    no_token_id="..."
)
await strategy.start()
```

#### 2. **Placeholder Strategies**

The following strategies are architected but not yet implemented:

- `CopyTradingStrategy` - Mirror another trader's positions
- `CrossExchangeArbitrageStrategy` - Buy low on Luno, sell high on Binance
- `TriangularArbitrageStrategy` - BTC→ETH→ZAR→BTC cycles
- `MarketMakingStrategy` - Post bid/ask spreads
- `GridTradingStrategy` - Buy/sell at predefined levels

### Strategy Factory

```python
from src.strategies import create_strategy

strategy = create_strategy("binary_arbitrage", provider, {
    "target_pair_cost": 0.99,
    "order_size": 50,
    "yes_token_id": "...",
    "no_token_id": "..."
})
```

---

## 🤖 Layer 3: Bot Orchestrator

**Location**: `src/strategies/multi_strategy.py`

**Purpose**: Manage multiple strategies with centralized control.

### MultiStrategyBot

```python
class MultiStrategyBot:
    def __init__(self, strategies: List[BaseStrategy])
    async def start()  # Start all strategies in parallel
    async def stop()   # Gracefully stop all strategies
    async def run()    # Run until stopped
    def get_stats()    # Aggregated statistics
```

**Features**:
- Parallel strategy execution
- Aggregated statistics
- Graceful shutdown
- Future: Centralized risk management

**Example**:
```python
from src.strategies import MultiStrategyBot

strategies = [
    create_strategy("binary_arbitrage", poly_provider, config1),
    create_strategy("copy_trading", poly_provider, config2),
    create_strategy("cross_exchange", luno_provider, config3),
]

bot = MultiStrategyBot(strategies)
await bot.run()
```

---

## ⚙️ Configuration System

**Location**: `src/config.py`

### Settings Dataclass

```python
@dataclass
class Settings:
    # Provider selection
    provider: str = "polymarket"  # polymarket, luno

    # Strategy selection
    strategy: str = "binary_arbitrage"

    # Polymarket settings
    private_key: str
    signature_type: int
    yes_token_id: str
    no_token_id: str

    # Luno settings
    luno_api_key_id: str
    luno_api_key_secret: str
    luno_default_pair: str

    # Trading parameters
    target_pair_cost: float
    order_size: float
    order_type: str

    # Trading profiles (capital-based)
    trading_profile: str = "auto"

    # Risk management
    max_daily_loss: float
    max_position_size: float
    max_trades_per_day: int
```

### Helper Functions

```python
# Load settings from .env
settings = load_settings()

# Extract provider-specific config
provider_config = get_provider_config(settings)

# Apply capital-based profile
settings = apply_profile_to_settings(settings, balance=1000.0)
```

---

## 🔄 Complete Integration Flow

### 1. Load Configuration

```python
from src.config import load_settings, get_provider_config

settings = load_settings()  # From .env file
```

### 2. Create Provider

```python
from src.providers import create_provider

provider_config = get_provider_config(settings)
provider = create_provider(settings.provider, provider_config)
provider.connect()
```

### 3. Create Strategy

```python
from src.strategies import create_strategy

strategy_config = {
    "target_pair_cost": settings.target_pair_cost,
    "order_size": settings.order_size,
    "yes_token_id": settings.yes_token_id,
    "no_token_id": settings.no_token_id,
    "dry_run": settings.dry_run,
}

strategy = create_strategy(settings.strategy, provider, strategy_config)
```

### 4. Run Strategy

```python
# Single strategy
await strategy.start()

# Or multi-strategy
from src.strategies import MultiStrategyBot

bot = MultiStrategyBot([strategy1, strategy2, strategy3])
await bot.run()
```

---

## 🧪 Testing Strategy

### Unit Testing

**Providers**: Mock exchange APIs, test data transformations

```python
def test_polymarket_orderbook_parsing():
    provider = PolymarketProvider(mock_config)
    orderbook = provider.get_orderbook("token_id")
    assert orderbook.best_bid.price == 0.48
```

**Strategies**: Mock provider, test opportunity detection

```python
def test_binary_arb_finds_opportunity():
    mock_provider = MockProvider()
    strategy = BinaryArbitrageStrategy(mock_provider, config)

    opportunity = await strategy.find_opportunity()
    assert opportunity.expected_profit > 0
```

### Integration Testing

Test full flow with testnet/sandbox credentials:

```python
# Use Polymarket testnet or Luno sandbox
settings = load_settings()
settings.dry_run = True  # Simulation mode

provider = create_provider("polymarket", test_config)
strategy = create_strategy("binary_arbitrage", provider, test_config)

await strategy.start()
```

---

## 📊 Performance Considerations

### Provider Layer
- **Connection pooling**: Reuse HTTP sessions
- **Rate limiting**: Respect API limits (300 calls/min for Luno)
- **Retry logic**: Exponential backoff on failures
- **Caching**: TTL-based balance caching

### Strategy Layer
- **Scan frequency**: Balance latency vs API usage
- **Parallel execution**: Multiple strategies don't block each other
- **Event-driven**: Lower latency for high-frequency strategies

### WebSocket Streaming
- **Sequence validation**: Ensure correct update order
- **Automatic reconnection**: Backoff on failures
- **Keep-alive**: Prevent disconnections

---

## 🔐 Security

### Credential Management
- **Environment variables**: Never hardcode credentials
- **Credential masking**: Log only last 4 characters
- **Separate configs**: Different .env for production/test

### Order Execution
- **Dry run mode**: Test without real money
- **FOK orders**: All-or-nothing execution (reduce partial fills)
- **Order validation**: Check balance before submission

### Risk Management
- **Daily loss limits**: Stop trading after threshold
- **Position size caps**: Prevent over-exposure
- **Trade frequency limits**: Prevent overtrading

---

## 🚀 Adding New Providers

1. **Create provider class** in `src/providers/your_provider.py`
2. **Inherit from** `BaseProvider`
3. **Implement required methods**: connect, get_balance, get_orderbook, place_order, etc.
4. **Add to factory** in `src/providers/factory.py`
5. **Update config** in `src/config.py`
6. **Create .env example**

---

## 🎯 Adding New Strategies

1. **Create strategy class** in `src/strategies/your_strategy.py`
2. **Inherit from** `PollingStrategy` or `EventDrivenStrategy`
3. **Implement**:
   - `find_opportunity()` (polling) or `on_*` events (event-driven)
   - `execute(opportunity)`
4. **Add to factory** in `src/strategies/factory.py`
5. **Update config**
6. **Create .env example**

---

## 📝 Future Enhancements

### Providers
- [ ] Binance (spot + futures)
- [ ] Kraken
- [ ] Coinbase
- [ ] More Polymarket markets

### Strategies
- [ ] Copy trading
- [ ] Cross-exchange arbitrage
- [ ] Triangular arbitrage
- [ ] Market making
- [ ] Grid trading
- [ ] DCA (Dollar Cost Averaging)

### Features
- [ ] Centralized risk management across strategies
- [ ] ML-based opportunity scoring
- [ ] Backtesting framework
- [ ] Web dashboard for monitoring
- [ ] Telegram notifications

---

## 📚 Related Documentation

- [README.md](./README.md) - General overview and setup
- [PROFILES.md](./PROFILES.md) - Capital-based trading profiles
- [PROFIT_ANALYSIS.md](./PROFIT_ANALYSIS.md) - Budget and profit analysis
- [STRATEGIES.md](./STRATEGIES.md) - Strategy guide (coming soon)

---

*Architecture designed for extensibility, testability, and production deployment.*
