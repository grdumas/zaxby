#!/usr/bin/env python
"""
Standalone test runner for _timed_query helper function.

This script tests the _timed_query fix without requiring pytest or OpenSearch.
Run directly with: python tests/performance/run_helper_tests.py
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict


# Original version (with bug)
def _timed_query_original(fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Original version that assumes response is always a dict."""
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


# Fixed version
def _timed_query(fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute a query callable and capture both wall-clock and OpenSearch execution time.

    Args:
        fn: Callable that returns an OpenSearch response (dict or list).

    Returns:
        Dict with keys: latency_ms (wall clock), took_ms (OpenSearch execution), response.
    """
    start = time.time()
    response = fn()
    end = time.time()

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


def test_original_fails_with_list():
    """Test that original version fails with list response."""
    print("Testing original _timed_query with list response...")

    def query_fn():
        return [
            {"metadata": {"sequence": 1}, "values": {"cpu": 10.5}},
            {"metadata": {"sequence": 2}, "values": {"cpu": 12.3}},
        ]

    try:
        _timed_query_original(query_fn)
        print("  FAIL: Expected AttributeError but got no error!")
        return False
    except AttributeError as e:
        if "'list' object has no attribute 'get'" in str(e):
            print(f"  PASS: Got expected error: {e}")
            return True
        else:
            print(f"  FAIL: Got unexpected AttributeError: {e}")
            return False


def test_fixed_dict_with_took():
    """Test fixed version with dict response containing 'took'."""
    print("Testing fixed _timed_query with dict response (with 'took')...")

    def query_fn():
        return {"took": 42, "hits": {"total": {"value": 100}, "hits": []}}

    result = _timed_query(query_fn)

    assert result["took_ms"] == 42, f"Expected took_ms=42, got {result['took_ms']}"
    assert result["latency_ms"] > 0, f"Expected positive latency_ms"
    assert isinstance(result["response"], dict), "Expected dict response"

    print(f"  PASS: took_ms={result['took_ms']}, latency_ms={result['latency_ms']:.2f}ms")
    return True


def test_fixed_dict_without_took():
    """Test fixed version with dict response missing 'took'."""
    print("Testing fixed _timed_query with dict response (without 'took')...")

    def query_fn():
        return {"hits": {"total": {"value": 50}, "hits": []}, "aggregations": {}}

    result = _timed_query(query_fn)

    assert result["took_ms"] == -1, f"Expected took_ms=-1, got {result['took_ms']}"
    assert result["latency_ms"] > 0, f"Expected positive latency_ms"
    assert isinstance(result["response"], dict), "Expected dict response"

    print(f"  PASS: took_ms={result['took_ms']}, latency_ms={result['latency_ms']:.2f}ms")
    return True


def test_fixed_list_response():
    """Test fixed version with list response."""
    print("Testing fixed _timed_query with list response...")

    def query_fn():
        return [
            {"metadata": {"sequence": 1}, "values": {"cpu": 10.5}},
            {"metadata": {"sequence": 2}, "values": {"cpu": 12.3}},
            {"metadata": {"sequence": 3}, "values": {"cpu": 11.8}},
        ]

    result = _timed_query(query_fn)

    assert result["took_ms"] == -1, f"Expected took_ms=-1 for list, got {result['took_ms']}"
    assert result["latency_ms"] > 0, f"Expected positive latency_ms"
    assert isinstance(result["response"], list), "Expected list response"
    assert len(result["response"]) == 3, f"Expected 3 items"

    print(f"  PASS: took_ms={result['took_ms']}, latency_ms={result['latency_ms']:.2f}ms, response_len={len(result['response'])}")
    return True


def test_fixed_empty_list():
    """Test fixed version with empty list response."""
    print("Testing fixed _timed_query with empty list...")

    def query_fn():
        return []

    result = _timed_query(query_fn)

    assert result["took_ms"] == -1, f"Expected took_ms=-1 for empty list"
    assert result["latency_ms"] > 0, f"Expected positive latency_ms"
    assert isinstance(result["response"], list), "Expected list response"
    assert len(result["response"]) == 0, f"Expected empty list"

    print(f"  PASS: took_ms={result['took_ms']}, latency_ms={result['latency_ms']:.2f}ms")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing _timed_query helper function")
    print("=" * 60)
    print()

    tests = [
        test_original_fails_with_list,
        test_fixed_dict_with_took,
        test_fixed_dict_without_took,
        test_fixed_list_response,
        test_fixed_empty_list,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
