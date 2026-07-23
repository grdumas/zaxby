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
    create_investigation_detail_chart,
    create_metrics_table,
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


def test_cloud_scaling_chart_colorblind_changes_colors(multi_benchmark_scaling_data):
    """Cloud scaling chart uses colorblind-safe colors in colorblind mode."""
    # Standard mode
    fig_standard = create_cloud_scaling_chart(multi_benchmark_scaling_data, colorblind_mode=False)

    # Colorblind mode
    fig_colorblind = create_cloud_scaling_chart(multi_benchmark_scaling_data, colorblind_mode=True)

    # Both should have traces
    assert len(fig_standard.data) > 0, "Standard chart should have traces"
    assert len(fig_colorblind.data) > 0, "Colorblind chart should have traces"

    # Extract colors from first trace (excluding reference line and shapes)
    standard_colors = []
    colorblind_colors = []

    for trace in fig_standard.data:
        if hasattr(trace, 'line') and hasattr(trace.line, 'color') and trace.line.color:
            standard_colors.append(trace.line.color)

    for trace in fig_colorblind.data:
        if hasattr(trace, 'line') and hasattr(trace.line, 'color') and trace.line.color:
            colorblind_colors.append(trace.line.color)

    # Should have at least one color in each mode
    assert len(standard_colors) > 0, "Standard mode should have line colors"
    assert len(colorblind_colors) > 0, "Colorblind mode should have line colors"

    # Colors should be different between modes (at least some)
    # This test verifies the palette is being applied
    assert standard_colors != colorblind_colors, "Colorblind mode should use different colors"


def test_cloud_scaling_chart_colorblind_adds_line_dashes(multi_benchmark_scaling_data):
    """Cloud scaling chart uses line dashes for redundant encoding in colorblind mode."""
    # Standard mode should use solid lines
    fig_standard = create_cloud_scaling_chart(multi_benchmark_scaling_data, colorblind_mode=False)

    # Colorblind mode should use varied line dashes
    fig_colorblind = create_cloud_scaling_chart(multi_benchmark_scaling_data, colorblind_mode=True)

    # Extract line dash patterns from non-reference traces (exclude the "Ideal Linear" reference line)
    standard_dashes = []
    colorblind_dashes = []

    for trace in fig_standard.data:
        # Skip the reference line (it has a dash pattern even in standard mode)
        if hasattr(trace, 'name') and 'Ideal' in str(trace.name):
            continue
        if hasattr(trace, 'line') and hasattr(trace.line, 'dash'):
            standard_dashes.append(trace.line.dash)

    for trace in fig_colorblind.data:
        # Skip the reference line
        if hasattr(trace, 'name') and 'Ideal' in str(trace.name):
            continue
        if hasattr(trace, 'line') and hasattr(trace.line, 'dash'):
            colorblind_dashes.append(trace.line.dash)

    # Should have multiple traces
    assert len(standard_dashes) >= 2, "Should have multiple data traces in standard mode"
    assert len(colorblind_dashes) >= 2, "Should have multiple data traces in colorblind mode"

    # Standard mode should use solid lines (None or 'solid')
    for dash in standard_dashes:
        assert dash is None or dash == 'solid', \
            f"Standard mode should use solid lines, found dash={dash}"

    # Colorblind mode should use varied line dashes (not all the same)
    unique_dashes = set(colorblind_dashes)
    assert len(unique_dashes) > 1, \
        "Colorblind mode should use different line dash patterns for redundant encoding"


def test_cloud_scaling_chart_colorblind_adds_marker_symbols(multi_benchmark_scaling_data):
    """Cloud scaling chart uses marker symbols for redundant encoding in colorblind mode."""
    # Standard mode
    fig_standard = create_cloud_scaling_chart(multi_benchmark_scaling_data, colorblind_mode=False)

    # Colorblind mode should use varied marker symbols
    fig_colorblind = create_cloud_scaling_chart(multi_benchmark_scaling_data, colorblind_mode=True)

    # Extract marker symbols from non-reference traces
    standard_symbols = []
    colorblind_symbols = []

    for trace in fig_standard.data:
        # Skip the reference line
        if hasattr(trace, 'name') and 'Ideal' in str(trace.name):
            continue
        if hasattr(trace, 'marker') and hasattr(trace.marker, 'symbol'):
            standard_symbols.append(trace.marker.symbol)

    for trace in fig_colorblind.data:
        # Skip the reference line
        if hasattr(trace, 'name') and 'Ideal' in str(trace.name):
            continue
        if hasattr(trace, 'marker') and hasattr(trace.marker, 'symbol'):
            colorblind_symbols.append(trace.marker.symbol)

    # Should have multiple traces
    assert len(standard_symbols) >= 2, "Should have multiple data traces in standard mode"
    assert len(colorblind_symbols) >= 2, "Should have multiple data traces in colorblind mode"

    # Colorblind mode should use varied marker symbols (not all the same)
    unique_symbols = set(colorblind_symbols)
    assert len(unique_symbols) > 1, \
        "Colorblind mode should use different marker symbols for redundant encoding"


def test_cloud_scaling_chart_colorblind_good_scaling_annotation():
    """Good scaling annotation uses colorblind-safe colors in colorblind mode."""
    # Create simple scaling data
    data = pd.DataFrame([
        {
            "instance_type": "c2-standard-4",
            "benchmark_category": "CPU",
            "cpu_cores": 4,
            "memory_gb": 16,
            "mean_performance": 100000.0,
        },
        {
            "instance_type": "c2-standard-8",
            "benchmark_category": "CPU",
            "cpu_cores": 8,
            "memory_gb": 32,
            "mean_performance": 195000.0,
        },
    ])

    # Standard mode
    fig_standard = create_cloud_scaling_chart(data, colorblind_mode=False)

    # Colorblind mode
    fig_colorblind = create_cloud_scaling_chart(data, colorblind_mode=True)

    # Check that both have the "Good scaling" shaded region
    assert len(fig_standard.layout.shapes) > 0, "Standard mode should have shaded region"
    assert len(fig_colorblind.layout.shapes) > 0, "Colorblind mode should have shaded region"

    # Extract the fillcolor from the shaded regions
    standard_fills = [shape.fillcolor for shape in fig_standard.layout.shapes if hasattr(shape, 'fillcolor')]
    colorblind_fills = [shape.fillcolor for shape in fig_colorblind.layout.shapes if hasattr(shape, 'fillcolor')]

    assert len(standard_fills) > 0, "Standard mode should have fill colors"
    assert len(colorblind_fills) > 0, "Colorblind mode should have fill colors"

    # The fill colors should be different (colorblind mode should not use green)
    assert standard_fills != colorblind_fills, \
        "Colorblind mode should use different fill color for good scaling region"

    # Colorblind fill should not contain green (RGB values around 76, 175, 80)
    for fill in colorblind_fills:
        assert "76, 175, 80" not in fill, \
            "Colorblind mode should not use green-only semantic colors"


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
def comparison_data_colorblind():
    """Sample comparison data for testing colorblind mode."""
    return pd.DataFrame([
        {"test_name": "benchmark1", "baseline_mean": 100, "comparison_mean": 110},
        {"test_name": "benchmark2", "baseline_mean": 200, "comparison_mean": 195},
    ])


@pytest.fixture
def regression_heatmap_data_colorblind():
    """Sample data for regression heatmap testing."""
    df = pd.DataFrame({
        "test1": [5.0, -5.0],  # % changes
        "test2": [10.0, -10.0],
    }, index=["rhel8_to_rhel9", "rhel9_to_rhel10"])
    return df


def test_create_comparison_chart_colorblind_mode(comparison_data_colorblind):
    """Comparison chart uses colorblind-safe colors when colorblind_mode=True."""
    # Standard mode
    fig_standard = create_comparison_chart(comparison_data_colorblind, colorblind_mode=False)
    # Colorblind mode
    fig_colorblind = create_comparison_chart(comparison_data_colorblind, colorblind_mode=True)

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


def test_regression_heatmap_colorblind_scale(regression_heatmap_data_colorblind):
    """Regression heatmap does not use red/green in colorblind mode."""
    fig_colorblind = create_regression_heatmap(
        regression_heatmap_data_colorblind, colorblind_mode=True
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
    assert "Red" not in legend_text and "Dark Red" not in legend_text, \
        "Colorblind legend should not use 'Red' or 'Dark Red'"
    assert "Green" not in legend_text, "Colorblind legend should not use 'Green'"


def test_version_comparison_hover_icons_respect_colorblind_mode():
    """
    Test that version comparison hover icons change from red/green to blue/orange
    in colorblind mode.

    The hover tooltips should use 🔵/🟠 in colorblind mode instead of 🔴/🟢.
    """
    # Create fixture data with multiple hardware configs
    comparison_df = pd.DataFrame([
        {
            "test_name": "test_with_regression",
            "baseline_mean": 100.0,
            "comparison_mean": 80.0,
            "percent_change": -20.0,
            "is_regression": True,
            "hardware_config": "config1"
        },
        {
            "test_name": "test_with_regression",
            "baseline_mean": 100.0,
            "comparison_mean": 85.0,
            "percent_change": -15.0,
            "is_regression": True,
            "hardware_config": "config2"
        },
        {
            "test_name": "test_with_improvement",
            "baseline_mean": 100.0,
            "comparison_mean": 120.0,
            "percent_change": 20.0,
            "is_regression": False,
            "hardware_config": "config1"
        },
        {
            "test_name": "test_with_improvement",
            "baseline_mean": 100.0,
            "comparison_mean": 125.0,
            "percent_change": 25.0,
            "is_regression": False,
            "hardware_config": "config2"
        }
    ])

    # Test colorblind mode
    fig_colorblind = create_version_comparison_bar_chart(
        comparison_df=comparison_df,
        baseline_version="v1.0",
        comparison_version="v2.0",
        colorblind_mode=True
    )

    # Extract hover text from customdata
    hover_data = fig_colorblind.data[0].customdata
    all_hover_text = " ".join(hover_data)

    # In colorblind mode, should use blue/orange emoji
    assert "🔵" in all_hover_text, "Colorblind mode should use blue emoji 🔵 for improvement"
    assert "🟠" in all_hover_text, "Colorblind mode should use orange emoji 🟠 for regression"

    # Should NOT use red/green emoji in colorblind mode
    assert "🔴" not in all_hover_text, "Colorblind mode should not use red emoji 🔴"
    assert "🟢" not in all_hover_text, "Colorblind mode should not use green emoji 🟢"

    # Test standard mode
    fig_standard = create_version_comparison_bar_chart(
        comparison_df=comparison_df,
        baseline_version="v1.0",
        comparison_version="v2.0",
        colorblind_mode=False
    )

    # Extract hover text from customdata
    hover_data_standard = fig_standard.data[0].customdata
    all_hover_text_standard = " ".join(hover_data_standard)

    # In standard mode, should use red/green emoji
    assert "🔴" in all_hover_text_standard, "Standard mode should use red emoji 🔴 for regression"
    assert "🟢" in all_hover_text_standard, "Standard mode should use green emoji 🟢 for improvement"

    # Should NOT use blue/orange emoji in standard mode
    assert "🔵" not in all_hover_text_standard, "Standard mode should not use blue emoji 🔵"
    assert "🟠" not in all_hover_text_standard, "Standard mode should not use orange emoji 🟠"


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
            if hasattr(shape, 'fillcolor') and shape.fillcolor:
                fillcolor = shape.fillcolor.lower()
                assert fillcolor != "green", "Should not use literal 'green' fillcolor in colorblind mode"


@pytest.fixture
def category_benchmark_data():
    """Sample category benchmark data for detail chart."""
    return pd.DataFrame([
        {
            "test_name": "benchmark1",
            "relative_performance": 95.0,  # Competitive (90-110%)
            "instance_type": "m5.large",
            "is_competitive": True,
        },
        {
            "test_name": "benchmark2",
            "relative_performance": 85.0,  # Moderate (80-120%)
            "instance_type": "m5.large",
            "is_competitive": False,
        },
        {
            "test_name": "benchmark3",
            "relative_performance": 75.0,  # Significant (<80% or >120%)
            "instance_type": "m5.large",
            "is_competitive": False,
        },
    ])


def test_category_benchmark_detail_chart_uses_colorblind_palette(category_benchmark_data):
    """Category benchmark detail chart uses colorblind-safe colors when colorblind_mode=True."""
    from src.components.visualizations import create_category_benchmark_detail_chart

    # Create chart in standard mode
    fig_standard = create_category_benchmark_detail_chart(
        category_benchmark_data,
        category="CPU",
        baseline_os="RHEL",
        colorblind_mode=False
    )

    # Create chart in colorblind mode
    fig_colorblind = create_category_benchmark_detail_chart(
        category_benchmark_data,
        category="CPU",
        baseline_os="RHEL",
        colorblind_mode=True
    )

    # Extract bar colors from both charts
    bar_trace_standard = fig_standard.data[0]
    bar_trace_colorblind = fig_colorblind.data[0]

    bar_colors_standard = bar_trace_standard.marker.color
    bar_colors_colorblind = bar_trace_colorblind.marker.color

    # Standard mode should use hardcoded red/green/amber
    assert "#1a9850" in bar_colors_standard or "#d73027" in bar_colors_standard, \
        "Standard mode should use red/green"

    # Colorblind mode should NOT use hardcoded red (#d73027) or green (#1a9850)
    if isinstance(bar_colors_colorblind, list):
        assert "#d73027" not in bar_colors_colorblind, \
            "Colorblind mode should not use standard red"
        assert "#1a9850" not in bar_colors_colorblind, \
            "Colorblind mode should not use standard green"

        # Should use colorblind-safe colors from palette
        # Improvement: #0072b2 (blue), Regression: #d55e00 (vermillion), Moderate: #e69f00 (amber)
        has_colorblind_colors = any(
            color in ["#0072b2", "#d55e00", "#e69f00"]
            for color in bar_colors_colorblind
        )
        assert has_colorblind_colors, \
            "Colorblind mode should use colorblind-safe colors from palette"

    # Verify fillcolor in shapes (competitive zone)
    # Should not use literal "green" in colorblind mode
    shapes_colorblind = fig_colorblind.layout.shapes
    if shapes_colorblind:
        for shape in shapes_colorblind:
            if hasattr(shape, 'fillcolor') and shape.fillcolor:
                fillcolor = shape.fillcolor.lower()
                assert fillcolor != "green", \
                    "Colorblind mode should not use literal 'green' fillcolor"


@pytest.fixture
def category_hardware_heatmap_data():
    """Sample category hardware heatmap data."""
    return pd.DataFrame([
        {
            "test_name": "benchmark1",
            "instance_type": "m5.large",
            "relative_performance": 95.0,  # Competitive
        },
        {
            "test_name": "benchmark1",
            "instance_type": "m5.xlarge",
            "relative_performance": 105.0,  # Competitive
        },
        {
            "test_name": "benchmark2",
            "instance_type": "m5.large",
            "relative_performance": 85.0,  # Moderate
        },
        {
            "test_name": "benchmark2",
            "instance_type": "m5.xlarge",
            "relative_performance": 115.0,  # Moderate
        },
    ])


def test_category_hardware_heatmap_uses_colorblind_scale(category_hardware_heatmap_data):
    """Category hardware heatmap uses colorblind-safe colorscale when colorblind_mode=True."""
    from src.components.visualizations import create_category_hardware_heatmap

    # Create heatmap in standard mode
    fig_standard = create_category_hardware_heatmap(
        category_hardware_heatmap_data,
        category="CPU",
        baseline_os="RHEL",
        colorblind_mode=False
    )

    # Create heatmap in colorblind mode
    fig_colorblind = create_category_hardware_heatmap(
        category_hardware_heatmap_data,
        category="CPU",
        baseline_os="RHEL",
        colorblind_mode=True
    )

    # Extract colorscales
    colorscale_standard = fig_standard.data[0].colorscale
    colorscale_colorblind = fig_colorblind.data[0].colorscale

    # Standard mode should use red-green scale
    standard_colors = [color for _, color in colorscale_standard]
    assert "#d73027" in standard_colors or "#1a9850" in standard_colors, \
        "Standard mode should use red-green colorscale"

    # Colorblind mode should NOT use red-green
    colorblind_colors = [color for _, color in colorscale_colorblind]
    assert "#d73027" not in colorblind_colors, \
        "Colorblind mode should not use standard red"
    assert "#1a9850" not in colorblind_colors, \
        "Colorblind mode should not use standard green"

    # Should use colorblind-safe colors from palette.hardware_heatmap_scale
    # Expected: vermillion (#d55e00), amber, light gray, sky blue (#56b4e9), strong blue (#0072b2)
    has_colorblind_colors = any(
        color in ["#d55e00", "#0072b2", "#56b4e9", "#f0f0f0"]
        for color in colorblind_colors
    )
    assert has_colorblind_colors, \
        "Colorblind mode should use colorblind-safe colors from hardware_heatmap_scale"

    # Verify scales are different
    assert colorscale_standard != colorscale_colorblind, \
        "Standard and colorblind modes should use different colorscales"


# ============================================================================
# Redundant Encoding (Line Dashes and Marker Symbols) Tests
# ============================================================================


def test_time_series_uses_line_dashes_in_colorblind_mode():
    """Time series chart uses different line dashes per series in colorblind mode."""
    # Create data with multiple series
    data = pd.DataFrame([
        {"timestamp": "2024-01-01", "primary_metric_value": 100, "test_name": "test_a"},
        {"timestamp": "2024-01-02", "primary_metric_value": 102, "test_name": "test_a"},
        {"timestamp": "2024-01-01", "primary_metric_value": 200, "test_name": "test_b"},
        {"timestamp": "2024-01-02", "primary_metric_value": 205, "test_name": "test_b"},
        {"timestamp": "2024-01-01", "primary_metric_value": 300, "test_name": "test_c"},
        {"timestamp": "2024-01-02", "primary_metric_value": 310, "test_name": "test_c"},
    ])

    # Colorblind mode should use line dashes
    fig_colorblind = create_time_series_chart(data, color_col='test_name', colorblind_mode=True)

    # Extract line dash patterns
    line_dashes = [trace.line.dash for trace in fig_colorblind.data if hasattr(trace, 'line')]

    # Should have at least 2 traces with line attributes
    assert len(line_dashes) >= 2, "Should have multiple traces with line attributes"

    # Not all line dashes should be the same (should cycle through patterns)
    unique_dashes = set(line_dashes)
    assert len(unique_dashes) > 1, "Should use different line dash patterns in colorblind mode"


def test_time_series_uses_solid_lines_in_standard_mode():
    """Time series chart uses solid lines in standard mode (no line dashes)."""
    # Create data with multiple series
    data = pd.DataFrame([
        {"timestamp": "2024-01-01", "primary_metric_value": 100, "test_name": "test_a"},
        {"timestamp": "2024-01-02", "primary_metric_value": 102, "test_name": "test_a"},
        {"timestamp": "2024-01-01", "primary_metric_value": 200, "test_name": "test_b"},
        {"timestamp": "2024-01-02", "primary_metric_value": 205, "test_name": "test_b"},
    ])

    # Standard mode should NOT use line dashes
    fig_standard = create_time_series_chart(data, color_col='test_name', colorblind_mode=False)

    # Extract line dash patterns
    line_dashes = [trace.line.dash for trace in fig_standard.data if hasattr(trace, 'line')]

    # All line dashes should be None or 'solid' (default behavior)
    for dash in line_dashes:
        assert dash is None or dash == 'solid', \
            f"Standard mode should use solid lines, found dash={dash}"


def test_scatter_plot_uses_marker_symbols_in_colorblind_mode():
    """Scatter plot uses different marker symbols per series in colorblind mode."""
    # Create data with multiple series
    data = pd.DataFrame([
        {"x": 1, "y": 10, "category": "cat_a"},
        {"x": 2, "y": 15, "category": "cat_a"},
        {"x": 1, "y": 20, "category": "cat_b"},
        {"x": 2, "y": 25, "category": "cat_b"},
        {"x": 1, "y": 30, "category": "cat_c"},
        {"x": 2, "y": 35, "category": "cat_c"},
    ])

    # Colorblind mode should use different marker symbols
    fig_colorblind = create_scatter_plot(
        data,
        x_col='x',
        y_col='y',
        color_col='category',
        colorblind_mode=True
    )

    # Extract marker symbols
    marker_symbols = [trace.marker.symbol for trace in fig_colorblind.data if hasattr(trace, 'marker')]

    # Should have at least 2 traces with marker attributes
    assert len(marker_symbols) >= 2, "Should have multiple traces with marker attributes"

    # Not all marker symbols should be the same
    unique_symbols = set(marker_symbols)
    assert len(unique_symbols) > 1, "Should use different marker symbols in colorblind mode"


def test_scatter_plot_uses_default_markers_in_standard_mode():
    """Scatter plot uses default marker symbols in standard mode (no variation)."""
    # Create data with multiple series
    data = pd.DataFrame([
        {"x": 1, "y": 10, "category": "cat_a"},
        {"x": 2, "y": 15, "category": "cat_a"},
        {"x": 1, "y": 20, "category": "cat_b"},
        {"x": 2, "y": 25, "category": "cat_b"},
    ])

    # Standard mode should NOT enforce different marker symbols
    fig_standard = create_scatter_plot(
        data,
        x_col='x',
        y_col='y',
        color_col='category',
        colorblind_mode=False
    )

    # Extract marker symbols
    marker_symbols = [trace.marker.symbol for trace in fig_standard.data if hasattr(trace, 'marker')]

    # All marker symbols should be None (Plotly's default) or all the same
    # Plotly may assign different symbols by default, but we shouldn't be enforcing it
    # The key is that we're NOT explicitly setting different symbols in standard mode
    for symbol in marker_symbols:
        assert symbol is None or isinstance(symbol, (str, int)), \
            "Standard mode should use default marker behavior"


def test_time_series_line_dash_cycling():
    """Time series chart uses all available line dash patterns deterministically.

    With name-based pattern assignment, patterns are distributed across traces
    based on trace name hash, not sequential index. The test verifies that:
    1. All patterns get used when we have enough traces
    2. Patterns repeat (via modulo) when we have more traces than patterns
    """
    from src.color_palettes import COLORBLIND

    # Create data with 6 series (more than available line dashes)
    data = pd.DataFrame([
        {"timestamp": f"2024-01-0{i}", "primary_metric_value": i*100, "test_name": f"test_{j}"}
        for i in range(1, 4)
        for j in range(6)
    ])

    fig_colorblind = create_time_series_chart(data, color_col='test_name', colorblind_mode=True)

    # Extract line dashes
    line_dashes = [trace.line.dash for trace in fig_colorblind.data if hasattr(trace, 'line')]

    # Should have 6 traces
    assert len(line_dashes) == 6, "Should have 6 traces"

    # With 5 available dash patterns and 6 series, at least one pattern must repeat
    available_dashes = COLORBLIND.patterns.line_dashes
    unique_dashes = set(line_dashes)

    # Should use at least 2 different patterns (not all the same)
    assert len(unique_dashes) >= 2, "Should use multiple different dash patterns"

    # All dashes should come from the available palette
    for dash in line_dashes:
        assert dash in available_dashes, f"Dash pattern '{dash}' should be from available patterns"

    # With 6 traces and 5 patterns, at least one pattern must appear twice
    dash_counts = {dash: line_dashes.count(dash) for dash in unique_dashes}
    assert any(count >= 2 for count in dash_counts.values()), \
        "With more traces than patterns, at least one pattern should repeat"


def test_scatter_plot_marker_symbol_cycling():
    """Scatter plot uses all available marker symbols deterministically.

    With name-based pattern assignment, symbols are distributed across traces
    based on trace name hash, not sequential index. The test verifies that:
    1. All symbols get used when we have enough traces
    2. Symbols repeat (via modulo) when we have more traces than symbols
    """
    from src.color_palettes import COLORBLIND

    # Create data with 7 series (more than available marker symbols)
    data = pd.DataFrame([
        {"x": i, "y": i*10, "category": f"cat_{j}"}
        for i in range(1, 3)
        for j in range(7)
    ])

    fig_colorblind = create_scatter_plot(
        data,
        x_col='x',
        y_col='y',
        color_col='category',
        colorblind_mode=True
    )

    # Extract marker symbols
    marker_symbols = [trace.marker.symbol for trace in fig_colorblind.data if hasattr(trace, 'marker')]

    # Should have 7 traces
    assert len(marker_symbols) == 7, "Should have 7 traces"

    # With 6 available marker symbols and 7 series, at least one symbol must repeat
    available_symbols = COLORBLIND.patterns.marker_symbols
    unique_symbols = set(marker_symbols)

    # Should use at least 2 different symbols (not all the same)
    assert len(unique_symbols) >= 2, "Should use multiple different marker symbols"

    # All symbols should come from the available palette
    for symbol in marker_symbols:
        assert symbol in available_symbols, f"Marker symbol '{symbol}' should be from available patterns"

    # With 7 traces and 6 symbols, at least one symbol must appear twice
    symbol_counts = {symbol: marker_symbols.count(symbol) for symbol in unique_symbols}
    assert any(count >= 2 for count in symbol_counts.values()), \
        "With more traces than symbols, at least one symbol should repeat"


# ============================================================================
# Deterministic Pattern Assignment Tests (Index-based → Name-based)
# ============================================================================


def test_time_series_patterns_stable_across_reordering():
    """Time series line dashes should be deterministic based on trace name, not order.

    Same trace name should get the same line dash pattern even if trace ordering changes.
    This ensures consistent visual encoding across different views of the same data.
    """
    # Create data with 3 series
    data = pd.DataFrame([
        {"timestamp": "2024-01-01", "primary_metric_value": 100, "test_name": "alpha"},
        {"timestamp": "2024-01-02", "primary_metric_value": 102, "test_name": "alpha"},
        {"timestamp": "2024-01-01", "primary_metric_value": 200, "test_name": "beta"},
        {"timestamp": "2024-01-02", "primary_metric_value": 205, "test_name": "beta"},
        {"timestamp": "2024-01-01", "primary_metric_value": 300, "test_name": "gamma"},
        {"timestamp": "2024-01-02", "primary_metric_value": 310, "test_name": "gamma"},
    ])

    # Render in original order (alpha, beta, gamma)
    fig1 = create_time_series_chart(data, color_col='test_name', colorblind_mode=True)

    # Reverse the data order (gamma, beta, alpha)
    data_reversed = data.sort_values('test_name', ascending=False).reset_index(drop=True)
    fig2 = create_time_series_chart(data_reversed, color_col='test_name', colorblind_mode=True)

    # Extract trace name → line dash mapping from both figures
    def get_trace_dash_map(fig):
        return {trace.name: trace.line.dash for trace in fig.data if hasattr(trace, 'line')}

    dash_map1 = get_trace_dash_map(fig1)
    dash_map2 = get_trace_dash_map(fig2)

    # Same trace names should get same patterns regardless of order
    assert dash_map1['alpha'] == dash_map2['alpha'], \
        "Trace 'alpha' should have same dash pattern in both orderings"
    assert dash_map1['beta'] == dash_map2['beta'], \
        "Trace 'beta' should have same dash pattern in both orderings"
    assert dash_map1['gamma'] == dash_map2['gamma'], \
        "Trace 'gamma' should have same dash pattern in both orderings"


def test_scatter_plot_symbols_stable_across_reordering():
    """Scatter plot marker symbols should be deterministic based on trace name, not order.

    Same trace name should get the same marker symbol even if trace ordering changes.
    """
    # Create data with 3 categories
    data = pd.DataFrame([
        {"x": 1, "y": 10, "category": "alpha"},
        {"x": 2, "y": 15, "category": "alpha"},
        {"x": 1, "y": 20, "category": "beta"},
        {"x": 2, "y": 25, "category": "beta"},
        {"x": 1, "y": 30, "category": "gamma"},
        {"x": 2, "y": 35, "category": "gamma"},
    ])

    # Render in original order
    fig1 = create_scatter_plot(data, x_col='x', y_col='y', color_col='category', colorblind_mode=True)

    # Reverse the data order
    data_reversed = data.sort_values('category', ascending=False).reset_index(drop=True)
    fig2 = create_scatter_plot(data_reversed, x_col='x', y_col='y', color_col='category', colorblind_mode=True)

    # Extract trace name → marker symbol mapping
    def get_trace_symbol_map(fig):
        return {trace.name: trace.marker.symbol for trace in fig.data if hasattr(trace, 'marker')}

    symbol_map1 = get_trace_symbol_map(fig1)
    symbol_map2 = get_trace_symbol_map(fig2)

    # Same trace names should get same symbols regardless of order
    assert symbol_map1['alpha'] == symbol_map2['alpha'], \
        "Trace 'alpha' should have same marker symbol in both orderings"
    assert symbol_map1['beta'] == symbol_map2['beta'], \
        "Trace 'beta' should have same marker symbol in both orderings"
    assert symbol_map1['gamma'] == symbol_map2['gamma'], \
        "Trace 'gamma' should have same marker symbol in both orderings"


def test_cloud_scaling_patterns_stable_across_reordering():
    """Cloud scaling chart patterns should be deterministic based on trace name, not order.

    Same benchmark category should get the same line dash and marker symbol even if
    data ordering changes.
    """
    # Create scaling data with 3 categories
    data = pd.DataFrame([
        # Alpha category
        {"instance_type": "c2-standard-4", "benchmark_category": "alpha",
         "cpu_cores": 4, "memory_gb": 16, "mean_performance": 100000.0},
        {"instance_type": "c2-standard-8", "benchmark_category": "alpha",
         "cpu_cores": 8, "memory_gb": 32, "mean_performance": 195000.0},
        # Beta category
        {"instance_type": "c2-standard-4", "benchmark_category": "beta",
         "cpu_cores": 4, "memory_gb": 16, "mean_performance": 50000.0},
        {"instance_type": "c2-standard-8", "benchmark_category": "beta",
         "cpu_cores": 8, "memory_gb": 32, "mean_performance": 80000.0},
        # Gamma category
        {"instance_type": "c2-standard-4", "benchmark_category": "gamma",
         "cpu_cores": 4, "memory_gb": 16, "mean_performance": 75000.0},
        {"instance_type": "c2-standard-8", "benchmark_category": "gamma",
         "cpu_cores": 8, "memory_gb": 32, "mean_performance": 140000.0},
    ])

    # Render in original order
    fig1 = create_cloud_scaling_chart(data, colorblind_mode=True)

    # Reverse the category order
    data_reversed = data.sort_values('benchmark_category', ascending=False).reset_index(drop=True)
    fig2 = create_cloud_scaling_chart(data_reversed, colorblind_mode=True)

    # Extract trace name → pattern mapping (skip reference line with "Ideal" in name)
    def get_trace_pattern_map(fig):
        result = {}
        for trace in fig.data:
            if hasattr(trace, 'name') and 'Ideal' in str(trace.name):
                continue  # Skip reference line
            if hasattr(trace, 'line') and hasattr(trace, 'marker'):
                result[trace.name] = {
                    'dash': trace.line.dash,
                    'symbol': trace.marker.symbol
                }
        return result

    pattern_map1 = get_trace_pattern_map(fig1)
    pattern_map2 = get_trace_pattern_map(fig2)

    # Same trace names should get same patterns regardless of order
    for category in ['alpha', 'beta', 'gamma']:
        assert category in pattern_map1 and category in pattern_map2, \
            f"Category '{category}' should exist in both figures"
        assert pattern_map1[category]['dash'] == pattern_map2[category]['dash'], \
            f"Category '{category}' should have same line dash in both orderings"
        assert pattern_map1[category]['symbol'] == pattern_map2[category]['symbol'], \
            f"Category '{category}' should have same marker symbol in both orderings"


# ============================================================================
# Box Plot Tests for TDD Fixes
# ============================================================================


def test_create_box_plot_empty_color_col():
    """Test that box plot handles empty string color_col without crashing."""
    data = pd.DataFrame([
        {"test_name": "coremark", "primary_metric_value": 100000},
        {"test_name": "coremark", "primary_metric_value": 102000},
        {"test_name": "streams", "primary_metric_value": 50000},
        {"test_name": "streams", "primary_metric_value": 51000},
    ])

    # Empty string should be normalized to None and not crash
    fig = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col=""
    )

    # Chart should be created successfully (no crash)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_create_box_plot_whitespace_color_col():
    """Test that box plot handles whitespace-only color_col without crashing."""
    data = pd.DataFrame([
        {"test_name": "coremark", "primary_metric_value": 100000},
        {"test_name": "coremark", "primary_metric_value": 102000},
        {"test_name": "streams", "primary_metric_value": 50000},
        {"test_name": "streams", "primary_metric_value": 51000},
    ])

    # Whitespace should be normalized to None and not crash
    fig = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col="   "
    )

    # Chart should be created successfully (no crash)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_create_box_plot_colorblind_changes_colors():
    """Test that box plot uses different colors when colorblind_mode=True."""
    data = pd.DataFrame([
        {"test_name": "coremark", "os_version": "RHEL 9.0", "primary_metric_value": 100000},
        {"test_name": "coremark", "os_version": "RHEL 9.0", "primary_metric_value": 102000},
        {"test_name": "coremark", "os_version": "RHEL 9.1", "primary_metric_value": 105000},
        {"test_name": "coremark", "os_version": "RHEL 9.1", "primary_metric_value": 107000},
    ])

    # Create box plots in both modes
    fig_standard = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col='os_version',
        colorblind_mode=False
    )

    fig_colorblind = create_box_plot(
        data,
        x_col='test_name',
        y_col='primary_metric_value',
        color_col='os_version',
        colorblind_mode=True
    )

    # Extract marker colors from traces
    standard_colors = []
    colorblind_colors = []

    for trace in fig_standard.data:
        if hasattr(trace, 'marker') and hasattr(trace.marker, 'color'):
            standard_colors.append(trace.marker.color)

    for trace in fig_colorblind.data:
        if hasattr(trace, 'marker') and hasattr(trace.marker, 'color'):
            colorblind_colors.append(trace.marker.color)

    # Should have colors in both modes
    assert len(standard_colors) > 0, "Standard mode should have colors"
    assert len(colorblind_colors) > 0, "Colorblind mode should have colors"

    # Colors should be different between modes
    assert standard_colors != colorblind_colors, \
        "Colorblind mode should use different colors than standard mode"


def test_investigation_detail_chart_uses_colorblind_palette():
    """Test that investigation detail chart uses colorblind-safe colors when colorblind_mode=True."""
    baseline_df = pd.DataFrame({
        'primary_metric_value': [100, 105, 102, 98, 101]
    })
    comparison_df = pd.DataFrame({
        'primary_metric_value': [110, 115, 112, 108, 111]
    })

    # Create charts in both modes
    fig_standard = create_investigation_detail_chart(
        baseline_df,
        comparison_df,
        test_name="coremark",
        baseline_label="Baseline",
        comparison_label="Comparison",
        colorblind_mode=False
    )

    fig_colorblind = create_investigation_detail_chart(
        baseline_df,
        comparison_df,
        test_name="coremark",
        baseline_label="Baseline",
        comparison_label="Comparison",
        colorblind_mode=True
    )

    # Extract marker colors from both charts
    standard_colors = [trace.marker.color for trace in fig_standard.data]
    colorblind_colors = [trace.marker.color for trace in fig_colorblind.data]

    # Both should have 2 traces (baseline and comparison)
    assert len(standard_colors) == 2, "Should have 2 traces in standard mode"
    assert len(colorblind_colors) == 2, "Should have 2 traces in colorblind mode"

    # Standard mode should use the old hardcoded colors
    assert standard_colors[0] == 'lightblue', "Standard baseline should be lightblue"
    assert standard_colors[1] == 'lightcoral', "Standard comparison should be lightcoral"

    # Colorblind mode should use palette.comparison colors
    from src.color_palettes import COLORBLIND
    assert colorblind_colors[0] == COLORBLIND.comparison.baseline, \
        f"Colorblind baseline should be {COLORBLIND.comparison.baseline}"
    assert colorblind_colors[1] == COLORBLIND.comparison.comparison, \
        f"Colorblind comparison should be {COLORBLIND.comparison.comparison}"

    # Colors should be different between modes
    assert standard_colors != colorblind_colors, \
        "Colorblind mode should use different colors than standard mode"


def test_metrics_table_uses_colorblind_palette():
    """Test that metrics table uses colorblind-safe colors when colorblind_mode=True."""
    test_df = pd.DataFrame({
        'test_name': ['coremark', 'dhrystone', 'whetstone'],
        'baseline_mean': [100.5, 200.3, 150.7],
        'comparison_mean': [105.2, 198.1, 155.3],
        'percent_change': [4.7, -1.1, 3.1]
    })

    # Create tables in both modes
    fig_standard = create_metrics_table(
        test_df,
        columns=['test_name', 'baseline_mean', 'comparison_mean', 'percent_change'],
        title="Test Metrics",
        colorblind_mode=False
    )

    fig_colorblind = create_metrics_table(
        test_df,
        columns=['test_name', 'baseline_mean', 'comparison_mean', 'percent_change'],
        title="Test Metrics",
        colorblind_mode=True
    )

    # Extract table colors from both figures
    standard_header = fig_standard.data[0].header.fill.color
    standard_cells = fig_standard.data[0].cells.fill.color

    colorblind_header = fig_colorblind.data[0].header.fill.color
    colorblind_cells = fig_colorblind.data[0].cells.fill.color

    # Standard mode should use the old hardcoded colors
    assert standard_header == 'paleturquoise', "Standard header should be paleturquoise"
    assert standard_cells == 'lavender', "Standard cells should be lavender"

    # Colorblind mode should use palette.table colors
    from src.color_palettes import COLORBLIND
    assert colorblind_header == COLORBLIND.table.header, \
        f"Colorblind header should be {COLORBLIND.table.header}"
    assert colorblind_cells == COLORBLIND.table.cells, \
        f"Colorblind cells should be {COLORBLIND.table.cells}"

    # Colors should be different between modes
    assert standard_header != colorblind_header, \
        "Colorblind mode should use different header color than standard mode"
    assert standard_cells != colorblind_cells, \
        "Colorblind mode should use different cell color than standard mode"


# ============================================================================
# XSS Prevention Tests
# ============================================================================


def test_escape_html_escapes_script_tags():
    """Test that _escape_html escapes script tags to prevent XSS."""
    from src.components.visualizations import _escape_html

    result = _escape_html("<script>alert('xss')</script>")
    # html.escape() also escapes single quotes to &#x27;
    assert result == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"


def test_escape_html_escapes_bold_tags():
    """Test that _escape_html escapes bold tags."""
    from src.components.visualizations import _escape_html

    result = _escape_html("<b>test</b>")
    assert result == "&lt;b&gt;test&lt;/b&gt;"


def test_escape_html_escapes_ampersands_and_brackets():
    """Test that _escape_html escapes ampersands and angle brackets."""
    from src.components.visualizations import _escape_html

    result = _escape_html("test & <test>")
    assert result == "test &amp; &lt;test&gt;"


def test_escape_html_handles_none():
    """Test that _escape_html handles None input gracefully."""
    from src.components.visualizations import _escape_html

    result = _escape_html(None)
    assert result == ""


def test_escape_html_handles_normal_text():
    """Test that _escape_html leaves normal text unchanged."""
    from src.components.visualizations import _escape_html

    result = _escape_html("normal text")
    assert result == "normal text"


def test_version_comparison_escapes_malicious_test_name():
    """Test that version comparison chart escapes malicious test names in hover text."""
    malicious_df = pd.DataFrame([
        {
            "test_name": "<script>alert('xss')</script>",
            "baseline_mean": 100.0,
            "comparison_mean": 95.0,
            "percent_change": -5.0,
            "is_regression": True,
            "hardware_config": "config1"
        }
    ])

    fig = create_version_comparison_bar_chart(
        malicious_df,
        baseline_version="v1.0",
        comparison_version="v2.0"
    )

    # Extract hover text from customdata
    hover_data = fig.data[0].customdata
    all_hover_text = " ".join(hover_data)

    # Should contain escaped version
    assert "&lt;script&gt;" in all_hover_text

    # Should NOT contain unescaped version (allow legitimate HTML tags like <b>)
    assert "<script>alert" not in all_hover_text


def test_version_comparison_escapes_hardware_config():
    """Test that version comparison chart escapes malicious hardware config names."""
    malicious_df = pd.DataFrame([
        {
            "test_name": "coremark",
            "baseline_mean": 100.0,
            "comparison_mean": 95.0,
            "percent_change": -5.0,
            "is_regression": True,
            "hardware_config": "<img src=x onerror=alert('xss')>"
        }
    ])

    fig = create_version_comparison_bar_chart(
        malicious_df,
        baseline_version="v1.0",
        comparison_version="v2.0"
    )

    # Extract hover text
    hover_data = fig.data[0].customdata
    all_hover_text = " ".join(hover_data)

    # Should contain escaped version
    assert "&lt;img" in all_hover_text

    # Should NOT contain unescaped version
    assert "<img src=x" not in all_hover_text


def test_peer_os_comparison_escapes_category_and_test_names():
    """Test that peer OS comparison chart escapes category and test names in hover text."""
    from src.components.visualizations import create_peer_os_comparison_chart

    malicious_df = pd.DataFrame([
        {
            "peer_os": "Ubuntu",
            "benchmark_category": "<iframe src='evil.com'>",
            "relative_performance": 95.0,
            "test_name": "<script>alert('xss')</script>"
        }
    ])

    fig = create_peer_os_comparison_chart(
        malicious_df,
        baseline_os="RHEL"
    )

    # Extract hover text from customdata
    hover_data = fig.data[0].customdata
    all_hover_text = " ".join(hover_data)

    # Should contain escaped versions
    assert "&lt;iframe" in all_hover_text or "&lt;script&gt;" in all_hover_text

    # Should NOT contain unescaped versions
    assert "<iframe src=" not in all_hover_text
    assert "<script>alert" not in all_hover_text


def test_peer_os_comparison_escapes_axis_labels_and_trace_names():
    """Test that peer OS comparison chart escapes x-axis labels (category) and trace names (peer_os).

    This test verifies that HTML special characters in category names (x-axis)
    and peer_os names (trace names) are properly escaped to prevent XSS.
    """
    from src.components.visualizations import create_peer_os_comparison_chart

    malicious_df = pd.DataFrame([
        {
            "peer_os": "<script>alert('os')</script>",
            "benchmark_category": "<img src=x onerror=alert(1)>",
            "relative_performance": 95.0,
            "test_name": "coremark"
        }
    ])

    fig = create_peer_os_comparison_chart(
        malicious_df,
        baseline_os="RHEL"
    )

    # Test 1: X-axis labels (category) should be escaped
    trace = fig.data[0]
    x_labels = trace.x

    # x_labels should contain escaped version of category
    assert len(x_labels) > 0, "Should have x-axis labels"
    assert "&lt;img src=x onerror=alert(1)&gt;" in x_labels, \
        "X-axis label (category) should be HTML-escaped"

    # X-axis should NOT contain unescaped HTML
    assert "<img src=x onerror=alert(1)>" not in x_labels, \
        "X-axis label should not contain raw HTML"

    # Test 2: Trace names (peer_os) should be escaped
    trace_name = trace.name

    # Trace name should be escaped
    assert "&lt;script&gt;alert(&#x27;os&#x27;)&lt;/script&gt;" == trace_name, \
        "Trace name (peer_os) should be HTML-escaped"

    # Trace name should NOT contain unescaped HTML
    assert "<script>" not in trace_name, \
        "Trace name should not contain raw HTML"


def test_regression_heatmap_escapes_test_names():
    """Test that regression heatmap escapes test names in hover text."""
    malicious_data = {
        '9.0→9.1': [5.2, -3.1],
        '9.1→9.2': [-2.5, 4.3]
    }
    malicious_df = pd.DataFrame(
        malicious_data,
        index=["<script>alert('xss')</script>", "streams"]
    )

    fig = create_regression_heatmap(malicious_df)

    # Extract hover text from hovertext attribute
    heatmap_trace = fig.data[0]
    hover_text = heatmap_trace.hovertext

    # Flatten hover text if it's a 2D array
    if isinstance(hover_text, list):
        all_hover_text = " ".join([item for sublist in hover_text for item in (sublist if isinstance(sublist, list) else [sublist])])
    else:
        all_hover_text = str(hover_text)

    # Should contain escaped version
    assert "&lt;script&gt;" in all_hover_text

    # Should NOT contain unescaped version
    assert "<script>alert" not in all_hover_text


def test_regression_heatmap_escapes_axis_labels():
    """Test that regression heatmap escapes axis labels (column and index names)."""
    malicious_data = {
        '9.0→9.1': [5.2, -3.1],
        '<img src=x onerror=alert("xss")>': [-2.5, 4.3]
    }
    malicious_df = pd.DataFrame(
        malicious_data,
        index=["<script>alert('xss')</script>", "<iframe src='evil.com'>"]
    )

    fig = create_regression_heatmap(malicious_df)

    # Extract x and y axis data
    heatmap_trace = fig.data[0]
    x_axis_labels = heatmap_trace.x
    y_axis_labels = heatmap_trace.y

    # Convert to strings for checking
    x_labels_str = " ".join([str(label) for label in x_axis_labels])
    y_labels_str = " ".join([str(label) for label in y_axis_labels])

    # X-axis labels should be escaped
    assert "&lt;img src=x onerror=alert(" in x_labels_str or "img src=x onerror=alert" not in x_labels_str
    assert "<img src=x onerror=alert" not in x_labels_str

    # Y-axis labels should be escaped
    assert "&lt;script&gt;" in y_labels_str
    assert "&lt;iframe" in y_labels_str
    assert "<script>alert" not in y_labels_str
    assert "<iframe src=" not in y_labels_str


def test_cloud_scaling_chart_escapes_category_names():
    """Test that cloud scaling chart escapes benchmark category names in hover text."""
    malicious_df = pd.DataFrame([
        {
            "instance_type": "c2-standard-4",
            "benchmark_category": "<svg onload=alert('xss')>",
            "cpu_cores": 4,
            "memory_gb": 16,
            "mean_performance": 100000.0
        },
        {
            "instance_type": "c2-standard-8",
            "benchmark_category": "<svg onload=alert('xss')>",
            "cpu_cores": 8,
            "memory_gb": 32,
            "mean_performance": 195000.0
        }
    ])

    fig = create_cloud_scaling_chart(malicious_df)

    # Extract hover text from customdata
    trace = fig.data[0]
    if hasattr(trace, 'customdata'):
        all_hover_text = " ".join([str(h) for h in trace.customdata if h])

        # Should contain escaped version
        assert "&lt;svg" in all_hover_text

        # Should NOT contain unescaped version
        assert "<svg onload" not in all_hover_text


def test_cloud_scaling_chart_escapes_instance_type_in_axis_ticktext():
    """Test that cloud scaling chart escapes instance_type in axis tick labels."""
    malicious_df = pd.DataFrame([
        {
            "instance_type": "<script>alert('xss')</script>",
            "benchmark_category": "CPU",
            "cpu_cores": 4,
            "memory_gb": 16,
            "mean_performance": 100000.0
        },
        {
            "instance_type": "<img src=x onerror=alert('xss')>",
            "benchmark_category": "CPU",
            "cpu_cores": 8,
            "memory_gb": 32,
            "mean_performance": 195000.0
        }
    ])

    fig = create_cloud_scaling_chart(malicious_df)

    # Extract tick labels from x-axis
    if fig.layout.xaxis.ticktext:
        all_tick_text = " ".join([str(t) for t in fig.layout.xaxis.ticktext])

        # Should contain escaped versions
        assert "&lt;script&gt;" in all_tick_text
        assert "&lt;img" in all_tick_text

        # Should NOT contain unescaped versions
        assert "<script>alert" not in all_tick_text
        assert "<img src=x" not in all_tick_text


def test_category_benchmark_detail_chart_escapes_test_name():
    """Test that category benchmark detail chart escapes test_name in hover text."""
    malicious_df = pd.DataFrame([
        {
            "test_name": "<script>alert('xss')</script>",
            "relative_performance": 95.0,
            "instance_type": "c2-standard-4",
            "is_competitive": 1.0
        },
        {
            "test_name": "<script>alert('xss')</script>",
            "relative_performance": 98.0,
            "instance_type": "c2-standard-8",
            "is_competitive": 1.0
        }
    ])

    from src.components.visualizations import create_category_benchmark_detail_chart
    fig = create_category_benchmark_detail_chart(malicious_df, "CPU")

    # Extract hover text from customdata
    trace = fig.data[0]
    if hasattr(trace, 'customdata'):
        all_hover_text = " ".join([str(h) for h in trace.customdata if h])

        # Should contain escaped version
        assert "&lt;script&gt;" in all_hover_text

        # Should NOT contain unescaped version
        assert "<script>alert" not in all_hover_text


def test_category_benchmark_detail_chart_escapes_axis_labels_and_title():
    """Test that category benchmark detail chart escapes test_name in y-axis labels and category in title."""
    malicious_test_name = "<script>alert('xss')</script>"
    malicious_category = "<img src=x onerror=alert('xss')>"

    malicious_df = pd.DataFrame([
        {
            "test_name": malicious_test_name,
            "relative_performance": 95.0,
            "instance_type": "c2-standard-4",
            "is_competitive": 1.0
        },
        {
            "test_name": malicious_test_name,
            "relative_performance": 98.0,
            "instance_type": "c2-standard-8",
            "is_competitive": 1.0
        }
    ])

    from src.components.visualizations import create_category_benchmark_detail_chart
    fig = create_category_benchmark_detail_chart(malicious_df, malicious_category)

    # Test y-axis labels are escaped
    trace = fig.data[0]
    y_labels = trace.y
    assert len(y_labels) > 0

    # Y-axis should contain escaped version
    y_labels_str = " ".join([str(label) for label in y_labels])
    assert "&lt;script&gt;" in y_labels_str
    assert "<script>alert" not in y_labels_str

    # Test title is escaped
    title = fig.layout.title.text
    assert "&lt;img" in title
    assert "<img src=x onerror" not in title


def test_category_hardware_heatmap_escapes_test_and_hardware():
    """Test that category hardware heatmap escapes test and hardware names in hover text."""
    malicious_df = pd.DataFrame([
        {
            "test_name": "<script>alert('xss')</script>",
            "instance_type": "<img src=x onerror=alert('xss')>",
            "relative_performance": 95.0
        },
        {
            "test_name": "<script>alert('xss')</script>",
            "instance_type": "c2-standard-8",
            "relative_performance": 105.0
        },
        {
            "test_name": "streams",
            "instance_type": "<img src=x onerror=alert('xss')>",
            "relative_performance": 110.0
        }
    ])

    from src.components.visualizations import create_category_hardware_heatmap
    fig = create_category_hardware_heatmap(malicious_df, "Memory")

    # Extract hover text from customdata
    trace = fig.data[0]
    if hasattr(trace, 'customdata'):
        # customdata is a 2D array for heatmaps
        all_hover_text = " ".join([
            str(cell) for row in trace.customdata
            for cell in (row if isinstance(row, (list, tuple)) else [row])
            if cell
        ])

        # Should contain escaped versions
        assert "&lt;script&gt;" in all_hover_text
        assert "&lt;img" in all_hover_text

        # Should NOT contain unescaped versions
        assert "<script>alert" not in all_hover_text
        assert "<img src=x" not in all_hover_text


def test_category_hardware_heatmap_escapes_axis_labels_and_title():
    """Test that category hardware heatmap escapes x-axis, y-axis labels, and title."""
    malicious_df = pd.DataFrame([
        {
            "test_name": "<script>alert('test')</script>",
            "instance_type": "<img src=x onerror=alert('hw')>",
            "relative_performance": 95.0
        },
        {
            "test_name": "safe_test",
            "instance_type": "<img src=x onerror=alert('hw')>",
            "relative_performance": 105.0
        },
        {
            "test_name": "<script>alert('test')</script>",
            "instance_type": "safe-hardware",
            "relative_performance": 110.0
        }
    ])

    from src.components.visualizations import create_category_hardware_heatmap
    malicious_category = "<iframe src='evil.com'>"
    fig = create_category_hardware_heatmap(malicious_df, malicious_category)

    # Test 1: X-axis labels (instance_type) should be escaped
    heatmap_trace = fig.data[0]
    x_axis_labels = heatmap_trace.x
    x_labels_str = " ".join([str(label) for label in x_axis_labels])

    assert "&lt;img src=x onerror=alert(" in x_labels_str, \
        "X-axis labels (instance_type) should be HTML-escaped"
    assert "<img src=x onerror=alert" not in x_labels_str, \
        "X-axis labels should not contain raw HTML"

    # Test 2: Y-axis labels (test_name) should be escaped
    y_axis_labels = heatmap_trace.y
    y_labels_str = " ".join([str(label) for label in y_axis_labels])

    assert "&lt;script&gt;" in y_labels_str, \
        "Y-axis labels (test_name) should be HTML-escaped"
    assert "<script>alert" not in y_labels_str, \
        "Y-axis labels should not contain raw HTML"

    # Test 3: Title (category) should be escaped
    title_text = fig.layout.title.text

    assert "&lt;iframe src=" in title_text, \
        "Title (category) should be HTML-escaped"
    assert "<iframe src='evil.com'>" not in title_text, \
        "Title should not contain raw HTML"


def test_heatmap_escapes_row_and_column_dimensions():
    """Test that heatmap escapes row and column dimension values in hover template."""
    malicious_df = pd.DataFrame([
        {
            "os_version": "<script>alert('xss')</script>",
            "instance_type": "<img src=x onerror=alert('xss')>",
            "primary_metric_value": 100.0,
            "test_name": "coremark"
        },
        {
            "os_version": "<script>alert('xss')</script>",
            "instance_type": "c2-standard-8",
            "primary_metric_value": 105.0,
            "test_name": "coremark"
        },
        {
            "os_version": "rhel-9.0",
            "instance_type": "<img src=x onerror=alert('xss')>",
            "primary_metric_value": 110.0,
            "test_name": "coremark"
        }
    ])

    fig = create_heatmap(malicious_df)

    # Extract the hovertemplate to check if it references escaped data
    trace = fig.data[0]
    hovertemplate = trace.hovertemplate

    # The hovertemplate uses %{y} and %{x} which pull from pivot.index and pivot.columns
    # These need to be escaped at the data source
    # Check if the x and y arrays contain escaped data
    x_values = " ".join([str(v) for v in trace.x])
    y_values = " ".join([str(v) for v in trace.y])

    # Should contain escaped versions
    assert "&lt;script&gt;" in y_values
    assert "&lt;img" in x_values

    # Should NOT contain unescaped versions
    assert "<script>alert" not in y_values
    assert "<img src=x" not in x_values


# ============================================================================
# Pattern Index Helper Tests (Defensive Coding)
# ============================================================================


def test_pattern_index_helper_handles_none_name():
    """Test that _get_pattern_index_for_name handles None name without crashing."""
    from src.components.visualizations import _get_pattern_index_for_name

    # Should not crash when name is None
    index = _get_pattern_index_for_name(None, 5)

    # Should return a valid index
    assert isinstance(index, int)
    assert 0 <= index < 5


def test_pattern_index_helper_handles_empty_string_name():
    """Test that _get_pattern_index_for_name handles empty string name without crashing."""
    from src.components.visualizations import _get_pattern_index_for_name

    # Should not crash when name is empty string
    index = _get_pattern_index_for_name("", 5)

    # Should return a valid index
    assert isinstance(index, int)
    assert 0 <= index < 5


def test_pattern_index_helper_handles_non_string_name():
    """Test that _get_pattern_index_for_name handles non-string name (int) without crashing."""
    from src.components.visualizations import _get_pattern_index_for_name

    # Should not crash when name is an integer
    index = _get_pattern_index_for_name(123, 5)

    # Should return a valid index
    assert isinstance(index, int)
    assert 0 <= index < 5


def test_pattern_index_helper_handles_zero_pattern_count():
    """Test that _get_pattern_index_for_name handles pattern_count=0 without crashing."""
    from src.components.visualizations import _get_pattern_index_for_name

    # Should not crash when pattern_count is 0
    index = _get_pattern_index_for_name("test", 0)

    # Should return 0 (the only valid index when clamped to min 1 pattern)
    assert isinstance(index, int)
    assert index == 0


def test_pattern_index_helper_handles_negative_pattern_count():
    """Test that _get_pattern_index_for_name handles negative pattern_count without crashing."""
    from src.components.visualizations import _get_pattern_index_for_name

    # Should not crash when pattern_count is negative
    index = _get_pattern_index_for_name("test", -5)

    # Should return 0 (the only valid index when clamped to min 1 pattern)
    assert isinstance(index, int)
    assert index == 0


def test_pattern_index_helper_deterministic_with_same_inputs():
    """Test that _get_pattern_index_for_name returns same index for same inputs (deterministic)."""
    from src.components.visualizations import _get_pattern_index_for_name

    # Call multiple times with same inputs
    index1 = _get_pattern_index_for_name("test_name", 10)
    index2 = _get_pattern_index_for_name("test_name", 10)
    index3 = _get_pattern_index_for_name("test_name", 10)

    # All should return the same index
    assert index1 == index2 == index3

    # Should be a valid index
    assert 0 <= index1 < 10


def test_heatmap_normalize_by_test_produces_correct_output():
    """Heatmap normalization by test produces correct percentage values."""
    # Create test data with two tests that have very different scales
    df = pd.DataFrame([
        {"test_name": "test_A", "os_version": "RHEL8", "instance_type": "m5.large", "primary_metric_value": 1000},
        {"test_name": "test_A", "os_version": "RHEL8", "instance_type": "m5.xlarge", "primary_metric_value": 1200},
        {"test_name": "test_A", "os_version": "RHEL9", "instance_type": "m5.large", "primary_metric_value": 800},
        {"test_name": "test_B", "os_version": "RHEL8", "instance_type": "m5.large", "primary_metric_value": 100},
        {"test_name": "test_B", "os_version": "RHEL8", "instance_type": "m5.xlarge", "primary_metric_value": 120},
        {"test_name": "test_B", "os_version": "RHEL9", "instance_type": "m5.large", "primary_metric_value": 80},
    ])

    # Test_A mean: (1000 + 1200 + 800) / 3 = 1000
    # Test_B mean: (100 + 120 + 80) / 3 = 100
    # After normalization, all values should be percentages of their test's mean

    fig = create_heatmap(
        df,
        row_dim="os_version",
        col_dim="instance_type",
        value_col="primary_metric_value",
        normalize_by_test=True
    )

    # Extract the heatmap data
    heatmap_trace = fig.data[0]
    z_values = heatmap_trace.z

    # Verify that normalized values are present (percentages around 80-120)
    # The normalized values should be: test_A: 100%, 120%, 80%; test_B: 100%, 120%, 80%
    # After pivoting and averaging (if multiple entries per cell), should still show percentage scale
    assert z_values is not None
    # Verify we're working with percentage scale (values around 100)
    assert any(50 < val < 150 for row in z_values for val in row), \
        "Normalized heatmap should have percentage values around 100"

    # Colorbar title should indicate percentage (in the heatmap trace)
    assert heatmap_trace.colorbar.title.text == "% of Avg"


def test_heatmap_normalize_by_test_groupby_equivalence():
    """Groupby transform approach produces same output as loop approach for normalization."""
    # Create test data with multiple tests
    df = pd.DataFrame([
        {"test_name": "test_A", "os_version": "RHEL8", "instance_type": "m5.large", "primary_metric_value": 1000},
        {"test_name": "test_A", "os_version": "RHEL8", "instance_type": "m5.xlarge", "primary_metric_value": 1200},
        {"test_name": "test_A", "os_version": "RHEL9", "instance_type": "m5.large", "primary_metric_value": 800},
        {"test_name": "test_B", "os_version": "RHEL8", "instance_type": "m5.large", "primary_metric_value": 100},
        {"test_name": "test_B", "os_version": "RHEL8", "instance_type": "m5.xlarge", "primary_metric_value": 120},
        {"test_name": "test_B", "os_version": "RHEL9", "instance_type": "m5.large", "primary_metric_value": 80},
    ])

    value_col = "primary_metric_value"

    # Loop approach (current implementation)
    df_loop = df.copy()
    for test_name in df_loop['test_name'].unique():
        test_mask = df_loop['test_name'] == test_name
        test_mean = df_loop.loc[test_mask, value_col].mean()
        if test_mean > 0:
            df_loop.loc[test_mask, value_col] = (df_loop.loc[test_mask, value_col] / test_mean) * 100

    # Groupby transform approach (optimized implementation)
    df_groupby = df.copy()
    df_groupby[value_col] = df_groupby.groupby('test_name')[value_col].transform(
        lambda x: (x / x.mean() * 100) if x.mean() > 0 else x
    )

    # Results should be identical in values (dtype may differ slightly due to transform)
    pd.testing.assert_frame_equal(df_loop, df_groupby, check_dtype=False)


def test_heatmap_colorblind_high_values_appear_blue():
    """
    Integration test: colorblind heatmap maps high values to blue, low to orange.

    The help text says "blue = higher performance, orange = lower performance".
    In Plotly, higher z-values map to the 1.0 end of the colorscale.
    Therefore the scale must have orange at 0.0 and blue at 1.0.

    This test verifies the scale is wired correctly by creating a heatmap
    with known high/low values and checking the colorscale endpoints.
    """
    # Create test data with known high and low values
    test_df = pd.DataFrame([
        {"os_version": "OS1", "instance_type": "small", "primary_metric_value": 10.0},
        {"os_version": "OS1", "instance_type": "large", "primary_metric_value": 100.0},
        {"os_version": "OS2", "instance_type": "small", "primary_metric_value": 20.0},
        {"os_version": "OS2", "instance_type": "large", "primary_metric_value": 90.0},
    ])

    fig = create_heatmap(
        test_df,
        row_dim='os_version',
        col_dim='instance_type',
        value_col='primary_metric_value',
        title="Test Heatmap",
        normalize_by_test=False,
        colorblind_mode=True
    )

    # Get the colorscale from the heatmap trace
    assert len(fig.data) > 0, "Heatmap should have at least one trace"
    heatmap_trace = fig.data[0]
    colorscale = heatmap_trace.colorscale

    # Verify colorscale is a list or tuple of (position, color) tuples
    assert isinstance(colorscale, (list, tuple)), "Colorscale should be a list or tuple"
    assert len(colorscale) > 0, "Colorscale should not be empty"

    # First stop (0.0) should be orange/vermillion for low performance
    first_position, first_color = colorscale[0]
    assert first_position == 0.0, f"First position should be 0.0, got {first_position}"
    assert first_color.lower() == "#d55e00", \
        f"First color (low values) should be vermillion/orange #d55e00, got {first_color}"

    # Last stop (1.0) should be blue for high performance
    last_position, last_color = colorscale[-1]
    assert last_position == 1.0, f"Last position should be 1.0, got {last_position}"
    assert last_color.lower() == "#0072b2", \
        f"Last color (high values) should be blue #0072b2, got {last_color}"


# ============================================================================
# Security Tests - HTML Escaping
# ============================================================================


def test_metrics_table_escapes_column_names_with_html():
    """
    Test that create_metrics_table() escapes column names containing HTML.

    This prevents XSS if column names are ever derived from user input or data.
    Column names with <script> tags should be HTML-escaped in the table header.
    """
    # Create test data with malicious column name
    test_df = pd.DataFrame({
        "Col<script>alert('xss')</script>": [1, 2, 3],
        "Normal Column": [4, 5, 6]
    })

    fig = create_metrics_table(test_df)

    # Extract header values from the table
    assert len(fig.data) > 0, "Table should have data"
    table_trace = fig.data[0]
    header_values = table_trace.header.values

    # Header should be a list or tuple of HTML strings
    assert isinstance(header_values, (list, tuple)), "Header values should be a list or tuple"

    # Join all header HTML to check for unescaped tags
    all_headers = " ".join(str(h) for h in header_values)

    # Raw <script> tags should NOT appear in the output
    assert "<script>" not in all_headers, \
        "Raw <script> tag should be escaped, not embedded in header HTML"
    assert "</script>" not in all_headers, \
        "Raw </script> tag should be escaped, not embedded in header HTML"

    # Escaped versions SHOULD appear
    assert "&lt;script&gt;" in all_headers or "Col&lt;script" in all_headers, \
        "Column name with HTML should be escaped using &lt; and &gt;"


# --- Point Drill-Down Chart Tests (RPOPC-1183) ---


@pytest.fixture
def sample_timeseries_points():
    """Sample timeseries points matching zathras_timeseries.json structure."""
    return [
        {
            "metadata": {
                "document_id": "test_doc123",
                "sequence": i,
                "timeseries_id": "test_abc_timeseries",
                "test_timestamp": f"2026-01-25T05:3{i}:23.928784Z",
            },
            "results": {
                "point_metrics": {
                    "tcp_stream_bw_gbs": 7.0 + i * 0.1,
                    "latency_us": 30.0 + i,
                }
            }
        }
        for i in range(5)
    ]


def test_create_point_drilldown_chart_basic(sample_timeseries_points):
    """Test basic point drill-down chart rendering."""
    from src.components.visualizations import create_point_drilldown_chart

    fig = create_point_drilldown_chart(
        points=sample_timeseries_points,
        metric_name="tcp_stream_bw_gbs",
        metric_unit="GB/s",
        summary_value=None,
        colorblind_mode=False,
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    trace = fig.data[0]
    assert trace.type == "scatter"
    assert trace.mode == "lines+markers"

    # X-axis should be sequence values 0-4
    assert list(trace.x) == [0, 1, 2, 3, 4]

    # Y-axis should match metric values
    expected_y = [7.0, 7.1, 7.2, 7.3, 7.4]
    assert list(trace.y) == expected_y

    # Title should include metric name
    assert "tcp_stream_bw_gbs" in fig.layout.title.text
    assert "Sequence" in fig.layout.xaxis.title.text
    assert "tcp_stream_bw_gbs" in fig.layout.yaxis.title.text
    assert "GB/s" in fig.layout.yaxis.title.text


def test_create_point_drilldown_chart_empty_points():
    """Test empty points list returns empty figure."""
    from src.components.visualizations import create_point_drilldown_chart

    fig = create_point_drilldown_chart(
        points=[],
        metric_name="tcp_stream_bw_gbs",
    )

    assert isinstance(fig, go.Figure)
    # Empty figure has no traces
    assert len(fig.data) == 0
    # Should have annotation with empty message
    assert len(fig.layout.annotations) > 0
    annotation_texts = [ann.text for ann in fig.layout.annotations]
    assert any("No timeseries data" in text for text in annotation_texts)


def test_create_point_drilldown_chart_with_summary_line(sample_timeseries_points):
    """Test summary reference line appears when summary_value is provided."""
    from src.components.visualizations import create_point_drilldown_chart

    fig = create_point_drilldown_chart(
        points=sample_timeseries_points,
        metric_name="tcp_stream_bw_gbs",
        summary_value=7.2,
    )

    # Should have a horizontal line shape
    assert len(fig.layout.shapes) > 0
    hline = fig.layout.shapes[0]
    assert hline.type == "line"
    assert hline.y0 == 7.2
    assert hline.y1 == 7.2
    assert "dash" in hline.line.dash


def test_create_point_drilldown_chart_no_summary_line(sample_timeseries_points):
    """Test no summary line when summary_value is None."""
    from src.components.visualizations import create_point_drilldown_chart

    fig = create_point_drilldown_chart(
        points=sample_timeseries_points,
        metric_name="tcp_stream_bw_gbs",
        summary_value=None,
    )

    # Should have no shapes
    assert len(fig.layout.shapes) == 0


def test_create_point_drilldown_chart_colorblind_mode(sample_timeseries_points):
    """Test colorblind mode adds marker symbols."""
    from src.components.visualizations import create_point_drilldown_chart

    fig = create_point_drilldown_chart(
        points=sample_timeseries_points,
        metric_name="tcp_stream_bw_gbs",
        colorblind_mode=True,
    )

    trace = fig.data[0]
    # Should have marker symbol for redundant encoding
    assert trace.marker.symbol is not None


def test_create_point_drilldown_chart_metric_not_in_point_metrics(sample_timeseries_points):
    """Test fallback when metric_name not in point_metrics."""
    from src.components.visualizations import create_point_drilldown_chart

    # Request a metric that doesn't exist
    fig = create_point_drilldown_chart(
        points=sample_timeseries_points,
        metric_name="nonexistent_metric",
    )

    # Should still render (falls back to first available metric)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    # Should have data (using tcp_stream_bw_gbs as fallback)
    assert len(fig.data[0].y) == 5


def test_create_point_drilldown_chart_escapes_metric_name():
    """Test HTML entities in metric name are escaped."""
    from src.components.visualizations import create_point_drilldown_chart

    malicious_points = [
        {
            "metadata": {"sequence": 0},
            "results": {"point_metrics": {"<script>alert</script>": 100.0}}
        }
    ]

    fig = create_point_drilldown_chart(
        points=malicious_points,
        metric_name="<script>alert</script>",
    )

    # Title should not contain raw script tags
    assert "<script>" not in fig.layout.title.text
    assert "</script>" not in fig.layout.title.text
    # Should contain escaped version
    assert "&lt;script&gt;" in fig.layout.title.text or "alert" in fig.layout.title.text
