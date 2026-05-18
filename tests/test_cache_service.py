"""Tests for cache service (RPOPC-1168)."""

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from src.cache_service import CacheMetrics, CacheService, get_cache_service


class TestCacheMetrics:
    """Test cache metrics tracking."""

    def test_metrics_initialization(self):
        """Metrics start at zero."""
        metrics = CacheMetrics()
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.errors == 0

    def test_total_requests(self):
        """Total requests is sum of hits and misses."""
        metrics = CacheMetrics(hits=10, misses=5)
        assert metrics.total_requests == 15

    def test_hit_rate_calculation(self):
        """Hit rate is calculated as percentage."""
        metrics = CacheMetrics(hits=80, misses=20)
        assert metrics.hit_rate == 80.0

    def test_hit_rate_with_no_requests(self):
        """Hit rate is 0 when no requests."""
        metrics = CacheMetrics()
        assert metrics.hit_rate == 0.0


class TestCacheKeyGeneration:
    """Test deterministic cache key generation."""

    def test_generate_cache_key_deterministic(self):
        """Same params produce same key."""
        cache = CacheService()
        params1 = {'query_type': 'test', 'filters': {'os': 'rhel', 'version': '9.4'}}
        params2 = {'query_type': 'test', 'filters': {'os': 'rhel', 'version': '9.4'}}

        key1 = cache._generate_cache_key(params1)
        key2 = cache._generate_cache_key(params2)

        assert key1 == key2

    def test_generate_cache_key_different_params(self):
        """Different params produce different keys."""
        cache = CacheService()
        params1 = {'query_type': 'test', 'filters': {'os': 'rhel'}}
        params2 = {'query_type': 'test', 'filters': {'os': 'sles'}}

        key1 = cache._generate_cache_key(params1)
        key2 = cache._generate_cache_key(params2)

        assert key1 != key2

    def test_generate_cache_key_order_independent(self):
        """Key is same regardless of dict key order."""
        cache = CacheService()
        params1 = {'a': 1, 'b': 2, 'c': 3}
        params2 = {'c': 3, 'a': 1, 'b': 2}

        key1 = cache._generate_cache_key(params1)
        key2 = cache._generate_cache_key(params2)

        assert key1 == key2

    def test_generate_cache_key_includes_query_type(self):
        """Cache key includes query type for readability."""
        cache = CacheService()
        params = {'query_type': 'pulse_kpis', 'filters': {}}

        key = cache._generate_cache_key(params)

        assert 'pulse_kpis' in key
        assert key.startswith('cache:')


class TestSimpleCache:
    """Test simple in-memory cache backend."""

    @pytest.fixture
    def simple_cache(self):
        """Create simple cache instance."""
        with patch.dict(os.environ, {'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TTL': '300'}):
            cache = CacheService()
            yield cache

    def test_simple_cache_get_miss(self, simple_cache):
        """Get returns None for cache miss."""
        params = {'query_type': 'test', 'key': 'value'}
        result = simple_cache.get(params)

        assert result is None
        assert simple_cache.metrics.misses == 1
        assert simple_cache.metrics.hits == 0

    def test_simple_cache_set_and_get(self, simple_cache):
        """Set and get work correctly."""
        params = {'query_type': 'test', 'key': 'value'}
        data = {'result': [1, 2, 3]}

        # Set
        success = simple_cache.set(params, data, ttl=60)
        assert success is True

        # Get
        result = simple_cache.get(params)
        assert result == data
        assert simple_cache.metrics.hits == 1

    def test_simple_cache_expiry(self, simple_cache):
        """Cached values expire after TTL."""
        params = {'query_type': 'test', 'key': 'value'}
        data = {'result': 'test'}

        # Set with 1 second TTL
        simple_cache.set(params, data, ttl=1)

        # Immediate get should hit
        assert simple_cache.get(params) == data

        # Wait for expiry
        time.sleep(1.1)

        # Should be expired now
        result = simple_cache.get(params)
        assert result is None

    def test_simple_cache_invalidate(self, simple_cache):
        """Invalidate removes cache entry."""
        params = {'query_type': 'test', 'key': 'value'}
        data = {'result': 'test'}

        simple_cache.set(params, data)
        assert simple_cache.get(params) == data

        # Invalidate
        success = simple_cache.invalidate(params)
        assert success is True

        # Should be gone
        assert simple_cache.get(params) is None

    def test_simple_cache_invalidate_nonexistent(self, simple_cache):
        """Invalidate returns False for non-existent key."""
        params = {'query_type': 'test', 'key': 'value'}

        success = simple_cache.invalidate(params)
        assert success is False

    def test_simple_cache_clear(self, simple_cache):
        """Clear removes all entries."""
        params1 = {'query_type': 'test1', 'key': 'value1'}
        params2 = {'query_type': 'test2', 'key': 'value2'}

        simple_cache.set(params1, {'data': 1})
        simple_cache.set(params2, {'data': 2})

        # Clear
        success = simple_cache.clear()
        assert success is True

        # Both should be gone
        assert simple_cache.get(params1) is None
        assert simple_cache.get(params2) is None

    def test_simple_cache_default_ttl_from_query_type(self, simple_cache):
        """TTL defaults based on query type."""
        # Pulse KPIs default is 300 seconds
        params = {'query_type': 'pulse_kpis'}
        ttl = simple_cache._get_ttl_for_query_type('pulse_kpis')
        assert ttl == 300

        # Track exceptions default is 900 seconds
        ttl = simple_cache._get_ttl_for_query_type('track_exceptions')
        assert ttl == 900

        # Unknown defaults to default TTL
        ttl = simple_cache._get_ttl_for_query_type('unknown_type')
        assert ttl == 300  # CACHE_DEFAULT_TTL


class TestNullCache:
    """Test null (disabled) cache backend."""

    @pytest.fixture
    def null_cache(self):
        """Create null cache instance."""
        with patch.dict(os.environ, {'CACHE_TYPE': 'null'}):
            cache = CacheService()
            yield cache

    def test_null_cache_always_misses(self, null_cache):
        """Null cache always returns None."""
        params = {'query_type': 'test'}
        result = null_cache.get(params)

        assert result is None
        assert null_cache.metrics.misses == 1

    def test_null_cache_set_does_nothing(self, null_cache):
        """Null cache set returns False."""
        params = {'query_type': 'test'}
        success = null_cache.set(params, {'data': 'test'})

        assert success is False

    def test_null_cache_invalidate_does_nothing(self, null_cache):
        """Null cache invalidate returns False."""
        params = {'query_type': 'test'}
        success = null_cache.invalidate(params)

        assert success is False

    def test_null_cache_clear_does_nothing(self, null_cache):
        """Null cache clear returns False."""
        success = null_cache.clear()
        assert success is False


class TestRedisCache:
    """Test Redis cache backend."""

    def test_redis_cache_initialization(self):
        """Redis cache initializes correctly."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            with patch.dict(os.environ, {
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': 'redis://localhost:6379/0'
            }):
                cache = CacheService()

                assert cache.cache_type == 'redis'
                assert cache._backend is not None
                mock_client.ping.assert_called_once()

    def test_redis_cache_fallback_on_missing_url(self):
        """Falls back to simple cache if Redis URL not set."""
        with patch.dict(os.environ, {'CACHE_TYPE': 'redis'}, clear=True):
            cache = CacheService()

            # Should fallback to simple
            assert cache.cache_type == 'simple'

    def test_redis_cache_fallback_on_connection_error(self):
        """Falls back to simple cache on connection error."""
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.side_effect = Exception("Connection failed")

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            with patch.dict(os.environ, {
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': 'redis://localhost:6379/0'
            }):
                cache = CacheService()

                # Should fallback to simple
                assert cache.cache_type == 'simple'

    def test_redis_cache_set_and_get(self):
        """Redis cache set and get work correctly."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            with patch.dict(os.environ, {
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': 'redis://localhost:6379/0'
            }):
                cache = CacheService()
                params = {'query_type': 'test', 'key': 'value'}
                data = {'result': [1, 2, 3]}

                # Set
                mock_client.setex.return_value = True
                success = cache.set(params, data, ttl=60)
                assert success is True
                mock_client.setex.assert_called_once()

                # Get
                mock_client.get.return_value = json.dumps(data)
                result = cache.get(params)
                assert result == data

    def test_redis_cache_get_miss(self):
        """Redis cache returns None on miss."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            with patch.dict(os.environ, {
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': 'redis://localhost:6379/0'
            }):
                cache = CacheService()
                params = {'query_type': 'test'}

                mock_client.get.return_value = None
                result = cache.get(params)

                assert result is None
                assert cache.metrics.misses == 1

    def test_redis_cache_invalidate(self):
        """Redis cache invalidate works."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            with patch.dict(os.environ, {
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': 'redis://localhost:6379/0'
            }):
                cache = CacheService()
                params = {'query_type': 'test'}

                mock_client.delete.return_value = 1
                success = cache.invalidate(params)

                assert success is True
                mock_client.delete.assert_called_once()

    def test_redis_cache_clear(self):
        """Redis cache clear removes all cache keys."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            with patch.dict(os.environ, {
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': 'redis://localhost:6379/0'
            }):
                cache = CacheService()

                mock_client.keys.return_value = ['cache:test1', 'cache:test2']
                mock_client.delete.return_value = 2

                success = cache.clear()
                assert success is True
                mock_client.keys.assert_called_once_with('cache:*')
                mock_client.delete.assert_called_once_with('cache:test1', 'cache:test2')


class TestCacheErrorHandling:
    """Test graceful error handling."""

    def test_get_error_handling(self):
        """Get handles errors gracefully."""
        with patch.dict(os.environ, {'CACHE_TYPE': 'simple'}):
            cache = CacheService()
            # Cause an error by making _generate_cache_key fail
            with patch.object(cache, '_generate_cache_key', side_effect=Exception("Test error")):
                result = cache.get({'query_type': 'test'})

                assert result is None
                assert cache.metrics.errors == 1

    def test_set_error_handling(self):
        """Set handles errors gracefully."""
        with patch.dict(os.environ, {'CACHE_TYPE': 'simple'}):
            cache = CacheService()
            # Cause an error
            with patch.object(cache, '_generate_cache_key', side_effect=Exception("Test error")):
                success = cache.set({'query_type': 'test'}, {'data': 'test'})

                assert success is False
                assert cache.metrics.errors == 1


class TestTTLConfiguration:
    """Test TTL configuration from environment."""

    def test_custom_ttl_from_environment(self):
        """TTL can be configured via environment variables."""
        with patch.dict(os.environ, {
            'CACHE_TYPE': 'simple',
            'CACHE_TTL_PULSE_KPIS': '600',
            'CACHE_TTL_TRACK_EXCEPTIONS': '1200'
        }):
            cache = CacheService()

            assert cache._get_ttl_for_query_type('pulse_kpis') == 600
            assert cache._get_ttl_for_query_type('track_exceptions') == 1200

    def test_invalid_ttl_uses_default(self):
        """Invalid TTL values fall back to defaults."""
        with patch.dict(os.environ, {
            'CACHE_TYPE': 'simple',
            'CACHE_TTL_PULSE_KPIS': 'invalid'
        }):
            cache = CacheService()

            # Should use default
            assert cache._get_ttl_for_query_type('pulse_kpis') == 300


class TestCacheServiceSingleton:
    """Test global cache service singleton."""

    def test_get_cache_service_returns_singleton(self):
        """get_cache_service returns same instance."""
        # Reset singleton
        import src.cache_service
        src.cache_service._cache_instance = None

        service1 = get_cache_service()
        service2 = get_cache_service()

        assert service1 is service2

    def test_cache_metrics_methods(self):
        """Test metrics retrieval and reset."""
        with patch.dict(os.environ, {'CACHE_TYPE': 'simple'}):
            cache = CacheService()

            # Generate some metrics
            params = {'query_type': 'test'}
            cache.get(params)  # miss
            cache.set(params, {'data': 'test'})
            cache.get(params)  # hit

            metrics = cache.get_metrics()
            assert metrics.hits == 1
            assert metrics.misses == 1

            # Reset
            cache.reset_metrics()
            metrics = cache.get_metrics()
            assert metrics.hits == 0
            assert metrics.misses == 0
