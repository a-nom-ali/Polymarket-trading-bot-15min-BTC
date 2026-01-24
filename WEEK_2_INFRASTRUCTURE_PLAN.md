# Week 2: Infrastructure Hardening (Revised)

**Date**: 2026-01-24
**Status**: Ready to Start
**Priority**: 🔴 CRITICAL - Foundation for production readiness

---

## Overview

Week 2 pivots from WebSocket UI to **infrastructure hardening** based on pain points analysis. Focus on production-ready backend systems with abstraction layers for easy local/hosted swapping.

**Key Principle**: Abstract all infrastructure behind interfaces so we can start local and migrate to hosted services without code changes.

---

## Goals

1. ✅ Persistent state management (survive crashes)
2. ✅ Robust error handling (retries, circuit breakers)
3. ✅ Production-grade logging (structured, searchable)
4. ✅ Emergency controls (halt/shutdown mechanisms)
5. ✅ Infrastructure abstraction (local ↔ hosted flexibility)

---

## Architecture: Abstraction-First Design

### Core Principle

```python
# Application code depends on interfaces, not implementations
from src.infrastructure.state import StateStore
from src.infrastructure.cache import CacheStore
from src.infrastructure.events import EventBus
from src.infrastructure.logging import Logger

# Implementation chosen at runtime via config
state_store = create_state_store(config.state_backend)  # "memory" | "redis" | "dynamodb"
cache_store = create_cache_store(config.cache_backend)  # "memory" | "redis" | "elasticache"
event_bus = create_event_bus(config.event_backend)     # "memory" | "redis" | "kafka"
```

### Benefits

- ✅ Start local (memory/Redis)
- ✅ Scale to hosted (ElastiCache, DynamoDB, Kafka)
- ✅ Test with in-memory backends (fast tests)
- ✅ No code changes when migrating
- ✅ Multi-environment support (dev/staging/prod)

---

## Implementation Plan

### Day 1: State Management Abstraction

#### 1.1 State Store Interface

```python
# src/infrastructure/state/base.py
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from datetime import timedelta

class StateStore(ABC):
    """Abstract state persistence layer"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        """Set value with optional TTL"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        """Get multiple keys at once"""
        pass

    @abstractmethod
    async def set_many(self, items: Dict[str, Any], ttl: Optional[timedelta] = None):
        """Set multiple keys at once"""
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomic increment"""
        pass

    @abstractmethod
    async def close(self):
        """Close connections"""
        pass
```

#### 1.2 In-Memory Implementation (Local Dev)

```python
# src/infrastructure/state/memory.py
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from .base import StateStore
import asyncio

class InMemoryStateStore(StateStore):
    """In-memory state store for local development"""

    def __init__(self):
        self._data: Dict[str, tuple[Any, Optional[datetime]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._data:
                return None

            value, expiry = self._data[key]

            # Check expiry
            if expiry and datetime.utcnow() > expiry:
                del self._data[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        async with self._lock:
            expiry = datetime.utcnow() + ttl if ttl else None
            self._data[key] = (value, expiry)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[timedelta] = None):
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def increment(self, key: str, amount: int = 1) -> int:
        async with self._lock:
            current = 0
            if key in self._data:
                current = self._data[key][0]
            new_value = current + amount
            self._data[key] = (new_value, None)
            return new_value

    async def close(self):
        self._data.clear()
```

#### 1.3 Redis Implementation (Local or Hosted)

```python
# src/infrastructure/state/redis_store.py
from typing import Any, Optional, Dict
from datetime import timedelta
import redis.asyncio as redis
import json
from .base import StateStore

class RedisStateStore(StateStore):
    """Redis state store (works with local Redis or hosted ElastiCache/Redis Cloud)"""

    def __init__(self, url: str = "redis://localhost:6379"):
        """
        Args:
            url: Redis connection URL
                - Local: "redis://localhost:6379"
                - Redis Cloud: "redis://:password@redis-12345.c1.cloud.redislabs.com:12345"
                - AWS ElastiCache: "redis://master.xxx.cache.amazonaws.com:6379"
        """
        self.url = url
        self._redis: Optional[redis.Redis] = None

    async def _ensure_connected(self):
        """Lazy connection initialization"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True
            )

    async def get(self, key: str) -> Optional[Any]:
        await self._ensure_connected()
        value = await self._redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        await self._ensure_connected()
        serialized = json.dumps(value)
        if ttl:
            await self._redis.setex(key, int(ttl.total_seconds()), serialized)
        else:
            await self._redis.set(key, serialized)

    async def delete(self, key: str) -> bool:
        await self._ensure_connected()
        result = await self._redis.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        await self._ensure_connected()
        return await self._redis.exists(key) > 0

    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        await self._ensure_connected()
        values = await self._redis.mget(keys)
        result = {}
        for key, value in zip(keys, values):
            if value:
                result[key] = json.loads(value)
        return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[timedelta] = None):
        await self._ensure_connected()
        pipe = self._redis.pipeline()
        for key, value in items.items():
            serialized = json.dumps(value)
            if ttl:
                pipe.setex(key, int(ttl.total_seconds()), serialized)
            else:
                pipe.set(key, serialized)
        await pipe.execute()

    async def increment(self, key: str, amount: int = 1) -> int:
        await self._ensure_connected()
        return await self._redis.incrby(key, amount)

    async def close(self):
        if self._redis:
            await self._redis.close()
```

#### 1.4 Factory Pattern

```python
# src/infrastructure/state/__init__.py
from typing import Optional
from .base import StateStore
from .memory import InMemoryStateStore
from .redis_store import RedisStateStore

def create_state_store(backend: str, **kwargs) -> StateStore:
    """
    Create state store based on configuration.

    Args:
        backend: "memory", "redis"
        **kwargs: Backend-specific configuration

    Examples:
        # Local development
        store = create_state_store("memory")

        # Local Redis
        store = create_state_store("redis", url="redis://localhost:6379")

        # Redis Cloud (hosted)
        store = create_state_store(
            "redis",
            url="redis://:password@redis-12345.c1.cloud.redislabs.com:12345"
        )

        # AWS ElastiCache
        store = create_state_store(
            "redis",
            url="redis://master.xxx.cache.amazonaws.com:6379"
        )
    """
    if backend == "memory":
        return InMemoryStateStore()
    elif backend == "redis":
        return RedisStateStore(url=kwargs.get("url", "redis://localhost:6379"))
    else:
        raise ValueError(f"Unknown state backend: {backend}")

__all__ = ["StateStore", "create_state_store"]
```

---

### Day 2: Event Bus Abstraction

#### 2.1 Event Bus Interface

```python
# src/infrastructure/events/base.py
from abc import ABC, abstractmethod
from typing import Callable, Any, Awaitable

EventHandler = Callable[[dict], Awaitable[None]]

class EventBus(ABC):
    """Abstract pub/sub event bus"""

    @abstractmethod
    async def publish(self, channel: str, event: dict):
        """Publish event to channel"""
        pass

    @abstractmethod
    async def subscribe(self, channel: str, handler: EventHandler):
        """Subscribe to channel with handler"""
        pass

    @abstractmethod
    async def unsubscribe(self, channel: str, handler: EventHandler):
        """Unsubscribe from channel"""
        pass

    @abstractmethod
    async def start_listening(self):
        """Start listening for events (background task)"""
        pass

    @abstractmethod
    async def stop_listening(self):
        """Stop listening"""
        pass

    @abstractmethod
    async def close(self):
        """Close connections"""
        pass
```

#### 2.2 In-Memory Implementation

```python
# src/infrastructure/events/memory.py
from typing import Dict, Set
import asyncio
from .base import EventBus, EventHandler

class InMemoryEventBus(EventBus):
    """In-memory event bus for local development/testing"""

    def __init__(self):
        self._handlers: Dict[str, Set[EventHandler]] = {}
        self._running = False

    async def publish(self, channel: str, event: dict):
        """Immediately call all handlers for this channel"""
        handlers = self._handlers.get(channel, set())
        for handler in handlers:
            await handler(event)

    async def subscribe(self, channel: str, handler: EventHandler):
        if channel not in self._handlers:
            self._handlers[channel] = set()
        self._handlers[channel].add(handler)

    async def unsubscribe(self, channel: str, handler: EventHandler):
        if channel in self._handlers:
            self._handlers[channel].discard(handler)

    async def start_listening(self):
        self._running = True

    async def stop_listening(self):
        self._running = False

    async def close(self):
        self._handlers.clear()
```

#### 2.3 Redis Implementation

```python
# src/infrastructure/events/redis_bus.py
import redis.asyncio as redis
import json
import asyncio
from typing import Dict, Set
from .base import EventBus, EventHandler

class RedisEventBus(EventBus):
    """Redis pub/sub event bus (works with local or hosted Redis)"""

    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._handlers: Dict[str, Set[EventHandler]] = {}
        self._listen_task: Optional[asyncio.Task] = None

    async def _ensure_connected(self):
        if self._redis is None:
            self._redis = await redis.from_url(self.url)
            self._pubsub = self._redis.pubsub()

    async def publish(self, channel: str, event: dict):
        await self._ensure_connected()
        await self._redis.publish(channel, json.dumps(event))

    async def subscribe(self, channel: str, handler: EventHandler):
        await self._ensure_connected()

        if channel not in self._handlers:
            self._handlers[channel] = set()
            await self._pubsub.subscribe(channel)

        self._handlers[channel].add(handler)

    async def unsubscribe(self, channel: str, handler: EventHandler):
        if channel in self._handlers:
            self._handlers[channel].discard(handler)
            if not self._handlers[channel]:
                await self._pubsub.unsubscribe(channel)
                del self._handlers[channel]

    async def start_listening(self):
        await self._ensure_connected()
        self._listen_task = asyncio.create_task(self._listen())

    async def _listen(self):
        """Background task to listen for events"""
        async for message in self._pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel'].decode()
                data = json.loads(message['data'])

                handlers = self._handlers.get(channel, set())
                for handler in handlers:
                    asyncio.create_task(handler(data))

    async def stop_listening(self):
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

    async def close(self):
        await self.stop_listening()
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
```

#### 2.4 Factory Pattern

```python
# src/infrastructure/events/__init__.py
from .base import EventBus, EventHandler
from .memory import InMemoryEventBus
from .redis_bus import RedisEventBus

def create_event_bus(backend: str, **kwargs) -> EventBus:
    """
    Create event bus based on configuration.

    Examples:
        # Local development
        bus = create_event_bus("memory")

        # Local Redis
        bus = create_event_bus("redis", url="redis://localhost:6379")

        # Hosted Redis
        bus = create_event_bus("redis", url="redis://...")
    """
    if backend == "memory":
        return InMemoryEventBus()
    elif backend == "redis":
        return RedisEventBus(url=kwargs.get("url", "redis://localhost:6379"))
    else:
        raise ValueError(f"Unknown event backend: {backend}")

__all__ = ["EventBus", "EventHandler", "create_event_bus"]
```

---

### Day 3: Logging & Observability

#### 3.1 Structured Logging Setup

```python
# src/infrastructure/logging/config.py
import structlog
import logging
import sys
from typing import Literal

def configure_logging(
    level: str = "INFO",
    format: Literal["json", "console"] = "json",
    add_correlation_id: bool = True
):
    """
    Configure structured logging for the entire application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format: "json" for production, "console" for development
        add_correlation_id: Whether to add correlation IDs to logs
    """

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )

    # Structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add correlation ID processor if enabled
    if add_correlation_id:
        processors.insert(0, add_correlation_id_processor)

    # Output renderer
    if format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Correlation ID processor
import contextvars
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)

def add_correlation_id_processor(logger, method_name, event_dict):
    """Add correlation ID to all log entries"""
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    return event_dict

def set_correlation_id(correlation_id: str):
    """Set correlation ID for this async context"""
    correlation_id_var.set(correlation_id)

def get_correlation_id() -> str:
    """Get current correlation ID"""
    return correlation_id_var.get()
```

#### 3.2 Logger Wrapper

```python
# src/infrastructure/logging/logger.py
import structlog
from typing import Any, Dict

def get_logger(name: str):
    """
    Get a structured logger instance.

    Usage:
        logger = get_logger(__name__)
        logger.info("event_occurred", user_id=123, action="trade")
    """
    return structlog.get_logger(name)

# Convenience function for binding context
def bind_context(**kwargs) -> structlog.BoundLogger:
    """
    Bind context to logger for all subsequent log calls.

    Usage:
        log = bind_context(bot_id="bot_001", strategy_id="arb_btc")
        log.info("strategy_started")
        log.info("opportunity_found", profit=123.45)
    """
    return structlog.get_logger().bind(**kwargs)
```

---

### Day 4: Error Handling & Retries

#### 4.1 Retry Decorator

```python
# src/infrastructure/resilience/retry.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import structlog
import functools

logger = structlog.get_logger(__name__)

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_on: tuple = (ConnectionError, TimeoutError)
):
    """
    Decorator to add retry logic to async functions.

    Usage:
        @with_retry(max_attempts=3, retry_on=(APIError,))
        async def fetch_price(symbol: str):
            return await exchange.get_price(symbol)
    """
    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 4.2 Circuit Breaker

```python
# src/infrastructure/resilience/circuit_breaker.py
from datetime import datetime, timedelta
from typing import Callable, Any
import asyncio
import structlog

logger = structlog.get_logger(__name__)

class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    States:
        - CLOSED: Normal operation
        - OPEN: Too many failures, reject all calls
        - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failures = 0
        self.successes = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""

        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == "OPEN":
            if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                logger.info(
                    "circuit_breaker_half_open",
                    breaker=self.name,
                    timeout_elapsed=self.recovery_timeout
                )
                self.state = "HALF_OPEN"
                self.successes = 0
            else:
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is OPEN"
                )

        # Execute function
        try:
            result = await func(*args, **kwargs)

            # Success handling
            if self.state == "HALF_OPEN":
                self.successes += 1
                if self.successes >= self.success_threshold:
                    logger.info(
                        "circuit_breaker_closed",
                        breaker=self.name,
                        successes=self.successes
                    )
                    self.state = "CLOSED"
                    self.failures = 0

            return result

        except Exception as e:
            # Failure handling
            self.failures += 1
            self.last_failure_time = datetime.utcnow()

            if self.failures >= self.failure_threshold:
                logger.warning(
                    "circuit_breaker_opened",
                    breaker=self.name,
                    failures=self.failures,
                    threshold=self.failure_threshold
                )
                self.state = "OPEN"

            raise
```

---

### Day 5: Emergency Controls & Configuration

#### 5.1 Emergency Controller

```python
# src/infrastructure/emergency/controller.py
from enum import Enum
from typing import Optional, Callable, Awaitable
import structlog

logger = structlog.get_logger(__name__)

class EmergencyLevel(Enum):
    """Emergency escalation levels"""
    NORMAL = "normal"          # Normal operation
    ALERT = "alert"            # High volatility, increase monitoring
    HALT = "halt"              # Pause new positions, keep monitoring
    SHUTDOWN = "shutdown"      # Stop everything, close positions

class EmergencyController:
    """
    Global emergency controls for the platform.

    Usage:
        emergency = EmergencyController()

        # Trigger emergency halt
        await emergency.set_level(
            EmergencyLevel.HALT,
            "Daily loss limit exceeded"
        )

        # Check before executing actions
        if emergency.level >= EmergencyLevel.HALT:
            raise Exception("Emergency halt in effect")
    """

    def __init__(self):
        self.level = EmergencyLevel.NORMAL
        self.reason: Optional[str] = None
        self._alert_handlers: list[Callable[[EmergencyLevel, str], Awaitable[None]]] = []

    async def set_level(self, level: EmergencyLevel, reason: str):
        """Set emergency level and trigger alerts"""
        old_level = self.level
        self.level = level
        self.reason = reason

        logger.warning(
            "emergency_level_changed",
            old_level=old_level.value,
            new_level=level.value,
            reason=reason
        )

        # Trigger alert handlers
        for handler in self._alert_handlers:
            await handler(level, reason)

    def register_alert_handler(
        self,
        handler: Callable[[EmergencyLevel, str], Awaitable[None]]
    ):
        """Register handler to be called when emergency level changes"""
        self._alert_handlers.append(handler)

    def is_allowed(self, required_level: EmergencyLevel = EmergencyLevel.NORMAL) -> bool:
        """Check if operation is allowed at current emergency level"""
        return self.level.value <= required_level.value

# Global instance
emergency_controller = EmergencyController()
```

#### 5.2 Configuration System

```python
# src/infrastructure/config.py
from pydantic import BaseSettings, Field
from typing import Literal

class InfrastructureConfig(BaseSettings):
    """
    Infrastructure configuration with environment variable support.

    Environment variables:
        STATE_BACKEND=memory|redis
        STATE_REDIS_URL=redis://...
        EVENT_BACKEND=memory|redis
        EVENT_REDIS_URL=redis://...
        LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
        LOG_FORMAT=json|console
    """

    # State management
    state_backend: Literal["memory", "redis"] = Field(
        default="memory",
        env="STATE_BACKEND"
    )
    state_redis_url: str = Field(
        default="redis://localhost:6379",
        env="STATE_REDIS_URL"
    )

    # Event bus
    event_backend: Literal["memory", "redis"] = Field(
        default="memory",
        env="EVENT_BACKEND"
    )
    event_redis_url: str = Field(
        default="redis://localhost:6379",
        env="EVENT_REDIS_URL"
    )

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: Literal["json", "console"] = Field(
        default="console",
        env="LOG_FORMAT"
    )

    # Resilience
    retry_max_attempts: int = Field(default=3, env="RETRY_MAX_ATTEMPTS")
    circuit_breaker_threshold: int = Field(default=5, env="CIRCUIT_BREAKER_THRESHOLD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Load configuration
config = InfrastructureConfig()
```

#### 5.3 Infrastructure Factory

```python
# src/infrastructure/__init__.py
from .config import config
from .state import create_state_store, StateStore
from .events import create_event_bus, EventBus
from .logging.config import configure_logging
import structlog

logger = structlog.get_logger(__name__)

class Infrastructure:
    """
    Central infrastructure manager.

    Usage:
        # Initialize all infrastructure
        infra = Infrastructure()
        await infra.initialize()

        # Use infrastructure services
        await infra.state.set("key", "value")
        await infra.events.publish("channel", {"data": "value"})

        # Shutdown
        await infra.shutdown()
    """

    def __init__(self):
        self.state: Optional[StateStore] = None
        self.events: Optional[EventBus] = None

    async def initialize(self):
        """Initialize all infrastructure services"""

        # Configure logging
        configure_logging(
            level=config.log_level,
            format=config.log_format
        )

        logger.info(
            "infrastructure_initializing",
            state_backend=config.state_backend,
            event_backend=config.event_backend
        )

        # Initialize state store
        self.state = create_state_store(
            backend=config.state_backend,
            url=config.state_redis_url
        )

        # Initialize event bus
        self.events = create_event_bus(
            backend=config.event_backend,
            url=config.event_redis_url
        )

        await self.events.start_listening()

        logger.info("infrastructure_initialized")

    async def shutdown(self):
        """Shutdown all infrastructure services"""
        logger.info("infrastructure_shutting_down")

        if self.events:
            await self.events.close()

        if self.state:
            await self.state.close()

        logger.info("infrastructure_shutdown_complete")

# Global infrastructure instance
infrastructure = Infrastructure()
```

---

## Environment Configuration Examples

### Local Development (.env.local)

```env
# State management (in-memory for fastest dev)
STATE_BACKEND=memory
EVENT_BACKEND=memory

# Logging (console for readability)
LOG_LEVEL=DEBUG
LOG_FORMAT=console

# Resilience (lenient for dev)
RETRY_MAX_ATTEMPTS=2
CIRCUIT_BREAKER_THRESHOLD=10
```

### Local with Redis (.env.local-redis)

```env
# State management (local Redis)
STATE_BACKEND=redis
STATE_REDIS_URL=redis://localhost:6379
EVENT_BACKEND=redis
EVENT_REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=console

# Resilience
RETRY_MAX_ATTEMPTS=3
CIRCUIT_BREAKER_THRESHOLD=5
```

### Production (.env.production)

```env
# State management (hosted Redis)
STATE_BACKEND=redis
STATE_REDIS_URL=redis://:password@redis-12345.c1.cloud.redislabs.com:12345
EVENT_BACKEND=redis
EVENT_REDIS_URL=redis://:password@redis-12345.c1.cloud.redislabs.com:12345

# Logging (JSON for log aggregation)
LOG_LEVEL=INFO
LOG_FORMAT=json

# Resilience (strict)
RETRY_MAX_ATTEMPTS=3
CIRCUIT_BREAKER_THRESHOLD=5
```

---

## Integration with Existing Code

### Update GraphRuntime

```python
# src/core/graph_runtime.py
import structlog
from src.infrastructure import infrastructure
from src.infrastructure.logging.logger import set_correlation_id
from src.infrastructure.resilience.circuit_breaker import CircuitBreaker
import uuid

logger = structlog.get_logger(__name__)

class GraphRuntime:
    def __init__(self, graph: StrategyGraph):
        self.graph = graph
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    async def execute(
        self,
        initial_inputs: Optional[Dict[str, Any]] = None,
        shared_state: Optional[Dict[str, Any]] = None
    ) -> GraphExecutionResult:
        # Generate correlation ID
        execution_id = str(uuid.uuid4())
        set_correlation_id(execution_id)

        # Create execution-scoped logger
        log = logger.bind(
            execution_id=execution_id,
            graph_id=self.graph.graph_id,
            bot_id=shared_state.get('bot_id'),
            strategy_id=shared_state.get('strategy_id')
        )

        log.info("graph_execution_started", node_count=len(self.graph.nodes))

        # Save initial state
        await infrastructure.state.set(
            f"execution:{execution_id}",
            {
                "graph_id": self.graph.graph_id,
                "started_at": datetime.utcnow().isoformat(),
                "status": "running"
            },
            ttl=timedelta(hours=1)
        )

        try:
            # Execute graph...
            for node_id in execution_order:
                log.info("node_execution_started", node_id=node_id)

                # Execute with circuit breaker protection
                circuit_breaker = self._get_circuit_breaker(node_id)
                node_result = await circuit_breaker.call(
                    node.execute,
                    context
                )

                log.info(
                    "node_execution_completed",
                    node_id=node_id,
                    status=node_result.status.value,
                    duration_ms=node_result.execution_time_ms
                )

                # Checkpoint progress
                await infrastructure.state.set(
                    f"execution:{execution_id}",
                    {
                        "nodes_completed": [n.node_id for n in completed],
                        "current_node": node_id
                    }
                )

                # Publish event
                await infrastructure.events.publish(
                    f"node_execution:{shared_state['strategy_id']}",
                    {
                        "node_id": node_id,
                        "status": node_result.status.value,
                        "outputs": node_result.outputs
                    }
                )

        except Exception as e:
            log.error("graph_execution_failed", error=str(e), exc_info=True)
            raise

        finally:
            log.info("graph_execution_completed")

    def _get_circuit_breaker(self, node_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for node"""
        if node_id not in self.circuit_breakers:
            self.circuit_breakers[node_id] = CircuitBreaker(
                name=f"node:{node_id}",
                failure_threshold=config.circuit_breaker_threshold
            )
        return self.circuit_breakers[node_id]
```

---

## Testing Infrastructure

### Unit Tests

```python
# tests/infrastructure/test_state_store.py
import pytest
from src.infrastructure.state import create_state_store

@pytest.mark.asyncio
async def test_memory_state_store():
    store = create_state_store("memory")

    await store.set("key1", "value1")
    assert await store.get("key1") == "value1"

    await store.delete("key1")
    assert await store.get("key1") is None

@pytest.mark.asyncio
async def test_redis_state_store():
    # Requires Redis running locally
    store = create_state_store("redis", url="redis://localhost:6379")

    await store.set("test_key", {"data": "value"})
    result = await store.get("test_key")
    assert result == {"data": "value"}

    await store.close()
```

---

## Deliverables

1. ✅ State store abstraction (memory + Redis)
2. ✅ Event bus abstraction (memory + Redis)
3. ✅ Structured logging with correlation IDs
4. ✅ Retry logic and circuit breakers
5. ✅ Emergency controller
6. ✅ Configuration system (.env support)
7. ✅ Infrastructure factory
8. ✅ Integration with GraphRuntime
9. ✅ Unit tests for all infrastructure

---

## Migration Path

### Phase 1: Local Development (Day 1-5)
```bash
# .env
STATE_BACKEND=memory
EVENT_BACKEND=memory
LOG_FORMAT=console
```

### Phase 2: Local Redis (Week 3)
```bash
docker-compose up -d redis
# .env
STATE_BACKEND=redis
EVENT_BACKEND=redis
```

### Phase 3: Hosted Redis (Production)
```bash
# Get Redis Cloud/ElastiCache URL
# .env
STATE_BACKEND=redis
STATE_REDIS_URL=redis://...
```

**Zero code changes required** - only environment variables.

---

## Success Criteria

- [ ] All infrastructure abstracted behind interfaces
- [ ] Can swap between memory/Redis via config
- [ ] Structured logging with correlation IDs working
- [ ] Retry logic preventing transient failures
- [ ] Circuit breakers preventing cascading failures
- [ ] Emergency controller can halt all bots
- [ ] State persists across crashes (with Redis)
- [ ] All tests passing

---

**Ready to implement. This provides the production-grade foundation needed before continuing with UI development.**
