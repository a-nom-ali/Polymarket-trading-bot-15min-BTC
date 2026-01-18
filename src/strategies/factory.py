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
from .cross_exchange_arbitrage import CrossExchangeArbitrageStrategy
from .triangular_arbitrage import TriangularArbitrageStrategy
from .funding_rate_arbitrage import FundingRateArbitrageStrategy
from .statistical_arbitrage import StatisticalArbitrageStrategy
from .basis_trading import BasisTradingStrategy
from .liquidation_sniping import LiquidationSnipingStrategy
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

    elif strategy_name_lower == "crossexchange" or strategy_name_lower == "crossexchangearbitrage":
        logger.info("💱 Creating Cross-Exchange Arbitrage strategy")

        provider_a = config.get("provider_a") or provider
        provider_b = config.get("provider_b")

        if not provider_b:
            raise ValueError(
                "Cross-exchange arbitrage requires 'provider_b' in config"
            )

        return CrossExchangeArbitrageStrategy(
            provider_a=provider_a,
            provider_b=provider_b,
            config=config
        )

    elif strategy_name_lower == "triangular" or strategy_name_lower == "triangulararbitrage":
        logger.info("🔺 Creating Triangular Arbitrage strategy")
        return TriangularArbitrageStrategy(
            provider=provider,
            config=config
        )

    elif strategy_name_lower == "fundingrate" or strategy_name_lower == "fundingratearbitrage" or strategy_name_lower == "fundingarb":
        logger.info("💎 Creating Funding Rate Arbitrage strategy")

        provider_a = config.get("provider_a") or provider
        provider_b = config.get("provider_b")

        if not provider_b:
            raise ValueError(
                "Funding rate arbitrage requires 'provider_b' in config"
            )

        return FundingRateArbitrageStrategy(
            provider_a=provider_a,
            provider_b=provider_b,
            config=config
        )

    elif strategy_name_lower == "statistical" or strategy_name_lower == "statisticalarbitrage" or strategy_name_lower == "statarb":
        logger.info("📊 Creating Statistical Arbitrage strategy")

        providers = config.get("providers")
        if not providers or len(providers) < 2:
            raise ValueError(
                "Statistical arbitrage requires 'providers' list with at least 2 providers in config"
            )

        return StatisticalArbitrageStrategy(
            providers=providers,
            config=config
        )

    elif strategy_name_lower == "basis" or strategy_name_lower == "basistrading" or strategy_name_lower == "spotfutures":
        logger.info("💰 Creating Basis Trading strategy")

        spot_provider = config.get("spot_provider") or provider
        futures_provider = config.get("futures_provider")

        if not futures_provider:
            raise ValueError(
                "Basis trading requires 'futures_provider' in config"
            )

        return BasisTradingStrategy(
            spot_provider=spot_provider,
            futures_provider=futures_provider,
            config=config
        )

    elif strategy_name_lower == "liquidation" or strategy_name_lower == "liquidationsniping" or strategy_name_lower == "liqsnipe":
        logger.info("⚡ Creating Liquidation Sniping strategy")
        logger.warning("⚠️  HIGH RISK STRATEGY - Use with caution!")
        return LiquidationSnipingStrategy(
            provider=provider,
            config=config
        )

    # Placeholder for future strategies
    elif strategy_name_lower == "copytrading":
        raise NotImplementedError(
            "Copy trading strategy not yet implemented. "
            "Coming soon!"
        )

    else:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Supported strategies: binary_arbitrage, high_probability_bond, "
            f"cross_platform, cross_exchange, triangular, funding_rate, statistical, "
            f"basis, liquidation, market_making, momentum"
        )


def get_supported_strategies() -> Dict[str, str]:
    """
    Get list of supported strategies with descriptions.

    Returns:
        Dict mapping strategy name to description
    """
    return {
        "binary_arbitrage": "Buy both sides of binary prediction market when total < $1.00 (0.5-3% ROI)",
        "high_probability_bond": "Buy near-certain outcomes (>95%) close to resolution (1-5% ROI, 1800% APY)",
        "cross_platform": "Exploit price discrepancies between Polymarket & Kalshi ($40M+ opportunity)",
        "cross_exchange": "Buy low on one exchange, sell high on another (0.3-1.5% ROI, Binance ↔ Coinbase)",
        "triangular": "Exploit pricing inefficiencies in circular paths (0.1-0.5% ROI, single exchange)",
        "funding_rate": "Earn funding rate differentials with delta-neutral positions (50-200% APY)",
        "statistical": "Trade price deviations using mean reversion across exchanges (0.5-2% ROI)",
        "basis": "Capture basis spread + funding with spot-futures arbitrage (80-200% APY)",
        "liquidation": "Snipe liquidation cascades on derivatives exchanges (2-10% ROI, HIGH RISK)",
        "market_making": "Post bid/ask spreads to capture liquidity (80-200% APY)",
        "momentum": "Follow strong price trends with momentum indicators (5-30% per trade)",
        "copy_trading": "Mirror another trader's positions (coming soon)",
    }
