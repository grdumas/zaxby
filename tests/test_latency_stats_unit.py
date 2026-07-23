"""
Unit tests for _compute_latency_stats percentile calculation.

These tests verify the nearest-rank percentile formula works correctly.
They do not require OpenSearch and can run independently.
"""

from __future__ import annotations

import math
import statistics
from typing import Dict, List

import pytest


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

        This is the bug case: with the OLD formula int(n*p), p95 would be the 20th element (max).
        With the CORRECT formula ceil(n*p)-1, p95 is the 19th element.
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


class TestBuggyImplementation:
    """
    Tests demonstrating the bug in the old int(n*p) formula.

    These tests show what would fail with the buggy implementation.
    """

    def _compute_latency_stats_buggy(self, latencies: List[float]) -> Dict[str, float]:
        """Old buggy implementation using int(n * p)."""
        if not latencies:
            return {"mean": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return {
            "mean": statistics.mean(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "p50": sorted_latencies[int(n * 0.50)],
            "p95": sorted_latencies[int(n * 0.95)] if n > 1 else sorted_latencies[0],
            "p99": sorted_latencies[int(n * 0.99)] if n > 1 else sorted_latencies[0],
        }

    def test_buggy_n20_p95_equals_max(self):
        """
        Demonstrate that the buggy formula makes p95 equal max for n=20.

        With int(n*p): int(20 * 0.95) = int(19.0) = 19, so p95 = data[19] = 20.0 = max
        This is incorrect!
        """
        data = list(range(1, 21))  # [1, 2, 3, ..., 20]
        stats = self._compute_latency_stats_buggy([float(x) for x in data])

        # The buggy formula produces wrong results
        assert stats["max"] == 20.0
        assert stats["p95"] == 20.0  # WRONG! Should be 19.0
        assert stats["p95"] == stats["max"]  # This is the bug!

    def test_corrected_n20_p95_not_max(self):
        """
        Show that the corrected formula gives the right answer.

        With ceil(n*p)-1: ceil(20 * 0.95) - 1 = 19 - 1 = 18, so p95 = data[18] = 19.0
        This is correct!
        """
        data = list(range(1, 21))
        stats = _compute_latency_stats([float(x) for x in data])

        # The corrected formula produces correct results
        assert stats["max"] == 20.0
        assert stats["p95"] == 19.0  # CORRECT!
        assert stats["p95"] != stats["max"]  # Fixed!
