"""
Utility functions for the arbitrage bot.
"""

import signal
import sys
import re
import decimal
import time
import logging
from typing import Callable, Optional, Union, Dict, Any
from decimal import Decimal
from collections import deque

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Handles graceful shutdown on SIGINT/SIGTERM signals."""
    
    def __init__(self):
        self.shutdown_requested = False
        self.shutdown_callbacks: list[Callable] = []
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        if not self.shutdown_requested:
            self.shutdown_requested = True
            print("\n🛑 Shutdown requested. Finishing current operations...")
            # Run shutdown callbacks
            for callback in self.shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in shutdown callback: {e}")
        else:
            # Force exit on second signal
            print("\n⚠️ Force exit requested.")
            sys.exit(1)
    
    def register_callback(self, callback: Callable):
        """Register a callback to run on shutdown."""
        self.shutdown_callbacks.append(callback)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested


# ============================================================================
# Security & Validation Utilities
# ============================================================================

def mask_credential(credential: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive credentials for safe logging.

    Args:
        credential: The credential to mask
        visible_chars: Number of characters to show at the start

    Returns:
        Masked string showing only first N characters

    Example:
        >>> mask_credential("abc123xyz789", 4)
        'abc1***'
    """
    if not credential or len(credential) <= visible_chars:
        return "***"
    return credential[:visible_chars] + "***"


def validate_ethereum_address(address: str) -> bool:
    """
    Validate Ethereum address format.

    Args:
        address: The address to validate

    Returns:
        True if valid format, False otherwise
    """
    if not address:
        return False
    # Basic validation: starts with 0x, followed by 40 hex characters
    pattern = r'^0x[a-fA-F0-9]{40}$'
    return bool(re.match(pattern, address))


def validate_order_id(order_id: str) -> bool:
    """
    Validate order ID format.

    Args:
        order_id: The order ID to validate

    Returns:
        True if valid format, False otherwise
    """
    if not order_id:
        return False
    # Order IDs should be non-empty strings with reasonable length
    return len(order_id) > 0 and len(order_id) < 256


def validate_market_slug(slug: str) -> bool:
    """
    Validate market slug format.

    Args:
        slug: The market slug to validate

    Returns:
        True if valid format, False otherwise
    """
    if not slug:
        return False
    # Slugs should contain alphanumeric characters, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, slug)) and len(slug) < 256


def safe_float_conversion(value: Union[str, int, float], default: float = 0.0) -> float:
    """
    Safely convert a value to float with error handling.

    Args:
        value: The value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default if conversion fails
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_decimal_conversion(value: Union[str, int, float], default: str = "0.0") -> Decimal:
    """
    Safely convert a value to Decimal for precise financial calculations.

    Args:
        value: The value to convert
        default: Default value if conversion fails

    Returns:
        Decimal value or default if conversion fails
    """
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return Decimal(default)


# ============================================================================
# Numeric Precision Constants
# ============================================================================

# Epsilon for order size comparisons (0.000000001 shares)
EPSILON_SIZE = 1e-9

# Epsilon for price comparisons (0.0001 = $0.0001)
EPSILON_PRICE = 1e-4

# Epsilon for balance comparisons (0.01 = $0.01)
EPSILON_BALANCE = 1e-2


def is_approximately_equal(a: float, b: float, epsilon: float = EPSILON_PRICE) -> bool:
    """
    Check if two floats are approximately equal within epsilon tolerance.

    Args:
        a: First value
        b: Second value
        epsilon: Tolerance for comparison

    Returns:
        True if values are within epsilon of each other
    """
    return abs(a - b) < epsilon


# ============================================================================
# API Response Validation
# ============================================================================

class APIResponseError(Exception):
    """Raised when API response validation fails."""
    pass


def validate_order_book_response(data: Any, token_id: str) -> Dict[str, Any]:
    """
    Validate and parse order book response from API.

    Args:
        data: Raw API response
        token_id: Expected token ID

    Returns:
        Validated order book data

    Raises:
        APIResponseError: If response is invalid
    """
    if not isinstance(data, dict):
        logger.error(f"Invalid order book response type: {type(data)}, data: {data}")
        raise APIResponseError(f"Expected dict response, got {type(data)}")

    # Check for required fields
    if 'asset_id' not in data and 'market' not in data:
        logger.error(f"Missing asset_id/market in response: {data}")
        raise APIResponseError("Missing asset_id or market field in order book response")

    # Validate bids and asks
    bids = data.get('bids', [])
    asks = data.get('asks', [])

    if not isinstance(bids, list) or not isinstance(asks, list):
        logger.error(f"Invalid bids/asks format: bids={type(bids)}, asks={type(asks)}")
        raise APIResponseError("Bids and asks must be lists")

    return data


def extract_price_from_level(level: Any, default: float = 0.0) -> float:
    """
    Safely extract price from order book level with validation.

    Args:
        level: Order book level (dict or tuple)
        default: Default value if extraction fails

    Returns:
        Price as float
    """
    try:
        if isinstance(level, dict):
            price = level.get('price')
            return safe_float_conversion(price, default)
        elif isinstance(level, (list, tuple)) and len(level) >= 2:
            return safe_float_conversion(level[0], default)
        else:
            logger.warning(f"Unexpected level format: {type(level)}, value: {level}")
            return default
    except Exception as e:
        logger.error(f"Error extracting price from level: {e}, level: {level}")
        return default


def extract_size_from_level(level: Any, default: float = 0.0) -> float:
    """
    Safely extract size from order book level with validation.

    Args:
        level: Order book level (dict or tuple)
        default: Default value if extraction fails

    Returns:
        Size as float
    """
    try:
        if isinstance(level, dict):
            size = level.get('size')
            return safe_float_conversion(size, default)
        elif isinstance(level, (list, tuple)) and len(level) >= 2:
            return safe_float_conversion(level[1], default)
        else:
            logger.warning(f"Unexpected level format: {type(level)}, value: {level}")
            return default
    except Exception as e:
        logger.error(f"Error extracting size from level: {e}, level: {level}")
        return default


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for API requests.

    Example:
        limiter = RateLimiter(max_requests=10, time_window=1.0)
        if limiter.allow_request():
            # Make API call
            pass
    """

    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times: deque = deque()

    def allow_request(self) -> bool:
        """
        Check if a request is allowed under rate limit.

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()

        # Remove requests outside the time window
        while self.request_times and self.request_times[0] < now - self.time_window:
            self.request_times.popleft()

        # Check if we're at the limit
        if len(self.request_times) >= self.max_requests:
            return False

        # Record this request
        self.request_times.append(now)
        return True

    def wait_if_needed(self) -> None:
        """
        Wait until a request is allowed (blocking).
        """
        while not self.allow_request():
            time.sleep(0.1)  # Wait 100ms before retrying

    def reset(self) -> None:
        """Reset the rate limiter."""
        self.request_times.clear()

    def get_current_rate(self) -> float:
        """
        Get current request rate (requests per second).

        Returns:
            Current rate in requests/second
        """
        now = time.time()
        # Remove old requests
        while self.request_times and self.request_times[0] < now - self.time_window:
            self.request_times.popleft()

        return len(self.request_times) / self.time_window if self.time_window > 0 else 0.0


# ============================================================================
# Balance Caching with TTL
# ============================================================================

class BalanceCache:
    """
    Cache for account balance with time-to-live (TTL) and error handling.

    Example:
        cache = BalanceCache(ttl=60.0)
        balance = cache.get_or_fetch(fetch_function)
    """

    def __init__(self, ttl: float = 60.0):
        """
        Initialize balance cache.

        Args:
            ttl: Time-to-live in seconds (default 60 seconds)
        """
        self.ttl = ttl
        self._balance: Optional[float] = None
        self._timestamp: Optional[float] = None
        self._fetch_failures = 0

    def get(self) -> Optional[float]:
        """
        Get cached balance if still valid.

        Returns:
            Cached balance or None if expired/invalid
        """
        if self._balance is None or self._timestamp is None:
            return None

        age = time.time() - self._timestamp
        if age > self.ttl:
            logger.debug(f"Balance cache expired (age: {age:.1f}s > ttl: {self.ttl}s)")
            return None

        return self._balance

    def set(self, balance: float) -> None:
        """
        Set cached balance with current timestamp.

        Args:
            balance: Balance value to cache
        """
        self._balance = balance
        self._timestamp = time.time()
        self._fetch_failures = 0
        logger.debug(f"Balance cached: ${balance:.2f}")

    def invalidate(self) -> None:
        """Invalidate the cached balance."""
        logger.debug("Balance cache invalidated")
        self._balance = None
        self._timestamp = None

    def get_or_fetch(self, fetch_func: Callable[[], float]) -> float:
        """
        Get cached balance or fetch new one if expired.

        Args:
            fetch_func: Function to fetch balance (should return float)

        Returns:
            Current balance

        Note:
            On fetch failure, returns cached value if available, otherwise 0.0
        """
        cached = self.get()
        if cached is not None:
            return cached

        try:
            balance = fetch_func()
            if balance < 0:
                logger.warning(f"Negative balance returned: {balance}, using 0.0")
                balance = 0.0

            self.set(balance)
            return balance

        except Exception as e:
            self._fetch_failures += 1
            logger.error(f"Failed to fetch balance (attempt {self._fetch_failures}): {e}")

            # Return stale cached value if available
            if self._balance is not None:
                logger.warning(f"Using stale cached balance: ${self._balance:.2f}")
                return self._balance

            # No cache available, return 0
            logger.error("No cached balance available, returning 0.0")
            return 0.0

    def is_valid(self) -> bool:
        """
        Check if cache has valid data.

        Returns:
            True if cache is valid and not expired
        """
        return self.get() is not None

    def get_age(self) -> Optional[float]:
        """
        Get age of cached data in seconds.

        Returns:
            Age in seconds or None if no cached data
        """
        if self._timestamp is None:
            return None
        return time.time() - self._timestamp

