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
                <h3>Bot #${this.bot.id.slice(-4)} - ${this.bot.strategy_name || 'Unknown'}</h3>
                <p class="bot-card__subtitle">${this.bot.provider_name || 'N/A'} | ${this.bot.pair || 'N/A'}</p>
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
        const canvas = document.getElementById(`sparkline-${this.bot.id}`);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const sparklineData = this.bot.sparkline || [];

        // Only render if Chart.js is available
        if (typeof Chart !== 'undefined') {
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
    }

    renderHealthIndicators() {
        const health = this.bot.health || {};
        const indicators = [
            { key: 'api_connected', label: 'API', icon: '📡' },
            { key: 'balance_sufficient', label: 'Balance', icon: '💰' },
            { key: 'error_rate', label: 'Errors', icon: '⚠️' }
        ];

        return indicators.map(ind => {
            const isOk = health[ind.key] === true || (ind.key === 'error_rate' && health[ind.key] < 0.05);
            return `
                <div class="health-indicator ${isOk ? 'health-indicator--ok' : 'health-indicator--warning'}">
                    <span class="health-indicator__icon">${ind.icon}</span>
                    <span class="health-indicator__label">${ind.label}</span>
                </div>
            `;
        }).join('');
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
        this.updateActivity();
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

        // Update trades count
        const tradesEl = card.querySelectorAll('.metric__value')[1];
        if (tradesEl) {
            tradesEl.textContent = this.bot.trades_count || 0;
        }

        // Update win rate
        const winRateEl = card.querySelectorAll('.metric__value')[2];
        if (winRateEl) {
            winRateEl.textContent = `${this.formatPercent(this.bot.win_rate || 0)}%`;
        }
    }

    updateSparkline() {
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
        if (healthContainer) {
            healthContainer.innerHTML = this.renderHealthIndicators();
        }
    }

    updateActivity() {
        const card = document.querySelector(`[data-bot-id="${this.bot.id}"]`);
        if (!card) return;

        const activityEl = card.querySelector('.activity-text');
        if (activityEl) {
            activityEl.textContent = `Last: ${this.formatLastActivity()}`;
        }
    }
}
