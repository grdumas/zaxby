"""
Performance tests for cache implementation.

Measures cache hit/miss performance, cache overhead, and validates
that cache provides meaningful performance improvements.

Run with: pytest tests/performance/test_cache_performance.py -v
"""

import time
from typing import Any, Dict

import pytest

from src.cache_service import CacheService


@pytest.fixture
def cache_service():
    """Create a fresh cache service instance for each test."""
    return CacheService()


@pytest.fixture
def sample_query_params():
    """Sample query parameters for testing."""
    return {
        'query_type': 'pulse_kpis',
        'template_id': 'TPL_CATEGORY_ROLLUP',
        'filters': {
            'date_range': ['2025-01-01', '2025-12-31'],
            'cloud_provider': 'aws',
        },
    }


@pytest.fixture
def sample_result():
    """Sample cached result data."""
    return {
        'total': 10000,
        'by_cloud': [('aws', 5000), ('gcp', 3000), ('azure', 2000)],
        'source': 'opensearch',
        'error': None,
    }


class TestCachePerformance:
    """Performance tests for cache operations."""

    def test_cache_write_performance(self, cache_service, sample_query_params, sample_result):
        """Measure cache write performance."""
        iterations = 100
        start_time = time.time()

        for i in range(iterations):
            params = {**sample_query_params, 'iteration': i}
            cache_service.set(params, sample_result)

        elapsed = time.time() - start_time
        avg_write_ms = (elapsed / iterations) * 1000

        # Cache writes should be fast (< 5ms per write for simple backend)
        assert avg_write_ms < 5.0, f"Cache write too slow: {avg_write_ms:.2f}ms avg"

        print(f"\nCache write performance: {avg_write_ms:.2f}ms avg ({iterations} iterations)")

    def test_cache_read_performance(self, cache_service, sample_query_params, sample_result):
        """Measure cache read performance."""
        # Pre-populate cache
        cache_service.set(sample_query_params, sample_result)

        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            result = cache_service.get(sample_query_params)
            assert result is not None

        elapsed = time.time() - start_time
        avg_read_ms = (elapsed / iterations) * 1000

        # Cache reads should be very fast (< 1ms for simple backend)
        assert avg_read_ms < 1.0, f"Cache read too slow: {avg_read_ms:.2f}ms avg"

        print(f"\nCache read performance: {avg_read_ms:.2f}ms avg ({iterations} iterations)")

    def test_cache_miss_performance(self, cache_service, sample_query_params):
        """Measure cache miss performance."""
        iterations = 1000
        start_time = time.time()

        for i in range(iterations):
            params = {**sample_query_params, 'iteration': i}
            result = cache_service.get(params)
            assert result is None

        elapsed = time.time() - start_time
        avg_miss_ms = (elapsed / iterations) * 1000

        # Cache misses should also be fast (< 1ms for simple backend)
        assert avg_miss_ms < 1.0, f"Cache miss too slow: {avg_miss_ms:.2f}ms avg"

        print(f"\nCache miss performance: {avg_miss_ms:.2f}ms avg ({iterations} iterations)")

    def test_cache_hit_rate(self, cache_service, sample_query_params, sample_result):
        """Verify cache hit rate calculation."""
        # Pre-populate cache with 10 entries
        for i in range(10):
            params = {**sample_query_params, 'id': i}
            cache_service.set(params, sample_result)

        # Reset metrics
        cache_service.reset_metrics()

        # Simulate 60% hit rate: 6 hits, 4 misses
        for i in range(6):
            params = {**sample_query_params, 'id': i}
            result = cache_service.get(params)
            assert result is not None

        for i in range(10, 14):
            params = {**sample_query_params, 'id': i}
            result = cache_service.get(params)
            assert result is None

        metrics = cache_service.get_metrics()
        assert metrics.hits == 6
        assert metrics.misses == 4
        assert metrics.total_requests == 10
        assert 59.0 <= metrics.hit_rate <= 61.0  # Allow small floating point variance

        print(f"\nCache hit rate: {metrics.hit_rate:.1f}%")

    def test_cache_invalidation_performance(self, cache_service, sample_query_params, sample_result):
        """Measure targeted cache invalidation performance."""
        # Pre-populate cache with 100 entries across different query types
        for query_type in ['pulse_kpis', 'track_exceptions', 'category_rollup']:
            for i in range(33):
                params = {
                    'query_type': query_type,
                    'id': i,
                    'filters': {},
                }
                cache_service.set(params, sample_result)

        # Measure invalidation of one query type
        start_time = time.time()
        invalidated = cache_service.invalidate_by_query_type('pulse_kpis')
        elapsed_ms = (time.time() - start_time) * 1000

        # Should invalidate ~33 entries
        assert 30 <= invalidated <= 36, f"Expected ~33 invalidations, got {invalidated}"

        # Invalidation should be fast (< 10ms for simple backend with 100 entries)
        assert elapsed_ms < 10.0, f"Invalidation too slow: {elapsed_ms:.2f}ms"

        print(f"\nInvalidated {invalidated} entries in {elapsed_ms:.2f}ms")

    def test_cache_clear_performance(self, cache_service, sample_query_params, sample_result):
        """Measure full cache clear performance."""
        # Pre-populate cache with 1000 entries
        for i in range(1000):
            params = {**sample_query_params, 'id': i}
            cache_service.set(params, sample_result)

        # Measure clear operation
        start_time = time.time()
        success = cache_service.clear()
        elapsed_ms = (time.time() - start_time) * 1000

        assert success
        # Clear should be fast even with 1000 entries (< 50ms for simple backend)
        assert elapsed_ms < 50.0, f"Cache clear too slow: {elapsed_ms:.2f}ms"

        print(f"\nCleared cache in {elapsed_ms:.2f}ms")

    def test_lru_eviction_performance(self, cache_service, sample_query_params, sample_result):
        """Measure performance when cache reaches size limit."""
        # Fill cache to max size (1000 entries for simple backend)
        for i in range(1000):
            params = {**sample_query_params, 'id': i}
            cache_service.set(params, sample_result)

        # Measure performance of writes that trigger eviction
        iterations = 100
        start_time = time.time()

        for i in range(1000, 1000 + iterations):
            params = {**sample_query_params, 'id': i}
            cache_service.set(params, sample_result)

        elapsed = time.time() - start_time
        avg_eviction_ms = (elapsed / iterations) * 1000

        # Eviction should not significantly slow writes (< 10ms per write)
        assert avg_eviction_ms < 10.0, f"LRU eviction too slow: {avg_eviction_ms:.2f}ms avg"

        print(f"\nLRU eviction performance: {avg_eviction_ms:.2f}ms avg ({iterations} iterations)")


class TestCacheBenefit:
    """Tests that verify cache provides actual performance benefits."""

    def test_cache_vs_no_cache_speedup(self, cache_service, sample_query_params):
        """Verify cache provides significant speedup over uncached queries."""
        # Simulate expensive query (10ms)
        def expensive_query():
            time.sleep(0.01)
            return {'result': 'data'}

        # Warm up cache
        result = expensive_query()
        cache_service.set(sample_query_params, result)

        # Measure uncached query time
        iterations = 10
        uncached_start = time.time()
        for _ in range(iterations):
            expensive_query()
        uncached_time = time.time() - uncached_start

        # Measure cached query time
        cached_start = time.time()
        for _ in range(iterations):
            cache_service.get(sample_query_params)
        cached_time = time.time() - cached_start

        speedup = uncached_time / cached_time if cached_time > 0 else 0

        # Cache should provide at least 10x speedup for this test
        assert speedup > 10, f"Insufficient speedup: {speedup:.1f}x"

        print(f"\nCache speedup: {speedup:.1f}x ({uncached_time*1000:.1f}ms uncached vs {cached_time*1000:.1f}ms cached)")

    def test_cache_latency_reduction(self, cache_service, sample_query_params, sample_result):
        """Verify cache reduces query latency by target percentage."""
        # Simulate expensive query (50ms)
        expensive_query_time = 0.05
        time.sleep(expensive_query_time)

        # Cache the result
        cache_service.set(sample_query_params, sample_result)

        # Measure cache retrieval time
        start = time.time()
        cached_result = cache_service.get(sample_query_params)
        cache_time = time.time() - start

        assert cached_result is not None

        # Calculate latency reduction percentage
        latency_reduction = ((expensive_query_time - cache_time) / expensive_query_time) * 100

        # Should achieve at least 80% latency reduction
        assert latency_reduction >= 80, f"Insufficient latency reduction: {latency_reduction:.1f}%"

        print(f"\nLatency reduction: {latency_reduction:.1f}% ({expensive_query_time*1000:.1f}ms -> {cache_time*1000:.1f}ms)")


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests with query_service functions."""

    def test_pulse_kpi_cache_integration(self, sample_query_params):
        """Test cache integration with actual query_service functions."""
        from src.cache_service import get_cache_service
        from src.query_service import ResultsOverviewSnapshot

        cache = get_cache_service()
        cache.reset_metrics()

        # Create a sample snapshot
        snapshot = ResultsOverviewSnapshot(
            total=1000,
            by_cloud=[('aws', 500), ('gcp', 300), ('azure', 200)],
            source='opensearch',
            error=None,
            from_cache=False,
            cache_timestamp=time.time(),
        )

        # Cache it
        cache.set(sample_query_params, snapshot)

        # Retrieve it
        cached_snapshot = cache.get(sample_query_params)

        assert cached_snapshot is not None
        assert cached_snapshot.total == 1000
        assert len(cached_snapshot.by_cloud) == 3

        metrics = cache.get_metrics()
        assert metrics.hits == 1
        assert metrics.hit_rate == 100.0

        print(f"\nQuery service integration: cache hit rate {metrics.hit_rate:.1f}%")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
