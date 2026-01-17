"""
Strategy factory for instantiating trading strategies.
"""

import logging
from typing import Dict, Any

from .base import BaseStrategy
from .binary_arbitrage import BinaryArbitrageStrategy
from .high_probability_bond import HighProbabilityBondStrategy
from .cross_platform_arbitrage import CrossPlatformArbitrageStrategy
from .simple_market_making import SimpleMarketMakingStrategy
from .momentum_trading import MomentumTradingStrategy
from ..providers.base import BaseProvider

logger = logging.getLogger(__name__)


def create_strategy(
    strategy_name: str,
    provider: BaseProvider,
    config: Dict[str, Any]
) -> BaseStrategy:
    """
    Factory function to create a strategy instance.

    Args:
        strategy_name: Strategy identifier ("binary_arbitrage", "copy_trading", etc.)
        provider: Trading provider instance
        config: Strategy-specific configuration

    Returns:
        Initialized strategy instance

    Raises:
        ValueError: If strategy_name is unknown

    Examples:
        >>> from src.providers import create_provider
        >>> provider = create_provider("polymarket", {...})
        >>>
        >>> # Create binary arbitrage strategy
        >>> config = {
        ...     "target_pair_cost": 0.99,
        ...     "order_size": 50,
        ...     "yes_token_id": "...",
        ...     "no_token_id": "..."
        ... }
        >>> strategy = create_strategy("binary_arbitrage", provider, config)
    """
    strategy_name_lower = strategy_name.lower().strip().replace("_", "").replace("-", "")

    if strategy_name_lower == "binaryarbitrage":
        logger.info("🎯 Creating Binary Arbitrage strategy")

        # Extract required parameters
        yes_token_id = config.get("yes_token_id")
        no_token_id = config.get("no_token_id")

        if not yes_token_id or not no_token_id:
            raise ValueError(
                "Binary arbitrage requires 'yes_token_id' and 'no_token_id' in config"
            )

        return BinaryArbitrageStrategy(
            provider=provider,
            config=config,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id
        )

    elif strategy_name_lower == "highprobabilitybond":
        logger.info("🎯 Creating High-Probability Bond strategy")
        return HighProbabilityBondStrategy(
            provider=provider,
            config=config
        )

    elif strategy_name_lower == "crossplatform" or strategy_name_lower == "crossplatformarbitrage":
        logger.info("🎯 Creating Cross-Platform Arbitrage strategy")

        # Requires two providers
        provider_a = config.get("provider_a") or provider
        provider_b = config.get("provider_b")

        if not provider_b:
            raise ValueError(
                "Cross-platform arbitrage requires 'provider_b' in config"
            )

        return CrossPlatformArbitrageStrategy(
            provider_a=provider_a,
            provider_b=provider_b,
            config=config
        )

    elif strategy_name_lower == "marketmaking" or strategy_name_lower == "simplemarketmaking":
        logger.info("🎯 Creating Market Making strategy")

        market_pair = config.get("market_pair")
        if not market_pair:
            raise ValueError(
                "Market making requires 'market_pair' in config"
            )

        return SimpleMarketMakingStrategy(
            provider=provider,
            config=config,
            market_pair=market_pair
        )

    elif strategy_name_lower == "momentum" or strategy_name_lower == "momentumtrading":
        logger.info("🎯 Creating Momentum Trading strategy")

        market_pair = config.get("market_pair")
        if not market_pair:
            raise ValueError(
                "Momentum trading requires 'market_pair' in config"
            )

        return MomentumTradingStrategy(
            provider=provider,
            config=config,
            market_pair=market_pair
        )

    # Placeholder for future strategies
    elif strategy_name_lower == "copytrading":
        raise NotImplementedError(
            "Copy trading strategy not yet implemented. "
            "Coming soon!"
        )

    elif strategy_name_lower == "crossexchange":
        raise NotImplementedError(
            "Cross-exchange arbitrage strategy not yet implemented. "
            "Coming soon!"
        )

    elif strategy_name_lower == "triangular":
        raise NotImplementedError(
            "Triangular arbitrage strategy not yet implemented. "
            "Coming soon!"
        )

    else:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Supported strategies: binary_arbitrage, high_probability_bond, "
            f"cross_platform, market_making, momentum"
        )


def get_supported_strategies() -> Dict[str, str]:
    """
    Get list of supported strategies with descriptions.

    Returns:
        Dict mapping strategy name to description
    """
    return {
        "binary_arbitrage": "Buy both sides of binary prediction market when total < $1.00",
        "high_probability_bond": "Buy near-certain outcomes (>95%) close to resolution for 1-5% returns",
        "cross_platform": "Exploit price discrepancies between different platforms",
        "market_making": "Post bid/ask spreads to capture liquidity (80-200% APY)",
        "momentum": "Follow strong price trends with momentum indicators",
        "copy_trading": "Mirror another trader's positions (coming soon)",
        "cross_exchange": "Buy low on one exchange, sell high on another (coming soon)",
        "triangular": "Exploit pricing inefficiencies across 3+ pairs (coming soon)",
    }
