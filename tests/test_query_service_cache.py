"""Tests for query_service cache integration (RPOPC-1169)."""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from src.cache_service import CacheService
from src.query_service import (
    fetch_pulse_scope_footnote,
    fetch_results_activity_timeline,
    fetch_results_category_kpis,
    fetch_results_overview_aggregates,
    log_cache_statistics,
    warm_query_cache,
)


@pytest.fixture
def mock_opensearch_client():
    """Create a mock OpenSearch client."""
    client = MagicMock()
    # Mock successful responses for all query types
    client.search_results.return_value = {
        "hits": {"total": {"value": 100}},
        "aggregations": {
            "by_cloud": {"buckets": [{"key": "aws", "doc_count": 60}, {"key": "gcp", "doc_count": 40}]},
            "by_test_name": {"buckets": [{"key": "streams", "doc_count": 50}]},
            "runs_by_month": {"buckets": [{"key_as_string": "2025-05", "doc_count": 100}]},
            "run_time_stats": {"count": 100, "min": 1704067200000.0, "max": 1735689600000.0},
        },
    }
    return client


@pytest.fixture
def simple_cache():
    """Create a simple cache instance for testing."""
    with patch.dict(os.environ, {'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TTL': '300'}):
        cache = CacheService()
        cache.clear()  # Clear any existing entries
        cache.reset_metrics()  # Reset metrics
        yield cache


class TestCacheIntegration:
    """Test cache integration in query_service functions."""

    def test_fetch_results_overview_aggregates_cache_miss_then_hit(self, mock_opensearch_client, simple_cache):
        """First call is cache miss, second call is cache hit."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # First call - cache miss
            result1 = fetch_results_overview_aggregates(mock_opensearch_client)
            assert result1.from_cache is False
            assert result1.cache_timestamp is not None
            assert result1.total == 100
            assert simple_cache.metrics.misses == 1
            assert simple_cache.metrics.hits == 0

            # Second call - cache hit
            result2 = fetch_results_overview_aggregates(mock_opensearch_client)
            assert result2.from_cache is True
            assert result2.cache_timestamp == result1.cache_timestamp
            assert result2.total == 100
            assert simple_cache.metrics.hits == 1
            assert simple_cache.metrics.misses == 1

    def test_fetch_results_category_kpis_cache_miss_then_hit(self, mock_opensearch_client, simple_cache):
        """Category KPI query uses cache correctly."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # First call - cache miss
            result1 = fetch_results_category_kpis(mock_opensearch_client)
            assert result1.from_cache is False
            assert result1.cache_timestamp is not None
            assert len(result1.by_category) > 0
            assert simple_cache.metrics.misses == 1

            # Second call - cache hit
            result2 = fetch_results_category_kpis(mock_opensearch_client)
            assert result2.from_cache is True
            assert result2.by_category == result1.by_category
            assert simple_cache.metrics.hits == 1

    def test_fetch_results_activity_timeline_cache_miss_then_hit(self, mock_opensearch_client, simple_cache):
        """Activity timeline query uses cache correctly."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # First call - cache miss
            result1 = fetch_results_activity_timeline(mock_opensearch_client)
            assert result1.from_cache is False
            assert result1.cache_timestamp is not None
            assert len(result1.by_month) > 0
            assert simple_cache.metrics.misses == 1

            # Second call - cache hit
            result2 = fetch_results_activity_timeline(mock_opensearch_client)
            assert result2.from_cache is True
            assert result2.by_month == result1.by_month
            assert simple_cache.metrics.hits == 1

    def test_fetch_pulse_scope_footnote_cache_miss_then_hit(self, mock_opensearch_client, simple_cache):
        """Scope footnote query uses cache correctly."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # First call - cache miss
            result1 = fetch_pulse_scope_footnote(mock_opensearch_client)
            assert result1.from_cache is False
            assert result1.cache_timestamp is not None
            assert result1.document_count == 100
            assert simple_cache.metrics.misses == 1

            # Second call - cache hit
            result2 = fetch_pulse_scope_footnote(mock_opensearch_client)
            assert result2.from_cache is True
            assert result2.document_count == result1.document_count
            assert simple_cache.metrics.hits == 1

    def test_cache_reduces_opensearch_calls(self, mock_opensearch_client, simple_cache):
        """Cache reduces number of OpenSearch calls."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # Call same query 5 times
            for _ in range(5):
                fetch_results_overview_aggregates(mock_opensearch_client)

            # OpenSearch should only be called once
            assert mock_opensearch_client.search_results.call_count == 1
            # Cache metrics: 1 miss, 4 hits
            assert simple_cache.metrics.misses == 1
            assert simple_cache.metrics.hits == 4
            assert simple_cache.metrics.hit_rate == 80.0  # 4/5 = 80%

    def test_cache_timestamp_for_staleness_detection(self, mock_opensearch_client, simple_cache):
        """Cache timestamp allows staleness detection."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # First call
            result1 = fetch_results_overview_aggregates(mock_opensearch_client)
            timestamp1 = result1.cache_timestamp

            # Wait a bit
            time.sleep(0.1)

            # Second call (from cache)
            result2 = fetch_results_overview_aggregates(mock_opensearch_client)
            timestamp2 = result2.cache_timestamp

            # Timestamps should be the same (from cache)
            assert timestamp1 == timestamp2

            # Age should be calculable
            age_seconds = time.time() - timestamp2
            assert age_seconds >= 0.1  # At least the sleep time


class TestCacheWarming:
    """Test cache warming functionality."""

    def test_warm_query_cache_disabled_by_default(self, mock_opensearch_client, simple_cache):
        """Cache warming is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.query_service.get_cache_service', return_value=simple_cache):
                result = warm_query_cache(mock_opensearch_client)

                assert result['enabled'] is False
                assert result['warmed'] == 0
                assert result['failed'] == 0

    def test_warm_query_cache_enabled(self, mock_opensearch_client, simple_cache):
        """Cache warming executes all queries when enabled."""
        with patch.dict(os.environ, {'ENABLE_CACHE_WARMING': 'true'}):
            with patch('src.query_service.get_cache_service', return_value=simple_cache):
                result = warm_query_cache(mock_opensearch_client)

                assert result['enabled'] is True
                assert result['warmed'] == 4  # 4 queries warmed
                assert result['failed'] == 0
                assert result['duration_seconds'] > 0
                assert len(result['details']) == 4

                # Verify all queries were successful
                for detail in result['details']:
                    assert detail['status'] == 'success'

    def test_warm_query_cache_populates_cache(self, mock_opensearch_client, simple_cache):
        """Cache warming populates the cache."""
        with patch.dict(os.environ, {'ENABLE_CACHE_WARMING': '1'}):
            with patch('src.query_service.get_cache_service', return_value=simple_cache):
                # Warm the cache
                warm_query_cache(mock_opensearch_client)

                # All subsequent queries should be cache hits
                result1 = fetch_results_overview_aggregates(mock_opensearch_client)
                assert result1.from_cache is True

                result2 = fetch_results_category_kpis(mock_opensearch_client)
                assert result2.from_cache is True

                result3 = fetch_results_activity_timeline(mock_opensearch_client)
                assert result3.from_cache is True

                result4 = fetch_pulse_scope_footnote(mock_opensearch_client)
                assert result4.from_cache is True

    def test_warm_query_cache_handles_errors(self, simple_cache):
        """Cache warming handles query errors gracefully."""
        # Mock client that raises errors
        error_client = MagicMock()
        error_client.search_results.side_effect = Exception("Connection error")

        with patch.dict(os.environ, {'ENABLE_CACHE_WARMING': 'yes'}):
            with patch('src.query_service.get_cache_service', return_value=simple_cache):
                result = warm_query_cache(error_client)

                assert result['enabled'] is True
                assert result['warmed'] == 0
                assert result['failed'] == 4  # All 4 queries failed
                assert len(result['details']) == 4

                # Verify all queries have error status
                for detail in result['details']:
                    assert detail['status'] in ('error', 'exception')


class TestCacheStatistics:
    """Test cache statistics logging."""

    def test_log_cache_statistics(self, mock_opensearch_client, simple_cache):
        """Cache statistics are logged correctly."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # Generate some cache activity
            fetch_results_overview_aggregates(mock_opensearch_client)  # miss
            fetch_results_overview_aggregates(mock_opensearch_client)  # hit
            fetch_results_overview_aggregates(mock_opensearch_client)  # hit

            # Log statistics
            stats = log_cache_statistics()

            assert stats['hits'] == 2
            assert stats['misses'] == 1
            assert stats['total_requests'] == 3
            assert stats['hit_rate'] == pytest.approx(66.67, rel=0.1)  # 2/3
            assert stats['miss_rate'] == pytest.approx(33.33, rel=0.1)  # 1/3
            assert stats['errors'] == 0

    def test_log_cache_statistics_no_requests(self, simple_cache):
        """Cache statistics handle zero requests."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            stats = log_cache_statistics()

            assert stats['hits'] == 0
            assert stats['misses'] == 0
            assert stats['total_requests'] == 0
            assert stats['hit_rate'] == 0.0
            assert stats['miss_rate'] == 0.0


class TestCachePerformance:
    """Test cache performance characteristics."""

    def test_cache_saves_query_time(self, mock_opensearch_client, simple_cache):
        """Cache hit saves significant query time."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # Simulate slow OpenSearch query
            def slow_search(*args, **kwargs):
                time.sleep(0.1)  # 100ms simulated query
                return {
                    "hits": {"total": {"value": 100}},
                    "aggregations": {
                        "by_cloud": {"buckets": [{"key": "aws", "doc_count": 100}]},
                    },
                }

            mock_opensearch_client.search_results = slow_search

            # First call - slow (cache miss)
            start1 = time.time()
            fetch_results_overview_aggregates(mock_opensearch_client)
            duration1 = time.time() - start1
            assert duration1 >= 0.1  # At least 100ms

            # Second call - fast (cache hit)
            start2 = time.time()
            fetch_results_overview_aggregates(mock_opensearch_client)
            duration2 = time.time() - start2
            assert duration2 < 0.05  # Should be much faster

            # Cache hit should save at least 80% of query time
            time_saved_percent = ((duration1 - duration2) / duration1) * 100
            assert time_saved_percent >= 80.0

    def test_different_queries_cached_independently(self, mock_opensearch_client, simple_cache):
        """Different query types are cached independently."""
        with patch('src.query_service.get_cache_service', return_value=simple_cache):
            # Call different queries
            result1 = fetch_results_overview_aggregates(mock_opensearch_client)
            result2 = fetch_results_category_kpis(mock_opensearch_client)

            # Both should be cache misses (different queries)
            assert simple_cache.metrics.misses == 2
            assert simple_cache.metrics.hits == 0

            # Call them again
            result1_cached = fetch_results_overview_aggregates(mock_opensearch_client)
            result2_cached = fetch_results_category_kpis(mock_opensearch_client)

            # Both should be cache hits
            assert simple_cache.metrics.hits == 2
            assert simple_cache.metrics.misses == 2
