"""
Cache service for query results.

Provides a configurable caching layer with support for multiple backends
(in-memory, Redis) and graceful fallback when cache is unavailable.

Supports:
- Deterministic cache key generation from query parameters
- Configurable TTL per query type
- Cache hit/miss metrics for monitoring
- Multiple backends for dev/prod environments
"""

import hashlib
import json
import logging
import os
import pickle
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache hit/miss metrics for monitoring."""
    hits: int = 0
    misses: int = 0
    errors: int = 0

    @property
    def total_requests(self) -> int:
        """Total cache requests (hits + misses)."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage (0-100)."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100.0


class CacheService:
    """
    Cache service with support for multiple backends and graceful degradation.

    Backends:
    - 'simple': In-memory dict with TTL (default, good for dev)
    - 'redis': Redis-backed cache (production)
    - 'null': No-op cache (for testing or disabling cache)

    Configuration via environment variables:
    - CACHE_TYPE: Cache backend type ('simple', 'redis', 'null')
    - CACHE_REDIS_URL: Redis connection URL (required for redis backend)
    - CACHE_DEFAULT_TTL: Default TTL in seconds (default: 300)

    Query type TTLs (can be overridden via environment):
    - CACHE_TTL_PULSE_KPIS: TTL for Pulse KPI queries (default: 300 seconds / 5 min)
    - CACHE_TTL_TRACK_EXCEPTIONS: TTL for Track exception queries (default: 900 seconds / 15 min)
    - CACHE_TTL_CATEGORY_ROLLUP: TTL for category rollup queries (default: 300 seconds / 5 min)
    """

    # Default TTLs by query type (seconds)
    DEFAULT_TTLS = {
        'pulse_kpis': 300,          # 5 minutes
        'track_exceptions': 900,     # 15 minutes
        'category_rollup': 300,      # 5 minutes
        'activity_timeline': 300,    # 5 minutes
        'scope_footnote': 300,       # 5 minutes
        'default': 300,              # 5 minutes
    }

    # Maximum size for simple in-memory cache (LRU eviction)
    SIMPLE_CACHE_MAX_SIZE = 1000

    def __init__(self):
        """Initialize cache service with configured backend."""
        self.cache_type = os.getenv('CACHE_TYPE', 'simple').lower()
        self.default_ttl = int(os.getenv('CACHE_DEFAULT_TTL', '300'))
        self.metrics = CacheMetrics()
        self._backend: Optional[Any] = None
        # LRU cache: OrderedDict maintains insertion order, key -> (value, expiry_time)
        self._simple_cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()

        # Load query-type-specific TTLs from environment
        self._ttls = self.DEFAULT_TTLS.copy()
        for query_type in self._ttls.keys():
            env_key = f'CACHE_TTL_{query_type.upper()}'
            if env_val := os.getenv(env_key):
                try:
                    self._ttls[query_type] = int(env_val)
                except ValueError:
                    logger.warning(f"Invalid TTL value for {env_key}: {env_val}")

        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the configured cache backend."""
        if self.cache_type == 'null':
            logger.info("Cache disabled (null backend)")
            return

        if self.cache_type == 'simple':
            logger.info("Using simple in-memory cache")
            return

        if self.cache_type == 'redis':
            try:
                import redis
                redis_url = os.getenv('CACHE_REDIS_URL')
                if not redis_url:
                    logger.error("CACHE_REDIS_URL not set, falling back to simple cache")
                    self.cache_type = 'simple'
                    return

                # Don't decode responses - we'll use pickle for serialization
                self._backend = redis.from_url(redis_url, decode_responses=False)
                # Test connection
                self._backend.ping()
                logger.info(f"Connected to Redis cache at {redis_url}")
            except ImportError:
                logger.error("redis package not installed, falling back to simple cache")
                self.cache_type = 'simple'
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}, falling back to simple cache")
                self.cache_type = 'simple'
                self._backend = None

    def _generate_cache_key(self, query_params: Dict[str, Any]) -> str:
        """
        Generate deterministic cache key from query parameters.

        Args:
            query_params: Dictionary of query parameters (filters, date range, template_id, mode, etc.)

        Returns:
            Deterministic cache key string
        """
        # Sort keys for deterministic hashing
        sorted_params = json.dumps(query_params, sort_keys=True, default=str)
        # Use SHA256 for robust hashing
        hash_obj = hashlib.sha256(sorted_params.encode('utf-8'))
        key_hash = hash_obj.hexdigest()[:32]  # Use 32 chars for better collision resistance

        # Include a prefix and query type for readability
        query_type = query_params.get('query_type', 'unknown')
        return f"cache:{query_type}:{key_hash}"

    def _get_ttl_for_query_type(self, query_type: Optional[str]) -> int:
        """Get TTL for a specific query type."""
        if not query_type:
            return self._ttls['default']
        return self._ttls.get(query_type, self._ttls['default'])

    def get(self, query_params: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieve cached value for query parameters.

        Args:
            query_params: Dictionary of query parameters

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if self.cache_type == 'null':
            self.metrics.misses += 1
            return None

        try:
            cache_key = self._generate_cache_key(query_params)

            if self.cache_type == 'simple':
                if cache_key in self._simple_cache:
                    value, expiry = self._simple_cache[cache_key]
                    if time.time() < expiry:
                        # Move to end to mark as recently used (LRU)
                        self._simple_cache.move_to_end(cache_key)
                        self.metrics.hits += 1
                        logger.debug(f"Cache HIT: {cache_key}")
                        # Return deep copy to prevent cache pollution from mutations
                        return deepcopy(value)
                    else:
                        # Expired, remove it
                        del self._simple_cache[cache_key]
                self.metrics.misses += 1
                logger.debug(f"Cache MISS: {cache_key}")
                return None

            elif self.cache_type == 'redis' and self._backend:
                value = self._backend.get(cache_key)
                if value is not None:
                    self.metrics.hits += 1
                    logger.debug(f"Cache HIT: {cache_key}")
                    # Deserialize from pickle
                    return pickle.loads(value)
                self.metrics.misses += 1
                logger.debug(f"Cache MISS: {cache_key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.metrics.errors += 1
            return None

    def set(
        self,
        query_params: Dict[str, Any],
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store value in cache with TTL.

        Args:
            query_params: Dictionary of query parameters (used to generate cache key)
            value: Value to cache
            ttl: Time-to-live in seconds (if None, uses query type default)

        Returns:
            True if successfully cached, False otherwise
        """
        if self.cache_type == 'null':
            return False

        try:
            cache_key = self._generate_cache_key(query_params)

            # Determine TTL
            if ttl is None:
                query_type = query_params.get('query_type')
                ttl = self._get_ttl_for_query_type(query_type)

            if self.cache_type == 'simple':
                # Evict oldest entry if cache is full (LRU eviction)
                if len(self._simple_cache) >= self.SIMPLE_CACHE_MAX_SIZE:
                    # Remove first (oldest) item
                    self._simple_cache.popitem(last=False)
                    logger.debug(f"Cache LRU eviction, size was {self.SIMPLE_CACHE_MAX_SIZE}")

                expiry_time = time.time() + ttl
                # Store deep copy to prevent cache pollution from mutations
                self._simple_cache[cache_key] = (deepcopy(value), expiry_time)
                logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
                return True

            elif self.cache_type == 'redis' and self._backend:
                # Serialize to pickle (preserves Python object types)
                serialized = pickle.dumps(value)
                self._backend.setex(cache_key, ttl, serialized)
                logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
                return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.metrics.errors += 1
            return False

        return False

    def invalidate(self, query_params: Dict[str, Any]) -> bool:
        """
        Invalidate (delete) a specific cache entry.

        Args:
            query_params: Dictionary of query parameters

        Returns:
            True if invalidated, False otherwise
        """
        if self.cache_type == 'null':
            return False

        try:
            cache_key = self._generate_cache_key(query_params)

            if self.cache_type == 'simple':
                if cache_key in self._simple_cache:
                    del self._simple_cache[cache_key]
                    logger.debug(f"Cache INVALIDATE: {cache_key}")
                    return True
                return False

            elif self.cache_type == 'redis' and self._backend:
                result = self._backend.delete(cache_key)
                logger.debug(f"Cache INVALIDATE: {cache_key}")
                return result > 0

        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            self.metrics.errors += 1
            return False

        return False

    def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if cleared successfully, False otherwise
        """
        if self.cache_type == 'null':
            return False

        try:
            if self.cache_type == 'simple':
                self._simple_cache.clear()
                logger.info("Cache cleared (simple)")
                return True

            elif self.cache_type == 'redis' and self._backend:
                # Use scan_iter to avoid blocking O(N) operation
                # Only clear keys with our prefix to avoid clearing unrelated data
                keys_deleted = 0
                batch = []
                batch_size = 1000  # Delete in batches to avoid exceeding max args

                for key in self._backend.scan_iter(match='cache:*', count=100):
                    batch.append(key)
                    if len(batch) >= batch_size:
                        self._backend.delete(*batch)
                        keys_deleted += len(batch)
                        batch = []

                # Delete remaining keys in final batch
                if batch:
                    self._backend.delete(*batch)
                    keys_deleted += len(batch)

                logger.info(f"Cache cleared (redis, {keys_deleted} keys)")
                return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.metrics.errors += 1
            return False

        return False

    def get_metrics(self) -> CacheMetrics:
        """
        Get current cache metrics.

        Returns:
            CacheMetrics instance with current hit/miss/error counts
        """
        return self.metrics

    def reset_metrics(self):
        """Reset cache metrics to zero."""
        self.metrics = CacheMetrics()


# Global cache instance
_cache_instance: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Get or create the global cache service instance.

    Returns:
        CacheService singleton instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance
