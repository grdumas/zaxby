"""
Track KPI calculations with baseline comparison (RPOPC-1162).

Provides baseline vs nightly delta calculations for performance benchmarks,
supporting both percentage change and absolute change calculations with
regression detection integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.regression_detection import (
    filter_dataframe_for_regression_math,
    is_regression_for_test_name,
    percent_change,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BaselineConfig:
    """
    Configuration for baseline comparison.

    Attributes:
        baseline_id: Unique identifier for the baseline dataset
        date_range: Tuple of (start_date, end_date) for baseline data collection
        benchmark_filter: Optional dictionary of filters to apply to benchmarks
    """

    baseline_id: str
    date_range: tuple[datetime, datetime]
    benchmark_filter: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class BenchmarkDelta:
    """
    Delta calculation for a single benchmark between baseline and nightly.

    Attributes:
        benchmark_name: Name of the benchmark (test.name)
        metric_name: Name of the metric being compared
        baseline_mean: Mean value from baseline dataset
        nightly_mean: Mean value from nightly run
        percent_change: Percentage change (baseline to nightly)
        absolute_change: Absolute change (nightly - baseline)
        is_regression: Whether change exceeds regression threshold
        status: One of 'unchanged', 'added', 'removed', 'changed'
    """

    benchmark_name: str
    metric_name: str
    baseline_mean: Optional[float]
    nightly_mean: Optional[float]
    percent_change: Optional[float]
    absolute_change: Optional[float]
    is_regression: bool
    status: str


@dataclass(frozen=True)
class TrackKpiResult:
    """
    Result bundle for baseline vs nightly comparison.

    Attributes:
        baseline_config: Configuration used for baseline
        nightly_timestamp: Timestamp of nightly run
        deltas: List of benchmark deltas
        summary: Summary statistics
        source: Data source ('opensearch' or 'synthetic')
        error: Optional error message if calculation failed
    """

    baseline_config: BaselineConfig
    nightly_timestamp: Optional[datetime]
    deltas: List[BenchmarkDelta]
    summary: Dict[str, Any]
    source: str
    error: Optional[str] = None


def fetch_baseline_results(
    client: Any,
    config: BaselineConfig,
) -> pd.DataFrame:
    """
    Retrieve baseline dataset from OpenSearch.

    Args:
        client: OpenSearch client (BenchmarkDataSource)
        config: Baseline configuration specifying which data to retrieve

    Returns:
        DataFrame with baseline benchmark results
    """
    start_date, end_date = config.date_range
    query_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "metadata.test_timestamp": {
                                "gte": start_date.isoformat(),
                                "lte": end_date.isoformat(),
                            }
                        }
                    }
                ],
            }
        },
        "size": 10000,
    }

    # Apply benchmark filters if provided
    if config.benchmark_filter:
        for field, value in config.benchmark_filter.items():
            if isinstance(value, list):
                query_body["query"]["bool"]["must"].append({"terms": {field: value}})
            else:
                query_body["query"]["bool"]["must"].append({"term": {field: value}})

    try:
        response = client.search_results(query_body)
        hits = response.get("hits", {}).get("hits", [])
        documents = [hit["_source"] for hit in hits]
        logger.info(
            f"Retrieved {len(documents)} baseline documents for baseline_id={config.baseline_id}"
        )
        return _parse_documents_to_dataframe(documents)
    except Exception as exc:
        logger.error(f"Failed to fetch baseline results: {exc}")
        return pd.DataFrame()


def fetch_nightly_results(
    client: Any,
    benchmark_filter: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Retrieve latest nightly run from OpenSearch.

    Args:
        client: OpenSearch client (BenchmarkDataSource)
        benchmark_filter: Optional filters to apply

    Returns:
        DataFrame with nightly benchmark results
    """
    query_body = {
        "query": {"match_all": {}},
        "sort": [{"metadata.test_timestamp": {"order": "desc"}}],
        "size": 10000,
    }

    # Apply filters if provided
    if benchmark_filter:
        must_clauses = []
        for field, value in benchmark_filter.items():
            if isinstance(value, list):
                must_clauses.append({"terms": {field: value}})
            else:
                must_clauses.append({"term": {field: value}})
        query_body["query"] = {"bool": {"must": must_clauses}}

    try:
        response = client.search_results(query_body)
        hits = response.get("hits", {}).get("hits", [])
        documents = [hit["_source"] for hit in hits]
        logger.info(f"Retrieved {len(documents)} nightly documents")
        return _parse_documents_to_dataframe(documents)
    except Exception as exc:
        logger.error(f"Failed to fetch nightly results: {exc}")
        return pd.DataFrame()


def _parse_documents_to_dataframe(documents: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Parse OpenSearch documents into a DataFrame with relevant fields.

    Args:
        documents: List of OpenSearch document sources

    Returns:
        DataFrame with normalized benchmark data
    """
    if not documents:
        return pd.DataFrame()

    rows = []
    for doc in documents:
        metadata = doc.get("metadata") or {}
        test = doc.get("test") or {}
        results = doc.get("results") or {}

        # Extract primary metric value
        primary_metric_value = (results.get("primary_metric") or {}).get("value")
        if primary_metric_value is None:
            # Try alternative locations
            primary_metric_value = results.get("value")

        row = {
            "test_name": test.get("name"),
            "test_timestamp": metadata.get("test_timestamp"),
            "cloud_provider": metadata.get("cloud_provider"),
            "os_vendor": metadata.get("os_vendor"),
            "instance_type": metadata.get("instance_type"),
            "status": results.get("status", "UNKNOWN"),
            "primary_metric_value": primary_metric_value,
            "primary_metric_name": (results.get("primary_metric") or {}).get("name") or "value",
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Convert timestamp to datetime
    if "test_timestamp" in df.columns and not df.empty:
        df["test_timestamp"] = pd.to_datetime(df["test_timestamp"], utc=True)

    return df


def calculate_delta(
    baseline_df: pd.DataFrame,
    nightly_df: pd.DataFrame,
    config: BaselineConfig,
) -> TrackKpiResult:
    """
    Calculate metric changes between baseline and nightly datasets.

    Computes percentage change and absolute change for each benchmark,
    applies regression detection, and handles missing benchmarks.

    Args:
        baseline_df: Baseline benchmark results
        nightly_df: Nightly benchmark results
        config: Baseline configuration

    Returns:
        TrackKpiResult with deltas and summary statistics
    """
    try:
        # Filter for PASS status only
        baseline_filtered = filter_dataframe_for_regression_math(
            baseline_df, context="baseline"
        )
        nightly_filtered = filter_dataframe_for_regression_math(
            nightly_df, context="nightly"
        )

        # Get nightly timestamp
        nightly_timestamp = None
        if not nightly_filtered.empty and "test_timestamp" in nightly_filtered.columns:
            nightly_timestamp = nightly_filtered["test_timestamp"].max()

        # Group by test_name and calculate means
        baseline_stats = _calculate_benchmark_stats(baseline_filtered)
        nightly_stats = _calculate_benchmark_stats(nightly_filtered)

        # Calculate deltas
        deltas = []
        all_benchmarks = set(baseline_stats.keys()) | set(nightly_stats.keys())

        for benchmark_name in all_benchmarks:
            baseline_stat = baseline_stats.get(benchmark_name)
            nightly_stat = nightly_stats.get(benchmark_name)

            delta = _compute_benchmark_delta(
                benchmark_name=benchmark_name,
                baseline_stat=baseline_stat,
                nightly_stat=nightly_stat,
            )
            deltas.append(delta)

        # Generate summary statistics
        summary = _generate_summary(deltas)

        return TrackKpiResult(
            baseline_config=config,
            nightly_timestamp=nightly_timestamp,
            deltas=deltas,
            summary=summary,
            source="opensearch",
            error=None,
        )

    except Exception as exc:
        logger.error(f"Failed to calculate delta: {exc}")
        return TrackKpiResult(
            baseline_config=config,
            nightly_timestamp=None,
            deltas=[],
            summary={},
            source="opensearch",
            error=str(exc),
        )


def _calculate_benchmark_stats(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Calculate statistics for each benchmark.

    Args:
        df: DataFrame with benchmark results

    Returns:
        Dictionary mapping benchmark name to statistics
    """
    if df.empty or "test_name" not in df.columns:
        return {}

    stats = {}
    for test_name, group in df.groupby("test_name"):
        if "primary_metric_value" not in group.columns:
            continue

        # Filter out non-numeric values
        values = pd.to_numeric(group["primary_metric_value"], errors="coerce").dropna()

        if len(values) > 0:
            metric_name = (group["primary_metric_name"].iloc[0] if "primary_metric_name" in group.columns else "value") or "value"
            stats[test_name] = {
                "mean": float(values.mean()),
                "count": len(values),
                "metric_name": metric_name,
            }

    return stats


def _compute_benchmark_delta(
    benchmark_name: str,
    baseline_stat: Optional[Dict[str, Any]],
    nightly_stat: Optional[Dict[str, Any]],
) -> BenchmarkDelta:
    """
    Compute delta for a single benchmark.

    Args:
        benchmark_name: Name of the benchmark
        baseline_stat: Baseline statistics
        nightly_stat: Nightly statistics

    Returns:
        BenchmarkDelta with comparison results
    """
    # Determine status and calculate changes
    if baseline_stat is None and nightly_stat is not None:
        # Benchmark added in nightly
        return BenchmarkDelta(
            benchmark_name=benchmark_name,
            metric_name=nightly_stat["metric_name"],
            baseline_mean=None,
            nightly_mean=nightly_stat["mean"],
            percent_change=None,
            absolute_change=None,
            is_regression=False,
            status="added",
        )
    elif baseline_stat is not None and nightly_stat is None:
        # Benchmark removed in nightly
        return BenchmarkDelta(
            benchmark_name=benchmark_name,
            metric_name=baseline_stat["metric_name"],
            baseline_mean=baseline_stat["mean"],
            nightly_mean=None,
            percent_change=None,
            absolute_change=None,
            is_regression=False,
            status="removed",
        )
    elif baseline_stat is None and nightly_stat is None:
        # Should not happen, but handle gracefully
        return BenchmarkDelta(
            benchmark_name=benchmark_name,
            metric_name="unknown",
            baseline_mean=None,
            nightly_mean=None,
            percent_change=None,
            absolute_change=None,
            is_regression=False,
            status="unchanged",
        )
    else:
        # Both exist - calculate delta
        baseline_mean = baseline_stat["mean"]
        nightly_mean = nightly_stat["mean"]
        metric_name = nightly_stat["metric_name"]

        # Calculate percentage change (avoiding division by zero)
        pct_change = None
        if baseline_mean != 0:
            pct_change = percent_change(baseline_mean, nightly_mean)

        # Calculate absolute change
        abs_change = nightly_mean - baseline_mean

        # Check for regression
        is_reg = False
        if pct_change is not None:
            is_reg = is_regression_for_test_name(pct_change, benchmark_name)

        return BenchmarkDelta(
            benchmark_name=benchmark_name,
            metric_name=metric_name,
            baseline_mean=baseline_mean,
            nightly_mean=nightly_mean,
            percent_change=pct_change,
            absolute_change=abs_change,
            is_regression=is_reg,
            status="changed",
        )


def _generate_summary(deltas: List[BenchmarkDelta]) -> Dict[str, Any]:
    """
    Generate summary statistics from deltas.

    Args:
        deltas: List of benchmark deltas

    Returns:
        Dictionary with summary statistics
    """
    total = len(deltas)
    added = sum(1 for d in deltas if d.status == "added")
    removed = sum(1 for d in deltas if d.status == "removed")
    changed = sum(1 for d in deltas if d.status == "changed")
    unchanged = sum(1 for d in deltas if d.status == "unchanged")
    regressions = sum(1 for d in deltas if d.is_regression)

    return {
        "total_benchmarks": total,
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "regressions": regressions,
        "regression_rate": regressions / changed if changed > 0 else 0.0,
    }


def calculate_delta_from_dataframes(
    baseline_df: pd.DataFrame,
    nightly_df: pd.DataFrame,
    baseline_id: str = "synthetic",
) -> TrackKpiResult:
    """
    Calculate delta from pre-loaded DataFrames (for synthetic/testing).

    Args:
        baseline_df: Baseline benchmark DataFrame
        nightly_df: Nightly benchmark DataFrame
        baseline_id: Identifier for the baseline

    Returns:
        TrackKpiResult with deltas and summary
    """
    # Create a minimal config for synthetic use
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
    config = BaselineConfig(
        baseline_id=baseline_id,
        date_range=(start_date, end_date),
        benchmark_filter=None,
    )

    result = calculate_delta(baseline_df, nightly_df, config)
    # Override source to synthetic
    return TrackKpiResult(
        baseline_config=result.baseline_config,
        nightly_timestamp=result.nightly_timestamp,
        deltas=result.deltas,
        summary=result.summary,
        source="synthetic",
        error=result.error,
    )
