"""
Multi-Bot Management System

Manages multiple trading bot instances running different strategies simultaneously.
Each bot can use different strategies, providers, and configurations.

Features:
- Run multiple strategies in parallel
- Individual bot control (start/stop/pause per bot)
- Aggregated and per-bot statistics
- Resource management and limits
- Bot health monitoring
- Auto-restart on failures

Usage:
    from src.web.multi_bot_manager import MultiBotManager

    manager = MultiBotManager(config)
    bot_id = manager.create_bot("cross_exchange", "binance", {...})
    manager.start_bot(bot_id)
"""

import logging
import asyncio
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from ..providers.factory import create_provider
from ..strategies.factory import create_strategy

logger = logging.getLogger(__name__)


class BotStatus(Enum):
    """Bot status enumeration."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BotInstance:
    """Single bot instance."""

    def __init__(self, bot_id: str, strategy_name: str, provider_name: str, config: Dict[str, Any]):
        """
        Initialize bot instance.

        Args:
            bot_id: Unique bot identifier
            strategy_name: Strategy to use
            provider_name: Provider to use
            config: Bot configuration
        """
        self.bot_id = bot_id
        self.strategy_name = strategy_name
        self.provider_name = provider_name
        self.config = config

        # State
        self.status = BotStatus.CREATED
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None

        # Runtime objects
        self.provider = None
        self.strategy = None
        self.task: Optional[asyncio.Task] = None
        self.thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        # Statistics
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "win_rate": 0.0,
            "avg_profit": 0.0,
            "uptime": 0,
            "last_trade_time": None,
            "error_count": 0,
            "last_error": None
        }

        # Health monitoring
        self.last_heartbeat = datetime.now()
        self.restart_count = 0
        self.max_restarts = config.get("max_restarts", 3)

        logger.info(f"Bot instance created: {bot_id} ({strategy_name} on {provider_name})")

    def get_info(self) -> Dict[str, Any]:
        """Get bot information."""
        return {
            "bot_id": self.bot_id,
            "strategy": self.strategy_name,
            "provider": self.provider_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "uptime": self._calculate_uptime(),
            "stats": self.stats,
            "restart_count": self.restart_count
        }

    def _calculate_uptime(self) -> int:
        """Calculate uptime in seconds."""
        if not self.started_at:
            return 0
        if self.stopped_at and self.stopped_at > self.started_at:
            return int((self.stopped_at - self.started_at).total_seconds())
        if self.status in [BotStatus.RUNNING, BotStatus.PAUSED]:
            return int((datetime.now() - self.started_at).total_seconds())
        return 0

    def update_stats(self, stats: Dict[str, Any]):
        """Update bot statistics."""
        self.stats.update(stats)
        self.last_heartbeat = datetime.now()


class MultiBotManager:
    """Manage multiple trading bot instances."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize multi-bot manager.

        Args:
            config: Manager configuration
        """
        self.config = config or {}
        self.bots: Dict[str, BotInstance] = {}

        # Limits
        self.max_bots = self.config.get("max_bots", 10)
        self.max_bots_per_provider = self.config.get("max_bots_per_provider", 3)

        # Monitoring
        self.monitoring_enabled = self.config.get("monitoring_enabled", True)
        self.monitoring_interval = self.config.get("monitoring_interval", 30)
        self.monitoring_task: Optional[asyncio.Task] = None

        # Aggregated stats
        self.aggregated_stats = {
            "total_bots": 0,
            "running_bots": 0,
            "total_trades": 0,
            "total_profit": 0.0,
            "win_rate": 0.0
        }

        logger.info(f"Multi-bot manager initialized (max bots: {self.max_bots})")

    def create_bot(self, strategy: str, provider: str, config: Dict[str, Any]) -> str:
        """
        Create a new bot instance.

        Args:
            strategy: Strategy name
            provider: Provider name
            config: Bot configuration

        Returns:
            Bot ID

        Raises:
            ValueError: If limits exceeded or invalid configuration
        """
        # Check limits
        if len(self.bots) >= self.max_bots:
            raise ValueError(f"Maximum number of bots ({self.max_bots}) reached")

        # Count bots using this provider
        provider_count = sum(1 for bot in self.bots.values() if bot.provider_name == provider)
        if provider_count >= self.max_bots_per_provider:
            raise ValueError(f"Maximum bots per provider ({self.max_bots_per_provider}) reached for {provider}")

        # Generate unique ID
        bot_id = str(uuid.uuid4())[:8]

        # Create bot instance
        bot = BotInstance(bot_id, strategy, provider, config)
        self.bots[bot_id] = bot

        # Update aggregated stats
        self._update_aggregated_stats()

        logger.info(f"Created bot {bot_id}: {strategy} on {provider}")
        return bot_id

    def start_bot(self, bot_id: str) -> bool:
        """
        Start a bot.

        Args:
            bot_id: Bot identifier

        Returns:
            True if started successfully

        Raises:
            ValueError: If bot not found or already running
        """
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")

        bot = self.bots[bot_id]

        if bot.status in [BotStatus.RUNNING, BotStatus.STARTING]:
            raise ValueError(f"Bot {bot_id} is already running")

        try:
            bot.status = BotStatus.STARTING
            bot.started_at = datetime.now()

            # Create provider and strategy in new thread with event loop
            def run_bot():
                """Run bot in dedicated thread."""
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    bot.loop = loop

                    # Initialize provider and strategy
                    bot.provider = create_provider(bot.provider_name, bot.config)
                    bot.strategy = create_strategy(bot.strategy_name, bot.provider, bot.config)

                    # Start strategy
                    bot.status = BotStatus.RUNNING
                    logger.info(f"Bot {bot_id} started")

                    # Run strategy (blocking)
                    loop.run_until_complete(bot.strategy.start())

                except Exception as e:
                    logger.error(f"Error running bot {bot_id}: {e}")
                    bot.status = BotStatus.ERROR
                    bot.stats["error_count"] += 1
                    bot.stats["last_error"] = str(e)

                    # Auto-restart if enabled
                    if bot.restart_count < bot.max_restarts:
                        logger.info(f"Auto-restarting bot {bot_id} (attempt {bot.restart_count + 1}/{bot.max_restarts})")
                        bot.restart_count += 1
                        self.start_bot(bot_id)

                finally:
                    if bot.loop:
                        bot.loop.close()

            # Start thread
            bot.thread = threading.Thread(target=run_bot, daemon=True)
            bot.thread.start()

            return True

        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {e}")
            bot.status = BotStatus.ERROR
            bot.stats["last_error"] = str(e)
            return False

    def stop_bot(self, bot_id: str) -> bool:
        """
        Stop a bot.

        Args:
            bot_id: Bot identifier

        Returns:
            True if stopped successfully
        """
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")

        bot = self.bots[bot_id]

        if bot.status not in [BotStatus.RUNNING, BotStatus.PAUSED]:
            logger.warning(f"Bot {bot_id} is not running (status: {bot.status.value})")
            return False

        try:
            bot.status = BotStatus.STOPPING
            bot.stopped_at = datetime.now()

            # Stop strategy
            if bot.strategy:
                asyncio.run_coroutine_threadsafe(bot.strategy.stop(), bot.loop)

            # Update status
            bot.status = BotStatus.STOPPED

            logger.info(f"Bot {bot_id} stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {e}")
            return False

    def pause_bot(self, bot_id: str) -> bool:
        """
        Pause a bot.

        Args:
            bot_id: Bot identifier

        Returns:
            True if paused successfully
        """
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")

        bot = self.bots[bot_id]

        if bot.status == BotStatus.RUNNING:
            bot.status = BotStatus.PAUSED
            logger.info(f"Bot {bot_id} paused")
            return True
        elif bot.status == BotStatus.PAUSED:
            bot.status = BotStatus.RUNNING
            logger.info(f"Bot {bot_id} resumed")
            return True
        else:
            logger.warning(f"Cannot pause bot {bot_id} (status: {bot.status.value})")
            return False

    def remove_bot(self, bot_id: str) -> bool:
        """
        Remove a bot.

        Args:
            bot_id: Bot identifier

        Returns:
            True if removed successfully
        """
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")

        # Stop if running
        bot = self.bots[bot_id]
        if bot.status in [BotStatus.RUNNING, BotStatus.PAUSED]:
            self.stop_bot(bot_id)

        # Remove
        del self.bots[bot_id]
        self._update_aggregated_stats()

        logger.info(f"Bot {bot_id} removed")
        return True

    def get_bot(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get bot information."""
        if bot_id not in self.bots:
            return None
        return self.bots[bot_id].get_info()

    def get_all_bots(self) -> List[Dict[str, Any]]:
        """Get information for all bots."""
        return [bot.get_info() for bot in self.bots.values()]

    def get_running_bots(self) -> List[Dict[str, Any]]:
        """Get information for running bots."""
        return [
            bot.get_info()
            for bot in self.bots.values()
            if bot.status in [BotStatus.RUNNING, BotStatus.PAUSED]
        ]

    def update_bot_stats(self, bot_id: str, stats: Dict[str, Any]) -> bool:
        """
        Update bot statistics.

        Args:
            bot_id: Bot identifier
            stats: Updated statistics

        Returns:
            True if updated successfully
        """
        if bot_id not in self.bots:
            return False

        self.bots[bot_id].update_stats(stats)
        self._update_aggregated_stats()
        return True

    def get_aggregated_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics across all bots."""
        return self.aggregated_stats.copy()

    def _update_aggregated_stats(self):
        """Update aggregated statistics."""
        self.aggregated_stats = {
            "total_bots": len(self.bots),
            "running_bots": sum(1 for bot in self.bots.values() if bot.status == BotStatus.RUNNING),
            "paused_bots": sum(1 for bot in self.bots.values() if bot.status == BotStatus.PAUSED),
            "stopped_bots": sum(1 for bot in self.bots.values() if bot.status == BotStatus.STOPPED),
            "error_bots": sum(1 for bot in self.bots.values() if bot.status == BotStatus.ERROR),
            "total_trades": sum(bot.stats["total_trades"] for bot in self.bots.values()),
            "total_profit": sum(bot.stats["total_profit"] for bot in self.bots.values()),
            "total_loss": sum(bot.stats["total_loss"] for bot in self.bots.values()),
            "total_uptime": sum(bot._calculate_uptime() for bot in self.bots.values())
        }

        # Calculate aggregated win rate
        total_trades = self.aggregated_stats["total_trades"]
        if total_trades > 0:
            winning_trades = sum(bot.stats["winning_trades"] for bot in self.bots.values())
            self.aggregated_stats["win_rate"] = (winning_trades / total_trades) * 100
        else:
            self.aggregated_stats["win_rate"] = 0.0

    async def _monitor_bots(self):
        """Monitor bot health."""
        while self.monitoring_enabled:
            try:
                # Check each bot
                for bot_id, bot in self.bots.items():
                    # Check heartbeat
                    if bot.status == BotStatus.RUNNING:
                        time_since_heartbeat = (datetime.now() - bot.last_heartbeat).total_seconds()

                        # If no heartbeat for 5 minutes, mark as error
                        if time_since_heartbeat > 300:
                            logger.warning(f"Bot {bot_id} heartbeat timeout ({time_since_heartbeat:.0f}s)")
                            bot.status = BotStatus.ERROR
                            bot.stats["last_error"] = "Heartbeat timeout"

                # Update aggregated stats
                self._update_aggregated_stats()

                # Wait before next check
                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in bot monitoring: {e}")
                await asyncio.sleep(self.monitoring_interval)

    def start_monitoring(self):
        """Start bot health monitoring."""
        if self.monitoring_enabled and not self.monitoring_task:
            self.monitoring_task = asyncio.create_task(self._monitor_bots())
            logger.info("Bot monitoring started")

    def stop_monitoring(self):
        """Stop bot health monitoring."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
            logger.info("Bot monitoring stopped")
