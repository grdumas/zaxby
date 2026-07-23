"""
pytest-benchmark tests for BenchmarkDataProcessor methods.

Tests the data transformation and analysis layer that processes benchmark
documents into DataFrames and computes analysis results for dashboard views.

Run with: pytest tests/performance/test_data_processing_benchmark.py --benchmark-only -v
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import pytest

from src.data_processing import BenchmarkDataProcessor

# Guard: pytest-benchmark is not in root requirements.txt
pytest.importorskip(
    "pytest_benchmark",
    reason="Performance tests require pytest-benchmark. Install with: pip install -r tests/performance/requirements.txt"
)


@pytest.mark.parametrize("scale_documents", ["1k", "10k", "100k"], indirect=True)
def test_documents_to_dataframe(
    benchmark,
    benchmark_processor: BenchmarkDataProcessor,
    scale_documents: List[Dict[str, Any]]
):
    """
    Benchmark documents_to_dataframe transformation.

    This is the startup path - converts raw documents to DataFrame. One of the
    most expensive operations in the data pipeline.

    Args:
        benchmark: pytest-benchmark fixture.
        benchmark_processor: Shared processor instance.
        scale_documents: Parametrized document list (1k/10k/100k).
    """
    result = benchmark(benchmark_processor.documents_to_dataframe, scale_documents)

    # Verify result is valid
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_filter_data_no_filters(
    benchmark,
    benchmark_processor: BenchmarkDataProcessor,
    scale_dataframe: pd.DataFrame
):
    """
    Benchmark filter_data with no filters (pass-through).

    Baseline for filter performance - just copies DataFrame.

    Args:
        benchmark: pytest-benchmark fixture.
        benchmark_processor: Shared processor instance.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    result = benchmark(
        benchmark_processor.filter_data,
        scale_dataframe
    )

    # Verify result is valid
    assert result is not None
    assert len(result) == len(scale_dataframe)


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_filter_data_single_filter(
    benchmark,
    benchmark_processor: BenchmarkDataProcessor,
    scale_dataframe: pd.DataFrame
):
    """
    Benchmark filter_data with single OS version filter.

    Most common filter pattern in production.

    Args:
        benchmark: pytest-benchmark fixture.
        benchmark_processor: Shared processor instance.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    # Extract a valid OS version from the data
    assert not scale_dataframe.empty, "DataFrame should not be empty"
    assert "os_version" in scale_dataframe.columns, "DataFrame missing required column: os_version"

    os_versions = scale_dataframe["os_version"].unique()
    if len(os_versions) == 0:
        pytest.skip("No OS versions in DataFrame")

    filter_os = [os_versions[0]]

    result = benchmark(
        benchmark_processor.filter_data,
        scale_dataframe,
        os_versions=filter_os
    )

    # Verify result is filtered
    assert result is not None
    assert len(result) <= len(scale_dataframe)


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_filter_data_multi_filter(
    benchmark,
    benchmark_processor: BenchmarkDataProcessor,
    scale_dataframe: pd.DataFrame
):
    """
    Benchmark filter_data with multiple filters (OS + cloud + date).

    Complex filter combination used in investigation drill-downs.

    Args:
        benchmark: pytest-benchmark fixture.
        benchmark_processor: Shared processor instance.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    # Extract valid filter values from data
    assert not scale_dataframe.empty, "DataFrame should not be empty"

    os_versions = scale_dataframe.get("os_version", pd.Series(dtype=str)).unique()
    cloud_providers = scale_dataframe.get("cloud_provider", pd.Series(dtype=str)).unique()
    timestamps = scale_dataframe.get("timestamp", pd.Series())

    if len(os_versions) == 0 or len(cloud_providers) == 0 or len(timestamps) == 0:
        pytest.skip("Insufficient data for multi-filter")

    # Build filter params
    filter_os = [os_versions[0]] if len(os_versions) > 0 else None
    filter_cloud = [cloud_providers[0]] if len(cloud_providers) > 0 else None
    min_date = timestamps.min()
    max_date = timestamps.max()
    date_range = (min_date, max_date) if min_date and max_date else None

    result = benchmark(
        benchmark_processor.filter_data,
        scale_dataframe,
        os_versions=filter_os,
        cloud_providers=filter_cloud,
        date_range=date_range
    )

    # Verify result is filtered
    assert result is not None
    assert len(result) <= len(scale_dataframe)


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_analyze_rhel_simplified_regressions(
    benchmark,
    benchmark_processor: BenchmarkDataProcessor,
    scale_dataframe: pd.DataFrame
):
    """
    Benchmark analyze_rhel_simplified_regressions.

    Heaviest analysis callback - computes three regression comparisons:
    - Latest 9.X vs Latest 10.X (major release)
    - Latest 9.X vs Previous 9.X (9.X sequential)
    - Latest 10.X vs Previous 10.X (10.X sequential)

    Args:
        benchmark: pytest-benchmark fixture.
        benchmark_processor: Shared processor instance.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    result = benchmark(
        benchmark_processor.analyze_rhel_simplified_regressions,
        scale_dataframe
    )

    # Verify result is valid
    assert result is not None
    assert isinstance(result, dict)


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_analyze_peer_os_comparison(
    benchmark,
    benchmark_processor: BenchmarkDataProcessor,
    scale_dataframe: pd.DataFrame
):
    """
    Benchmark analyze_peer_os_comparison.

    Compares RHEL performance against peer operating systems.

    Args:
        benchmark: pytest-benchmark fixture.
        benchmark_processor: Shared processor instance.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    result = benchmark(
        benchmark_processor.analyze_peer_os_comparison,
        scale_dataframe,
        baseline_os="RHEL"
    )

    # Verify result is valid
    assert result is not None
    assert isinstance(result, dict)


@pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True)
def test_analyze_cloud_scaling(
    benchmark,
    benchmark_processor: BenchmarkDataProcessor,
    scale_dataframe: pd.DataFrame
):
    """
    Benchmark analyze_cloud_scaling.

    Analyzes performance scaling across cloud instance sizes.
    Extract valid cloud_provider and os_version from data.

    Args:
        benchmark: pytest-benchmark fixture.
        benchmark_processor: Shared processor instance.
        scale_dataframe: Parametrized DataFrame (1k/10k/100k).
    """
    # Extract valid parameters from data
    assert not scale_dataframe.empty, "DataFrame should not be empty"

    cloud_providers = scale_dataframe.get("cloud_provider", pd.Series(dtype=str)).unique()
    os_versions = scale_dataframe.get("os_version", pd.Series(dtype=str)).unique()

    if len(cloud_providers) == 0 or len(os_versions) == 0:
        pytest.skip("Insufficient data for cloud scaling analysis")

    cloud_provider = cloud_providers[0]
    os_version = os_versions[0]

    result = benchmark(
        benchmark_processor.analyze_cloud_scaling,
        scale_dataframe,
        cloud_provider=cloud_provider,
        os_version=os_version
    )

    # Verify result is valid
    assert result is not None
    assert isinstance(result, dict)
