"""
pytest-benchmark tests for query_service synthetic-mode aggregation functions.

These functions are called by Dash callbacks in DATA_MODE=synthetic to compute
KPIs from in-memory DataFrames. They mirror the OpenSearch aggregation queries.

Run with: pytest tests/performance/test_query_service_benchmark.py --benchmark-only -v
Filter by scale: pytest tests/performance/ -k "1k" --benchmark-only
Save baseline: pytest tests/performance/ --benchmark-save=baseline_v1
Compare: pytest tests/performance/ --benchmark-compare=baseline_v1
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.query_service import (
    aggregate_results_overview_from_dataframe,
    aggregate_category_kpis_from_dataframe,
    aggregate_activity_timeline_from_dataframe,
    aggregate_pulse_scope_footnote_from_dataframe,
    aggregate_baseline_comparison_from_dataframe,
    aggregate_recent_nightly_runs_from_dataframe,
)

# Guard: pytest-benchmark is not in root requirements.txt
pytest.importorskip(
    "pytest_benchmark",
    reason="Performance tests require pytest-benchmark. Install with: pip install -r tests/performance/requirements.txt"
)


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_aggregate_results_overview(benchmark, scale_dataframe: pd.DataFrame):
    """
    Benchmark aggregate_results_overview_from_dataframe.

    Simple groupby on cloud_provider. Expected to be fast even at 100K scale.

    Args:
        benchmark: pytest-benchmark fixture.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    result = benchmark(aggregate_results_overview_from_dataframe, scale_dataframe)

    # Verify result is valid
    assert result is not None
    assert result.total > 0
    assert len(result.by_cloud) > 0


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_aggregate_category_kpis(benchmark, scale_dataframe: pd.DataFrame):
    """
    Benchmark aggregate_category_kpis_from_dataframe.

    Groupby on test_name with category mapping. Moderate complexity.

    Args:
        benchmark: pytest-benchmark fixture.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    result = benchmark(aggregate_category_kpis_from_dataframe, scale_dataframe)

    # Verify result is valid
    assert result is not None
    assert len(result.by_category) > 0


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_aggregate_activity_timeline(benchmark, scale_dataframe: pd.DataFrame):
    """
    Benchmark aggregate_activity_timeline_from_dataframe.

    Monthly date histogram. Time-based grouping.

    Args:
        benchmark: pytest-benchmark fixture.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    result = benchmark(aggregate_activity_timeline_from_dataframe, scale_dataframe)

    # Verify result is valid
    assert result is not None
    assert len(result.timeline) > 0


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_aggregate_pulse_scope_footnote(benchmark, scale_dataframe: pd.DataFrame):
    """
    Benchmark aggregate_pulse_scope_footnote_from_dataframe.

    Document count and date range. Very fast.

    Args:
        benchmark: pytest-benchmark fixture.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    result = benchmark(aggregate_pulse_scope_footnote_from_dataframe, scale_dataframe)

    # Verify result is valid
    assert result is not None
    assert result.document_count > 0
    assert result.date_range_start is not None
    assert result.date_range_end is not None


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_aggregate_baseline_comparison(benchmark, scale_dataframe: pd.DataFrame):
    """
    Benchmark aggregate_baseline_comparison_from_dataframe.

    Heavy analysis: baseline vs nightly comparison with regression detection.
    Split DataFrame by date midpoint to simulate baseline/nightly cohorts.

    Args:
        benchmark: pytest-benchmark fixture.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    # Split DataFrame into baseline (first half) and nightly (second half) by date
    if scale_dataframe.empty or "timestamp" not in scale_dataframe.columns:
        pytest.skip("DataFrame missing timestamp column")

    dates = scale_dataframe["timestamp"].sort_values()
    midpoint_date = dates.iloc[len(dates) // 2]

    baseline_df = scale_dataframe[scale_dataframe["timestamp"] < midpoint_date].copy()
    nightly_df = scale_dataframe[scale_dataframe["timestamp"] >= midpoint_date].copy()

    # Skip if either cohort is empty
    if baseline_df.empty or nightly_df.empty:
        pytest.skip("Insufficient data for baseline/nightly split")

    result = benchmark(
        aggregate_baseline_comparison_from_dataframe,
        baseline_df,
        nightly_df,
        baseline_id="synthetic_baseline"
    )

    # Verify result is valid
    assert result is not None


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_aggregate_recent_nightly_runs(benchmark, scale_dataframe: pd.DataFrame):
    """
    Benchmark aggregate_recent_nightly_runs_from_dataframe.

    Nightly run grouping with test category breakdown. Moderate complexity.

    Args:
        benchmark: pytest-benchmark fixture.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    # Extract date range from data
    if scale_dataframe.empty or "timestamp" not in scale_dataframe.columns:
        pytest.skip("DataFrame missing timestamp column")

    min_date = scale_dataframe["timestamp"].min()
    max_date = scale_dataframe["timestamp"].max()

    result = benchmark(
        aggregate_recent_nightly_runs_from_dataframe,
        scale_dataframe,
        max_runs=10,
        date_range=(min_date, max_date),
        min_test_threshold=5
    )

    # Verify result is valid (may be empty if no nightly runs detected)
    assert result is not None
    assert isinstance(result, list)
