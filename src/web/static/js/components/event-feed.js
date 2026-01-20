// src/web/static/js/components/event-feed.js

class EventFeed {
    constructor(containerId) {
        this.containerId = containerId;
        this.events = [];
        this.maxEvents = 100;
        this.isPaused = false;
        this.filters = {
            info: true,
            success: true,
            warning: true,
            error: true
        };
    }

    addEvent(message, level = 'info', metadata = {}) {
        const event = {
            id: Date.now() + Math.random(),
            timestamp: new Date().toISOString(),
            message,
            level,
            metadata
        };

        this.events.unshift(event); // Add to beginning

        // Keep only max events
        if (this.events.length > this.maxEvents) {
            this.events.pop();
        }

        if (!this.isPaused) {
            this.render();
        }
    }

    render() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const filteredEvents = this.events.filter(event => this.filters[event.level]);

        if (filteredEvents.length === 0) {
            container.innerHTML = '<div class="event-feed__empty">No events yet</div>';
            return;
        }

        container.innerHTML = filteredEvents.map(event => this.renderEvent(event)).join('');

        // Auto-scroll to top if not paused
        if (!this.isPaused) {
            container.scrollTop = 0;
        }
    }

    renderEvent(event) {
        const icon = this.getIcon(event.level);
        const time = this.formatTime(event.timestamp);

        return `
            <div class="event-item event-item--${event.level}">
                <div class="event-item__icon">${icon}</div>
                <div class="event-item__content">
                    <div class="event-item__time">${time}</div>
                    <div class="event-item__message">${this.escapeHtml(event.message)}</div>
                    ${event.metadata && Object.keys(event.metadata).length > 0
                        ? `<div class="event-item__metadata">${this.renderMetadata(event.metadata)}</div>`
                        : ''
                    }
                </div>
            </div>
        `;
    }

    getIcon(level) {
        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌'
        };
        return icons[level] || 'ℹ️';
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;

        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    renderMetadata(metadata) {
        return Object.entries(metadata)
            .map(([key, value]) => `<span class="metadata-item">${key}: ${value}</span>`)
            .join(' ');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        const pauseBtn = document.querySelector('.event-feed-pause-btn');
        if (pauseBtn) {
            pauseBtn.textContent = this.isPaused ? '▶' : '⏸';
            pauseBtn.title = this.isPaused ? 'Resume' : 'Pause';
        }

        if (!this.isPaused) {
            this.render();
        }
    }

    setFilter(level, enabled) {
        this.filters[level] = enabled;
        this.render();
    }

    clear() {
        this.events = [];
        this.render();
    }

    exportEvents(format = 'json') {
        if (format === 'json') {
            const blob = new Blob([JSON.stringify(this.events, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `events_${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } else if (format === 'csv') {
            const csv = [
                ['Timestamp', 'Level', 'Message'],
                ...this.events.map(e => [e.timestamp, e.level, e.message])
            ].map(row => row.join(',')).join('\n');

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `events_${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        }
    }
}

// Note: Global instance is created in dashboard.html
// Keeping this commented to avoid conflicts
// const eventFeed = new EventFeed('eventFeedContainer');
