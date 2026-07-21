"""
Tests for visualization components.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
from src.components.visualizations import (
    create_cloud_scaling_chart,
    create_comparison_chart
)


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


def test_create_cloud_scaling_chart_handles_partial_nan_cpu_cores():
    """Test that chart handles partially missing cpu_cores gracefully.

    This test specifically checks that pd.NA (nullable integer NA) values
    don't cause TypeError during truthiness checks in efficiency calculation.
    """
    # Create data where some instances have NaN cpu_cores
    # Use nullable Int64 dtype to ensure pd.NA behavior
    data_partial_cores = pd.DataFrame([
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
        {
            "instance_type": "unknown-instance",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": pd.NA,  # Missing cpu_cores with pd.NA
            "memory_gb": 64,
            "mean_performance": 150000.0,
        },
    ])
    # Explicitly convert to nullable integer to trigger pd.NA truthiness issues
    data_partial_cores['cpu_cores'] = data_partial_cores['cpu_cores'].astype('Int64')

    # Should render without crashing (would fail with "boolean value of NA is ambiguous")
    fig = create_cloud_scaling_chart(data_partial_cores)

    # Verify chart was created
    assert fig is not None
    assert len(fig.data) > 0

    # Only instances with valid cpu_cores should appear in tick labels
    tick_labels = fig.layout.xaxis.ticktext
    assert len(tick_labels) == 2  # Only 2 instances with valid cores
    assert "4 vCPU" in tick_labels[0]
    assert "8 vCPU" in tick_labels[1]

    # Verify efficiency calculation worked (customdata should have valid hover text)
    trace = fig.data[0]
    assert hasattr(trace, 'customdata')
    # Check that only valid cores get hover text with efficiency info
    valid_hovers = [h for h in trace.customdata if h]  # Filter empty strings
    assert len(valid_hovers) == 2  # Only 2 instances with valid cores
    # Check that hover text contains efficiency info (proves calculation succeeded)
    assert "Scaling Efficiency:" in valid_hovers[0]
    assert "Scaling Efficiency:" in valid_hovers[1]


def test_create_cloud_scaling_chart_handles_nan_memory_values():
    """Test that chart handles NaN memory_gb values gracefully.

    Validates that hover text (stored in customdata) does not show "nan GB"
    when memory_gb contains pd.NA values.
    """
    # Create data where memory_gb column exists but some values are NaN
    data_nan_memory = pd.DataFrame([
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
            "memory_gb": pd.NA,  # Missing memory
            "mean_performance": 195000.0,
        },
        {
            "instance_type": "c2-standard-16",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 16,
            "memory_gb": pd.NA,  # Missing memory
            "mean_performance": 380000.0,
        },
    ])

    # Should render without crashing
    fig = create_cloud_scaling_chart(data_nan_memory)

    # Verify chart was created
    assert fig is not None
    assert len(fig.data) > 0

    # Check customdata (which feeds hovertemplate) doesn't contain "nan GB"
    trace = fig.data[0]
    assert hasattr(trace, 'customdata'), "Chart should use customdata for hover text"

    # Verify all hover texts are valid and don't contain "nan GB"
    for hover_text in trace.customdata:
        hover_str = str(hover_text).lower()
        # Should not contain "nan gb" or "nan" near "gb"
        assert "nan gb" not in hover_str, f"Found 'nan GB' in hover text: {hover_text}"
        assert "nan.0 gb" not in hover_str, f"Found 'nan.0 GB' in hover text: {hover_text}"

        # More robust check: if "gb" appears, there shouldn't be "nan" before it
        if " gb" in hover_str:
            # Extract the part before " gb" (e.g., "16.0 gb" -> "16.0")
            gb_parts = hover_str.split(" gb")
            for part in gb_parts[:-1]:  # All parts except the last (after final "gb")
                # Get the last token before "gb" (the number)
                tokens = part.split()
                if tokens:
                    last_token = tokens[-1]
                    assert "nan" not in last_token, f"Found 'nan' before GB in: {hover_text}"

    # First instance should have memory in hover text
    assert "16 GB" in trace.customdata[0] or "16.0 GB" in trace.customdata[0]

    # Second and third instances should NOT have memory info
    assert "Memory:" not in trace.customdata[1] or " GB" not in trace.customdata[1]
    assert "Memory:" not in trace.customdata[2] or " GB" not in trace.customdata[2]


@pytest.fixture
def comparison_data():
    """Sample comparison data for baseline vs comparison charts."""
    return pd.DataFrame([
        {
            "test_name": "coremark",
            "baseline_mean": 100000.0,
            "baseline_std": 1000.0,
            "comparison_mean": 105000.0,
            "comparison_std": 1500.0
        },
        {
            "test_name": "streams",
            "baseline_mean": 50000.0,
            "baseline_std": 500.0,
            "comparison_mean": 48000.0,
            "comparison_std": 600.0
        },
        {
            "test_name": "iperf",
            "baseline_mean": 8500.0,
            "baseline_std": 100.0,
            "comparison_mean": 8700.0,
            "comparison_std": 150.0
        }
    ])


def test_create_comparison_chart_has_legend(comparison_data):
    """Test that comparison chart has a visible legend explaining colors."""
    fig = create_comparison_chart(comparison_data)

    # Chart should have legend enabled
    assert fig.layout.showlegend is not False, "Legend should be visible"

    # Should have legend configuration
    assert hasattr(fig.layout, 'legend'), "Chart should have legend config"


def test_create_comparison_chart_legend_positioned_consistently(comparison_data):
    """Test that legend is positioned at bottom (consistent positioning)."""
    fig = create_comparison_chart(comparison_data)

    # Legend should be positioned at bottom with horizontal orientation
    assert fig.layout.legend.orientation == 'h', "Legend should be horizontal"
    assert fig.layout.legend.yanchor == 'top', "Legend should be anchored to top"
    assert fig.layout.legend.y < 0, "Legend should be below chart (y < 0)"


def test_create_comparison_chart_legend_explains_colors(comparison_data):
    """Test that legend trace names explain what baseline/comparison colors mean."""
    fig = create_comparison_chart(comparison_data)

    # Should have two traces: Baseline and Comparison
    assert len(fig.data) == 2, "Should have two traces"

    trace_names = [trace.name for trace in fig.data]
    assert 'Baseline' in trace_names, "Should have Baseline trace"
    assert 'Comparison' in trace_names, "Should have Comparison trace"


def test_create_comparison_chart_legend_does_not_obscure_data(comparison_data):
    """Test that legend positioning doesn't obscure chart data."""
    fig = create_comparison_chart(comparison_data)

    # Legend should be outside plot area (below it)
    # This is ensured by y < 0 which places it below the plot
    assert fig.layout.legend.y < 0, "Legend should be positioned below chart to avoid obscuring data"

    # Chart should have bottom margin to accommodate legend
    assert fig.layout.margin.b >= 80, "Chart should have bottom margin for legend"
