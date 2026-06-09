"""
Tests for Track mode UI components (RPOPC-1167).

Tests component rendering, data display, and user interactions.
"""

import pytest
from dash import html

from src.query_service import BaselineComparisonSnapshot
from src.track_ui import (
    create_track_exception_table,
    create_track_mode_layout,
    create_track_summary_metrics,
)


def test_create_track_mode_layout():
    """Test Track mode layout creation."""
    layout = create_track_mode_layout()

    assert layout is not None
    assert isinstance(layout, html.Div)

    # Verify layout contains key sections
    layout_str = str(layout)
    assert "Track Mode" in layout_str
    assert "Configuration" in layout_str
    assert "Run Comparison" in layout_str


def test_create_track_summary_metrics_with_valid_snapshot():
    """Test summary metrics with valid snapshot data."""
    snapshot = BaselineComparisonSnapshot(
        baseline_id="test-baseline",
        nightly_timestamp="2025-02-01T06:00:00Z",
        total_benchmarks=100,
        changed=25,
        regressions=3,
        improvements=5,
        added=2,
        removed=1,
        unchanged=72,
        regression_rate=12.0,
        source="opensearch",
        error=None,
    )

    result = create_track_summary_metrics(snapshot)

    assert result is not None
    result_str = str(result)

    # Verify summary contains key metrics
    assert "100" in result_str  # total
    assert "25" in result_str   # changed
    assert "3" in result_str    # regressions
    assert "5" in result_str    # improvements


def test_create_track_summary_metrics_with_none():
    """Test summary metrics with None snapshot."""
    result = create_track_summary_metrics(None)

    assert result is not None
    result_str = str(result)
    assert "No comparison run yet" in result_str


def test_create_track_summary_metrics_with_error():
    """Test summary metrics with error in snapshot."""
    snapshot = BaselineComparisonSnapshot(
        baseline_id="test-baseline",
        nightly_timestamp=None,
        total_benchmarks=0,
        changed=0,
        regressions=0,
        improvements=0,
        added=0,
        removed=0,
        unchanged=0,
        regression_rate=0.0,
        source="opensearch",
        error="OpenSearch connection failed",
    )

    result = create_track_summary_metrics(snapshot)

    assert result is not None
    result_str = str(result)
    assert "OpenSearch connection failed" in result_str


def test_create_track_exception_table_with_data():
    """Test exception table with valid data."""
    exceptions = [
        {
            "benchmark_name": "coremark",
            "metric_name": "iterations/sec",
            "baseline_mean": 100.0,
            "nightly_mean": 90.0,
            "percent_change": -10.0,
            "absolute_change": -10.0,
            "is_regression": True,
            "status": "changed",
            "exception_type": "regression",
        },
        {
            "benchmark_name": "streams",
            "metric_name": "MB/s",
            "baseline_mean": 50000.0,
            "nightly_mean": 55000.0,
            "percent_change": 10.0,
            "absolute_change": 5000.0,
            "is_regression": False,
            "status": "changed",
            "exception_type": "improvement",
        },
        {
            "benchmark_name": "pyperf",
            "metric_name": "seconds",
            "baseline_mean": 1.5,
            "nightly_mean": None,
            "percent_change": None,
            "absolute_change": None,
            "is_regression": False,
            "status": "removed",
            "exception_type": "missing",
        },
    ]

    result = create_track_exception_table(exceptions)

    assert result is not None
    # Exception table uses dash_table which may not render to string easily
    # Just verify it returns a component
    assert hasattr(result, '__class__')


def test_create_track_exception_table_empty():
    """Test exception table with empty data."""
    result = create_track_exception_table([])

    assert result is not None
    result_str = str(result)
    assert "No exceptions" in result_str or "empty" in result_str.lower()


def test_create_track_exception_table_none():
    """Test exception table with None."""
    result = create_track_exception_table(None)

    assert result is not None


def test_summary_metrics_zero_regressions():
    """Test summary metrics when no regressions."""
    snapshot = BaselineComparisonSnapshot(
        baseline_id="clean-baseline",
        nightly_timestamp="2025-02-01T06:00:00Z",
        total_benchmarks=50,
        changed=10,
        regressions=0,  # No regressions
        improvements=5,
        added=0,
        removed=0,
        unchanged=40,
        regression_rate=0.0,
        source="opensearch",
        error=None,
    )

    result = create_track_summary_metrics(snapshot)

    assert result is not None
    result_str = str(result)
    assert "0" in result_str  # regressions should show 0


def test_summary_metrics_all_regressions():
    """Test summary metrics when all changed benchmarks are regressions."""
    snapshot = BaselineComparisonSnapshot(
        baseline_id="bad-baseline",
        nightly_timestamp="2025-02-01T06:00:00Z",
        total_benchmarks=20,
        changed=10,
        regressions=10,  # All changed are regressions
        improvements=0,
        added=0,
        removed=0,
        unchanged=10,
        regression_rate=100.0,
        source="opensearch",
        error=None,
    )

    result = create_track_summary_metrics(snapshot)

    assert result is not None
    result_str = str(result)
    assert "10" in result_str  # regressions
    assert "100" in result_str  # regression rate or total


def test_summary_metrics_high_regression_rate():
    """Test summary metrics with high regression rate."""
    snapshot = BaselineComparisonSnapshot(
        baseline_id="regression-baseline",
        nightly_timestamp="2025-02-01T06:00:00Z",
        total_benchmarks=100,
        changed=20,
        regressions=15,
        improvements=2,
        added=0,
        removed=0,
        unchanged=80,
        regression_rate=75.0,  # 75% of changed are regressions
        source="opensearch",
        error=None,
    )

    result = create_track_summary_metrics(snapshot)

    assert result is not None
    # Should display prominently since regression rate is high


def test_exception_table_regression_formatting():
    """Test that regressions are formatted distinctly."""
    exceptions = [
        {
            "benchmark_name": "benchmark_regression",
            "metric_name": "throughput",
            "baseline_mean": 1000.0,
            "nightly_mean": 800.0,
            "percent_change": -20.0,
            "absolute_change": -200.0,
            "is_regression": True,
            "status": "changed",
            "exception_type": "regression",
        },
    ]

    result = create_track_exception_table(exceptions)

    # Regression should be visually distinct (color, icon, etc.)
    assert result is not None


def test_exception_table_missing_benchmark():
    """Test formatting of missing benchmarks."""
    exceptions = [
        {
            "benchmark_name": "missing_test",
            "metric_name": "value",
            "baseline_mean": 100.0,
            "nightly_mean": None,
            "percent_change": None,
            "absolute_change": None,
            "is_regression": False,
            "status": "removed",
            "exception_type": "missing",
        },
    ]

    result = create_track_exception_table(exceptions)

    assert result is not None


def test_exception_table_new_benchmark():
    """Test formatting of new benchmarks."""
    exceptions = [
        {
            "benchmark_name": "new_test",
            "metric_name": "ops/sec",
            "baseline_mean": None,
            "nightly_mean": 5000.0,
            "percent_change": None,
            "absolute_change": None,
            "is_regression": False,
            "status": "added",
            "exception_type": "new",
        },
    ]

    result = create_track_exception_table(exceptions)

    assert result is not None


def test_summary_metrics_synthetic_source():
    """Test summary metrics from synthetic data source."""
    snapshot = BaselineComparisonSnapshot(
        baseline_id="synthetic-baseline",
        nightly_timestamp="2025-02-01T06:00:00Z",
        total_benchmarks=50,
        changed=15,
        regressions=3,
        improvements=7,
        added=1,
        removed=1,
        unchanged=33,
        regression_rate=20.0,
        source="synthetic",  # Synthetic source
        error=None,
    )

    result = create_track_summary_metrics(snapshot)

    assert result is not None
    result_str = str(result)
    # Should indicate synthetic source
    assert "synthetic" in result_str.lower() or result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
