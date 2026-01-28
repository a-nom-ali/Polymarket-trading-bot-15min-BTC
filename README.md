
<center>

![BrakeDancerLogoRenderSmall.png](BrakeDancerLogoRenderSmall.png)

# Professional Multi-Provider Trading Bot

</center>

**Advanced algorithmic trading bot** with support for **8 exchanges**, **11 proven strategies**, and a **comprehensive management platform**.

> 🌐 **Web Dashboard** - Monitor and control with beautiful real-time interface! See [WEB_DASHBOARD.md](WEB_DASHBOARD.md)

> 🤖 **Multi-Bot Management** - Run multiple strategies simultaneously on different exchanges

> 🎯 **Multi-Provider Architecture** - Trade on 8 platforms: Polymarket, Luno, Kalshi, Binance, Coinbase, Bybit, Kraken, dYdX

> 💎 **11 Trading Strategies** - From simple arbitrage to advanced statistical trading and funding rate capture

> 📊 **Research-Backed** - All strategies based on documented market opportunities with real performance data

> 🔬 **Backtesting** - Test strategies on historical data before live trading

> 📧 **Alerts** - Email and SMS notifications for trades and errors

> 📱 **Mobile-Responsive** - Works beautifully on all devices with dark/light themes

## 🌟 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-web.txt  # For web dashboard

# Start web dashboard
python -m src.web.server --port 8080

# Open browser
http://localhost:8080

# Or run bot directly
python main.py
```

## 📊 Supported Exchanges (8)

| Exchange | Type | Volume | Best For |
|----------|------|--------|----------|
| **Polymarket** | Prediction Market | High | Binary arbitrage, high-probability bonds |
| **Kalshi** | Prediction Market | $23.8B (2025) | Cross-platform arbitrage with Polymarket |
| **Binance** | Crypto Spot | Largest globally | Cross-exchange arb, triangular arb |
| **Coinbase** | Crypto Spot | Largest US | Cross-exchange arb (US premium) |
| **Bybit** | Derivatives | Leading | Funding rate arb, liquidation sniping |
| **Kraken** | Crypto Spot | Trusted | Fiat pairs, statistical arb |
| **dYdX** | DeFi Derivatives | $1.5T+ volume | Funding rate arb (hourly funding) |
| **Luno** | Crypto Spot | South Africa | ZAR trading pairs |

## 🎯 Trading Strategies (11)

### Arbitrage Strategies

| Strategy | ROI/Trade | Frequency | Risk | Capital |
|----------|-----------|-----------|------|---------|
| **Binary Arbitrage** | 0.5-3% | 1-5/day | Low | $50-$5K |
| **High-Probability Bond** | 1-5% (1800% APY) | 5-20/day | Low | $100+ |
| **Cross-Platform Arb** | 0.5-5% | 1-10/day | Medium | $500+ |
| **Cross-Exchange Arb** | 0.3-1.5% | 5-20/day | Low | $500-$5K |
| **Triangular Arb** | 0.1-0.5% | 10-50/day | Low | $200-$2K |
| **Statistical Arb** | 0.5-2% | 3-10/day | Medium | $1K-$5K |

### Advanced Strategies

| Strategy | APY | Type | Risk | Capital |
|----------|-----|------|------|---------|
| **Funding Rate Arb** | 50-200% | Delta-neutral | Low | $1K-$10K |
| **Basis Trading** | 80-200% | Spot-futures | Low | $2K-$10K |
| **Market Making** | 80-200% | Liquidity provision | High | $2K+ |
| **Momentum Trading** | 5-30%/trade | Directional | Medium | $500+ |
| **Liquidation Sniping** | 2-10%/event | Flash crashes | **HIGH** | $500-$5K |

See [STRATEGIES.md](STRATEGIES.md) for detailed strategy documentation.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Trading Bot System                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │   Provider   │─────▶│   Strategy   │─────▶│     Bot      │   │
│  │    Layer     │      │    Layer     │      │ Orchestrator │   │
│  └──────────────┘      └──────────────┘      └──────────────┘   │
│         │                     │                      │            │
│         ▼                     ▼                      ▼            │
│  • 8 Exchanges          • 11 Strategies       • Web Dashboard    │
│  • REST + WS            • Multi-provider      • Risk Mgmt        │
│  • Unified API          • Research-backed     • Live Stats       │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

**3-Layer Design:**
1. **Provider Layer** - Abstract exchange APIs into common interface
2. **Strategy Layer** - Trading logic independent of exchange
3. **Bot Orchestrator** - Execution, risk management, statistics

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details.

## 🌐 Web Dashboard

**Real-time monitoring and control** with WebSocket updates:

### Core Features
- 📊 Live statistics (trades, win rate, profit/loss, balance)
- 📈 Performance chart with cumulative profits
- 🎮 Start/Stop/Pause controls
- 🔔 Trade execution notifications
- 📋 Recent trade history
- ⚙️ Strategy & provider selection

### New UX Enhancements ✨
- 🤖 **Multi-Bot Management** - Individual status cards for each bot with real-time updates
- 💰 **Live Profit Tracking** - Sparkline charts showing profit trends per bot
- 🏥 **Health Monitoring** - API status, balance sufficiency, and error rate tracking
- 🎨 **Visual Strategy Builder** - Drag-and-drop interface for creating trading strategies
- 🔐 **Profile Management** - Securely manage multiple trading profiles with encrypted credentials
- 🔌 **Provider Health Dashboard** - Real-time latency monitoring and status for all exchanges
- 📊 **Comprehensive Bot Config** - Full configuration editor with risk management settings
- 🐍 **Code Generation** - Convert visual workflows to executable Python strategies

**Start Dashboard:**
```bash
pip install -r requirements-web.txt
python -m src.web.server --port 8080
```

See [WEB_DASHBOARD.md](WEB_DASHBOARD.md) for complete documentation.

## 📚 Installation

### Prerequisites

- Python 3.9+
- API keys for your chosen exchange(s)
- Wallet/credentials for trading

### Step 1: Install Dependencies

```bash
# Clone repository
git clone <repository-url>
cd trading-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install core dependencies
pip install -r requirements.txt

# Install web dashboard (optional)
pip install -r requirements-web.txt
```

### Step 2: Configure Environment

Choose a configuration template based on your strategy:

```bash
# Simple arbitrage strategies
cp .env.example.polymarket .env           # Binary arbitrage
cp .env.example.kalshi .env               # Cross-platform arb
cp .env.example.high_probability_bond .env # High-prob bonds

# Advanced strategies
cp .env.example.binance .env              # Cross-exchange arb
cp .env.example.advanced_strategies .env  # All advanced strategies

# Edit configuration
nano .env
```

### Step 3: Add API Keys

Edit `.env` and add your credentials:

```bash
# Example for Binance
PROVIDER=binance
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Example for Polymarket
PROVIDER=polymarket
POLYMARKET_PRIVATE_KEY=0x...
```

See provider-specific documentation for credential setup.

## 🚀 Usage

### Basic Usage

```bash
# Run with default configuration
python main.py

# Run with specific config
python main.py --config .env.custom

# Dry run mode (simulation)
python main.py --dry-run

# Verbose logging
python main.py --verbose
```

### With Web Dashboard

```bash
# Terminal 1: Start web dashboard
python -m src.web.server --port 8080

# Terminal 2: Run bot
python main.py

# Browser: Open dashboard
http://localhost:8080
```

### Advanced Usage

```python
from src.providers import create_provider
from src.strategies import create_strategy
from src.web import create_web_server
import threading

# Start web dashboard
web_server = create_web_server({"port": 8080})
web_thread = threading.Thread(target=web_server.run)
web_thread.daemon = True
web_thread.start()

# Create provider
provider = create_provider("binance", {
    "api_key": "...",
    "api_secret": "..."
})

# Create strategy
strategy = create_strategy("cross_exchange", provider, {
    "provider_b": coinbase_provider,
    "min_spread_pct": 0.3,
    "order_size": 0.01
})

# Run strategy
await strategy.start()

# Update dashboard
web_server.update_stats(strategy.stats)
web_server.add_trade(trade_data)
```

## 💡 Strategy Examples

### Example 1: Cross-Exchange Arbitrage (Binance ↔ Coinbase)

```bash
STRATEGY=cross_exchange
PROVIDER_A=binance
PROVIDER_B=coinbase
PAIR=BTCUSDT
MIN_SPREAD_PCT=0.3
ORDER_SIZE=0.01
```

**Expected**: 0.3-1.5% profit per trade, 5-20 opportunities/day

### Example 2: Funding Rate Arbitrage (Bybit ↔ dYdX)

```bash
STRATEGY=funding_rate
PROVIDER_A=bybit
PROVIDER_B=dydx
PAIR=BTC-USD
POSITION_SIZE=0.1
MIN_FUNDING_DIFF_APY=20.0
```

**Expected**: 50-200% APY with delta-neutral positions

### Example 3: Triangular Arbitrage (Binance)

```bash
STRATEGY=triangular
PROVIDER=binance
TRIANGLE_PAIRS=BTCUSDT,ETHUSDT,ETHBTC
MIN_PROFIT_PCT=0.1
ORDER_SIZE=0.01
```

**Expected**: 0.1-0.5% per cycle, 10-50 opportunities/day

See [STRATEGIES.md](STRATEGIES.md) for all strategy examples.

## 🛡️ Risk Management

**Built-in safeguards:**

- ✅ **Stop Loss** - Automatic position exits on adverse moves
- ✅ **Position Limits** - Maximum position size enforcement
- ✅ **Daily Loss Caps** - Stop trading after max daily loss
- ✅ **Trade Limits** - Maximum trades per day
- ✅ **Balance Checks** - Minimum balance requirements
- ✅ **Dry Run Mode** - Test strategies without real money
- ✅ **Inventory Management** - Track positions across exchanges

**Configuration:**
```bash
MAX_DAILY_LOSS=100.0
MAX_TRADES_PER_DAY=50
MIN_BALANCE_REQUIRED=100.0
MAX_POSITION_SIZE=1000.0
MAX_BALANCE_UTILIZATION=0.7
```

## 🚀 Advanced Features

### Multi-Bot Management
Run multiple strategies simultaneously with visual monitoring:
```python
from src.web import MultiBotManager

manager = MultiBotManager()
bot_1 = manager.create_bot("cross_exchange", "binance", {...})
bot_2 = manager.create_bot("funding_rate", "bybit", {...})
manager.start_bot(bot_1)
manager.start_bot(bot_2)
```

**Web Dashboard Features:**
- Individual bot status cards with real-time profit tracking
- Health indicators (API connection, balance sufficiency, error rate)
- Sparkline charts showing profit trends
- Quick action buttons (pause/stop/configure)
- Per-bot and aggregated performance metrics

### Visual Strategy Builder
Create trading strategies without coding:
```bash
# Access via web dashboard
http://localhost:8080/strategy-builder

# Features:
- Drag-and-drop canvas with zoom/pan controls
- 7 trigger types (price cross, volume spike, RSI, etc.)
- 6 condition types (price comparison, technical indicators)
- 4 action types (market/limit orders)
- 4 risk management blocks (stop loss, take profit, etc.)
- Python code generation from visual workflows
- Template library with pre-built strategies
```

### Profile Management
Securely manage multiple trading configurations:
```bash
# Create profiles via web dashboard
http://localhost:8080 → Click profile icon

# Features:
- AES-256 encrypted credential storage
- Multiple profiles (production, staging, test)
- One-click profile switching
- Credential visibility toggle
- Connection testing before activation
- Separate configuration per profile (RPC, gas limits, etc.)
```

### Backtesting
Test strategies before live trading:
```python
from src.backtesting import BacktestEngine

engine = BacktestEngine(strategy_class, historical_data, config)
result = await engine.run()
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```

### Data Export
Export trading data in multiple formats:
```bash
# Export trades to CSV
curl "http://localhost:8080/api/export/trades?format=csv" > trades.csv

# Export performance metrics
curl "http://localhost:8080/api/export/stats?format=json" > stats.json
```

### Email/SMS Alerts
Get notified about trades and errors:
```bash
# Configure in .env
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
TWILIO_ACCOUNT_SID=your_sid
ALERT_ON_PROFIT_THRESHOLD=100.0
```

## 📖 Documentation

### Core Documentation
- **[FEATURES.md](FEATURES.md)** - Complete feature list with examples
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[STRATEGIES.md](STRATEGIES.md)** - All 11 strategies explained
- **[WEB_DASHBOARD.md](WEB_DASHBOARD.md)** - Web interface documentation
- **[PROVIDER_RESEARCH.md](PROVIDER_RESEARCH.md)** - Exchange research and selection
- **[PROFILES.md](PROFILES.md)** - Capital-based trading profiles

### UX Enhancement Documentation (New!)
- **[UX_ENHANCEMENT_PLAN.md](UX_ENHANCEMENT_PLAN.md)** - Next-generation dashboard design plan
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Code examples and implementation details
- **[QUICK_START_UX.md](QUICK_START_UX.md)** - Quick start guide for UX enhancements
- **[MOCKUPS.md](MOCKUPS.md)** - Visual mockups and design reference

## 🎓 Strategy Selection Guide

**For Beginners ($100-$500):**
- Binary Arbitrage (Polymarket)
- High-Probability Bond (Polymarket)
- Cross-Exchange Arbitrage (Binance ↔ Coinbase)

**For Intermediate ($500-$2,000):**
- Triangular Arbitrage (Binance)
- Cross-Platform Arbitrage (Polymarket ↔ Kalshi)
- Statistical Arbitrage (3+ exchanges)

**For Advanced ($2,000-$10,000):**
- Funding Rate Arbitrage (Bybit ↔ dYdX)
- Basis Trading (Spot + Futures)
- Market Making (requires large capital)

**High Risk (Experienced Only):**
- Liquidation Sniping (Bybit)
- Momentum Trading (directional)

## 🔒 Security Best Practices

1. **Never share private keys or API secrets**
2. **Use API keys with minimal permissions** (trading only, no withdrawals)
3. **Test with small amounts first** using dry run mode
4. **Set up IP whitelisting** on exchange APIs
5. **Use 2FA** on all exchange accounts
6. **Monitor positions regularly**
7. **Keep software updated**

## 📊 Performance Tracking

**Built-in statistics:**
- Total trades executed
- Win rate percentage
- Total profit/loss
- Average profit per trade
- Sharpe ratio (via backtesting)
- Maximum drawdown (via backtesting)
- Per-bot and aggregated metrics

**Export trade history:**
```bash
# Export via API
curl "http://localhost:8080/api/export/trades?format=csv" > trades.csv
curl "http://localhost:8080/api/export/stats?format=json" > stats.json
curl "http://localhost:8080/api/export/chart-data?interval=1h" > chart.csv
```

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional exchange integrations
- New trading strategies
- Performance optimizations
- Documentation improvements
- Test coverage

## ⚠️ Disclaimer

**This software is for educational and research purposes.**

- Trading cryptocurrencies and prediction markets involves substantial risk
- Past performance does not guarantee future results
- Only trade with money you can afford to lose
- The authors are not responsible for any financial losses
- Not financial advice - do your own research
- Test thoroughly before using real funds

## 📜 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Research data from DeFi protocols and exchange documentation
- Community feedback and contributions
- Open source libraries: Flask, Chart.js, py-clob-client

## 📞 Support

- **Documentation**: Check docs/ folder
- **Issues**: Open GitHub issue
- **Discussions**: GitHub discussions

---

**Built with ❤️ for algorithmic traders**

Current Version: 3.0.0 (Multi-Bot + Analytics + Alerts)
