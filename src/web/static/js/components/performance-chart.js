// src/web/static/js/components/performance-chart.js

class PerformanceChart {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chart = null;
        this.timeframe = '1H';
        this.data = {
            '1H': [],
            '4H': [],
            '24H': [],
            '7D': [],
            '30D': []
        };
        this.refreshInterval = null;
    }

    init() {
        const ctx = document.getElementById(this.canvasId);
        if (!ctx) return;

        this.chart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Cumulative Profit',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary')
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#f1f5f9',
                        bodyColor: '#e2e8f0',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return `Profit: $${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-tertiary'),
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        },
                        grid: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--border-color')
                        }
                    },
                    x: {
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-tertiary'),
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 8
                        },
                        grid: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--border-color')
                        }
                    }
                }
            }
        });

        this.startAutoRefresh();
    }

    setTimeframe(timeframe) {
        this.timeframe = timeframe;
        this.updateChart();

        // Update active button
        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-timeframe="${timeframe}"]`)?.classList.add('active');
    }

    addDataPoint(timestamp, profit) {
        const timeframes = ['1H', '4H', '24H', '7D', '30D'];

        timeframes.forEach(tf => {
            this.data[tf].push({ timestamp, profit });

            // Keep only relevant data based on timeframe
            const maxPoints = {
                '1H': 60,
                '4H': 240,
                '24H': 1440,
                '7D': 10080,
                '30D': 43200
            };

            if (this.data[tf].length > maxPoints[tf]) {
                this.data[tf].shift();
            }
        });

        if (this.chart) {
            this.updateChart();
        }
    }

    updateChart() {
        if (!this.chart) return;

        const currentData = this.data[this.timeframe] || [];

        // Calculate cumulative profit
        let cumulative = 0;
        const labels = [];
        const values = [];

        currentData.forEach(point => {
            cumulative += point.profit;
            labels.push(this.formatTimestamp(point.timestamp, this.timeframe));
            values.push(cumulative);
        });

        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = values;

        // Update color based on final value
        const finalValue = values[values.length - 1] || 0;
        this.chart.data.datasets[0].borderColor = finalValue >= 0 ? '#10b981' : '#ef4444';
        this.chart.data.datasets[0].backgroundColor = finalValue >= 0
            ? 'rgba(16, 185, 129, 0.1)'
            : 'rgba(239, 68, 68, 0.1)';

        this.chart.update('none'); // Update without animation
    }

    formatTimestamp(timestamp, timeframe) {
        const date = new Date(timestamp);

        switch(timeframe) {
            case '1H':
            case '4H':
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            case '24H':
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            case '7D':
                return date.toLocaleDateString('en-US', { weekday: 'short', hour: '2-digit' });
            case '30D':
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            default:
                return date.toLocaleString();
        }
    }

    startAutoRefresh() {
        // Auto-refresh based on timeframe
        const refreshRates = {
            '1H': 1000,   // 1 second
            '4H': 5000,   // 5 seconds
            '24H': 60000, // 1 minute
            '7D': 300000, // 5 minutes
            '30D': 300000 // 5 minutes
        };

        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.refreshInterval = setInterval(() => {
            this.updateChart();
        }, refreshRates[this.timeframe] || 5000);
    }

    updateTheme() {
        if (!this.chart) return;

        // Update chart colors based on theme
        const textTertiary = getComputedStyle(document.documentElement).getPropertyValue('--text-tertiary');
        const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--border-color');
        const textSecondary = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary');

        this.chart.options.scales.y.ticks.color = textTertiary;
        this.chart.options.scales.y.grid.color = borderColor;
        this.chart.options.scales.x.ticks.color = textTertiary;
        this.chart.options.scales.x.grid.color = borderColor;
        this.chart.options.plugins.legend.labels.color = textSecondary;

        this.chart.update();
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// Note: Global instance is created in dashboard.html
// Keeping this commented to avoid conflicts
// let performanceChart = null;
