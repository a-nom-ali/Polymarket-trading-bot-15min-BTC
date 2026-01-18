"""
Web Dashboard Module

Flask-based web interface for trading bot with real-time WebSocket updates.
"""

from .server import TradingBotWebServer, create_web_server

__all__ = ['TradingBotWebServer', 'create_web_server']
