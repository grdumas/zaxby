"""
Shared helper functions for OpenSearch performance benchmarks.

This module contains reusable timing and statistics functions used across
benchmark tests. By centralizing these helpers, unit tests can validate the
actual production code rather than testing copies.
"""
import math
import statistics
import time
from typing import Any, Callable, Dict, List


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


def _compute_latency_stats(latencies: List[float]) -> Dict[str, float]:
    """
    Compute latency statistics from a list of measurements.

    Uses nearest-rank percentile calculation: for percentile p,
    index = min(n-1, max(0, ceil(p*n) - 1))

    Args:
        latencies: List of latency values in milliseconds.

    Returns:
        Dict with keys: mean, min, max, p50, p95, p99.
    """
    if not latencies:
        return {"mean": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    # Nearest-rank percentile calculation
    def percentile(p: float) -> float:
        idx = min(n - 1, max(0, math.ceil(p * n) - 1))
        return sorted_latencies[idx]

    return {
        "mean": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
    }
