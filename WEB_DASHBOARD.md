# Web Dashboard Documentation

Real-time web interface for monitoring and controlling your trading bot.

## Features

### 📊 Real-Time Monitoring
- **Live Statistics**: Total trades, win rate, profit/loss, balance
- **WebSocket Updates**: Instant updates without page refresh
- **Performance Chart**: Cumulative profit visualization
- **Trade History**: Last 20 trades with details
- **Active Orders**: Monitor open orders in real-time

### 🎮 Bot Control
- **Start/Stop/Pause**: Full bot lifecycle control
- **Strategy Selection**: Choose from 11 built-in strategies
- **Provider Selection**: Select from 8 integrated exchanges
- **Live Status**: Visual indicators for bot state

### 🔔 Notifications
- **Trade Alerts**: Instant notifications when trades execute
- **System Events**: Bot started/stopped/paused alerts
- **Error Notifications**: Real-time error reporting

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements-web.txt
```

This installs:
- Flask (web framework)
- Flask-SocketIO (WebSocket support)
- Flask-CORS (cross-origin requests)
- python-socketio (Socket.IO server)
- eventlet (async I/O)

### 2. Start the Server

#### Option A: Standalone Server

```bash
python -m src.web.server --port 8080 --host 0.0.0.0
```

#### Option B: Integrate with Bot

```python
from src.web import create_web_server
import threading

# Create web server
web_server = create_web_server({
    "port": 8080,
    "host": "0.0.0.0"
})

# Run in separate thread
web_thread = threading.Thread(target=web_server.run)
web_thread.daemon = True
web_thread.start()

# Your bot code here
# ...

# Update stats from bot
web_server.update_stats({
    "total_trades": 150,
    "winning_trades": 95,
    "total_profit": 1250.50,
    "balance": 10500.00
})

# Add trade notifications
web_server.add_trade({
    "strategy": "cross_exchange",
    "pair": "BTCUSDT",
    "side": "BUY",
    "size": 0.01,
    "price": 43000.00,
    "profit": 15.50
})
```

### 3. Access Dashboard

Open your browser and navigate to:
```
http://localhost:8080
```

## API Endpoints

### REST API

#### `GET /api/status`
Get current bot status.

**Response**:
```json
{
    "running": true,
    "paused": false,
    "strategy": "cross_exchange",
    "provider": "binance",
    "uptime": 3600
}
```

#### `GET /api/stats`
Get trading statistics.

**Response**:
```json
{
    "total_trades": 150,
    "winning_trades": 95,
    "losing_trades": 55,
    "total_profit": 1250.50,
    "total_loss": 450.20,
    "win_rate": 63.3,
    "avg_profit": 13.16,
    "uptime": 3600,
    "balance": 10500.00
}
```

#### `GET /api/trades?limit=50`
Get recent trades.

**Response**:
```json
[
    {
        "timestamp": "2026-01-18T10:30:15",
        "strategy": "cross_exchange",
        "pair": "BTCUSDT",
        "side": "BUY",
        "size": 0.01,
        "price": 43000.00,
        "profit": 15.50
    }
]
```

#### `GET /api/orders`
Get active orders.

**Response**:
```json
[
    {
        "order_id": "abc123",
        "pair": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "size": 0.01,
        "price": 42500.00,
        "status": "OPEN"
    }
]
```

#### `GET /api/providers`
Get available providers.

**Response**:
```json
{
    "polymarket": "Prediction market (BTC UP/DOWN, binary outcomes)",
    "binance": "World's largest cryptocurrency exchange (global liquidity)",
    "coinbase": "Largest US-based exchange (regulatory compliance)",
    ...
}
```

#### `GET /api/strategies`
Get available strategies.

**Response**:
```json
{
    "binary_arbitrage": "Buy both sides of binary prediction market when total < $1.00 (0.5-3% ROI)",
    "cross_exchange": "Buy low on one exchange, sell high on another (0.3-1.5% ROI, Binance ↔ Coinbase)",
    ...
}
```

#### `POST /api/start`
Start the bot.

**Request**:
```json
{
    "strategy": "cross_exchange",
    "provider": "binance",
    "config": {
        "pair": "BTCUSDT",
        "order_size": 0.01
    }
}
```

**Response**:
```json
{
    "status": "started"
}
```

#### `POST /api/stop`
Stop the bot.

**Response**:
```json
{
    "status": "stopped"
}
```

#### `POST /api/pause`
Pause/Resume the bot.

**Response**:
```json
{
    "status": "paused",
    "paused": true
}
```

### WebSocket Events

#### Client → Server Events

##### `connect`
Client connects to server.

##### `request_stats`
Request current statistics.

##### `request_trades`
Request recent trades.

**Payload**:
```json
{
    "limit": 50
}
```

#### Server → Client Events

##### `connected`
Connection established.

**Payload**:
```json
{
    "message": "Connected to trading bot",
    "timestamp": "2026-01-18T10:30:15"
}
```

##### `stats_update`
Statistics updated.

**Payload**: Same as `/api/stats`

##### `trades_update`
Trades updated.

**Payload**: Array of trades

##### `trade_executed`
New trade executed.

**Payload**:
```json
{
    "timestamp": "2026-01-18T10:30:15",
    "strategy": "cross_exchange",
    "pair": "BTCUSDT",
    "side": "BUY",
    "size": 0.01,
    "price": 43000.00,
    "profit": 15.50
}
```

##### `orders_update`
Active orders updated.

**Payload**: Array of orders

##### `bot_started`
Bot started.

**Payload**:
```json
{
    "strategy": "cross_exchange",
    "provider": "binance",
    "timestamp": "2026-01-18T10:30:15"
}
```

##### `bot_stopped`
Bot stopped.

**Payload**:
```json
{
    "timestamp": "2026-01-18T10:30:15"
}
```

##### `bot_paused`
Bot paused.

**Payload**:
```json
{
    "timestamp": "2026-01-18T10:30:15"
}
```

##### `bot_resumed`
Bot resumed.

**Payload**:
```json
{
    "timestamp": "2026-01-18T10:30:15"
}
```

##### `notification`
System notification.

**Payload**:
```json
{
    "message": "Trade executed successfully",
    "level": "success",
    "timestamp": "2026-01-18T10:30:15"
}
```

Levels: `info`, `success`, `warning`, `error`

## Usage Examples

### Example 1: Basic Integration

```python
from src.web import create_web_server
from src.providers import create_provider
from src.strategies import create_strategy
import threading

# Start web server
web_server = create_web_server({"port": 8080})
web_thread = threading.Thread(target=web_server.run)
web_thread.daemon = True
web_thread.start()

# Create provider and strategy
provider = create_provider("binance", {...})
strategy = create_strategy("cross_exchange", provider, {...})

# Run strategy and update dashboard
async def run_bot():
    await strategy.start()

    # Update stats periodically
    while strategy.running:
        web_server.update_stats({
            "total_trades": strategy.stats.total_trades,
            "winning_trades": strategy.stats.winning_trades,
            "total_profit": strategy.stats.total_profit,
            "balance": provider.get_balance()["USDT"].total
        })

        await asyncio.sleep(1)

asyncio.run(run_bot())
```

### Example 2: Trade Notifications

```python
# After executing a trade
trade_result = await strategy.execute(opportunity)

if trade_result:
    web_server.add_trade({
        "strategy": "cross_exchange",
        "pair": "BTCUSDT",
        "side": "BUY",
        "size": 0.01,
        "price": 43000.00,
        "profit": 15.50
    })
```

### Example 3: Custom Notifications

```python
# Send custom notification
web_server.send_notification(
    "Large arbitrage opportunity detected!",
    level="warning"
)

# Send error notification
web_server.send_notification(
    "Failed to connect to exchange",
    level="error"
)

# Send success notification
web_server.send_notification(
    "Bot started successfully",
    level="success"
)
```

## Security Considerations

### ⚠️ Important Security Notes

1. **Do NOT expose to public internet** without authentication
2. **Use firewall** to restrict access to localhost or trusted IPs
3. **HTTPS recommended** for production use
4. **Add authentication** for production deployments

### Production Deployment

For production, add authentication:

```python
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

users = {
    "admin": "your_secure_password"  # Use environment variable
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

# Protect all routes
@app.before_request
@auth.login_required
def before_request():
    pass
```

### Firewall Configuration

Restrict to localhost only:
```bash
# Only allow localhost
python -m src.web.server --host 127.0.0.1 --port 8080
```

Allow specific IP range:
```python
# In server.py
from flask import request, abort

@app.before_request
def limit_remote_addr():
    allowed_ips = ['127.0.0.1', '192.168.1.100']
    if request.remote_addr not in allowed_ips:
        abort(403)
```

## Customization

### Custom Themes

Edit `src/web/templates/dashboard.html` CSS variables:

```css
:root {
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --text-primary: #e2e8f0;
    --accent: #3b82f6;
    --success: #10b981;
    --error: #ef4444;
    --warning: #f59e0b;
}
```

### Add Custom Metrics

Extend `TradingBotWebServer.update_stats()`:

```python
web_server.update_stats({
    "total_trades": 150,
    "custom_metric": 42,  # Your custom metric
    "sharpe_ratio": 2.5,
    "max_drawdown": -5.2
})
```

Update dashboard HTML to display new metrics.

## Troubleshooting

### Issue: WebSocket not connecting

**Solution**: Check firewall and CORS settings. Ensure eventlet is installed.

### Issue: Chart not updating

**Solution**: Check browser console for JavaScript errors. Verify Chart.js CDN is accessible.

### Issue: Port already in use

**Solution**: Use different port:
```bash
python -m src.web.server --port 8081
```

### Issue: High CPU usage

**Solution**: Reduce update frequency in your bot code. Use `asyncio.sleep()` between stat updates.

## Performance Tips

1. **Update stats max once per second** to avoid overwhelming clients
2. **Limit trade history** to last 1000 trades (already implemented)
3. **Use connection pooling** for database if storing historical data
4. **Gzip compression** for large data transfers

## Future Enhancements

Planned features:
- [ ] Multi-bot management (run multiple strategies simultaneously)
- [ ] Historical chart data export
- [ ] Backtesting integration
- [ ] Mobile-responsive design improvements
- [ ] Dark/light theme toggle
- [ ] Trading strategy builder UI
- [ ] Advanced filtering and search
- [ ] Performance analytics dashboard
- [ ] Email/SMS alerts integration

## Support

For issues or feature requests, please open an issue on GitHub.
