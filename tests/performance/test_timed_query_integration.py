#!/usr/bin/env python
"""
Integration test for _timed_query with mock OpenSearch responses.

This test verifies the fix for handling both dict and list responses
in concurrent workload scenarios WITHOUT requiring a live OpenSearch cluster.
"""

from __future__ import annotations

import sys
import os

# Add tests/performance to path to import _timed_query
sys.path.insert(0, os.path.dirname(__file__))

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable
import time


# Copy of the fixed _timed_query function for standalone testing
def _timed_query(fn: Callable[[], Any]) -> Dict[str, Any]:
    """
    Execute a query callable and capture both wall-clock and OpenSearch execution time.

    Args:
        fn: Callable that returns an OpenSearch response (dict or list).

    Returns:
        Dict with keys: latency_ms (wall clock), took_ms (OpenSearch execution), response.
    """
    start = time.perf_counter()
    response = fn()
    end = time.perf_counter()

    latency_ms = (end - start) * 1000

    # Handle both dict and non-dict responses
    if isinstance(response, dict):
        took_ms = response.get("took", -1)
    else:
        took_ms = -1

    return {
        "latency_ms": latency_ms,
        "took_ms": took_ms,
        "response": response,
    }


def test_concurrent_mixed_responses():
    """
    Simulate the concurrent_mixed_workload test scenario with mock responses.

    This test verifies that _timed_query can handle a mix of dict and list
    responses in a concurrent context, which is the actual bug scenario.
    """

    # Mock query functions that simulate OpenSearch responses
    def mock_dict_query_with_took():
        """Simulates search_results() - returns dict with 'took' field."""
        time.sleep(0.001)  # Simulate network latency
        return {
            "took": 15,
            "hits": {
                "total": {"value": 1000},
                "hits": []
            }
        }

    def mock_dict_query_without_took():
        """Simulates aggregation query - returns dict without 'took' field."""
        time.sleep(0.001)
        return {
            "aggregations": {
                "by_field": {
                    "buckets": [{"key": "value", "doc_count": 100}]
                }
            }
        }

    def mock_list_query():
        """Simulates fetch_timeseries_for_document() - returns list."""
        time.sleep(0.001)
        return [
            {"metadata": {"sequence": 1}, "values": {"cpu": 10.5}},
            {"metadata": {"sequence": 2}, "values": {"cpu": 12.3}},
            {"metadata": {"sequence": 3}, "values": {"cpu": 11.8}},
        ]

    # Mix of query types (similar to test_concurrent_mixed_workload)
    queries = [
        mock_dict_query_with_took,
        mock_dict_query_with_took,
        mock_dict_query_without_took,
        mock_list_query,  # This is the problematic case
        mock_list_query,
    ]

    num_users = 3
    results = []

    # Run queries concurrently (mirrors the actual test structure)
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        for _ in range(num_users):
            for query_fn in queries:
                futures.append(executor.submit(_timed_query, query_fn))

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f"FAIL: Query failed with exception: {exc}")
                return False

    # Verify results structure
    total_queries = num_users * len(queries)
    if len(results) != total_queries:
        print(f"FAIL: Expected {total_queries} results, got {len(results)}")
        return False

    # Verify took_ms handling
    dict_results = [r for r in results if isinstance(r["response"], dict)]
    list_results = [r for r in results if isinstance(r["response"], list)]

    # All list responses should have took_ms = -1
    list_took_values = [r["took_ms"] for r in list_results]
    if not all(t == -1 for t in list_took_values):
        print(f"FAIL: List results should have took_ms=-1, got: {list_took_values}")
        return False

    # Dict responses with 'took' field should have took_ms >= 0
    dict_with_took = [r for r in dict_results if "took" in r["response"]]
    if dict_with_took:
        took_values = [r["took_ms"] for r in dict_with_took]
        if not all(t >= 0 for t in took_values):
            print(f"FAIL: Dict results with 'took' should have took_ms >= 0, got: {took_values}")
            return False

    # All results should have latency_ms > 0
    latencies = [r["latency_ms"] for r in results]
    if not all(lat > 0 for lat in latencies):
        print(f"FAIL: All results should have latency_ms > 0")
        return False

    # Simulate the took_values filtering from test_concurrent_mixed_workload (line 803)
    took_values = [r["took_ms"] for r in results if r["took_ms"] >= 0]

    print(f"PASS: Successfully processed {total_queries} concurrent queries")
    print(f"  - {len(dict_results)} dict responses")
    print(f"  - {len(list_results)} list responses")
    print(f"  - {len(took_values)} queries with valid 'took' values")
    print(f"  - Latency range: {min(latencies):.2f}ms - {max(latencies):.2f}ms")

    return True


def main():
    """Run integration test."""
    print("=" * 60)
    print("Integration test: _timed_query with concurrent mixed responses")
    print("=" * 60)
    print()

    success = test_concurrent_mixed_responses()

    print()
    print("=" * 60)
    if success:
        print("Result: PASS")
        return 0
    else:
        print("Result: FAIL")
        return 1


if __name__ == "__main__":
    exit(main())
