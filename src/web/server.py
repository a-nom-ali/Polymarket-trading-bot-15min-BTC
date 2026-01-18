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

        # Bot state
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
        def handle_request_trades(data):
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
