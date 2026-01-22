"""
Domain Adapters

This package contains adapter implementations that bridge the generic
abstraction layer with specific domains (trading, GPU, ads, ecommerce).
"""

from .trading import TradingVenueAdapter, FinancialAssetAdapter
from .compute import ComputeMarketplaceAdapter, GPUAssetAdapter
from .advertising import AdPlatformAdapter, AdInventoryAdapter
from .ecommerce import EcommerceMarketplaceAdapter, ProductSKUAdapter

__all__ = [
    'TradingVenueAdapter',
    'FinancialAssetAdapter',
    'ComputeMarketplaceAdapter',
    'GPUAssetAdapter',
    'AdPlatformAdapter',
    'AdInventoryAdapter',
    'EcommerceMarketplaceAdapter',
    'ProductSKUAdapter',
]
