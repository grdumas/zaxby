"""
Tests for visualization components.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
from src.components.visualizations import (
    create_cloud_scaling_chart,
    create_comparison_chart,
    create_box_plot,
    create_scatter_plot,
    create_heatmap,
    create_regression_heatmap,
    create_time_series_chart,
    create_version_comparison_bar_chart,
    LEGEND_RIGHT_MARGIN
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


@pytest.fixture
def box_plot_data_with_color():
    """Sample data for box plot with color grouping."""
    return pd.DataFrame([
        {"test_name": "coremark", "os_version": "RHEL 9.0", "primary_metric_value": 100000},
        {"test_name": "coremark", "os_version": "RHEL 9.0", "primary_metric_value": 102000},
        {"test_name": "coremark", "os_version": "RHEL 9.1", "primary_metric_value": 105000},
        {"test_name": "coremark", "os_version": "RHEL 9.1", "primary_metric_value": 107000},
        {"test_name": "streams", "os_version": "RHEL 9.0", "primary_metric_value": 50000},
        {"test_name": "streams", "os_version": "RHEL 9.0", "primary_metric_value": 51000},
        {"test_name": "streams", "os_version": "RHEL 9.1", "primary_metric_value": 52000},
        {"test_name": "streams", "os_version": "RHEL 9.1", "primary_metric_value": 53000},
    ])


def test_create_box_plot_with_color_has_legend(box_plot_data_with_color):
    """Test that box plot with color grouping has visible legend."""
    fig = create_box_plot(
        box_plot_data_with_color,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col='os_version'
    )

    # Legend should be visible when color_col is used
    assert fig.layout.showlegend is not False, "Legend should be visible"
    assert hasattr(fig.layout, 'legend'), "Chart should have legend config"


def test_create_box_plot_legend_positioned_at_bottom(box_plot_data_with_color):
    """Test that box plot legend is positioned consistently at bottom."""
    fig = create_box_plot(
        box_plot_data_with_color,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col='os_version'
    )

    # Legend should be horizontal at bottom
    assert fig.layout.legend.orientation == 'h', "Legend should be horizontal"
    assert fig.layout.legend.yanchor == 'top', "Legend should anchor to top"
    assert fig.layout.legend.y < 0, "Legend should be below chart"


def test_create_box_plot_legend_explains_color_groups(box_plot_data_with_color):
    """Test that legend explains what color groups represent."""
    fig = create_box_plot(
        box_plot_data_with_color,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col='os_version'
    )

    # Should have traces for each OS version
    trace_names = [trace.name for trace in fig.data]
    assert any("RHEL 9.0" in name for name in trace_names), "Should have RHEL 9.0 in legend"
    assert any("RHEL 9.1" in name for name in trace_names), "Should have RHEL 9.1 in legend"


def test_create_box_plot_without_color_has_no_legend():
    """Test that box plot without color grouping doesn't need legend."""
    data = pd.DataFrame([
        {"test_name": "coremark", "primary_metric_value": 100000},
        {"test_name": "coremark", "primary_metric_value": 102000},
        {"test_name": "streams", "primary_metric_value": 50000},
        {"test_name": "streams", "primary_metric_value": 51000},
    ])

    fig = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col=None
    )

    # No color grouping, so legend can be hidden
    # (Not required, but acceptable to show trace names)
    assert isinstance(fig, go.Figure), "Should create valid figure"


def test_faceted_box_plot_hides_legend_when_no_color():
    """Test that faceted box plots hide legend when color_col is None (redundant).

    When faceting without color grouping, the facet labels already identify each
    group, making the legend redundant.
    """
    # Create data with multiple test names, no color grouping
    data = pd.DataFrame([
        {"test_name": "coremark", "primary_metric_value": 100000.0},
        {"test_name": "coremark", "primary_metric_value": 102000.0},
        {"test_name": "streams", "primary_metric_value": 50000.0},
        {"test_name": "streams", "primary_metric_value": 51000.0},
    ])

    # Create faceted box plot WITHOUT color grouping
    fig = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col=None,
        use_facets=True
    )

    # Legend should be disabled because facet labels already identify test names
    assert fig.layout.showlegend is False, (
        "Faceted box plots without color grouping should hide legend "
        "(redundant with facet labels)"
    )


def test_faceted_box_plot_shows_legend_when_color_differs_from_facet():
    """Test that faceted box plots show legend when color represents different dimension.

    When color_col represents a different grouping variable than the facet variable,
    the legend is needed to explain what the colors represent. Facet labels only
    identify the facet dimension, not the color dimension.
    """
    # Create data with faceting by test_name and coloring by config
    data = pd.DataFrame([
        {"test_name": "coremark", "config": "baseline", "primary_metric_value": 100000.0},
        {"test_name": "coremark", "config": "baseline", "primary_metric_value": 102000.0},
        {"test_name": "coremark", "config": "optimized", "primary_metric_value": 120000.0},
        {"test_name": "coremark", "config": "optimized", "primary_metric_value": 122000.0},
        {"test_name": "streams", "config": "baseline", "primary_metric_value": 50000.0},
        {"test_name": "streams", "config": "baseline", "primary_metric_value": 51000.0},
        {"test_name": "streams", "config": "optimized", "primary_metric_value": 55000.0},
        {"test_name": "streams", "config": "optimized", "primary_metric_value": 56000.0},
    ])

    # Create faceted box plot with color representing different dimension
    fig = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col='config',  # Different from facet variable
        use_facets=True
    )

    # Legend should be shown because colors represent a different dimension (config)
    # that's not captured by facet labels
    assert fig.layout.showlegend is not False, (
        "Faceted box plots should show legend when color_col represents "
        "a different dimension than the facet variable"
    )


def test_faceted_box_plot_legend_positioned_when_shown():
    """Test that legend is positioned consistently when shown in faceted box plots."""
    # Create data with faceting and color representing different dimensions
    data = pd.DataFrame([
        {"test_name": "coremark", "os_version": "RHEL 9.0", "primary_metric_value": 100000.0},
        {"test_name": "coremark", "os_version": "RHEL 9.1", "primary_metric_value": 105000.0},
        {"test_name": "streams", "os_version": "RHEL 9.0", "primary_metric_value": 50000.0},
        {"test_name": "streams", "os_version": "RHEL 9.1", "primary_metric_value": 52000.0},
    ])

    # Create faceted box plot with color grouping
    fig = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col='os_version',  # Different dimension
        use_facets=True
    )

    # When legend is shown, it should use consistent positioning (horizontal bottom)
    if fig.layout.showlegend is not False:
        legend = fig.layout.legend
        assert legend is not None, "Legend config should exist when showlegend is True"
        assert legend.orientation == 'h', "Legend should be horizontal"
        assert legend.yanchor == 'top', "Legend should anchor to top"
        assert legend.y < 0, "Legend should be below chart"


@pytest.fixture
def scatter_plot_data():
    """Sample data for scatter plots."""
    return pd.DataFrame([
        {"cpu_cores": 4, "performance": 100000, "instance_type": "c2-standard-4", "cost": 150},
        {"cpu_cores": 8, "performance": 195000, "instance_type": "c2-standard-8", "cost": 300},
        {"cpu_cores": 16, "performance": 380000, "instance_type": "c2-standard-16", "cost": 600},
        {"cpu_cores": 4, "performance": 98000, "instance_type": "n2-standard-4", "cost": 140},
        {"cpu_cores": 8, "performance": 190000, "instance_type": "n2-standard-8", "cost": 280},
        {"cpu_cores": 16, "performance": 370000, "instance_type": "n2-standard-16", "cost": 560},
    ])


def test_create_scatter_plot_with_color_has_legend(scatter_plot_data):
    """Test that scatter plot with color grouping has visible legend."""
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        color_col='instance_type'
    )

    # Legend should be visible when color_col is used
    assert fig.layout.showlegend is not False, "Legend should be visible"
    assert hasattr(fig.layout, 'legend'), "Chart should have legend config"


def test_create_scatter_plot_legend_positioned_right(scatter_plot_data):
    """Test that scatter plot legend is positioned on right side."""
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        color_col='instance_type'
    )

    # Legend should be vertical on right side (better for scatter plots)
    assert fig.layout.legend.orientation == 'v', "Legend should be vertical"
    assert fig.layout.legend.xanchor == 'left', "Legend should anchor to left"
    assert fig.layout.legend.x > 1.0, "Legend should be to right of chart"


def test_create_scatter_plot_legend_explains_colors(scatter_plot_data):
    """Test that legend explains what colors represent."""
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        color_col='instance_type'
    )

    # Should have traces for each instance type
    trace_names = [trace.name for trace in fig.data]
    assert 'c2-standard-4' in trace_names or 'instance_type=c2-standard-4' in str(trace_names)


def test_create_scatter_plot_with_size_has_legend(scatter_plot_data):
    """Test that scatter plot with size encoding has legend for both color and size."""
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        color_col='instance_type',
        size_col='cost'
    )

    # Legend should be visible
    assert fig.layout.showlegend is not False, "Legend should be visible for color/size"


def test_create_scatter_plot_legend_does_not_obscure_data(scatter_plot_data):
    """Test that legend is positioned outside plot area."""
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        color_col='instance_type'
    )

    # Legend should be positioned to right (x > 1) to avoid obscuring data
    assert fig.layout.legend.x > 1.0, "Legend should be outside plot area"

    # Chart should have right margin for legend
    assert fig.layout.margin.r >= 150, "Chart should have right margin for legend"


def test_create_scatter_plot_with_only_size_has_minimal_margin(scatter_plot_data):
    """Test that scatter plot with ONLY size encoding uses minimal right margin.

    When only size_col is set (no color_col), Plotly doesn't create a discrete
    legend that needs 200px of space. The margin should be minimal (default).
    """
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        size_col='cost'
    )

    # Should NOT have large right margin when only size is used
    # Verify that code did NOT set the right margin to LEGEND_RIGHT_MARGIN
    margin_r = fig.layout.margin.r
    assert margin_r != LEGEND_RIGHT_MARGIN, \
        f"Right margin should not be set to LEGEND_RIGHT_MARGIN without color legend, got {margin_r}"


def test_create_scatter_plot_empty_string_color_col_behaves_like_none(scatter_plot_data):
    """Test that color_col='' (empty string) behaves like color_col=None.

    This defends against UI passing empty strings instead of None, which could
    crash Plotly Express. Empty string should be normalized to None.
    """
    # Create scatter plot with empty string color_col
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        color_col=""
    )

    # Chart should be created successfully (no crash)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0

    # Should NOT have large right margin (same behavior as color_col=None)
    margin_r = fig.layout.margin.r
    assert margin_r != LEGEND_RIGHT_MARGIN, \
        f"Empty string color_col should not trigger large right margin, got {margin_r}"


def test_create_scatter_plot_with_color_has_large_margin(scatter_plot_data):
    """Test that scatter plot with color encoding has large right margin for discrete legend."""
    fig = create_scatter_plot(
        scatter_plot_data,
        x_col='cpu_cores',
        y_col='performance',
        color_col='instance_type'
    )

    # Should have large right margin for discrete color legend
    assert fig.layout.margin.r == LEGEND_RIGHT_MARGIN, \
        f"Chart with color legend should have right margin set to LEGEND_RIGHT_MARGIN ({LEGEND_RIGHT_MARGIN}), got {fig.layout.margin.r}"


@pytest.fixture
def heatmap_data():
    """Sample data for heatmap."""
    return pd.DataFrame([
        {"os_version": "RHEL 9.0", "instance_type": "c2-standard-4", "primary_metric_value": 100000},
        {"os_version": "RHEL 9.0", "instance_type": "c2-standard-8", "primary_metric_value": 195000},
        {"os_version": "RHEL 9.1", "instance_type": "c2-standard-4", "primary_metric_value": 105000},
        {"os_version": "RHEL 9.1", "instance_type": "c2-standard-8", "primary_metric_value": 200000},
        {"os_version": "RHEL 9.2", "instance_type": "c2-standard-4", "primary_metric_value": 103000},
        {"os_version": "RHEL 9.2", "instance_type": "c2-standard-8", "primary_metric_value": 198000},
    ])


def test_create_heatmap_has_colorbar(heatmap_data):
    """Test that heatmap has colorbar legend."""
    fig = create_heatmap(heatmap_data)

    # Heatmap should have a colorbar (Plotly heatmaps have this by default)
    assert len(fig.data) > 0, "Heatmap should have data"
    assert hasattr(fig.data[0], 'colorbar'), "Heatmap should have colorbar"


def test_create_heatmap_has_help_annotation(heatmap_data):
    """Test that heatmap has help annotation explaining how to read it."""
    fig = create_heatmap(heatmap_data)

    # Should have at least one annotation with help text
    assert len(fig.layout.annotations) > 0, "Heatmap should have help annotations"

    # Check that annotation contains helpful context
    annotation_texts = [ann.text.lower() for ann in fig.layout.annotations]
    has_help_text = any(
        'color' in text or 'red' in text or 'green' in text or 'performance' in text
        for text in annotation_texts
    )
    assert has_help_text, "Annotation should provide context about color meaning"


def test_create_heatmap_annotation_positioned_clearly(heatmap_data):
    """Test that help annotation is positioned to not obscure data."""
    fig = create_heatmap(heatmap_data)

    # Annotations should be positioned outside main plot area or in corner
    has_outside_annotation = False
    for ann in fig.layout.annotations:
        # Check that annotation uses paper coordinates (relative positioning)
        # and is positioned in a corner or edge
        if hasattr(ann, 'xref') and ann.xref == 'paper':
            # Should be in corner (x near 0 or 1, y near 0 or 1)
            is_in_corner = (
                (ann.x <= 0.1 or ann.x >= 0.9) or
                (ann.y <= 0.1 or ann.y >= 0.9)
            )
            # At least some annotations should be positioned clearly
            # (This is a soft check - we just want to verify positioning is considered)
            if ann.x > 1.0:
                has_outside_annotation = True

    # At least one annotation should be positioned outside plot area (x > 1.0)
    assert has_outside_annotation, "At least one annotation should be positioned outside plot area (x > 1.0)"

    # Chart should have right margin for annotation positioned outside
    assert fig.layout.margin.r is not None and fig.layout.margin.r >= 180, "Chart should have right margin for annotation"


def test_create_heatmap_colorbar_has_title(heatmap_data):
    """Test that colorbar has a descriptive title."""
    fig = create_heatmap(heatmap_data)

    # Colorbar should have a title
    colorbar = fig.data[0].colorbar
    assert hasattr(colorbar, 'title'), "Colorbar should have title config"
    assert colorbar.title.text is not None, "Colorbar title should not be empty"


@pytest.fixture
def regression_heatmap_data():
    """Sample data for regression heatmap (percent changes)."""
    data = {
        '9.0→9.1': [5.2, -3.1, 1.8],
        '9.1→9.2': [-2.5, 4.3, 0.9],
        '9.2→9.3': [7.8, -5.2, 2.1]
    }
    return pd.DataFrame(data, index=['coremark', 'streams', 'iperf'])


def test_create_regression_heatmap_has_colorbar(regression_heatmap_data):
    """Test that regression heatmap has colorbar."""
    fig = create_regression_heatmap(regression_heatmap_data)

    # Should have colorbar
    assert len(fig.data) > 0, "Heatmap should have data"
    assert hasattr(fig.data[0], 'colorbar'), "Should have colorbar"


def test_create_regression_heatmap_has_help_annotation(regression_heatmap_data):
    """Test that regression heatmap has help annotation explaining color scale."""
    fig = create_regression_heatmap(regression_heatmap_data)

    # Should have help annotation
    assert len(fig.layout.annotations) > 0, "Should have help annotations"

    # Check for color explanation
    annotation_texts = [ann.text.lower() for ann in fig.layout.annotations]
    has_color_help = any(
        'red' in text or 'green' in text or 'regression' in text or 'improvement' in text
        for text in annotation_texts
    )
    assert has_color_help, "Annotation should explain red/green color meaning"


def test_create_regression_heatmap_annotation_positioned_clearly(regression_heatmap_data):
    """Test that annotation is positioned outside plot area with proper margin."""
    fig = create_regression_heatmap(regression_heatmap_data)

    # Should have at least one annotation positioned outside the right edge
    assert len(fig.layout.annotations) > 0, "Should have help annotations"

    # At least one annotation should be positioned to the right (x > 1.0) using paper coordinates
    annotations_outside_right = [
        ann for ann in fig.layout.annotations
        if hasattr(ann, 'xref') and ann.xref == 'paper' and ann.x > 1.0
    ]
    assert len(annotations_outside_right) > 0, \
        "At least one annotation should be positioned outside right edge (xref='paper', x > 1.0)"

    # Chart should have right margin to accommodate the annotation
    assert fig.layout.margin.r >= 180, \
        "Chart should have right margin >= 180 to prevent annotation clipping"


def test_create_heatmap_colorbar_positioned_explicitly(heatmap_data):
    """Test that heatmap colorbar has explicit positioning to avoid overlap with help annotation."""
    fig = create_heatmap(heatmap_data)

    # Colorbar should have explicit positioning
    colorbar = fig.data[0].colorbar
    assert hasattr(colorbar, 'x'), "Colorbar should have explicit x position"
    assert colorbar.x is not None, "Colorbar x position should be set"
    assert hasattr(colorbar, 'xanchor'), "Colorbar should have xanchor"
    assert colorbar.xanchor == 'left', "Colorbar should be anchored to left edge"


def test_create_heatmap_annotation_avoids_colorbar_collision(heatmap_data):
    """Test that help annotation is positioned to not overlap with colorbar."""
    fig = create_heatmap(heatmap_data)

    # Get colorbar position
    colorbar = fig.data[0].colorbar
    colorbar_x = colorbar.x if hasattr(colorbar, 'x') and colorbar.x is not None else 1.02

    # Get help annotation position
    help_annotations = [
        ann for ann in fig.layout.annotations
        if hasattr(ann, 'xref') and ann.xref == 'paper' and ann.x > 1.0
    ]
    assert len(help_annotations) > 0, "Should have help annotation positioned outside plot"

    help_ann = help_annotations[0]

    # Help annotation should either:
    # 1. Be positioned further right than colorbar (with sufficient gap), OR
    # 2. Use xshift to move away from colorbar position
    if hasattr(help_ann, 'xshift') and help_ann.xshift is not None:
        # If using xshift, the shift should be significant enough to avoid overlap
        assert abs(help_ann.xshift) >= 80, \
            f"Help annotation should use xshift >= 80 to avoid colorbar, got {help_ann.xshift}"
    else:
        # If not using xshift, x position should be sufficiently different
        x_gap = abs(help_ann.x - colorbar_x)
        assert x_gap >= 0.15, \
            f"Help annotation x position should be at least 0.15 away from colorbar, got gap={x_gap:.3f}"


def test_create_regression_heatmap_colorbar_positioned_explicitly(regression_heatmap_data):
    """Test that regression heatmap colorbar has explicit positioning."""
    fig = create_regression_heatmap(regression_heatmap_data)

    # Colorbar should have explicit positioning
    colorbar = fig.data[0].colorbar
    assert hasattr(colorbar, 'x'), "Colorbar should have explicit x position"
    assert colorbar.x is not None, "Colorbar x position should be set"
    assert hasattr(colorbar, 'xanchor'), "Colorbar should have xanchor"
    assert colorbar.xanchor == 'left', "Colorbar should be anchored to left edge"


def test_create_regression_heatmap_annotation_avoids_colorbar_collision(regression_heatmap_data):
    """Test that regression heatmap help annotation avoids colorbar collision."""
    fig = create_regression_heatmap(regression_heatmap_data)

    # Get colorbar position
    colorbar = fig.data[0].colorbar
    colorbar_x = colorbar.x if hasattr(colorbar, 'x') and colorbar.x is not None else 1.02

    # Get help annotation position
    help_annotations = [
        ann for ann in fig.layout.annotations
        if hasattr(ann, 'xref') and ann.xref == 'paper' and ann.x > 1.0
    ]
    assert len(help_annotations) > 0, "Should have help annotation positioned outside plot"

    help_ann = help_annotations[0]

    # Help annotation should either use xshift or be positioned with sufficient gap
    if hasattr(help_ann, 'xshift') and help_ann.xshift is not None:
        assert abs(help_ann.xshift) >= 80, \
            f"Help annotation should use xshift >= 80 to avoid colorbar, got {help_ann.xshift}"
    else:
        x_gap = abs(help_ann.x - colorbar_x)
        assert x_gap >= 0.15, \
            f"Help annotation x position should be at least 0.15 away from colorbar, got gap={x_gap:.3f}"


def test_create_heatmap_adequate_right_margin(heatmap_data):
    """Test that heatmap has adequate right margin for colorbar and annotation."""
    fig = create_heatmap(heatmap_data)

    # Should have sufficient right margin to accommodate both colorbar and annotation
    # Colorbar typically needs ~80px, annotation needs ~120px + gap
    assert fig.layout.margin.r >= 200, \
        f"Heatmap should have right margin >= 200 to fit colorbar + annotation, got {fig.layout.margin.r}"


def test_create_regression_heatmap_adequate_right_margin(regression_heatmap_data):
    """Test that regression heatmap has adequate right margin."""
    fig = create_regression_heatmap(regression_heatmap_data)

    # Should have sufficient right margin
    assert fig.layout.margin.r >= 200, \
        f"Regression heatmap should have right margin >= 200, got {fig.layout.margin.r}"


@pytest.fixture
def time_series_data():
    """Sample time series data."""
    return pd.DataFrame([
        {"timestamp": "2024-01-01", "primary_metric_value": 100000, "test_name": "coremark"},
        {"timestamp": "2024-01-02", "primary_metric_value": 102000, "test_name": "coremark"},
        {"timestamp": "2024-01-03", "primary_metric_value": 101500, "test_name": "coremark"},
        {"timestamp": "2024-01-01", "primary_metric_value": 50000, "test_name": "streams"},
        {"timestamp": "2024-01-02", "primary_metric_value": 51000, "test_name": "streams"},
        {"timestamp": "2024-01-03", "primary_metric_value": 52000, "test_name": "streams"},
    ])


def test_create_time_series_chart_has_legend(time_series_data):
    """Test that time series chart has visible legend."""
    fig = create_time_series_chart(time_series_data, color_col='test_name')

    # Legend should be visible
    assert fig.layout.showlegend is not False, "Legend should be visible"


def test_create_time_series_legend_positioned_consistently(time_series_data):
    """Test that time series legend is positioned consistently (top-right)."""
    fig = create_time_series_chart(time_series_data, color_col='test_name', use_facets=False)

    # Legend should be positioned at top-right (standard for time series)
    legend = fig.layout.legend
    assert legend.orientation == 'v', "Legend should be vertical"
    assert legend.xanchor == 'right', "Legend should anchor to right"
    assert legend.x >= 0.95, "Legend should be on right side"
    assert legend.yanchor == 'top', "Legend should anchor to top"
    assert legend.y >= 0.95, "Legend should be at top"


def test_create_time_series_legend_does_not_obscure_data(time_series_data):
    """Test that legend positioning doesn't obscure time series data."""
    fig = create_time_series_chart(time_series_data, color_col='test_name', use_facets=False)

    # Legend should be inside plot area but at top-right corner
    # This is acceptable for time series as data usually doesn't reach top-right
    legend = fig.layout.legend
    assert legend.x <= 1.0, "Legend should be within plot area (not outside)"
    assert legend.y <= 1.0, "Legend should be within plot area"


def test_create_time_series_faceted_hides_legend(time_series_data):
    """Test that faceted time series hides legend (redundant with facet labels)."""
    fig = create_time_series_chart(
        time_series_data,
        color_col='test_name',
        use_facets=True
    )

    # Legend should be hidden when using facets (facet labels replace legend)
    assert fig.layout.showlegend is False, "Legend should be hidden for faceted time series"

    # Verify that facets were actually created (multiple subplot rows)
    # In plotly, faceted charts have multiple yaxis (yaxis, yaxis2, yaxis3, etc.)
    # Use public API: check for existence of second y-axis
    assert hasattr(fig.layout, 'yaxis2'), "Should have multiple y-axes for faceted chart"


@pytest.fixture
def single_trace_time_series_data():
    """Sample time series data with single trace (no grouping)."""
    return pd.DataFrame([
        {"timestamp": "2024-01-01", "primary_metric_value": 100000},
        {"timestamp": "2024-01-02", "primary_metric_value": 102000},
        {"timestamp": "2024-01-03", "primary_metric_value": 101500},
        {"timestamp": "2024-01-04", "primary_metric_value": 103000},
    ])


def test_create_time_series_single_trace_no_legend_config(single_trace_time_series_data):
    """Test that single-trace time series (color_col=None) does not configure legend.

    When there's only one trace (no color_col), a legend is unnecessary and
    should not be explicitly configured.
    """
    fig = create_time_series_chart(
        single_trace_time_series_data,
        color_col=None,
        use_facets=False
    )

    # Chart should be created successfully
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0

    # Legend should either be disabled or not explicitly configured
    # Plotly may show a default legend even for single trace, but we shouldn't
    # be explicitly positioning it with our custom legend dict
    # Check that our custom legend config (top-right positioning) was not applied
    legend = fig.layout.legend

    # If legend dict exists, it should not have our custom positioning
    # (orientation='v', x=0.99, y=0.99, etc.)
    # The best way to check this is that the legend dict should either not exist
    # or should not have all our custom properties
    if legend is not None:
        # Should not have ALL of our custom legend properties
        has_all_custom_props = (
            hasattr(legend, 'orientation') and legend.orientation == 'v' and
            hasattr(legend, 'xanchor') and legend.xanchor == 'right' and
            hasattr(legend, 'x') and legend.x == 0.99 and
            hasattr(legend, 'yanchor') and legend.yanchor == 'top' and
            hasattr(legend, 'y') and legend.y == 0.99
        )
        assert not has_all_custom_props, \
            "Single-trace chart should not have custom legend positioning"


def test_create_time_series_multi_trace_has_legend_config(time_series_data):
    """Test that multi-trace time series (color_col provided) configures legend properly.

    When color_col is provided, we expect multiple traces with different colors,
    so the legend should be explicitly configured and positioned.
    """
    fig = create_time_series_chart(
        time_series_data,
        color_col='test_name',
        use_facets=False
    )

    # Chart should be created successfully
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 1, "Should have multiple traces when color_col is provided"

    # Legend should be explicitly configured with our standard positioning
    legend = fig.layout.legend
    assert legend is not None, "Legend should be configured for multi-trace chart"
    assert legend.orientation == 'v', "Legend should be vertical"
    assert legend.xanchor == 'right', "Legend should anchor to right"
    assert legend.x == 0.99, "Legend should be at x=0.99"
    assert legend.yanchor == 'top', "Legend should anchor to top"
    assert legend.y == 0.99, "Legend should be at y=0.99"
    assert legend.bgcolor == 'rgba(255, 255, 255, 0.8)', \
        "Legend should have semi-transparent background"


def test_create_time_series_empty_string_color_col_behaves_like_none(time_series_data):
    """Test that color_col='' (empty string) behaves like color_col=None.

    This defends against UI passing empty strings instead of None, which could
    crash Plotly Express. Empty string should be normalized to None.
    """
    # Create chart with empty string color_col
    fig = create_time_series_chart(
        time_series_data,
        color_col="",
        use_facets=False
    )

    # Chart should be created successfully (no crash)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0

    # Legend should NOT be configured (same behavior as color_col=None)
    legend = fig.layout.legend
    if legend is not None:
        # Should not have our custom legend positioning for multi-trace
        has_all_custom_props = (
            hasattr(legend, 'orientation') and legend.orientation == 'v' and
            hasattr(legend, 'xanchor') and legend.xanchor == 'right' and
            hasattr(legend, 'x') and legend.x == 0.99 and
            hasattr(legend, 'yanchor') and legend.yanchor == 'top' and
            hasattr(legend, 'y') and legend.y == 0.99
        )
        assert not has_all_custom_props, \
            "Empty string color_col should not trigger custom legend config"


# ============================================================================
# Colorblind Mode Tests
# ============================================================================

@pytest.fixture
def comparison_data():
    """Sample comparison data for testing colorblind mode."""
    return pd.DataFrame([
        {"test_name": "benchmark1", "baseline_mean": 100, "comparison_mean": 110},
        {"test_name": "benchmark2", "baseline_mean": 200, "comparison_mean": 195},
    ])


@pytest.fixture
def regression_heatmap_data():
    """Sample data for regression heatmap testing."""
    df = pd.DataFrame({
        "test1": [5.0, -5.0],  # % changes
        "test2": [10.0, -10.0],
    }, index=["rhel8_to_rhel9", "rhel9_to_rhel10"])
    return df


def test_create_comparison_chart_colorblind_mode(comparison_data):
    """Comparison chart uses colorblind-safe colors when colorblind_mode=True."""
    # Standard mode
    fig_standard = create_comparison_chart(comparison_data, colorblind_mode=False)
    # Colorblind mode
    fig_colorblind = create_comparison_chart(comparison_data, colorblind_mode=True)

    # Verify different colors are used
    baseline_color_standard = fig_standard.data[0].marker.color
    baseline_color_colorblind = fig_colorblind.data[0].marker.color

    # Should not be the same
    assert baseline_color_standard != baseline_color_colorblind

    # Colorblind should use sky blue (#56b4e9) not lightblue
    assert baseline_color_colorblind == "#56b4e9"


def test_create_heatmap_colorblind_uses_safe_scale():
    """Heatmap uses colorblind-safe scale instead of RdYlGn when colorblind_mode=True."""
    df = pd.DataFrame({
        "os_version": ["RHEL8", "RHEL8", "RHEL9", "RHEL9"],
        "instance_type": ["m5.large", "m5.xlarge", "m5.large", "m5.xlarge"],
        "primary_metric_value": [100, 110, 105, 115],
    })

    fig_standard = create_heatmap(df, colorblind_mode=False)
    fig_colorblind = create_heatmap(df, colorblind_mode=True)

    standard_scale = fig_standard.data[0].colorscale
    colorblind_scale = fig_colorblind.data[0].colorscale

    # Standard mode: Plotly may keep it as the string 'RdYlGn' or expand to RGB values
    if isinstance(standard_scale, str):
        assert standard_scale == 'RdYlGn'
    else:
        # If expanded, verify it's a list/tuple
        assert isinstance(standard_scale, (list, tuple))

    # Colorblind mode: should be a list/tuple with blue-orange scale
    assert isinstance(colorblind_scale, (list, tuple))

    # The scales should be different
    assert standard_scale != colorblind_scale

    # Colorblind scale should contain hex codes from the blue-orange palette
    # Extract color values (second element of each tuple)
    colorblind_colors = [c[1] for c in colorblind_scale if isinstance(c, tuple)]
    # Verify it doesn't match the standard RdYlGn RGB pattern
    if isinstance(standard_scale, (list, tuple)):
        standard_colors = [c[1] for c in standard_scale if isinstance(c, tuple)]
        assert colorblind_colors != standard_colors


def test_regression_heatmap_colorblind_scale(regression_heatmap_data):
    """Regression heatmap does not use red/green in colorblind mode."""
    fig_colorblind = create_regression_heatmap(
        regression_heatmap_data, colorblind_mode=True
    )

    colorscale = fig_colorblind.data[0].colorscale

    # Extract all color hex codes from the scale
    colors = [color for _, color in colorscale]

    # Should NOT contain standard red or green
    assert "#d73027" not in colors, "Colorblind heatmap should not use standard red"
    assert "#1a9850" not in colors, "Colorblind heatmap should not use standard green"

    # Should contain colorblind-safe colors
    # The COLORBLIND palette uses #d55e00 (vermillion) and #0072b2 (blue)
    # At minimum, verify it's using a different scale
    assert colorscale != [
        (0.0, "#d73027"),
        (0.4, "#fee090"),
        (0.5, "#e0e0e0"),
        (0.6, "#e0f3db"),
        (1.0, "#1a9850"),
    ], "Colorblind mode should use a different scale than standard"


def test_version_comparison_legend_matches_colorblind_palette():
    """
    Test that version comparison chart legend uses colorblind palette labels
    when colorblind_mode=True.

    The legend should show "Vermillion" and "Blue" in colorblind mode, not
    "Red" and "Green" from the standard palette.
    """
    # Create fixture data with all types of results
    comparison_df = pd.DataFrame([
        {
            "test_name": "all_regressed",
            "baseline_mean": 100.0,
            "comparison_mean": 80.0,
            "percent_change": -20.0,
            "is_regression": True,
            "hardware_config": "config1"
        },
        {
            "test_name": "all_regressed",
            "baseline_mean": 100.0,
            "comparison_mean": 85.0,
            "percent_change": -15.0,
            "is_regression": True,
            "hardware_config": "config2"
        },
        {
            "test_name": "all_improved",
            "baseline_mean": 100.0,
            "comparison_mean": 120.0,
            "percent_change": 20.0,
            "is_regression": False,
            "hardware_config": "config1"
        },
        {
            "test_name": "all_improved",
            "baseline_mean": 100.0,
            "comparison_mean": 125.0,
            "percent_change": 25.0,
            "is_regression": False,
            "hardware_config": "config2"
        },
        {
            "test_name": "mixed_net_regression",
            "baseline_mean": 100.0,
            "comparison_mean": 90.0,
            "percent_change": -10.0,
            "is_regression": True,
            "hardware_config": "config1"
        },
        {
            "test_name": "mixed_net_regression",
            "baseline_mean": 100.0,
            "comparison_mean": 105.0,
            "percent_change": 5.0,
            "is_regression": False,
            "hardware_config": "config2"
        }
    ])

    fig = create_version_comparison_bar_chart(
        comparison_df=comparison_df,
        baseline_version="v1.0",
        comparison_version="v2.0",
        colorblind_mode=True
    )

    # Extract legend annotation text from fig.layout.annotations
    legend_annotations = [
        ann for ann in fig.layout.annotations
        if hasattr(ann, 'text') and 'Legend:' in ann.text
    ]

    assert len(legend_annotations) == 1, "Should have exactly one legend annotation"
    legend_text = legend_annotations[0].text

    # In colorblind mode, legend should use colorblind palette terms
    assert "Vermillion" in legend_text, "Colorblind legend should mention 'Vermillion' for regression"
    assert "Blue" in legend_text, "Colorblind legend should mention 'Blue' for improvement"

    # In colorblind mode, legend should NOT use standard palette terms
    assert "Red" not in legend_text or "Dark Red" not in legend_text, \
        "Colorblind legend should not use 'Red' or 'Dark Red'"
    assert "Green" not in legend_text, "Colorblind legend should not use 'Green'"


@pytest.fixture
def peer_os_comparison_data():
    """Sample peer OS comparison data with competitive, moderate, and significant differences."""
    return pd.DataFrame([
        {
            "peer_os": "Ubuntu",
            "benchmark_category": "CPU",
            "relative_performance": 95.0,  # Competitive (90-110%)
            "test_name": "coremark"
        },
        {
            "peer_os": "Ubuntu",
            "benchmark_category": "Memory",
            "relative_performance": 85.0,  # Moderate (80-120%)
            "test_name": "streams"
        },
        {
            "peer_os": "Ubuntu",
            "benchmark_category": "Network",
            "relative_performance": 75.0,  # Significant (<80% or >120%)
            "test_name": "iperf"
        },
    ])


def test_peer_os_comparison_uses_colorblind_palette(peer_os_comparison_data):
    """Peer OS comparison chart uses colorblind-safe colors when colorblind_mode=True."""
    from src.components.visualizations import create_peer_os_comparison_chart

    fig = create_peer_os_comparison_chart(
        peer_os_comparison_data,
        baseline_os="RHEL",
        colorblind_mode=True
    )

    # Verify chart was created
    assert len(fig.data) > 0

    # Extract bar colors
    bar_trace = fig.data[0]
    bar_colors = bar_trace.marker.color

    # Should NOT use hardcoded red (#d73027) or green (#1a9850)
    assert "#d73027" not in bar_colors, "Should not use standard red in colorblind mode"
    assert "#1a9850" not in bar_colors, "Should not use standard green in colorblind mode"

    # Verify fillcolor in shapes (competitive zone)
    # Should not use literal "green"
    shapes = fig.layout.shapes
    if shapes:
        for shape in shapes:
            if hasattr(shape, 'fillcolor'):
                fillcolor = shape.fillcolor.lower()
                assert fillcolor != "green", "Should not use literal 'green' fillcolor in colorblind mode"
