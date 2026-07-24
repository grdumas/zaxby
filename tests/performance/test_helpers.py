"""
Unit tests for performance helper functions.

Tests the _timed_query helper to ensure it handles both dict and list responses
correctly. This is critical for concurrent workload tests that mix queries returning
dicts (with "took" field) and queries returning lists (like fetch_timeseries_for_document).

Now imports from tests.performance.helpers to validate actual production code.
"""

from __future__ import annotations

import time
import pytest
from typing import Any, Callable, Dict, List

from tests.performance.helpers import _timed_query


# Copy of _timed_query BEFORE the fix (for testing the bug existed)
def _timed_query_original(fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """
    Original version (with bug): assumes response is always a dict.
    """
    start = time.time()
    response = fn()
    end = time.time()

    latency_ms = (end - start) * 1000
    took_ms = response.get("took", -1)  # BUG: fails if response is a list

    return {
        "latency_ms": latency_ms,
        "took_ms": took_ms,
        "response": response,
    }


class TestTimedQueryOriginalBug:
    """Test the original _timed_query to demonstrate the bug."""

    def test_list_response_fails_with_original(self):
        """Test that the original _timed_query fails with list responses."""
        # Callable returning a list (like fetch_timeseries_for_document)
        def query_fn():
            return [
                {"metadata": {"sequence": 1}, "values": {"cpu": 10.5}},
                {"metadata": {"sequence": 2}, "values": {"cpu": 12.3}},
            ]

        # This should raise AttributeError: 'list' object has no attribute 'get'
        with pytest.raises(AttributeError, match="'list' object has no attribute 'get'"):
            _timed_query_original(query_fn)


class TestTimedQueryFixed:
    """Test the fixed _timed_query helper function."""

    def test_dict_response_with_took(self):
        """Test _timed_query with a dict response containing 'took' field."""
        # Callable returning a dict with "took" field
        def query_fn():
            return {
                "took": 42,
                "hits": {
                    "total": {"value": 100},
                    "hits": []
                }
            }

        result = _timed_query(query_fn)

        # Assertions
        assert "latency_ms" in result, "Missing latency_ms in result"
        assert "took_ms" in result, "Missing took_ms in result"
        assert "response" in result, "Missing response in result"

        assert result["took_ms"] == 42, f"Expected took_ms=42, got {result['took_ms']}"
        assert result["latency_ms"] > 0, f"Expected positive latency_ms, got {result['latency_ms']}"
        assert isinstance(result["response"], dict), "Expected dict response"
        assert result["response"]["took"] == 42, "Response dict should be preserved"

    def test_dict_response_without_took(self):
        """Test _timed_query with a dict response missing 'took' field."""
        # Callable returning a dict without "took" field
        def query_fn():
            return {
                "hits": {
                    "total": {"value": 50},
                    "hits": []
                },
                "aggregations": {}
            }

        result = _timed_query(query_fn)

        # Assertions
        assert "latency_ms" in result, "Missing latency_ms in result"
        assert "took_ms" in result, "Missing took_ms in result"
        assert "response" in result, "Missing response in result"

        assert result["took_ms"] == -1, f"Expected took_ms=-1 for missing field, got {result['took_ms']}"
        assert result["latency_ms"] > 0, f"Expected positive latency_ms, got {result['latency_ms']}"
        assert isinstance(result["response"], dict), "Expected dict response"

    def test_list_response(self):
        """Test _timed_query with a list response (like fetch_timeseries_for_document)."""
        # Callable returning a list (like fetch_timeseries_for_document)
        def query_fn():
            return [
                {"metadata": {"sequence": 1}, "values": {"cpu": 10.5}},
                {"metadata": {"sequence": 2}, "values": {"cpu": 12.3}},
                {"metadata": {"sequence": 3}, "values": {"cpu": 11.8}},
            ]

        result = _timed_query(query_fn)

        # Assertions
        assert "latency_ms" in result, "Missing latency_ms in result"
        assert "took_ms" in result, "Missing took_ms in result"
        assert "response" in result, "Missing response in result"

        assert result["took_ms"] == -1, f"Expected took_ms=-1 for list response, got {result['took_ms']}"
        assert result["latency_ms"] > 0, f"Expected positive latency_ms, got {result['latency_ms']}"
        assert isinstance(result["response"], list), "Expected list response"
        assert len(result["response"]) == 3, f"Expected 3 items in list, got {len(result['response'])}"

    def test_empty_list_response(self):
        """Test _timed_query with an empty list response."""
        # Callable returning an empty list
        def query_fn():
            return []

        result = _timed_query(query_fn)

        # Assertions
        assert "latency_ms" in result, "Missing latency_ms in result"
        assert "took_ms" in result, "Missing took_ms in result"
        assert "response" in result, "Missing response in result"

        assert result["took_ms"] == -1, f"Expected took_ms=-1 for empty list, got {result['took_ms']}"
        assert result["latency_ms"] > 0, f"Expected positive latency_ms, got {result['latency_ms']}"
        assert isinstance(result["response"], list), "Expected list response"
        assert len(result["response"]) == 0, f"Expected empty list, got {len(result['response'])}"

    def test_latency_measurement_accuracy(self):
        """Test that latency_ms is always computed regardless of response type."""
        import time

        # Callable that takes a known amount of time
        def slow_query_fn():
            time.sleep(0.01)  # 10ms
            return {"took": 5}

        result = _timed_query(slow_query_fn)

        # Latency should be >= 10ms (wall clock includes sleep + execution)
        assert result["latency_ms"] >= 10, f"Expected latency_ms >= 10ms, got {result['latency_ms']}"

        # took_ms should be from the response dict
        assert result["took_ms"] == 5, f"Expected took_ms=5, got {result['took_ms']}"

    def test_response_preservation(self):
        """Test that the original response is preserved exactly."""
        # Complex response to ensure no mutation
        original_response = {
            "took": 123,
            "hits": {
                "total": {"value": 1000, "relation": "eq"},
                "hits": [
                    {"_id": "1", "_source": {"field": "value1"}},
                    {"_id": "2", "_source": {"field": "value2"}},
                ]
            },
            "aggregations": {
                "by_field": {
                    "buckets": [
                        {"key": "bucket1", "doc_count": 500},
                        {"key": "bucket2", "doc_count": 500},
                    ]
                }
            }
        }

        def query_fn():
            return original_response

        result = _timed_query(query_fn)

        # Response should be identical to original
        assert result["response"] is original_response, "Response should be the same object"
        assert result["response"]["took"] == 123
        assert len(result["response"]["hits"]["hits"]) == 2
        assert len(result["response"]["aggregations"]["by_field"]["buckets"]) == 2


# Import _compute_latency_stats for testing
from tests.performance.test_opensearch_queries import _compute_latency_stats


class TestComputeLatencyStats:
    """Test suite for _compute_latency_stats percentile calculation."""

    def test_known_small_dataset(self):
        """
        Test percentile calculations with a known small dataset.

        Verifies that p50, p95, p99 are calculated correctly using
        nearest-rank method on a simple integer sequence.
        """
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        stats = _compute_latency_stats(data)

        # For n=10:
        # p50 (50th percentile): ceil(10 * 0.50) - 1 = ceil(5.0) - 1 = 4 -> data[4] = 5.0
        # p95 (95th percentile): ceil(10 * 0.95) - 1 = ceil(9.5) - 1 = 9 -> data[9] = 10.0
        # p99 (99th percentile): ceil(10 * 0.99) - 1 = ceil(9.9) - 1 = 9 -> data[9] = 10.0
        assert stats["mean"] == 5.5
        assert stats["min"] == 1.0
        assert stats["max"] == 10.0
        assert stats["p50"] == 5.0, f"Expected p50=5.0, got {stats['p50']}"
        assert stats["p95"] == 10.0, f"Expected p95=10.0, got {stats['p95']}"
        assert stats["p99"] == 10.0, f"Expected p99=10.0, got {stats['p99']}"

    def test_n20_p95_not_max(self):
        """
        Test that p95 with n=20 should not equal max.

        This is the bug case: with n=20, p95 should be the 19th element,
        not the 20th (max). Verifies the nearest-rank formula is correct.
        """
        # Create dataset where we can clearly see p95 vs max
        data = list(range(1, 21))  # [1, 2, 3, ..., 20]
        stats = _compute_latency_stats([float(x) for x in data])

        # For n=20:
        # p95: ceil(20 * 0.95) - 1 = ceil(19.0) - 1 = 18 -> data[18] = 19.0
        # max: 20.0
        assert stats["max"] == 20.0
        assert stats["p95"] == 19.0, f"Expected p95=19.0 (not max), got {stats['p95']}"
        assert stats["p95"] != stats["max"], "p95 should not equal max for n=20"

    def test_edge_case_n2(self):
        """
        Test percentile calculation with n=2 (minimal non-trivial case).

        Verifies behavior at the edge of the formula with very small datasets.
        """
        data = [1.0, 2.0]
        stats = _compute_latency_stats(data)

        # For n=2:
        # p50: ceil(2 * 0.50) - 1 = ceil(1.0) - 1 = 0 -> data[0] = 1.0
        # p95: ceil(2 * 0.95) - 1 = ceil(1.9) - 1 = 1 -> data[1] = 2.0
        # p99: ceil(2 * 0.99) - 1 = ceil(1.98) - 1 = 1 -> data[1] = 2.0
        assert stats["mean"] == 1.5
        assert stats["min"] == 1.0
        assert stats["max"] == 2.0
        assert stats["p50"] == 1.0, f"Expected p50=1.0, got {stats['p50']}"
        assert stats["p95"] == 2.0, f"Expected p95=2.0, got {stats['p95']}"
        assert stats["p99"] == 2.0, f"Expected p99=2.0, got {stats['p99']}"

    def test_edge_case_n1(self):
        """
        Test percentile calculation with n=1 (single element).

        All percentiles should equal the single value.
        """
        data = [42.0]
        stats = _compute_latency_stats(data)

        # For n=1, all percentiles should be the single value
        # p50: ceil(1 * 0.50) - 1 = ceil(0.5) - 1 = 0 -> data[0] = 42.0
        # p95: ceil(1 * 0.95) - 1 = ceil(0.95) - 1 = 0 -> data[0] = 42.0
        # p99: ceil(1 * 0.99) - 1 = ceil(0.99) - 1 = 0 -> data[0] = 42.0
        assert stats["mean"] == 42.0
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["p50"] == 42.0
        assert stats["p95"] == 42.0
        assert stats["p99"] == 42.0

    def test_empty_list(self):
        """
        Test percentile calculation with empty list.

        Should return all zeros without raising an exception.
        """
        data = []
        stats = _compute_latency_stats(data)

        # Empty list should return zeros for all stats
        assert stats["mean"] == 0
        assert stats["min"] == 0
        assert stats["max"] == 0
        assert stats["p50"] == 0
        assert stats["p95"] == 0
        assert stats["p99"] == 0

    def test_identical_values(self):
        """
        Test percentile calculation when all values are identical.

        All statistics should equal the constant value.
        """
        data = [7.0] * 100
        stats = _compute_latency_stats(data)

        assert stats["mean"] == 7.0
        assert stats["min"] == 7.0
        assert stats["max"] == 7.0
        assert stats["p50"] == 7.0
        assert stats["p95"] == 7.0
        assert stats["p99"] == 7.0

    def test_unsorted_input(self):
        """
        Test that function handles unsorted input correctly.

        The function should sort the data internally before computing percentiles.
        """
        data = [10.0, 1.0, 5.0, 3.0, 8.0, 2.0, 9.0, 4.0, 7.0, 6.0]
        stats = _compute_latency_stats(data)

        # Same expected values as test_known_small_dataset
        assert stats["mean"] == 5.5
        assert stats["min"] == 1.0
        assert stats["max"] == 10.0
        assert stats["p50"] == 5.0
        assert stats["p95"] == 10.0
        assert stats["p99"] == 10.0
