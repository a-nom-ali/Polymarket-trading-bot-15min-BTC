"""
Web Dashboard Module

Flask-based web interface for trading bot with real-time WebSocket updates.
"""

from .server import TradingBotWebServer, create_web_server
from .multi_bot_manager import MultiBotManager, BotInstance, BotStatus
from .data_export import DataExporter, create_data_exporter

__all__ = [
    'TradingBotWebServer',
    'create_web_server',
    'MultiBotManager',
    'BotInstance',
    'BotStatus',
    'DataExporter',
    'create_data_exporter'
]
