# Implementation Guide - Priority Features

This guide provides specific implementation details for the top-priority UX enhancements.

---

## 🚀 Phase 1: Multi-Bot Status Cards & Live Updates

### 1. Enhanced WebSocket Architecture

#### Backend: Update `src/web/server.py`

Add new WebSocket events for live bot updates:

```python
def _setup_websocket_handlers(self):
    """Setup WebSocket event handlers with live updates."""

    # ... existing handlers ...

    @self.socketio.on('request_bot_list')
    def handle_request_bot_list(data=None):
        """Send current bot list to client."""
        bots = self.bot_manager.get_all_bots()

        # Enrich with live metrics
        for bot in bots:
            bot_id = bot['id']
            bot['health'] = self._get_bot_health(bot_id)
            bot['sparkline'] = self._get_profit_sparkline(bot_id, points=10)
            bot['last_activity'] = self._get_last_activity(bot_id)

        emit('bot_list_update', bots)

    @self.socketio.on('request_provider_health')
    def handle_request_provider_health(data=None):
        """Send provider health status."""
        health = self._check_provider_health()
        emit('provider_health_update', health)

def _get_bot_health(self, bot_id: str) -> Dict[str, Any]:
    """Get bot health indicators."""
    bot = self.bot_manager.get_bot(bot_id)
    if not bot:
        return {}

    return {
        'api_connected': bot.get('api_connected', True),
        'balance_sufficient': bot.get('balance_sufficient', True),
        'error_rate': bot.get('error_rate', 0.0),
        'last_trade_age': bot.get('last_trade_age', 0),  # seconds
        'overall': 'healthy' if all([
            bot.get('api_connected'),
            bot.get('balance_sufficient'),
            bot.get('error_rate', 0) < 0.05
        ]) else 'warning'
    }

def _get_profit_sparkline(self, bot_id: str, points: int = 10) -> List[float]:
    """Get profit sparkline data for bot."""
    bot = self.bot_manager.get_bot(bot_id)
    if not bot:
        return []

    # Get last N trades for this bot
    bot_trades = [t for t in self.recent_trades if t.get('bot_id') == bot_id]
    recent = bot_trades[-points:]

    # Calculate cumulative profit
    cumulative = []
    total = 0
    for trade in recent:
        total += trade.get('profit', 0)
        cumulative.append(total)

    return cumulative

def _check_provider_health(self) -> Dict[str, Any]:
    """Check health of all configured providers."""
    health = {}

    for provider_name in get_supported_providers():
        try:
            # Try to create provider connection
            provider = create_provider(provider_name, {})

            # Measure latency
            start = time.time()
            # Ping provider API (implement in base provider)
            await provider.ping()
            latency = (time.time() - start) * 1000  # ms

            health[provider_name] = {
                'status': 'online',
                'latency_ms': round(latency, 1),
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            health[provider_name] = {
                'status': 'offline',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }

    return health

# Add background task for live updates
def start_live_update_loop(self):
    """Background task to push live updates to clients."""
    def update_loop():
        while True:
            try:
                # Update bot list every second
                bots = self.bot_manager.get_all_bots()
                for bot in bots:
                    bot['health'] = self._get_bot_health(bot['id'])
                    bot['sparkline'] = self._get_profit_sparkline(bot['id'])

                self.socketio.emit('bot_list_update', bots)

                # Update provider health every 5 seconds
                if int(time.time()) % 5 == 0:
                    health = self._check_provider_health()
                    self.socketio.emit('provider_health_update', health)

                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in live update loop: {e}")
                time.sleep(5)

    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
```

#### Frontend: Create `bot-card.js` Component

```javascript
// src/web/static/js/components/bot-card.js

class BotCard {
    constructor(bot, container) {
        this.bot = bot;
        this.container = container;
        this.render();
    }

    render() {
        const card = document.createElement('div');
        card.className = `bot-card bot-card--${this.bot.status}`;
        card.dataset.botId = this.bot.id;

        card.innerHTML = `
            <div class="bot-card__header">
                <div class="bot-card__status-indicator bot-card__status-indicator--${this.getStatusColor()}">
                    <span class="bot-card__status-dot"></span>
                    <span class="bot-card__status-text">${this.bot.status}</span>
                </div>
                <div class="bot-card__actions">
                    <button class="btn-icon" onclick="pauseBot('${this.bot.id}')" title="Pause">⏸</button>
                    <button class="btn-icon" onclick="stopBot('${this.bot.id}')" title="Stop">⏹</button>
                    <button class="btn-icon" onclick="configBot('${this.bot.id}')" title="Settings">⚙️</button>
                </div>
            </div>

            <div class="bot-card__title">
                <h3>Bot #${this.bot.id.slice(-4)} - ${this.bot.strategy}</h3>
                <p class="bot-card__subtitle">${this.bot.provider} | ${this.bot.pair || 'N/A'}</p>
            </div>

            <div class="bot-card__metrics">
                <div class="metric">
                    <span class="metric__label">Profit (24h)</span>
                    <span class="metric__value metric__value--${this.getProfitColor()}">
                        $${this.formatNumber(this.bot.profit_24h || 0)}
                        <span class="metric__change">(${this.formatPercent(this.bot.profit_pct || 0)}%)</span>
                    </span>
                </div>
                <div class="metric">
                    <span class="metric__label">Trades</span>
                    <span class="metric__value">${this.bot.trades_count || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric__label">Win Rate</span>
                    <span class="metric__value">${this.formatPercent(this.bot.win_rate || 0)}%</span>
                </div>
            </div>

            <div class="bot-card__sparkline">
                <canvas id="sparkline-${this.bot.id}" height="40"></canvas>
            </div>

            <div class="bot-card__footer">
                <div class="bot-card__health">
                    ${this.renderHealthIndicators()}
                </div>
                <div class="bot-card__activity">
                    <span class="activity-text">Last: ${this.formatLastActivity()}</span>
                </div>
            </div>
        `;

        this.container.appendChild(card);
        this.renderSparkline();
    }

    renderSparkline() {
        const ctx = document.getElementById(`sparkline-${this.bot.id}`).getContext('2d');
        const sparklineData = this.bot.sparkline || [];

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: sparklineData.map((_, i) => i),
                datasets: [{
                    data: sparklineData,
                    borderColor: this.getProfitColor() === 'positive' ? '#10b981' : '#ef4444',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { display: false }
                }
            }
        });
    }

    renderHealthIndicators() {
        const health = this.bot.health || {};
        const indicators = [
            { key: 'api_connected', label: 'API', icon: '📡' },
            { key: 'balance_sufficient', label: 'Balance', icon: '💰' },
            { key: 'error_rate_ok', label: 'Errors', icon: '⚠️' }
        ];

        return indicators.map(ind => `
            <div class="health-indicator ${health[ind.key] ? 'health-indicator--ok' : 'health-indicator--warning'}">
                <span class="health-indicator__icon">${ind.icon}</span>
                <span class="health-indicator__label">${ind.label}</span>
            </div>
        `).join('');
    }

    getStatusColor() {
        const colors = {
            'running': 'success',
            'paused': 'warning',
            'stopped': 'neutral',
            'error': 'danger'
        };
        return colors[this.bot.status] || 'neutral';
    }

    getProfitColor() {
        return (this.bot.profit_24h || 0) >= 0 ? 'positive' : 'negative';
    }

    formatNumber(num) {
        return Math.abs(num).toFixed(2);
    }

    formatPercent(num) {
        const sign = num >= 0 ? '+' : '';
        return sign + num.toFixed(2);
    }

    formatLastActivity() {
        if (!this.bot.last_activity) return 'Never';

        const seconds = Math.floor((Date.now() - new Date(this.bot.last_activity)) / 1000);

        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    update(newBot) {
        this.bot = newBot;
        // Re-render only changed elements for performance
        this.updateMetrics();
        this.updateSparkline();
        this.updateHealth();
    }

    updateMetrics() {
        const card = document.querySelector(`[data-bot-id="${this.bot.id}"]`);
        if (!card) return;

        const profitEl = card.querySelector('.metric__value--positive, .metric__value--negative');
        if (profitEl) {
            profitEl.className = `metric__value metric__value--${this.getProfitColor()}`;
            profitEl.innerHTML = `
                $${this.formatNumber(this.bot.profit_24h || 0)}
                <span class="metric__change">(${this.formatPercent(this.bot.profit_pct || 0)}%)</span>
            `;
        }
    }

    updateSparkline() {
        // Update Chart.js instance
        const canvas = document.getElementById(`sparkline-${this.bot.id}`);
        if (!canvas) return;

        const chart = Chart.getChart(canvas);
        if (chart) {
            chart.data.datasets[0].data = this.bot.sparkline || [];
            chart.update('none'); // Update without animation for performance
        }
    }

    updateHealth() {
        const card = document.querySelector(`[data-bot-id="${this.bot.id}"]`);
        if (!card) return;

        const healthContainer = card.querySelector('.bot-card__health');
        healthContainer.innerHTML = this.renderHealthIndicators();
    }
}
```

#### Frontend: Update `dashboard.html`

Add bot grid section:

```html
<!-- Add after controls section -->
<div class="section">
    <div class="section-header">
        <h2>🤖 Active Bots</h2>
        <button class="btn btn--primary" onclick="createBot()">+ New Bot</button>
    </div>

    <div id="botGrid" class="bot-grid">
        <!-- Bot cards will be dynamically inserted here -->
        <div class="bot-grid__empty">
            <p>No bots running. Create your first bot to get started!</p>
            <button class="btn btn--primary" onclick="createBot()">+ Create Bot</button>
        </div>
    </div>
</div>

<!-- Add provider health panel -->
<div class="section">
    <h2>📡 Provider Status</h2>
    <div class="card">
        <div id="providerHealth" class="provider-health-grid">
            <!-- Provider health items will be inserted here -->
        </div>
    </div>
</div>
```

Add CSS:

```css
/* Bot Grid */
.bot-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 20px;
    margin-top: 20px;
}

.bot-grid__empty {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 20px;
    color: var(--text-tertiary);
}

/* Bot Card */
.bot-card {
    background: var(--bg-secondary);
    border: 2px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.bot-card:hover {
    border-color: var(--info);
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.bot-card--running {
    border-left: 4px solid var(--success);
}

.bot-card--paused {
    border-left: 4px solid var(--warning);
}

.bot-card--stopped {
    border-left: 4px solid var(--text-tertiary);
    opacity: 0.7;
}

.bot-card__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.bot-card__status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.bot-card__status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

.bot-card__status-indicator--success .bot-card__status-dot {
    background: var(--success);
}

.bot-card__status-indicator--warning .bot-card__status-dot {
    background: var(--warning);
}

.bot-card__status-indicator--neutral .bot-card__status-dot {
    background: var(--text-tertiary);
}

.bot-card__actions {
    display: flex;
    gap: 8px;
}

.btn-icon {
    padding: 6px 10px;
    background: var(--bg-tertiary);
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 16px;
}

.btn-icon:hover {
    transform: scale(1.1);
    background: var(--bg-primary);
}

.bot-card__title h3 {
    font-size: 16px;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.bot-card__subtitle {
    font-size: 13px;
    color: var(--text-tertiary);
}

.bot-card__metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px;
    margin: 20px 0;
}

.metric {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.metric__label {
    font-size: 11px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metric__value {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
}

.metric__value--positive {
    color: var(--success);
}

.metric__value--negative {
    color: var(--error);
}

.metric__change {
    font-size: 12px;
    font-weight: 500;
    margin-left: 4px;
}

.bot-card__sparkline {
    height: 40px;
    margin: 15px 0;
}

.bot-card__footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 15px;
    border-top: 1px solid var(--border-color);
}

.bot-card__health {
    display: flex;
    gap: 10px;
}

.health-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
}

.health-indicator__icon {
    font-size: 14px;
}

.health-indicator--ok {
    color: var(--success);
}

.health-indicator--warning {
    color: var(--warning);
}

.activity-text {
    font-size: 11px;
    color: var(--text-tertiary);
}

/* Provider Health Grid */
.provider-health-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
}

.provider-health-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: var(--bg-tertiary);
    border-radius: 8px;
    border-left: 3px solid var(--border-color);
}

.provider-health-item--online {
    border-left-color: var(--success);
}

.provider-health-item--offline {
    border-left-color: var(--error);
}

.provider-health-item--warning {
    border-left-color: var(--warning);
}

.provider-health__name {
    font-weight: 600;
    color: var(--text-primary);
}

.provider-health__metrics {
    display: flex;
    gap: 15px;
    font-size: 12px;
    color: var(--text-tertiary);
}

.provider-health__latency {
    font-weight: 500;
}
```

Add JavaScript:

```javascript
// Bot management
let botCards = new Map();

socket.on('bot_list_update', (bots) => {
    const botGrid = document.getElementById('botGrid');
    const empty = botGrid.querySelector('.bot-grid__empty');

    if (bots.length === 0) {
        if (!empty) {
            botGrid.innerHTML = `
                <div class="bot-grid__empty">
                    <p>No bots running. Create your first bot to get started!</p>
                    <button class="btn btn--primary" onclick="createBot()">+ Create Bot</button>
                </div>
            `;
        }
        return;
    }

    // Remove empty state
    if (empty) empty.remove();

    // Update or create bot cards
    bots.forEach(bot => {
        if (botCards.has(bot.id)) {
            botCards.get(bot.id).update(bot);
        } else {
            const card = new BotCard(bot, botGrid);
            botCards.set(bot.id, card);
        }
    });

    // Remove cards for deleted bots
    botCards.forEach((card, botId) => {
        if (!bots.find(b => b.id === botId)) {
            document.querySelector(`[data-bot-id="${botId}"]`)?.remove();
            botCards.delete(botId);
        }
    });
});

socket.on('provider_health_update', (health) => {
    const container = document.getElementById('providerHealth');

    container.innerHTML = Object.entries(health).map(([name, status]) => `
        <div class="provider-health-item provider-health-item--${status.status}">
            <div>
                <div class="provider-health__name">${name}</div>
                <div class="provider-health__metrics">
                    ${status.status === 'online'
                        ? `<span class="provider-health__latency">Ping: ${status.latency_ms}ms</span>`
                        : `<span style="color: var(--error);">${status.error}</span>`
                    }
                </div>
            </div>
            <div class="provider-health__status">
                ${status.status === 'online' ? '🟢' : '🔴'}
            </div>
        </div>
    `).join('');
});

// Request bot list on connect
socket.on('connected', () => {
    socket.emit('request_bot_list');
    socket.emit('request_provider_health');

    // Poll for updates every second
    setInterval(() => {
        socket.emit('request_bot_list');
    }, 1000);

    // Poll provider health every 5 seconds
    setInterval(() => {
        socket.emit('request_provider_health');
    }, 5000);
});
```

---

## 🔐 Phase 2: Profile & Credential Management

### Backend: Create `src/web/profile_manager.py`

```python
"""Profile and credential management with encryption."""

import os
import json
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import logging

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manage trading profiles with encrypted credentials."""

    def __init__(self, master_password: Optional[str] = None):
        """Initialize profile manager.

        Args:
            master_password: Master password for encryption (defaults to env var)
        """
        self.profiles_dir = Path.home() / '.trading-bot' / 'profiles'
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        password = master_password or os.getenv('MASTER_PASSWORD', 'changeme')
        self.cipher = self._create_cipher(password)

        self.active_profile = None

    def _create_cipher(self, password: str) -> Fernet:
        """Create Fernet cipher from password."""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'trading-bot-salt',  # In production, use random salt per user
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def create_profile(self, name: str, config: Dict[str, Any]) -> str:
        """Create new trading profile.

        Args:
            name: Profile name
            config: Profile configuration including credentials

        Returns:
            Profile ID
        """
        profile_id = name.lower().replace(' ', '_')
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if profile_path.exists():
            raise ValueError(f"Profile '{name}' already exists")

        # Encrypt sensitive fields
        encrypted_config = self._encrypt_credentials(config)

        profile = {
            'id': profile_id,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'config': encrypted_config
        }

        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)

        logger.info(f"Created profile: {name}")
        return profile_id

    def _encrypt_credentials(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive credential fields."""
        encrypted = config.copy()

        sensitive_fields = [
            'api_key', 'api_secret', 'private_key', 'password',
            'binance_api_key', 'binance_api_secret',
            'coinbase_api_key', 'coinbase_api_secret',
            # ... add all provider credential fields
        ]

        for field in sensitive_fields:
            if field in encrypted:
                value = encrypted[field]
                if value:
                    encrypted[field] = self.cipher.encrypt(value.encode()).decode()

        return encrypted

    def _decrypt_credentials(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive credential fields."""
        decrypted = config.copy()

        sensitive_fields = [
            'api_key', 'api_secret', 'private_key', 'password',
            'binance_api_key', 'binance_api_secret',
            'coinbase_api_key', 'coinbase_api_secret',
        ]

        for field in sensitive_fields:
            if field in decrypted:
                value = decrypted[field]
                if value:
                    try:
                        decrypted[field] = self.cipher.decrypt(value.encode()).decode()
                    except Exception as e:
                        logger.error(f"Failed to decrypt {field}: {e}")
                        decrypted[field] = None

        return decrypted

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get profile by ID with decrypted credentials."""
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if not profile_path.exists():
            return None

        with open(profile_path) as f:
            profile = json.load(f)

        # Decrypt credentials
        profile['config'] = self._decrypt_credentials(profile['config'])

        return profile

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles (without decrypted credentials)."""
        profiles = []

        for profile_path in self.profiles_dir.glob('*.json'):
            with open(profile_path) as f:
                profile = json.load(f)

            # Don't include credentials in list
            profiles.append({
                'id': profile['id'],
                'name': profile['name'],
                'created_at': profile['created_at'],
                'providers': list(profile['config'].get('providers', {}).keys())
            })

        return profiles

    def activate_profile(self, profile_id: str) -> bool:
        """Activate a profile for trading.

        Args:
            profile_id: Profile to activate

        Returns:
            True if successful
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return False

        self.active_profile = profile
        logger.info(f"Activated profile: {profile['name']}")
        return True

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile.

        Args:
            profile_id: Profile to delete

        Returns:
            True if successful
        """
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if not profile_path.exists():
            return False

        profile_path.unlink()
        logger.info(f"Deleted profile: {profile_id}")
        return True

    def validate_credentials(self, provider: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Validate API credentials by testing connection.

        Args:
            provider: Provider name
            credentials: Credential dict

        Returns:
            Validation result with permissions
        """
        try:
            # Create provider instance
            from ..providers import create_provider
            prov = create_provider(provider, credentials)

            # Test connection
            balance = await prov.get_balance()

            # Check permissions (simplified)
            permissions = {
                'trading': True,  # If we can query balance, trading likely works
                'withdrawal': False,  # Assume no withdrawal unless explicitly granted
                'reading': True
            }

            return {
                'valid': True,
                'permissions': permissions,
                'balance': balance
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
```

### Backend: Add profile routes to `server.py`

```python
# In TradingBotWebServer.__init__
self.profile_manager = ProfileManager()

# In _setup_routes
@self.app.route('/api/profiles', methods=['GET'])
def api_list_profiles():
    """List all profiles."""
    return jsonify(self.profile_manager.list_profiles())

@self.app.route('/api/profiles', methods=['POST'])
def api_create_profile():
    """Create new profile."""
    data = request.json or {}
    name = data.get('name')
    config = data.get('config', {})

    if not name:
        return jsonify({"error": "name required"}), 400

    try:
        profile_id = self.profile_manager.create_profile(name, config)
        return jsonify({"profile_id": profile_id, "status": "created"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@self.app.route('/api/profiles/<profile_id>', methods=['GET'])
def api_get_profile(profile_id):
    """Get profile (credentials masked)."""
    profile = self.profile_manager.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Mask credentials in response
    masked = profile.copy()
    for key in masked['config']:
        if 'key' in key or 'secret' in key or 'password' in key:
            if masked['config'][key]:
                masked['config'][key] = '•' * 16 + masked['config'][key][-4:]

    return jsonify(masked)

@self.app.route('/api/profiles/<profile_id>/activate', methods=['POST'])
def api_activate_profile(profile_id):
    """Activate a profile."""
    success = self.profile_manager.activate_profile(profile_id)
    if success:
        return jsonify({"status": "activated"})
    return jsonify({"error": "Failed to activate profile"}), 500

@self.app.route('/api/profiles/<profile_id>', methods=['DELETE'])
def api_delete_profile(profile_id):
    """Delete profile."""
    success = self.profile_manager.delete_profile(profile_id)
    if success:
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Failed to delete profile"}), 500

@self.app.route('/api/profiles/validate-credentials', methods=['POST'])
def api_validate_credentials():
    """Validate API credentials."""
    data = request.json or {}
    provider = data.get('provider')
    credentials = data.get('credentials', {})

    if not provider:
        return jsonify({"error": "provider required"}), 400

    result = self.profile_manager.validate_credentials(provider, credentials)
    return jsonify(result)
```

---

## 📋 Next Steps

1. **Install Dependencies**
   ```bash
   pip install cryptography
   ```

2. **Test WebSocket Updates**
   - Start server: `python -m src.web.server`
   - Open browser: `http://localhost:8080`
   - Create test bots and verify live updates

3. **Add Profile UI**
   - Create profile modal in `dashboard.html`
   - Add profile switcher in header
   - Implement setup wizard

4. **Security Hardening**
   - Use environment-specific master passwords
   - Add 2FA for profile access
   - Implement audit logging

---

## 🔗 Related Files

- Backend: `src/web/server.py`
- Frontend: `src/web/templates/dashboard.html`
- Styles: `src/web/static/css/dashboard.css`
- Components: `src/web/static/js/components/`

