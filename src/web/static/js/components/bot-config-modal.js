// src/web/static/js/components/bot-config-modal.js

class BotConfigModal {
    constructor() {
        this.modal = null;
        this.providers = [];
        this.strategies = [];
    }

    async show(defaultProvider = '', defaultStrategy = '') {
        await this.loadOptions();
        this.render(defaultProvider, defaultStrategy);
        this.modal.style.display = 'flex';
    }

    hide() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
    }

    async loadOptions() {
        try {
            // Load providers
            const providersResponse = await fetch('/api/providers');
            const providersData = await providersResponse.json();
            this.providers = Object.entries(providersData).map(([key, value]) => ({
                id: key,
                name: key,
                description: value
            }));

            // Load strategies
            const strategiesResponse = await fetch('/api/strategies');
            const strategiesData = await strategiesResponse.json();
            this.strategies = Object.entries(strategiesData).map(([key, value]) => ({
                id: key,
                name: key,
                description: value
            }));
        } catch (error) {
            console.error('Error loading options:', error);
        }
    }

    render(defaultProvider = '', defaultStrategy = '') {
        // Remove existing modal if any
        const existing = document.getElementById('botConfigModal');
        if (existing) existing.remove();

        this.modal = document.createElement('div');
        this.modal.id = 'botConfigModal';
        this.modal.className = 'modal';
        this.modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>🤖 Create New Bot</h2>
                    <button class="modal-close" onclick="botConfigModal.hide()">×</button>
                </div>
                <div class="modal-body">
                    <form id="createBotForm" onsubmit="botConfigModal.createBot(event)">
                        <div class="form-group">
                            <label>Provider *</label>
                            <select name="provider" required>
                                <option value="">Select Provider...</option>
                                ${this.providers.map(p => `
                                    <option value="${p.id}" ${p.id === defaultProvider ? 'selected' : ''}>
                                        ${p.name} - ${p.description}
                                    </option>
                                `).join('')}
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Strategy *</label>
                            <select name="strategy" required>
                                <option value="">Select Strategy...</option>
                                ${this.strategies.map(s => `
                                    <option value="${s.id}" ${s.id === defaultStrategy ? 'selected' : ''}>
                                        ${s.name} - ${s.description}
                                    </option>
                                `).join('')}
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Trading Pair (Optional)</label>
                            <input type="text" name="pair" placeholder="e.g., BTC/USDT">
                            <small>Leave empty to use strategy defaults</small>
                        </div>

                        <div class="form-group">
                            <label>Risk Settings</label>
                            <div class="form-row">
                                <div class="form-col">
                                    <label for="maxLoss">Max Daily Loss ($)</label>
                                    <input type="number" name="max_loss" id="maxLoss" placeholder="100" step="0.01">
                                </div>
                                <div class="form-col">
                                    <label for="maxTrades">Max Trades/Day</label>
                                    <input type="number" name="max_trades" id="maxTrades" placeholder="50">
                                </div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" name="auto_start" checked>
                                Auto-start bot after creation
                            </label>
                        </div>

                        <div class="form-actions">
                            <button type="button" class="btn btn--secondary" onclick="botConfigModal.hide()">Cancel</button>
                            <button type="submit" class="btn btn--primary">Create & Start Bot</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);

        // Close on background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    }

    async createBot(event) {
        event.preventDefault();
        const formData = new FormData(event.target);

        const provider = formData.get('provider');
        const strategy = formData.get('strategy');
        const autoStart = formData.get('auto_start') === 'on';

        // Build config object
        const config = {};
        if (formData.get('pair')) config.pair = formData.get('pair');
        if (formData.get('max_loss')) config.max_daily_loss = parseFloat(formData.get('max_loss'));
        if (formData.get('max_trades')) config.max_trades_per_day = parseInt(formData.get('max_trades'));

        try {
            // Create bot
            const response = await fetch('/api/bots', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, strategy, config })
            });

            const result = await response.json();

            if (response.ok) {
                const botId = result.bot_id;
                showNotification('Bot created successfully!', 'success');

                // Auto-start if checked
                if (autoStart) {
                    const startResponse = await fetch(`/api/bots/${botId}/start`, {
                        method: 'POST'
                    });

                    if (startResponse.ok) {
                        showNotification('Bot started!', 'success');
                    }
                }

                this.hide();
            } else {
                showNotification(result.error || 'Failed to create bot', 'error');
            }
        } catch (error) {
            console.error('Error creating bot:', error);
            showNotification('Error creating bot', 'error');
        }
    }
}

// Global instance
const botConfigModal = new BotConfigModal();
