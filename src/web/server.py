"""
Web Dashboard Server

Flask-based web server with WebSocket support for real-time monitoring.
Provides live stats, strategy selection, and bot control.

Features:
- Real-time metrics via WebSocket
- Strategy selection and configuration
- Profile management
- Trade history visualization
- Start/stop/pause bot control
- Live order book display
- Performance analytics

Usage:
    python -m src.web.server --port 8080
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from ..providers.factory import create_provider, get_supported_providers
from ..strategies.factory import create_strategy, get_supported_strategies
from .multi_bot_manager import MultiBotManager
from .data_export import DataExporter
from .alerts import AlertManager
from ..backtesting import BacktestEngine, HistoricalDataProvider

logger = logging.getLogger(__name__)


class TradingBotWebServer:
    """Web dashboard server for trading bot."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize web server.

        Args:
            config: Server configuration
        """
        self.config = config or {}
        self.port = self.config.get("port", 8080)
        self.host = self.config.get("host", "0.0.0.0")

        # Flask app
        self.app = Flask(
            __name__,
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static")
        )

        # Enable CORS
        CORS(self.app)

        # Socket.IO for WebSocket
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading'
        )

        # Multi-bot manager
        self.bot_manager = MultiBotManager(self.config.get("bot_manager", {}))

        # Data exporter
        self.data_exporter = DataExporter(self.config.get("data_export", {}))

        # Alert manager
        self.alert_manager = AlertManager(self.config.get("alerts", {}))

        # Bot state (legacy single-bot support)
        self.bot_running = False
        self.bot_paused = False
        self.current_strategy = None
        self.current_provider = None
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "win_rate": 0.0,
            "avg_profit": 0.0,
            "uptime": 0,
            "balance": 0.0
        }
        self.recent_trades = []
        self.active_orders = []

        # Setup routes
        self._setup_routes()
        self._setup_websocket_handlers()

        logger.info(f"Web server initialized on {self.host}:{self.port}")

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html')

        @self.app.route('/api/status')
        def api_status():
            """Get bot status."""
            return jsonify({
                "running": self.bot_running,
                "paused": self.bot_paused,
                "strategy": self.current_strategy,
                "provider": self.current_provider,
                "uptime": self.stats["uptime"]
            })

        @self.app.route('/api/stats')
        def api_stats():
            """Get trading statistics."""
            return jsonify(self.stats)

        @self.app.route('/api/trades')
        def api_trades():
            """Get recent trades."""
            limit = request.args.get('limit', 50, type=int)
            return jsonify(self.recent_trades[-limit:])

        @self.app.route('/api/orders')
        def api_orders():
            """Get active orders."""
            return jsonify(self.active_orders)

        @self.app.route('/api/providers')
        def api_providers():
            """Get available providers."""
            return jsonify(get_supported_providers())

        @self.app.route('/api/strategies')
        def api_strategies():
            """Get available strategies."""
            return jsonify(get_supported_strategies())

        @self.app.route('/api/start', methods=['POST'])
        def api_start():
            """Start the bot."""
            data = request.json or {}
            strategy = data.get('strategy')
            provider = data.get('provider')
            config = data.get('config', {})

            if not strategy or not provider:
                return jsonify({"error": "strategy and provider required"}), 400

            try:
                self.current_strategy = strategy
                self.current_provider = provider
                self.bot_running = True
                self.bot_paused = False

                logger.info(f"Bot started: {strategy} on {provider}")

                # Emit WebSocket event
                self.socketio.emit('bot_started', {
                    'strategy': strategy,
                    'provider': provider,
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({"status": "started"})

            except Exception as e:
                logger.error(f"Error starting bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/stop', methods=['POST'])
        def api_stop():
            """Stop the bot."""
            try:
                self.bot_running = False
                self.bot_paused = False

                logger.info("Bot stopped")

                # Emit WebSocket event
                self.socketio.emit('bot_stopped', {
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({"status": "stopped"})

            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/pause', methods=['POST'])
        def api_pause():
            """Pause/Resume the bot."""
            try:
                self.bot_paused = not self.bot_paused

                logger.info(f"Bot {'paused' if self.bot_paused else 'resumed'}")

                # Emit WebSocket event
                self.socketio.emit('bot_paused' if self.bot_paused else 'bot_resumed', {
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({
                    "status": "paused" if self.bot_paused else "running",
                    "paused": self.bot_paused
                })

            except Exception as e:
                logger.error(f"Error pausing bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/static/<path:path>')
        def send_static(path):
            """Serve static files."""
            return send_from_directory('static', path)

        # Multi-bot management routes
        @self.app.route('/api/bots', methods=['GET'])
        def api_get_bots():
            """Get all bots."""
            return jsonify(self.bot_manager.get_all_bots())

        @self.app.route('/api/bots/running', methods=['GET'])
        def api_get_running_bots():
            """Get running bots."""
            return jsonify(self.bot_manager.get_running_bots())

        @self.app.route('/api/bots/<bot_id>', methods=['GET'])
        def api_get_bot(bot_id):
            """Get specific bot."""
            bot = self.bot_manager.get_bot(bot_id)
            if bot:
                return jsonify(bot)
            return jsonify({"error": "Bot not found"}), 404

        @self.app.route('/api/bots', methods=['POST'])
        def api_create_bot():
            """Create new bot."""
            data = request.json or {}
            strategy = data.get('strategy')
            provider = data.get('provider')
            config = data.get('config', {})

            if not strategy or not provider:
                return jsonify({"error": "strategy and provider required"}), 400

            try:
                bot_id = self.bot_manager.create_bot(strategy, provider, config)

                # Emit WebSocket event
                self.socketio.emit('bot_created', {
                    'bot_id': bot_id,
                    'strategy': strategy,
                    'provider': provider,
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({"bot_id": bot_id, "status": "created"})

            except Exception as e:
                logger.error(f"Error creating bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>/start', methods=['POST'])
        def api_start_bot(bot_id):
            """Start specific bot."""
            try:
                success = self.bot_manager.start_bot(bot_id)

                if success:
                    # Emit WebSocket event
                    self.socketio.emit('bot_started', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": "started"})
                else:
                    return jsonify({"error": "Failed to start bot"}), 500

            except Exception as e:
                logger.error(f"Error starting bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>/stop', methods=['POST'])
        def api_stop_bot(bot_id):
            """Stop specific bot."""
            try:
                success = self.bot_manager.stop_bot(bot_id)

                if success:
                    # Emit WebSocket event
                    self.socketio.emit('bot_stopped', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": "stopped"})
                else:
                    return jsonify({"error": "Failed to stop bot"}), 500

            except Exception as e:
                logger.error(f"Error stopping bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>/pause', methods=['POST'])
        def api_pause_bot(bot_id):
            """Pause/resume specific bot."""
            try:
                success = self.bot_manager.pause_bot(bot_id)

                if success:
                    bot = self.bot_manager.get_bot(bot_id)
                    is_paused = bot['status'] == 'paused'

                    # Emit WebSocket event
                    self.socketio.emit('bot_paused' if is_paused else 'bot_resumed', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": bot['status']})
                else:
                    return jsonify({"error": "Failed to pause bot"}), 500

            except Exception as e:
                logger.error(f"Error pausing bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>', methods=['DELETE'])
        def api_remove_bot(bot_id):
            """Remove specific bot."""
            try:
                success = self.bot_manager.remove_bot(bot_id)

                if success:
                    # Emit WebSocket event
                    self.socketio.emit('bot_removed', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": "removed"})
                else:
                    return jsonify({"error": "Failed to remove bot"}), 500

            except Exception as e:
                logger.error(f"Error removing bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/stats/aggregated', methods=['GET'])
        def api_get_aggregated_stats():
            """Get aggregated statistics across all bots."""
            return jsonify(self.bot_manager.get_aggregated_stats())

        # Data export routes
        @self.app.route('/api/export/trades', methods=['GET'])
        def api_export_trades():
            """Export trade history."""
            format = request.args.get('format', 'csv')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Parse dates
            start = datetime.fromisoformat(start_date) if start_date else None
            end = datetime.fromisoformat(end_date) if end_date else None

            try:
                data = self.data_exporter.export_trades(
                    self.recent_trades,
                    format=format,
                    start_date=start,
                    end_date=end
                )

                # Determine mimetype
                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                elif format == 'json':
                    mimetype = 'application/json'
                    filename = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                elif format == 'excel':
                    mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    filename = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                else:
                    return jsonify({"error": "Invalid format"}), 400

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting trades: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/export/stats', methods=['GET'])
        def api_export_stats():
            """Export performance statistics."""
            format = request.args.get('format', 'json')

            try:
                data = self.data_exporter.export_performance_metrics(
                    self.stats,
                    format=format
                )

                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                else:
                    mimetype = 'application/json'
                    filename = f'stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting stats: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/export/chart-data', methods=['GET'])
        def api_export_chart_data():
            """Export chart data."""
            format = request.args.get('format', 'csv')
            interval = request.args.get('interval', '1h')

            try:
                # Generate chart data
                chart_data = self.data_exporter.generate_profit_chart_data(
                    self.recent_trades,
                    interval=interval
                )

                # Export
                data = self.data_exporter.export_chart_data(
                    chart_data,
                    format=format
                )

                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'chart_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                else:
                    mimetype = 'application/json'
                    filename = f'chart_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting chart data: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/export/bots', methods=['GET'])
        def api_export_bots():
            """Export multi-bot summary."""
            format = request.args.get('format', 'csv')

            try:
                bots = self.bot_manager.get_all_bots()
                data = self.data_exporter.export_bot_summary(bots, format=format)

                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'bots_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                else:
                    mimetype = 'application/json'
                    filename = f'bots_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting bots: {e}")
                return jsonify({"error": str(e)}), 500

        # Backtesting routes
        @self.app.route('/api/backtest', methods=['POST'])
        def api_run_backtest():
            """Run strategy backtest."""
            data = request.json or {}
            strategy_name = data.get('strategy')
            historical_data = data.get('historical_data', [])
            config = data.get('config', {})

            if not strategy_name or not historical_data:
                return jsonify({"error": "strategy and historical_data required"}), 400

            try:
                # Parse timestamps in historical data
                for point in historical_data:
                    if isinstance(point.get('timestamp'), str):
                        point['timestamp'] = datetime.fromisoformat(point['timestamp'])

                # Get strategy class
                from ..strategies import factory
                # Create a mock provider for the strategy class lookup
                mock_provider = HistoricalDataProvider(historical_data)
                strategy_instance = create_strategy(strategy_name, mock_provider, config)
                strategy_class = type(strategy_instance)

                # Run backtest
                async def run():
                    engine = BacktestEngine(strategy_class, historical_data, config)
                    return await engine.run()

                result = asyncio.run(run())

                # Emit WebSocket event
                self.socketio.emit('backtest_completed', {
                    'strategy': strategy_name,
                    'result': result.to_dict(),
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify(result.to_dict())

            except Exception as e:
                logger.error(f"Error running backtest: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/backtest/optimize', methods=['POST'])
        def api_optimize_parameters():
            """Optimize strategy parameters."""
            data = request.json or {}
            strategy_name = data.get('strategy')
            historical_data = data.get('historical_data', [])
            param_grid = data.get('param_grid', {})
            metric = data.get('metric', 'sharpe_ratio')

            if not strategy_name or not historical_data or not param_grid:
                return jsonify({"error": "strategy, historical_data, and param_grid required"}), 400

            try:
                # Parse timestamps
                for point in historical_data:
                    if isinstance(point.get('timestamp'), str):
                        point['timestamp'] = datetime.fromisoformat(point['timestamp'])

                # Get strategy class
                mock_provider = HistoricalDataProvider(historical_data)
                strategy_instance = create_strategy(strategy_name, mock_provider, {})
                strategy_class = type(strategy_instance)

                # Run optimization
                from ..backtesting.engine import ParameterOptimizer

                async def run():
                    optimizer = ParameterOptimizer(strategy_class, historical_data)
                    return await optimizer.optimize(param_grid, metric)

                result = asyncio.run(run())

                return jsonify({
                    'best_params': result['best_params'],
                    'best_score': result['best_score'],
                    'result': result['best_result'].to_dict()
                })

            except Exception as e:
                logger.error(f"Error optimizing parameters: {e}")
                return jsonify({"error": str(e)}), 500

        # Alert routes
        @self.app.route('/api/alerts/config', methods=['GET'])
        def api_get_alert_config():
            """Get alert configuration."""
            return jsonify({
                'email_enabled': self.alert_manager.email_enabled,
                'sms_enabled': self.alert_manager.sms_enabled,
                'alert_on_trade': self.alert_manager.alert_on_trade,
                'alert_on_error': self.alert_manager.alert_on_error,
                'alert_on_profit_threshold': self.alert_manager.alert_on_profit_threshold,
                'alert_on_loss_threshold': self.alert_manager.alert_on_loss_threshold,
                'max_alerts_per_hour': self.alert_manager.max_alerts_per_hour
            })

        @self.app.route('/api/alerts/config', methods=['POST'])
        def api_update_alert_config():
            """Update alert configuration."""
            data = request.json or {}

            try:
                if 'alert_on_trade' in data:
                    self.alert_manager.alert_on_trade = data['alert_on_trade']
                if 'alert_on_error' in data:
                    self.alert_manager.alert_on_error = data['alert_on_error']
                if 'alert_on_profit_threshold' in data:
                    self.alert_manager.alert_on_profit_threshold = float(data['alert_on_profit_threshold'])
                if 'alert_on_loss_threshold' in data:
                    self.alert_manager.alert_on_loss_threshold = float(data['alert_on_loss_threshold'])

                return jsonify({"status": "updated"})

            except Exception as e:
                logger.error(f"Error updating alert config: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/alerts/test', methods=['POST'])
        def api_test_alert():
            """Send test alert."""
            data = request.json or {}
            message = data.get('message', 'Test alert from trading bot')

            try:
                success = self.alert_manager.send_custom_alert(
                    'Test Alert',
                    message,
                    level='info'
                )

                if success:
                    return jsonify({"status": "sent"})
                else:
                    return jsonify({"error": "Failed to send alert"}), 500

            except Exception as e:
                logger.error(f"Error sending test alert: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/alerts/history', methods=['GET'])
        def api_get_alert_history():
            """Get alert history."""
            limit = request.args.get('limit', 100, type=int)

            try:
                history = self.alert_manager.get_alert_history(limit)

                # Convert datetime to ISO format
                for alert in history:
                    if 'timestamp' in alert:
                        alert['timestamp'] = alert['timestamp'].isoformat()

                return jsonify(history)

            except Exception as e:
                logger.error(f"Error getting alert history: {e}")
                return jsonify({"error": str(e)}), 500

    def _setup_websocket_handlers(self):
        """Setup WebSocket event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {
                'message': 'Connected to trading bot',
                'timestamp': datetime.now().isoformat()
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")

        @self.socketio.on('request_stats')
        def handle_request_stats():
            """Send current stats to client."""
            emit('stats_update', self.stats)

        @self.socketio.on('request_trades')
        def handle_request_trades(data=None):
            """Send recent trades to client."""
            limit = data.get('limit', 50) if data else 50
            emit('trades_update', self.recent_trades[-limit:])

    def update_stats(self, stats: Dict[str, Any]):
        """
        Update statistics and broadcast to clients.

        Args:
            stats: Updated statistics
        """
        self.stats.update(stats)

        # Broadcast to all connected clients
        self.socketio.emit('stats_update', self.stats)

    def add_trade(self, trade: Dict[str, Any]):
        """
        Add a trade and broadcast to clients.

        Args:
            trade: Trade information
        """
        trade['timestamp'] = datetime.now().isoformat()
        self.recent_trades.append(trade)

        # Keep only last 1000 trades
        if len(self.recent_trades) > 1000:
            self.recent_trades = self.recent_trades[-1000:]

        # Broadcast to all connected clients
        self.socketio.emit('trade_executed', trade)
        self.socketio.emit('trades_update', self.recent_trades[-50:])

    def update_orders(self, orders: list):
        """
        Update active orders and broadcast to clients.

        Args:
            orders: List of active orders
        """
        self.active_orders = orders

        # Broadcast to all connected clients
        self.socketio.emit('orders_update', self.active_orders)

    def send_notification(self, message: str, level: str = "info"):
        """
        Send notification to clients.

        Args:
            message: Notification message
            level: Notification level (info, warning, error, success)
        """
        self.socketio.emit('notification', {
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat()
        })

    def run(self):
        """Start the web server."""
        logger.info(f"Starting web server on {self.host}:{self.port}")
        self.socketio.run(
            self.app,
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False
        )


def create_web_server(config: Optional[Dict[str, Any]] = None) -> TradingBotWebServer:
    """
    Create and return web server instance.

    Args:
        config: Server configuration

    Returns:
        TradingBotWebServer instance
    """
    return TradingBotWebServer(config)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trading Bot Web Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = create_web_server({
        "port": args.port,
        "host": args.host
    })

    server.run()
