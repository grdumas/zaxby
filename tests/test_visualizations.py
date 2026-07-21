"""
Tests for visualization components.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
from src.components.visualizations import create_cloud_scaling_chart


@pytest.fixture
def scaling_data_with_cores():
    """Sample scaling data with CPU cores and memory."""
    return pd.DataFrame([
        {
            "instance_type": "c2-standard-4",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 4,
            "memory_gb": 16,
            "mean_performance": 100000.0,
            "std_performance": 1000.0
        },
        {
            "instance_type": "c2-standard-8",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 8,
            "memory_gb": 32,
            "mean_performance": 195000.0,
            "std_performance": 2000.0
        },
        {
            "instance_type": "c2-standard-16",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 16,
            "memory_gb": 64,
            "mean_performance": 380000.0,
            "std_performance": 3000.0
        },
    ])


@pytest.fixture
def multi_benchmark_scaling_data():
    """Scaling data with multiple benchmarks."""
    return pd.DataFrame([
        # CoreMark - good scaling
        {
            "instance_type": "c2-standard-4",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 4,
            "memory_gb": 16,
            "mean_performance": 100000.0,
        },
        {
            "instance_type": "c2-standard-8",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 8,
            "memory_gb": 32,
            "mean_performance": 195000.0,
        },
        # STREAM - memory bound
        {
            "instance_type": "c2-standard-4",
            "test_name": "streams",
            "benchmark_category": "Memory",
            "cpu_cores": 4,
            "memory_gb": 16,
            "mean_performance": 50000.0,
        },
        {
            "instance_type": "c2-standard-8",
            "test_name": "streams",
            "benchmark_category": "Memory",
            "cpu_cores": 8,
            "memory_gb": 32,
            "mean_performance": 80000.0,
        },
    ])


def test_create_cloud_scaling_chart_basic(scaling_data_with_cores):
    """Test basic cloud scaling chart creation."""
    fig = create_cloud_scaling_chart(scaling_data_with_cores)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.layout.title.text == "Performance Scaling Across Instance Sizes"


def test_create_cloud_scaling_chart_empty_data():
    """Test chart with empty DataFrame."""
    empty_df = pd.DataFrame()
    fig = create_cloud_scaling_chart(empty_df)

    assert isinstance(fig, go.Figure)
    # Should return an empty figure with message
    assert "No scaling data available" in fig.layout.annotations[0].text


def test_create_cloud_scaling_chart_custom_title(scaling_data_with_cores):
    """Test chart with custom title."""
    custom_title = "GCP Instance Scaling Analysis"
    fig = create_cloud_scaling_chart(scaling_data_with_cores, title=custom_title)

    assert fig.layout.title.text == custom_title


def test_create_cloud_scaling_chart_sorts_instances_by_cores(scaling_data_with_cores):
    """Test that instances are sorted by CPU cores in visualization (Acceptance Criterion 1)."""
    # Shuffle data to verify sorting works
    shuffled_data = (
        scaling_data_with_cores
        .sample(frac=1, random_state=42)
        .reset_index(drop=True)
    )

    fig = create_cloud_scaling_chart(shuffled_data)

    # Extract x-axis tick labels
    tick_labels = fig.layout.xaxis.ticktext

    # Verify tick labels are ordered by cores (4, 8, 16)
    assert len(tick_labels) == 3
    assert "4 vCPU" in tick_labels[0]
    assert "8 vCPU" in tick_labels[1]
    assert "16 vCPU" in tick_labels[2]


def test_create_cloud_scaling_chart_includes_memory_in_labels(scaling_data_with_cores):
    """Test that memory is included in labels (Acceptance Criterion 3 - multi-dimensional)."""
    fig = create_cloud_scaling_chart(scaling_data_with_cores)

    tick_labels = fig.layout.xaxis.ticktext

    # Verify memory values are in labels
    assert "16 GB" in tick_labels[0]
    assert "32 GB" in tick_labels[1]
    assert "64 GB" in tick_labels[2]


def test_create_cloud_scaling_chart_calculates_efficiency(scaling_data_with_cores):
    """Test that scaling efficiency is calculated (Acceptance Criterion 2)."""
    fig = create_cloud_scaling_chart(scaling_data_with_cores)

    # The chart should have traces with hover text containing efficiency
    assert len(fig.data) > 0

    # Check that hover text mentions efficiency (in customdata or hovertemplate)
    trace = fig.data[0]

    # Verify efficiency is being calculated by checking the trace has data
    # The y-values should represent efficiency percentages
    assert trace.y is not None
    assert len(trace.y) > 0

    # Y-values should be efficiency percentages (around 100% for linear scaling)
    # For the test data, efficiency should be ~95-100%
    assert all(80 <= y <= 120 for y in trace.y if y is not None)


def test_create_cloud_scaling_chart_shows_efficiency_percentage(scaling_data_with_cores):
    """Test that y-axis shows efficiency as percentage (Acceptance Criterion 2)."""
    fig = create_cloud_scaling_chart(scaling_data_with_cores)

    # Y-axis should be labeled as efficiency/percentage
    y_axis_title = fig.layout.yaxis.title.text
    assert "Efficiency" in y_axis_title or "%" in y_axis_title


def test_create_cloud_scaling_chart_multi_benchmark(multi_benchmark_scaling_data):
    """Test chart with multiple benchmarks."""
    fig = create_cloud_scaling_chart(multi_benchmark_scaling_data)

    # Should have traces for each benchmark category
    assert len(fig.data) >= 2  # CPU and Memory categories


def test_create_cloud_scaling_chart_handles_missing_memory_field():
    """Test that chart handles missing memory_gb field gracefully."""
    data_no_memory = pd.DataFrame([
        {
            "instance_type": "c2-standard-4",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 4,
            "mean_performance": 100000.0,
        },
        {
            "instance_type": "c2-standard-8",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 8,
            "mean_performance": 195000.0,
        },
    ])

    # Should render without crashing when memory_gb is missing
    fig = create_cloud_scaling_chart(data_no_memory)

    # Verify chart was created
    assert fig is not None
    assert len(fig.data) > 0

    # Verify tick labels contain CPU info but NOT memory info
    tick_labels = fig.layout.xaxis.ticktext
    assert len(tick_labels) == 2
    assert "4 vCPU" in tick_labels[0]
    assert "8 vCPU" in tick_labels[1]
    # Should NOT contain GB (memory) in labels
    assert "GB" not in tick_labels[0]
    assert "GB" not in tick_labels[1]


def test_create_cloud_scaling_chart_aggregates_per_instance(multi_benchmark_scaling_data):
    """Test that chart aggregates multiple tests per instance correctly."""
    # Add duplicate test data for same instance
    data_with_dupes = pd.concat([
        multi_benchmark_scaling_data,
        multi_benchmark_scaling_data.iloc[:2].copy()  # Duplicate first 2 rows
    ]).reset_index(drop=True)

    fig = create_cloud_scaling_chart(data_with_dupes)

    # Should still create valid chart without errors
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_create_cloud_scaling_chart_dynamic_y_axis():
    """Test that y-axis range is dynamic based on data."""
    # Create data with super-linear scaling (>100%)
    superlinear_data = pd.DataFrame([
        {
            "instance_type": "c2-standard-4",
            "test_name": "test",
            "benchmark_category": "CPU",
            "cpu_cores": 4,
            "memory_gb": 16,
            "mean_performance": 100000.0,
        },
        {
            "instance_type": "c2-standard-8",
            "test_name": "test",
            "benchmark_category": "CPU",
            "cpu_cores": 8,
            "memory_gb": 32,
            "mean_performance": 220000.0,  # 110% scaling
        },
    ])

    fig = create_cloud_scaling_chart(superlinear_data)

    # Y-axis should accommodate values >100%
    y_range = fig.layout.yaxis.range
    assert y_range is None or y_range[1] > 100  # None means auto-range
