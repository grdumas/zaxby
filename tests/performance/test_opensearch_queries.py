"""
pytest-benchmark tests for OpenSearch query performance.

These tests benchmark OpenSearch queries directly against a live cluster. Unlike the
existing performance tests (which benchmark DataFrame operations), these exercise the
actual OpenSearch query layer: search, aggregation, timeseries lookup, scroll, and
concurrent load.

Tests automatically skip when OpenSearch is unavailable.

Run with: pytest tests/performance/test_opensearch_queries.py --benchmark-only -v
Filter by class: pytest tests/performance/test_opensearch_queries.py -k "TestResultsIndexQueries" -v
"""

from __future__ import annotations

import logging
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List

import pytest

from src.opensearch_client import BenchmarkDataSource
from src.query_service import (
    build_results_overview_aggregation_body,
    build_results_test_name_terms_aggregation_body,
    build_results_monthly_activity_histogram_body,
    build_results_run_timestamp_stats_body,
    RESULTS_ACTIVITY_TIMESTAMP_FIELD,
    MAX_SEARCH_HITS,
    MAX_PAGE_SIZE,
)
from src.investigation_templates import (
    FIELD_CLOUD_PROVIDER,
    FIELD_OS_DISTRIBUTION,
    FIELD_OS_VERSION,
    FIELD_TEST_NAME,
    FIELD_DOCUMENT_ID,
)

# Guard: pytest-benchmark is not in root requirements.txt
pytest.importorskip(
    "pytest_benchmark",
    reason="Performance tests require pytest-benchmark. Install with: pip install -r tests/performance/requirements.txt"
)

logger = logging.getLogger(__name__)


# --- Module-level helpers ---


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


def _log_query_metrics(name: str, stats: Dict[str, float], took_values: List[int]) -> None:
    """
    Log structured query metrics for baseline documentation.

    Args:
        name: Query name/description.
        stats: Latency statistics from _compute_latency_stats.
        took_values: List of OpenSearch 'took' values in milliseconds.
    """
    took_stats = _compute_latency_stats([float(t) for t in took_values if t >= 0])

    logger.info(
        f"{name} | "
        f"Latency: mean={stats['mean']:.1f}ms p50={stats['p50']:.1f}ms p95={stats['p95']:.1f}ms | "
        f"OpenSearch took: mean={took_stats['mean']:.1f}ms p50={took_stats['p50']:.1f}ms"
    )


# --- Test Class 1: Results Index Queries ---


class TestResultsIndexQueries:
    """
    Scenario 1: Results index queries -- filter by date range, cloud provider, OS version.

    Tests benchmark production query builders from query_service.py against a live
    OpenSearch results index. Expected: thousands of documents.
    """

    def test_results_overview_aggregation(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark results overview aggregation (cloud provider terms).

        Query: match_all with terms aggregation on metadata.cloud_provider.keyword.
        Expected baseline: < 50ms on ~5K docs.
        """
        body = build_results_overview_aggregation_body()
        result = benchmark(opensearch_client.search_results, body)

        # Capture OpenSearch-side query time
        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Results overview aggregation - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "by_cloud" in result["aggregations"], "Missing 'by_cloud' aggregation"
        assert result["hits"]["total"]["value"] > 0, "No documents found"

    def test_results_test_name_terms_aggregation(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark test name terms aggregation for category rollup.

        Query: match_all with terms aggregation on test.name.keyword.
        Expected baseline: < 100ms on ~5K docs.
        """
        body = build_results_test_name_terms_aggregation_body()
        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Test name terms aggregation - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "by_test_name" in result["aggregations"], "Missing 'by_test_name' aggregation"

    def test_results_monthly_activity_histogram(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark monthly activity histogram on test timestamps.

        Query: match_all with date_histogram aggregation on metadata.test_timestamp.
        Expected baseline: < 80ms on ~5K docs.
        """
        body = build_results_monthly_activity_histogram_body()
        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Monthly activity histogram - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "by_month" in result["aggregations"], "Missing 'by_month' aggregation"

    def test_results_timestamp_stats(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark timestamp stats aggregation for scope footnote.

        Query: match_all with stats aggregation on metadata.test_timestamp.
        Expected baseline: < 30ms on ~5K docs.
        """
        body = build_results_run_timestamp_stats_body()
        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Timestamp stats aggregation - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "timestamp_stats" in result["aggregations"], "Missing 'timestamp_stats' aggregation"

    def test_results_filter_by_cloud_provider(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark term filter on cloud provider.

        Query: bool/must with term on metadata.cloud_provider.keyword = "aws".
        Expected baseline: < 40ms on ~5K docs.
        """
        body = {
            "size": MAX_PAGE_SIZE,
            "query": {
                "bool": {
                    "must": [
                        {"term": {FIELD_CLOUD_PROVIDER: "aws"}}
                    ]
                }
            },
            "sort": [
                {RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"},
                {FIELD_DOCUMENT_ID: "asc"}
            ]
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Filter by cloud provider - OpenSearch took: {took_ms}ms")

        # Validate results
        assert "hits" in result, "Response missing hits"
        hits = result.get("hits", {}).get("hits", [])
        if hits:
            # Verify filter worked (defensive access to nested fields)
            first_hit = hits[0]
            source = first_hit.get("_source", {})
            metadata = source.get("metadata", {})
            assert metadata.get("cloud_provider") == "aws", "Expected cloud_provider=aws in first hit"

    def test_results_filter_by_date_range(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark range filter on test timestamp.

        Query: range on metadata.test_timestamp (last 30 days).
        Expected baseline: < 50ms on ~5K docs.
        """
        # Use a 30-day window
        body = {
            "size": MAX_PAGE_SIZE,
            "query": {
                "range": {
                    RESULTS_ACTIVITY_TIMESTAMP_FIELD: {
                        "gte": "now-30d/d",
                        "lte": "now/d"
                    }
                }
            },
            "sort": [
                {RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"},
                {FIELD_DOCUMENT_ID: "asc"}
            ]
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Filter by date range - OpenSearch took: {took_ms}ms")

        # Validate results
        assert "hits" in result, "Response missing hits"

    def test_results_filter_by_os_version(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark multi-field term filter on OS distribution and version.

        Query: bool/must with terms on OS distribution and version.
        Expected baseline: < 60ms on ~5K docs.
        """
        body = {
            "size": MAX_PAGE_SIZE,
            "query": {
                "bool": {
                    "must": [
                        {"term": {FIELD_OS_DISTRIBUTION: "rhel"}},
                        {"term": {FIELD_OS_VERSION: "9.5"}}
                    ]
                }
            },
            "sort": [
                {RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"},
                {FIELD_DOCUMENT_ID: "asc"}
            ]
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Filter by OS version - OpenSearch took: {took_ms}ms")

        # Validate results
        assert "hits" in result, "Response missing hits"

    def test_results_nightly_runs_aggregation(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark nightly runs aggregation with nested pass/fail counts.

        Query: date_histogram with filter sub-aggregations for pass/fail counts.
        Expected baseline: < 150ms on ~5K docs.
        """
        body = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "by_day": {
                    "date_histogram": {
                        "field": RESULTS_ACTIVITY_TIMESTAMP_FIELD,
                        "calendar_interval": "1d",
                        "order": {"_key": "desc"}
                    },
                    "aggs": {
                        "pass_count": {
                            "filter": {"term": {"results.status.keyword": "PASS"}}
                        },
                        "fail_count": {
                            "filter": {"term": {"results.status.keyword": "FAIL"}}
                        },
                        "by_test_name": {
                            "terms": {
                                "field": FIELD_TEST_NAME,
                                "size": 200
                            }
                        }
                    }
                }
            }
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Nightly runs aggregation - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "by_day" in result["aggregations"], "Missing 'by_day' aggregation"


# --- Test Class 2: Timeseries Index Queries ---


class TestTimeseriesIndexQueries:
    """
    Scenario 2: Timeseries index queries -- point lookups by document_id, bounded windows.

    Tests benchmark timeseries queries against the timeseries index. Expected: hundreds
    of thousands of documents.
    """

    def test_timeseries_point_lookup(self, benchmark, opensearch_client: BenchmarkDataSource, sample_document_ids: List[str], opensearch_timeseries_count: int):
        """
        Benchmark single timeseries point lookup by document_id.

        Query: term on metadata.document_id with sort by metadata.sequence.
        Expected baseline: < 20ms for ~1K points per document.
        """
        doc_id = sample_document_ids[0]

        result = benchmark(
            opensearch_client.fetch_timeseries_for_document,
            document_id=doc_id
        )

        # fetch_timeseries_for_document returns a list of documents
        assert isinstance(result, list), "Expected list of timeseries documents"
        logger.info(f"Timeseries point lookup - Retrieved {len(result)} points for document {doc_id}")

    def test_timeseries_point_lookup_large(self, benchmark, opensearch_client: BenchmarkDataSource, sample_document_ids: List[str], opensearch_timeseries_count: int):
        """
        Benchmark large timeseries point lookup (size=10000).

        Query: term on metadata.document_id with size=10000.
        Expected baseline: < 100ms for 10K points.
        """
        doc_id = sample_document_ids[0]

        result = benchmark(
            opensearch_client.fetch_timeseries_for_document,
            document_id=doc_id,
            size=10000
        )

        assert isinstance(result, list), "Expected list of timeseries documents"
        logger.info(f"Large timeseries lookup - Retrieved {len(result)} points for document {doc_id}")

    def test_timeseries_bounded_time_window(self, benchmark, opensearch_client: BenchmarkDataSource, opensearch_timeseries_count: int):
        """
        Benchmark timeseries range query on test timestamp.

        Query: range on metadata.test_timestamp (last 7 days).
        Expected baseline: < 200ms on large timeseries index.
        """
        body = {
            "size": 1000,
            "query": {
                "range": {
                    RESULTS_ACTIVITY_TIMESTAMP_FIELD: {
                        "gte": "now-7d/d",
                        "lte": "now/d"
                    }
                }
            },
            "sort": [
                {RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"},
                {"metadata.sequence": "asc"}
            ]
        }

        result = benchmark(opensearch_client.search_timeseries, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Timeseries bounded window - OpenSearch took: {took_ms}ms")

        # Validate results
        assert "hits" in result, "Response missing hits"


# --- Test Class 3: Aggregation Queries ---


class TestAggregationQueries:
    """
    Scenario 3: Aggregation queries -- group by category, compute stats across large sets.

    Tests benchmark various aggregation patterns used in the dashboard.
    """

    def test_aggregation_category_rollup(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark category rollup aggregation (test.name terms).

        Query: terms aggregation on test.name.keyword (200 buckets).
        Expected baseline: < 100ms on ~5K docs.
        """
        body = build_results_test_name_terms_aggregation_body()
        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Category rollup aggregation - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "by_test_name" in result["aggregations"], "Missing 'by_test_name' aggregation"

    def test_aggregation_multi_field_terms(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark multi-field terms aggregation (cloud + OS version).

        Query: nested terms aggregations on cloud_provider and OS version.
        Expected baseline: < 80ms on ~5K docs.
        """
        body = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "by_cloud": {
                    "terms": {
                        "field": FIELD_CLOUD_PROVIDER,
                        "size": 10
                    },
                    "aggs": {
                        "by_os_version": {
                            "terms": {
                                "field": FIELD_OS_VERSION,
                                "size": 20
                            }
                        }
                    }
                }
            }
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Multi-field terms aggregation - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "by_cloud" in result["aggregations"], "Missing 'by_cloud' aggregation"

    def test_aggregation_stats_on_primary_metric(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark stats aggregation on primary metric values.

        Query: stats aggregation on results.primary_metric.value.
        Expected baseline: < 50ms on ~5K docs.
        """
        body = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "metric_stats": {
                    "stats": {
                        "field": "results.primary_metric.value"
                    }
                }
            }
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Stats on primary metric - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "metric_stats" in result["aggregations"], "Missing 'metric_stats' aggregation"

    def test_aggregation_nested_date_histogram(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark nested date histogram with pass/fail sub-aggregations.

        Query: date_histogram with filter sub-aggs (nightly runs pattern).
        Expected baseline: < 150ms on ~5K docs.
        """
        body = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "by_day": {
                    "date_histogram": {
                        "field": RESULTS_ACTIVITY_TIMESTAMP_FIELD,
                        "calendar_interval": "1d",
                        "order": {"_key": "desc"}
                    },
                    "aggs": {
                        "pass_count": {
                            "filter": {"term": {"results.status.keyword": "PASS"}}
                        },
                        "fail_count": {
                            "filter": {"term": {"results.status.keyword": "FAIL"}}
                        }
                    }
                }
            }
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Nested date histogram - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "by_day" in result["aggregations"], "Missing 'by_day' aggregation"

    def test_aggregation_cardinality(self, benchmark, opensearch_client: BenchmarkDataSource):
        """
        Benchmark cardinality aggregation on document IDs (unique run count).

        Query: cardinality aggregation on metadata.document_id.
        Expected baseline: < 40ms on ~5K docs.
        """
        body = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "unique_documents": {
                    "cardinality": {
                        "field": FIELD_DOCUMENT_ID
                    }
                }
            }
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Cardinality aggregation - OpenSearch took: {took_ms}ms")

        # Validate structure
        assert "aggregations" in result, "Response missing aggregations"
        assert "unique_documents" in result["aggregations"], "Missing 'unique_documents' aggregation"


# --- Test Class 4: Concurrent Query Load ---


class TestConcurrentQueryLoad:
    """
    Scenario 4: Concurrent query load -- multiple users running queries simultaneously.

    Tests use ThreadPoolExecutor with manual timing (not pytest-benchmark) to simulate
    concurrent user load and measure latency degradation and cluster health impact.
    """

    def test_concurrent_pulse_queries(self, opensearch_client: BenchmarkDataSource):
        """
        Test concurrent Pulse KPI queries (5 users x 4 queries each).

        Simulates 5 concurrent users each running the 4 main Pulse aggregations:
        - Results overview (cloud provider terms)
        - Test name terms
        - Monthly activity histogram
        - Timestamp stats

        Expected: < 200ms p95 latency with 5 concurrent users.
        """
        queries = [
            lambda: opensearch_client.search_results(build_results_overview_aggregation_body()),
            lambda: opensearch_client.search_results(build_results_test_name_terms_aggregation_body()),
            lambda: opensearch_client.search_results(build_results_monthly_activity_histogram_body()),
            lambda: opensearch_client.search_results(build_results_run_timestamp_stats_body()),
        ]

        num_users = 5
        results = []

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
                    logger.error(f"Query failed: {exc}")
                    pytest.fail(f"Concurrent query failed: {exc}")

        # Compute statistics
        latencies = [r["latency_ms"] for r in results]
        took_values = [r["took_ms"] for r in results]

        stats = _compute_latency_stats(latencies)
        _log_query_metrics("Concurrent Pulse queries", stats, took_values)

        # Assertions
        assert len(results) == num_users * len(queries), "Some queries failed"
        assert stats["p95"] < 500, f"P95 latency too high: {stats['p95']:.1f}ms"

    def test_concurrent_investigation_queries(self, opensearch_client: BenchmarkDataSource, sample_document_ids: List[str]):
        """
        Test concurrent investigation queries (5 users x different filter patterns).

        Simulates 5 concurrent users each running different filter queries:
        - Cloud provider filter
        - Date range filter
        - OS version filter
        - Document ID lookup
        - Multi-field filter

        Expected: < 250ms p95 latency with 5 concurrent users.
        """
        queries = [
            # Cloud provider filter
            lambda: opensearch_client.search_results({
                "size": MAX_PAGE_SIZE,
                "query": {"bool": {"must": [{"term": {FIELD_CLOUD_PROVIDER: "aws"}}]}},
                "sort": [{RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"}, {FIELD_DOCUMENT_ID: "asc"}]
            }),
            # Date range filter
            lambda: opensearch_client.search_results({
                "size": MAX_PAGE_SIZE,
                "query": {"range": {RESULTS_ACTIVITY_TIMESTAMP_FIELD: {"gte": "now-30d/d", "lte": "now/d"}}},
                "sort": [{RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"}, {FIELD_DOCUMENT_ID: "asc"}]
            }),
            # OS version filter
            lambda: opensearch_client.search_results({
                "size": MAX_PAGE_SIZE,
                "query": {"bool": {"must": [{"term": {FIELD_OS_DISTRIBUTION: "rhel"}}, {"term": {FIELD_OS_VERSION: "9.5"}}]}},
                "sort": [{RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"}, {FIELD_DOCUMENT_ID: "asc"}]
            }),
            # Document ID lookup
            lambda: opensearch_client.search_results({
                "size": 1,
                "query": {"term": {FIELD_DOCUMENT_ID: sample_document_ids[0]}},
                "sort": [{RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"}, {FIELD_DOCUMENT_ID: "asc"}]
            }),
            # Multi-field filter
            lambda: opensearch_client.search_results({
                "size": MAX_PAGE_SIZE,
                "query": {"bool": {"must": [
                    {"term": {FIELD_CLOUD_PROVIDER: "aws"}},
                    {"term": {FIELD_OS_DISTRIBUTION: "rhel"}},
                    {"range": {RESULTS_ACTIVITY_TIMESTAMP_FIELD: {"gte": "now-7d/d"}}}
                ]}},
                "sort": [{RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"}, {FIELD_DOCUMENT_ID: "asc"}]
            }),
        ]

        num_users = 5
        results = []

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
                    logger.error(f"Query failed: {exc}")
                    pytest.fail(f"Concurrent query failed: {exc}")

        # Compute statistics
        latencies = [r["latency_ms"] for r in results]
        took_values = [r["took_ms"] for r in results]

        stats = _compute_latency_stats(latencies)
        _log_query_metrics("Concurrent investigation queries", stats, took_values)

        # Assertions
        assert len(results) == num_users * len(queries), "Some queries failed"
        assert stats["p95"] < 600, f"P95 latency too high: {stats['p95']:.1f}ms"

    def test_concurrent_mixed_workload(self, opensearch_client: BenchmarkDataSource, sample_document_ids: List[str], opensearch_timeseries_count: int):
        """
        Test mixed workload (10 users x Pulse/Investigate/Track patterns).

        Simulates realistic dashboard usage with 10 concurrent users running
        a mix of:
        - Pulse aggregations
        - Investigation filters
        - Timeseries lookups

        Expected: < 400ms p95 latency with 10 concurrent users.
        """
        queries = [
            # Pulse: overview aggregation
            lambda: opensearch_client.search_results(build_results_overview_aggregation_body()),
            # Pulse: category rollup
            lambda: opensearch_client.search_results(build_results_test_name_terms_aggregation_body()),
            # Investigate: cloud provider filter
            lambda: opensearch_client.search_results({
                "size": MAX_PAGE_SIZE,
                "query": {"bool": {"must": [{"term": {FIELD_CLOUD_PROVIDER: "azure"}}]}},
                "sort": [{RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"}, {FIELD_DOCUMENT_ID: "asc"}]
            }),
            # Investigate: date range
            lambda: opensearch_client.search_results({
                "size": MAX_PAGE_SIZE,
                "query": {"range": {RESULTS_ACTIVITY_TIMESTAMP_FIELD: {"gte": "now-14d/d", "lte": "now/d"}}},
                "sort": [{RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"}, {FIELD_DOCUMENT_ID: "asc"}]
            }),
            # Track: timeseries lookup
            lambda: opensearch_client.fetch_timeseries_for_document(document_id=sample_document_ids[0]),
        ]

        num_users = 10
        results = []

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
                    logger.error(f"Query failed: {exc}")
                    pytest.fail(f"Concurrent query failed: {exc}")

        # Compute statistics
        latencies = [r["latency_ms"] for r in results]
        took_values = [r["took_ms"] for r in results if r["took_ms"] >= 0]  # timeseries returns list, no 'took'

        stats = _compute_latency_stats(latencies)
        _log_query_metrics("Concurrent mixed workload", stats, took_values if took_values else [-1])

        # Assertions
        assert len(results) == num_users * len(queries), "Some queries failed"
        assert stats["p95"] < 800, f"P95 latency too high: {stats['p95']:.1f}ms"

    @pytest.mark.parametrize("num_users", [1, 5, 10, 20])
    def test_concurrent_scaling(self, opensearch_client: BenchmarkDataSource, num_users: int):
        """
        Test query latency scaling with increasing concurrent users.

        Parameterized test measuring latency degradation as concurrency increases
        from 1 to 20 users. Each user runs a simple overview aggregation.

        Expected:
        - 1 user: < 50ms p95
        - 5 users: < 150ms p95
        - 10 users: < 300ms p95
        - 20 users: < 600ms p95
        """
        query_fn = lambda: opensearch_client.search_results(build_results_overview_aggregation_body())

        results = []

        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(_timed_query, query_fn) for _ in range(num_users)]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    logger.error(f"Query failed: {exc}")
                    pytest.fail(f"Concurrent query failed: {exc}")

        # Compute statistics
        latencies = [r["latency_ms"] for r in results]
        took_values = [r["took_ms"] for r in results]

        stats = _compute_latency_stats(latencies)
        _log_query_metrics(f"Concurrent scaling ({num_users} users)", stats, took_values)

        # Assertions
        assert len(results) == num_users, "Some queries failed"

        # Adaptive threshold based on user count
        if num_users == 1:
            assert stats["p95"] < 100, f"P95 latency too high for 1 user: {stats['p95']:.1f}ms"
        elif num_users == 5:
            assert stats["p95"] < 300, f"P95 latency too high for 5 users: {stats['p95']:.1f}ms"
        elif num_users == 10:
            assert stats["p95"] < 600, f"P95 latency too high for 10 users: {stats['p95']:.1f}ms"
        elif num_users == 20:
            assert stats["p95"] < 1200, f"P95 latency too high for 20 users: {stats['p95']:.1f}ms"


# --- Test Class 5: Large Result Pagination ---


class TestLargeResultPagination:
    """
    Scenario 5: Large result pagination -- scroll through 10K+ document sets.

    Tests benchmark scroll API and search_after pagination patterns for handling
    large result sets.
    """

    def test_scroll_results_full(self, benchmark, opensearch_client: BenchmarkDataSource, opensearch_results_count: int):
        """
        Benchmark full scroll of results index (up to 10K docs).

        Uses scroll API with 2m timeout and batch_size=1000.
        Expected baseline: < 2000ms for 10K docs on production cluster.
        """
        if opensearch_results_count < 100:
            pytest.skip(f"Insufficient documents for scroll test: {opensearch_results_count}")

        # Limit to min(results_count, 10000) to avoid excessive test time
        max_docs = min(opensearch_results_count, 10000)

        result = benchmark(opensearch_client.scroll_results, max_docs=max_docs)

        # Validate results
        assert isinstance(result, list), "Expected list of documents"
        assert len(result) > 0, "Scroll returned no documents"
        logger.info(f"Scroll retrieved {len(result)} documents")

    def test_scroll_results_batched(self, opensearch_client: BenchmarkDataSource, opensearch_results_count: int):
        """
        Benchmark scroll with manual per-batch timing.

        Measures latency for each scroll batch (batch_size=1000) to identify
        pagination performance characteristics.

        Expected: First batch < 100ms, subsequent batches < 50ms.
        """
        if opensearch_results_count < 100:
            pytest.skip(f"Insufficient documents for scroll test: {opensearch_results_count}")

        max_docs = min(opensearch_results_count, 5000)  # Smaller limit for batched test
        batch_size = 1000

        try:
            batch_latencies = []
            all_documents = []

            # Initial search with scroll
            logger.debug(f"OpenSearch operation: search with scroll on index {opensearch_client.results_index}")
            start = time.perf_counter()
            response = opensearch_client.client.search(
                index=opensearch_client.results_index,
                scroll="2m",
                size=batch_size,
                body={"query": {"match_all": {}}},
            )
            first_batch_latency = (time.perf_counter() - start) * 1000
            batch_latencies.append(first_batch_latency)

            # Defensive access to _scroll_id and hits
            scroll_id = response.get("_scroll_id")
            hits = response.get("hits", {}).get("hits", [])
            all_documents.extend([hit.get("_source", {}) for hit in hits if "_source" in hit])

            # Subsequent scroll batches
            while len(hits) > 0 and len(all_documents) < max_docs and scroll_id:
                logger.debug("OpenSearch operation: scroll")
                start = time.perf_counter()
                response = opensearch_client.client.scroll(scroll_id=scroll_id, scroll="2m")
                batch_latency = (time.perf_counter() - start) * 1000
                batch_latencies.append(batch_latency)

                scroll_id = response.get("_scroll_id")
                hits = response.get("hits", {}).get("hits", [])
                all_documents.extend([hit.get("_source", {}) for hit in hits if "_source" in hit])

            # Clear scroll (only if scroll_id is valid)
            if scroll_id:
                try:
                    logger.debug("OpenSearch operation: clear_scroll")
                    opensearch_client.client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass

            # Compute and log statistics
            stats = _compute_latency_stats(batch_latencies)
            logger.info(
                f"Scroll batched: {len(batch_latencies)} batches, {len(all_documents)} docs | "
                f"First batch: {batch_latencies[0]:.1f}ms | "
                f"Mean: {stats['mean']:.1f}ms | P95: {stats['p95']:.1f}ms"
            )

            # Assertions
            assert len(all_documents) > 0, "Scroll returned no documents"
            assert stats["mean"] < 200, f"Mean batch latency too high: {stats['mean']:.1f}ms"

        except Exception as exc:
            logger.error(f"Scroll batched test failed: {exc}")
            pytest.fail(f"Scroll batched test failed: {exc}")

    def test_large_search_with_size(self, benchmark, opensearch_client: BenchmarkDataSource, opensearch_results_count: int):
        """
        Benchmark large single search with size=MAX_SEARCH_HITS (10000).

        Tests non-scroll approach for retrieving large result sets in one request.
        Expected baseline: < 500ms for 10K docs.
        """
        if opensearch_results_count < 100:
            pytest.skip(f"Insufficient documents for large search test: {opensearch_results_count}")

        body = {
            "size": MAX_SEARCH_HITS,
            "query": {"match_all": {}},
            "sort": [
                {RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"},
                {FIELD_DOCUMENT_ID: "asc"}
            ]
        }

        result = benchmark(opensearch_client.search_results, body)

        took_ms = result.get("took", -1)
        assert took_ms >= 0, "Response missing 'took' field"
        logger.info(f"Large search (size={MAX_SEARCH_HITS}) - OpenSearch took: {took_ms}ms")

        # Validate results
        assert "hits" in result, "Response missing hits"
        hits = result.get("hits", {}).get("hits", [])
        logger.info(f"Large search retrieved {len(hits)} documents")

    def test_search_after_pagination(self, opensearch_client: BenchmarkDataSource, opensearch_results_count: int):
        """
        Benchmark search_after pagination pattern for deep pages.

        Implements the search_after strategy documented in query_service.py:
        - Initial search with sort
        - Subsequent pages using search_after with last hit's sort values

        Expected: Each page < 100ms for page_size=500.
        """
        if opensearch_results_count < 100:
            pytest.skip(f"Insufficient documents for search_after test: {opensearch_results_count}")

        page_size = 500
        max_pages = 5  # Test first 5 pages (2500 docs)

        try:
            page_latencies = []
            all_documents = []

            # Initial search
            body = {
                "size": page_size,
                "query": {"match_all": {}},
                "sort": [
                    {RESULTS_ACTIVITY_TIMESTAMP_FIELD: "desc"},
                    {FIELD_DOCUMENT_ID: "asc"}
                ]
            }

            start = time.perf_counter()
            response = opensearch_client.search_results(body)
            first_page_latency = (time.perf_counter() - start) * 1000
            page_latencies.append(first_page_latency)

            hits = response.get("hits", {}).get("hits", [])
            all_documents.extend([hit.get("_source", {}) for hit in hits if "_source" in hit])

            # Subsequent pages with search_after
            for page_num in range(1, max_pages):
                if not hits:
                    break

                # Get sort values from last hit (defensive access)
                last_hit = hits[-1]
                last_hit_sort = last_hit.get("sort")
                if not last_hit_sort:
                    break
                body["search_after"] = last_hit_sort

                start = time.perf_counter()
                response = opensearch_client.search_results(body)
                page_latency = (time.perf_counter() - start) * 1000
                page_latencies.append(page_latency)

                hits = response.get("hits", {}).get("hits", [])
                all_documents.extend([hit.get("_source", {}) for hit in hits if "_source" in hit])

            # Compute and log statistics
            stats = _compute_latency_stats(page_latencies)
            logger.info(
                f"search_after pagination: {len(page_latencies)} pages, {len(all_documents)} docs | "
                f"First page: {page_latencies[0]:.1f}ms | "
                f"Mean: {stats['mean']:.1f}ms | P95: {stats['p95']:.1f}ms"
            )

            # Assertions
            assert len(all_documents) > 0, "search_after returned no documents"
            assert stats["mean"] < 200, f"Mean page latency too high: {stats['mean']:.1f}ms"
            assert stats["p95"] < 400, f"P95 page latency too high: {stats['p95']:.1f}ms"

        except Exception as exc:
            logger.error(f"search_after pagination test failed: {exc}")
            pytest.fail(f"search_after pagination test failed: {exc}")
