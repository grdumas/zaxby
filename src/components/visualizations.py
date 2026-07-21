"""
Visualization components for the dashboard.

Provides Plotly-based visualizations for benchmark data.

## Legend and Help Text Conventions

All charts include clear legends and help text to aid interpretation:

**Legend Positioning:**
- **Bottom horizontal** (y=-0.15): Used for simple charts with few traces
  - Comparison charts (baseline vs comparison)
  - Box plots with color grouping
  - Bar charts with 2-3 categories

- **Top-right corner** (x=0.99, y=0.99): Used for time series
  - Vertical orientation
  - Semi-transparent background
  - Positioned inside plot area

- **Right side** (x=1.02): Used for scatter plots and charts with many traces
  - Vertical orientation
  - Positioned outside plot area with right margin

**Help Annotations:**
- Heatmaps include color scale interpretation (green/yellow/red meaning)
- Regression heatmaps explain red=regression, green=improvement
- Complex charts (version comparison, peer OS) have detailed legends explaining
  color schemes and patterns

**Design Principles:**
- Legends never obscure chart data
- Consistent positioning within chart types
- Color meanings are always explained
- Tooltips provide additional context on hover
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List

from src.benchmark_categories import benchmark_groups


def _normalize_color_col(color_col: Optional[str]) -> Optional[str]:
    """
    Normalize empty string color_col values to None.

    Defends against UI passing empty strings instead of None, which would
    crash Plotly Express with "Value of 'color' is not the name of a column".

    Args:
        color_col: Color column name (may be empty string)

    Returns:
        None if color_col is falsy (None, empty string, whitespace), otherwise color_col
    """
    if not color_col or (isinstance(color_col, str) and not color_col.strip()):
        return None
    return color_col


# Legend and margin constants
# These values standardize chart legend positioning and spacing
LEGEND_RIGHT_MARGIN = 200  # Right margin for discrete color legends and help annotations
LEGEND_BOTTOM_MARGIN = 100  # Bottom margin for horizontal legends
HEATMAP_HELP_MARGIN = 200  # Right margin for heatmap help annotations

# Standard legend configurations
LEGEND_HORIZONTAL_BOTTOM = {
    'orientation': 'h',
    'yanchor': 'top',
    'y': -0.15,
    'xanchor': 'center',
    'x': 0.5
}

LEGEND_VERTICAL_TOPRIGHT = {
    'orientation': 'v',
    'xanchor': 'right',
    'x': 0.99,
    'yanchor': 'top',
    'y': 0.99,
    'bgcolor': 'rgba(255, 255, 255, 0.8)',
    'bordercolor': 'rgba(0, 0, 0, 0.2)',
    'borderwidth': 1
}


def create_comparison_chart(
    df: pd.DataFrame,
    group_by: str = 'test_name',
    title: str = "Performance Comparison",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a side-by-side bar chart for comparing configurations.

    Args:
        df: DataFrame with comparison data (must have baseline_mean, comparison_mean)
        group_by: Column used for grouping
        title: Chart title
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    if df.empty:
        return create_empty_figure("No data available for comparison")

    palette = get_palette(colorblind_mode)

    fig = go.Figure()

    # Baseline bars
    baseline_marker = dict(color=palette.comparison.baseline)
    if colorblind_mode:
        baseline_marker['pattern'] = dict(shape='/', solidity=0.3, fillmode='overlay')

    fig.add_trace(go.Bar(
        x=df[group_by],
        y=df['baseline_mean'],
        name='Baseline',
        marker=baseline_marker,
        error_y=dict(type='data', array=df['baseline_std']) if 'baseline_std' in df.columns else None
    ))

    # Comparison bars
    comparison_marker = dict(color=palette.comparison.comparison)
    if colorblind_mode:
        comparison_marker['pattern'] = dict(shape='\\', solidity=0.3, fillmode='overlay')

    fig.add_trace(go.Bar(
        x=df[group_by],
        y=df['comparison_mean'],
        name='Comparison',
        marker=comparison_marker,
        error_y=dict(type='data', array=df['comparison_std']) if 'comparison_std' in df.columns else None
    ))

    fig.update_layout(
        title=title,
        xaxis_title=group_by.replace('_', ' ').title(),
        yaxis_title="Performance Metric",
        barmode='group',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        legend=LEGEND_HORIZONTAL_BOTTOM,
        margin=dict(b=LEGEND_BOTTOM_MARGIN)
    )

    return fig


def create_time_series_chart(
    df: pd.DataFrame,
    x_col: str = 'timestamp',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = 'test_name',
    title: str = "Performance Trends Over Time",
    use_facets: bool = False,
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a time series line chart.

    Args:
        df: DataFrame with time series data
        x_col: Column for x-axis (timestamp)
        y_col: Column for y-axis (metric values)
        color_col: Column to use for line colors
        title: Chart title
        use_facets: If True and color_col='test_name', create separate subplots with independent y-axes
        colorblind_mode: If True, use line dashes for redundant encoding

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    if df.empty:
        return create_empty_figure("No time series data available")

    # Normalize empty string to None to prevent Plotly crash
    color_col = _normalize_color_col(color_col)

    # If color_col is test_name and we have multiple tests with different scales, use facets
    if use_facets and color_col == 'test_name' and len(df[color_col].unique()) > 1:
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            markers=True,
            title=title,
            template='plotly_white',
            facet_row=color_col,
            facet_row_spacing=0.05
        )

        # Update each facet to have independent y-axis
        fig.update_yaxes(matches=None, showticklabels=True, title_text="")

        fig.update_layout(
            xaxis_title="Date",
            hovermode='x unified',
            height=max(500, len(df[color_col].unique()) * 200),
            showlegend=False  # Legend is redundant with facet labels
        )
    else:
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            markers=True,
            title=title,
            template='plotly_white'
        )

        # Base layout configuration
        layout_config = {
            'xaxis_title': "Date",
            'yaxis_title': "Performance Metric",
            'hovermode': 'x unified',
            'height': 500
        }

        # Only configure legend for multi-trace charts (when color_col is provided)
        if color_col is not None:
            layout_config['legend'] = LEGEND_VERTICAL_TOPRIGHT

        fig.update_layout(**layout_config)

    fig.update_traces(mode='lines+markers')

    # In colorblind mode, apply line dashes for redundant encoding beyond color
    if colorblind_mode and color_col is not None:
        palette = get_palette(colorblind_mode)
        line_dashes = palette.patterns.line_dashes

        # Apply different line dash to each trace
        for i, trace in enumerate(fig.data):
            if hasattr(trace, 'line'):
                dash_pattern = line_dashes[i % len(line_dashes)]
                trace.line.dash = dash_pattern

    return fig


def create_heatmap(
    df: pd.DataFrame,
    row_dim: str = 'os_version',
    col_dim: str = 'instance_type',
    value_col: str = 'primary_metric_value',
    title: str = "Performance Heatmap",
    normalize_by_test: bool = True,
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a heatmap for regression analysis.

    Args:
        df: DataFrame with benchmark data
        row_dim: Dimension for rows
        col_dim: Dimension for columns
        value_col: Column containing values for heatmap
        title: Chart title
        normalize_by_test: If True and data contains multiple test types, normalize within each test
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    if df.empty:
        return create_empty_figure("No data available for heatmap")

    palette = get_palette(colorblind_mode)
    
    # If we have multiple test types with different scales, normalize within each test
    if normalize_by_test and 'test_name' in df.columns and len(df['test_name'].unique()) > 1:
        # Calculate mean baseline for each test
        df_normalized = df.copy()
        for test_name in df_normalized['test_name'].unique():
            test_mask = df_normalized['test_name'] == test_name
            test_mean = df_normalized.loc[test_mask, value_col].mean()
            if test_mean > 0:
                # Convert to percentage of mean (100 = average performance)
                df_normalized.loc[test_mask, value_col] = (df_normalized.loc[test_mask, value_col] / test_mean) * 100
        
        # Create pivot table from normalized data
        pivot = df_normalized.pivot_table(
            values=value_col,
            index=row_dim,
            columns=col_dim,
            aggfunc='mean'
        )
        
        colorbar_title = "% of Avg"
        text_suffix = "%"
    else:
        # Create pivot table
        pivot = df.pivot_table(
            values=value_col,
            index=row_dim,
            columns=col_dim,
            aggfunc='mean'
        )
        colorbar_title = "Metric Value"
        text_suffix = ""
    
    if pivot.empty:
        return create_empty_figure("Insufficient data for heatmap")
    
    # Create hover text with formatted values
    hover_text = [[f"{val:.1f}{text_suffix}" for val in row] for row in pivot.values]

    # Determine colorscale
    if colorblind_mode:
        # Use colorblind-safe scale from palette
        if isinstance(palette.performance_heatmap_scale, str):
            colorscale = palette.performance_heatmap_scale
        else:
            colorscale = palette.performance_heatmap_scale.scale
    else:
        colorscale = 'RdYlGn'

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=colorscale,
        text=pivot.values.round(1),
        hovertext=hover_text,
        hovertemplate='%{y} × %{x}<br>%{hovertext}<extra></extra>',
        texttemplate='%{text}' + text_suffix,
        textfont={"size": 10},
        colorbar=dict(
            title=colorbar_title,
            x=1.02,
            xanchor='left',
            thickness=18
        )
    ))

    fig.update_layout(
        title=title,
        xaxis_title=col_dim.replace('_', ' ').title(),
        yaxis_title=row_dim.replace('_', ' ').title(),
        template='plotly_white',
        height=500,
        margin=dict(r=HEATMAP_HELP_MARGIN)
    )

    # Add help annotation explaining color scale
    # Position to right of colorbar using xshift to avoid collision
    if colorblind_mode:
        help_text = (
            "<b>How to read:</b><br>"
            "🔵 Blue = Higher performance<br>"
            "⚪ Gray = Medium performance<br>"
            "🟠 Orange = Lower performance"
        )
    else:
        help_text = (
            "<b>How to read:</b><br>"
            "🟢 Green = Higher performance<br>"
            "🟡 Yellow = Medium performance<br>"
            "🔴 Red = Lower performance"
        )

    fig.add_annotation(
        text=help_text,
        xref="paper", yref="paper",
        x=1.02, y=0.5,
        xshift=100,  # Shift right by 100px to avoid colorbar collision
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=4,
        xanchor="left",
        yanchor="middle"
    )

    return fig


def create_box_plot(
    df: pd.DataFrame,
    x_col: str = 'test_name',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = None,
    title: str = "Performance Distribution",
    use_facets: bool = False,
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a box plot showing distribution of performance metrics.
    
    Args:
        df: DataFrame with benchmark data
        x_col: Column for x-axis categories
        y_col: Column for y-axis values
        color_col: Optional column for color grouping
        title: Chart title
        use_facets: If True and x_col='test_name', create separate subplots with independent y-axes
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for distribution plot")
    
    # If x_col is test_name and we have multiple tests with different scales, use facets
    if use_facets and x_col == 'test_name' and len(df[x_col].unique()) > 1:
        fig = px.box(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            template='plotly_white',
            points='all',
            facet_col=x_col,
            facet_col_wrap=3
        )

        # Update each facet to have independent y-axis
        fig.update_yaxes(matches=None, showticklabels=True)

        # Determine if legend is needed
        # Legend is only redundant when:
        # 1. No color grouping (color_col is None), OR
        # 2. Color represents the same dimension as facets (color_col == x_col)
        # Otherwise, color represents a different dimension and legend is needed
        legend_is_redundant = color_col is None or color_col == x_col

        if legend_is_redundant:
            # Hide legend when it's redundant with facet labels
            fig.update_layout(
                height=500,
                showlegend=False
            )
        else:
            # Show legend with consistent positioning when it provides unique information
            fig.update_layout(
                height=500,
                legend=LEGEND_HORIZONTAL_BOTTOM,
                margin=dict(b=LEGEND_BOTTOM_MARGIN)
            )
    else:
        fig = px.box(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            template='plotly_white',
            points='all'
        )

        # Configure legend positioning when color grouping is used
        if color_col:
            fig.update_layout(
                xaxis_title=x_col.replace('_', ' ').title(),
                yaxis_title="Performance Metric",
                height=500,
                legend=LEGEND_HORIZONTAL_BOTTOM,
                margin=dict(b=LEGEND_BOTTOM_MARGIN)
            )
        else:
            fig.update_layout(
                xaxis_title=x_col.replace('_', ' ').title(),
                yaxis_title="Performance Metric",
                height=500
            )

    return fig


def create_scatter_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    hover_data: Optional[List[str]] = None,
    title: str = "Performance Scatter Plot",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a scatter plot for exploring relationships.

    Args:
        df: DataFrame with benchmark data
        x_col: Column for x-axis
        y_col: Column for y-axis
        color_col: Optional column for point colors
        size_col: Optional column for point sizes
        hover_data: Additional columns to show in hover
        title: Chart title
        colorblind_mode: If True, use marker symbols for redundant encoding

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    if df.empty:
        return create_empty_figure("No data available for scatter plot")

    # Normalize empty string to None to prevent Plotly crash
    color_col = _normalize_color_col(color_col)

    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        size=size_col,
        hover_data=hover_data,
        title=title,
        template='plotly_white'
    )

    # Configure legend positioning when color encoding creates a discrete legend
    # Note: size_col alone doesn't create a discrete legend that needs extra margin
    if color_col:
        fig.update_layout(
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title=y_col.replace('_', ' ').title(),
            height=500,
            legend=dict(
                orientation='v',
                yanchor='top',
                y=1.0,
                xanchor='left',
                x=1.02
            ),
            margin=dict(r=LEGEND_RIGHT_MARGIN)
        )
    else:
        fig.update_layout(
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title=y_col.replace('_', ' ').title(),
            height=500
        )

    # In colorblind mode, apply marker symbols for redundant encoding beyond color
    if colorblind_mode and color_col is not None:
        palette = get_palette(colorblind_mode)
        marker_symbols = palette.patterns.marker_symbols

        # Apply different marker symbol to each trace
        for i, trace in enumerate(fig.data):
            if hasattr(trace, 'marker'):
                symbol = marker_symbols[i % len(marker_symbols)]
                trace.marker.symbol = symbol

    return fig


def create_performance_delta_chart(
    df: pd.DataFrame,
    x_col: str = 'test_name',
    title: str = "Performance Change (%)",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a bar chart showing percentage changes with color coding.

    Uses the same 5-color + pattern scheme as version comparison charts
    when is_regression data is available.

    Args:
        df: DataFrame with percent_change column (and optionally is_regression)
        x_col: Column for x-axis labels
        title: Chart title
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    if df.empty or 'percent_change' not in df.columns:
        return create_empty_figure("No comparison data available")

    palette = get_palette(colorblind_mode)

    # Determine colors and patterns
    # If we have is_regression info, use the 5-color scheme
    if 'is_regression' in df.columns:
        colors = []
        patterns = []
        for _, row in df.iterrows():
            pct = row['percent_change']
            is_reg = row['is_regression']
            # For simple delta chart, assume single config (any == all)
            color, pattern = _get_regression_color_and_pattern(
                pct, is_reg, is_reg, colorblind_mode=colorblind_mode
            )
            colors.append(color)
            patterns.append(pattern)
        
        marker_config = dict(
            color=colors,
            pattern_shape=patterns,
            pattern_fillmode='overlay',
            pattern_size=8,
            pattern_solidity=0.3
        )
    else:
        # Fallback to simple color coding using palette
        colors = [
            palette.semantic.regression if x < -5
            else palette.semantic.improvement if x > 5
            else '#e0e0e0'
            for x in df['percent_change']
        ]
        marker_config = dict(color=colors)
    
    fig = go.Figure(data=[
        go.Bar(
            x=df[x_col],
            y=df['percent_change'],
            marker=marker_config,
            text=df['percent_change'].round(1).astype(str) + '%',
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title="Percent Change (%)",
        template='plotly_white',
        height=500
    )
    
    # Add reference line at 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    # Add stable zone
    fig.add_hrect(y0=-5, y1=5, fillcolor="gray", opacity=0.1, line_width=0,
                  annotation_text="Stable zone (±5%)", annotation_position="top right")
    
    return fig


def create_metrics_table(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    title: str = "Detailed Metrics",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a table visualization for detailed metrics.
    
    Args:
        df: DataFrame with metric data
        columns: Specific columns to display (None = all)
        title: Table title
        
    Returns:
        Plotly Figure with table
    """
    if df.empty:
        return create_empty_figure("No data available for table")
    
    if columns:
        display_df = df[columns].copy()
    else:
        display_df = df.copy()
    
    # Round numeric columns
    numeric_cols = display_df.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_cols:
        display_df[col] = display_df[col].round(2)
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{col}</b>" for col in display_df.columns],
            fill_color='paleturquoise',
            align='left',
            font=dict(size=12)
        ),
        cells=dict(
            values=[display_df[col] for col in display_df.columns],
            fill_color='lavender',
            align='left',
            font=dict(size=11)
        )
    )])
    
    fig.update_layout(
        title=title,
        height=400
    )
    
    return fig


def create_empty_figure(message: str = "No data available") -> go.Figure:
    """
    Create an empty figure with a message.
    
    Args:
        message: Message to display
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=20, color="gray")
    )
    
    fig.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        height=400,
        template='plotly_white'
    )
    
    return fig


def create_separate_test_charts(
    df: pd.DataFrame,
    chart_type: str = 'box',
    x_col: str = 'os_version',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = None,
    title_prefix: str = "Performance"
) -> List[go.Figure]:
    """
    Create separate charts for each test type to handle different scales.
    
    Args:
        df: DataFrame with benchmark data
        chart_type: Type of chart ('box', 'time_series')
        x_col: Column for x-axis
        y_col: Column for y-axis values
        color_col: Optional column for color grouping
        title_prefix: Prefix for chart titles
        
    Returns:
        List of Plotly Figures, one per test type
    """
    if df.empty or 'test_name' not in df.columns:
        return [create_empty_figure("No data available")]
    
    figures = []
    test_names = sorted(df['test_name'].unique())
    
    for test_name in test_names:
        test_df = df[df['test_name'] == test_name]
        
        if chart_type == 'box':
            fig = create_box_plot(
                test_df,
                x_col=x_col,
                y_col=y_col,
                color_col=color_col if color_col != 'test_name' else None,
                title=f"{title_prefix}: {test_name}",
                use_facets=False
            )
        elif chart_type == 'time_series':
            fig = create_time_series_chart(
                test_df,
                x_col=x_col,
                y_col=y_col,
                color_col=color_col if color_col != 'test_name' else None,
                title=f"{title_prefix}: {test_name}",
                use_facets=False
            )
        else:
            fig = create_empty_figure(f"Unknown chart type: {chart_type}")
        
        figures.append(fig)
    
    return figures


def create_summary_cards_data(df: pd.DataFrame) -> dict:
    """
    Calculate summary statistics for dashboard cards.
    
    Args:
        df: DataFrame with benchmark data
        
    Returns:
        Dictionary with summary statistics
    """
    if df.empty:
        return {
            'total_tests': 0,
            'unique_configs': 0,
            'pass_rate': 0,
            'avg_metric': 0
        }
    
    summary = {
        'total_tests': len(df),
        'unique_configs': df[['os_version', 'instance_type']].drop_duplicates().shape[0],
        'pass_rate': (df['status'] == 'PASS').sum() / len(df) * 100 if len(df) > 0 else 0,
        'avg_metric': df['primary_metric_value'].mean() if 'primary_metric_value' in df.columns else 0,
        'date_range': f"{df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}" if 'timestamp' in df.columns else "N/A"
    }
    
    return summary


def create_regression_heatmap(
    pct_change_df: pd.DataFrame,
    title: str = "OS Version Regressions by Benchmark",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a heatmap showing percentage changes between OS versions.

    Args:
        pct_change_df: DataFrame with test_name as index, version transitions as columns
        title: Chart title
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    if pct_change_df.empty:
        return create_empty_figure("No regression data available")

    palette = get_palette(colorblind_mode)

    # Use palette's regression heatmap scale
    colorscale = palette.regression_heatmap_scale.scale
    
    # Create hover text
    hover_text = []
    for i, row_name in enumerate(pct_change_df.index):
        hover_row = []
        for j, col_name in enumerate(pct_change_df.columns):
            val = pct_change_df.iloc[i, j]
            if pd.isna(val):
                hover_row.append("No data")
            else:
                direction = "↑" if val > 0 else "↓" if val < 0 else "→"
                hover_row.append(f"{row_name}<br>{col_name}<br>{direction} {abs(val):.1f}%")
        hover_text.append(hover_row)
    
    # Create text annotations for cells
    text_values = []
    for i, row_name in enumerate(pct_change_df.index):
        text_row = []
        for j, col_name in enumerate(pct_change_df.columns):
            val = pct_change_df.iloc[i, j]
            if pd.isna(val):
                text_row.append("")
            else:
                text_row.append(f"{val:.1f}%")
        text_values.append(text_row)
    
    fig = go.Figure(data=go.Heatmap(
        z=pct_change_df.values,
        x=pct_change_df.columns,
        y=pct_change_df.index,
        colorscale=colorscale,
        zmid=0,  # Center the color scale at 0
        text=text_values,
        hovertext=hover_text,
        hovertemplate='%{hovertext}<extra></extra>',
        texttemplate='%{text}',
        textfont={"size": 11, "color": "black"},
        colorbar=dict(
            title="% Change",
            ticksuffix="%",
            x=1.02,
            xanchor='left',
            thickness=18
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="OS Version Transition",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(400, len(pct_change_df.index) * 40),
        xaxis={'side': 'bottom'},
        yaxis={'autorange': 'reversed'},  # Top to bottom
        margin=dict(r=HEATMAP_HELP_MARGIN)
    )

    # Add help annotation explaining color scale
    # Position to right of colorbar using xshift to avoid collision
    if colorblind_mode:
        help_text = (
            "<b>How to read:</b><br>"
            "🟠 Orange = Regression (slower)<br>"
            "⚪ Gray = Stable/No change<br>"
            "🔵 Blue = Improvement (faster)"
        )
    else:
        help_text = (
            "<b>How to read:</b><br>"
            "🔴 Red = Regression (slower)<br>"
            "⚪ Gray = Stable/No change<br>"
            "🟢 Green = Improvement (faster)"
        )

    fig.add_annotation(
        text=help_text,
        xref="paper", yref="paper",
        x=1.02, y=0.5,
        xshift=100,  # Shift right by 100px to avoid colorbar collision
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=4,
        xanchor="left",
        yanchor="middle"
    )

    return fig


def _get_regression_color_and_pattern(
    percent_change: float,
    is_any_regression: bool,
    is_all_regression: bool,
    stable_threshold: float = 5.0,
    colorblind_mode: bool = False
) -> tuple:
    """
    Determine bar color and pattern based on change and consistency across runs.

    Returns a 5-color + pattern scheme:
    - Solid Dark Red/Vermillion: All runs regressed, average is negative
    - Striped Orange/Amber: Mixed results, net regression
    - Gray: Stable (within threshold)
    - Striped Amber/Blue: Mixed results, net improvement
    - Solid Green/Blue: All runs improved, average is positive

    In colorblind mode, amplifies pattern usage for redundant encoding.

    Args:
        percent_change: Average percent change across runs
        is_any_regression: True if ANY run showed regression
        is_all_regression: True if ALL runs showed regression
        stable_threshold: Threshold for stable zone (default ±5%)
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Tuple of (color hex, pattern shape or empty string)
    """
    from src.color_palettes import get_palette

    palette = get_palette(colorblind_mode)

    if percent_change is None or (isinstance(percent_change, float) and pd.isna(percent_change)):
        return palette.semantic.undefined, ''  # Neutral gray if undefined

    # Stable zone: within threshold
    if abs(percent_change) <= stable_threshold:
        return palette.semantic.stable, palette.patterns.stable

    if percent_change < 0:
        # Net regression
        if is_all_regression:
            return palette.semantic.regression, palette.patterns.regression
        else:
            return palette.semantic.mixed_regression, palette.patterns.mixed_regression
    else:
        # Net improvement
        if not is_any_regression:
            return palette.semantic.improvement, palette.patterns.improvement
        else:
            return palette.semantic.mixed_improvement, palette.patterns.mixed_improvement


def create_version_comparison_bar_chart(
    comparison_df: pd.DataFrame,
    baseline_version: str,
    comparison_version: str,
    title: Optional[str] = None,
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a bar chart comparing performance between two OS versions.

    Uses a 5-color + pattern scheme to communicate both the net result AND
    consistency across hardware configurations:
    - Solid Dark Red/Vermillion: All configs regressed
    - Striped Orange/Amber: Mixed results, net regression
    - Gray: Stable (within ±5%)
    - Striped Amber/Blue: Mixed results, net improvement
    - Solid Green/Blue: All configs improved

    Args:
        comparison_df: DataFrame with comparison data (must have columns:
                      test_name, baseline_mean, comparison_mean, percent_change, is_regression,
                      hardware_config (optional))
        baseline_version: Baseline version name
        comparison_version: Comparison version name
        title: Chart title (auto-generated if None)
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    palette = get_palette(colorblind_mode)

    if comparison_df.empty:
        return create_empty_figure("No comparison data available")

    if title is None:
        title = f"Performance Comparison: {baseline_version} vs {comparison_version}"
    
    # Check if we have multiple hardware configs per test
    has_hardware = 'hardware_config' in comparison_df.columns
    if has_hardware:
        # Group by test name and show average, but include hardware in hover
        grouped = comparison_df.groupby('test_name').agg({
            'percent_change': 'mean',
            'is_regression': ['any', 'all'],  # Track both any and all regression
            'baseline_mean': 'mean',
            'comparison_mean': 'mean'
        }).reset_index()
        
        # Flatten multi-level column names
        grouped.columns = ['test_name', 'percent_change', 'is_any_regression', 
                          'is_all_regression', 'baseline_mean', 'comparison_mean']
        
        # Count configs for labels
        config_counts = comparison_df.groupby('test_name')['hardware_config'].nunique()
        
        # Create labels that include hardware info
        test_labels = []
        for test_name in grouped['test_name']:
            hw_configs = comparison_df[comparison_df['test_name'] == test_name]['hardware_config'].unique()
            if len(hw_configs) > 1:
                test_labels.append(f"{test_name} (avg across {len(hw_configs)} configs)")
            else:
                test_labels.append(f"{test_name} ({hw_configs[0]})")
        
        grouped['test_label'] = test_labels
        comparison_df_sorted = grouped.sort_values('percent_change')
    else:
        # No hardware config info, use as-is
        comparison_df_sorted = comparison_df.sort_values('percent_change').copy()
        comparison_df_sorted['test_label'] = comparison_df_sorted['test_name']
        # For single-config case, any == all
        comparison_df_sorted['is_any_regression'] = comparison_df_sorted['is_regression']
        comparison_df_sorted['is_all_regression'] = comparison_df_sorted['is_regression']
    
    # Determine colors and patterns based on the 5-color scheme
    colors = []
    patterns = []
    for _, row in comparison_df_sorted.iterrows():
        color, pattern = _get_regression_color_and_pattern(
            row['percent_change'],
            row['is_any_regression'],
            row['is_all_regression'],
            colorblind_mode=colorblind_mode
        )
        colors.append(color)
        patterns.append(pattern)
    
    # Build hover template with consistency info
    hover_texts = []
    for idx, row in comparison_df_sorted.iterrows():
        test_name = row['test_name']
        
        # Determine consistency status for hover
        if row['is_all_regression']:
            consistency = "All configs regressed"
        elif row['is_any_regression']:
            consistency = "Mixed results (some configs regressed)"
        elif row['percent_change'] > 5:
            consistency = "All configs improved"
        else:
            consistency = "Stable across configs"
        
        if has_hardware:
            # Show all hardware configs for this test
            test_hw_data = comparison_df[comparison_df['test_name'] == test_name]
            hw_lines = []
            for _, hw_row in test_hw_data.iterrows():
                status_icon = "🔴" if hw_row['is_regression'] else "🟢" if hw_row['percent_change'] > 5 else "⚪"
                hw_lines.append(
                    f"  {status_icon} {hw_row['hardware_config']}: {hw_row['percent_change']:+.1f}% "
                    f"({hw_row['baseline_mean']:.2f} → {hw_row['comparison_mean']:.2f})"
                )
            hw_detail = "<br>".join(hw_lines)
            hover_text = (
                f"<b>{test_name}</b><br>"
                f"Average change: {row['percent_change']:+.1f}%<br>"
                f"<i>{consistency}</i><br>"
                f"<br><b>By Hardware:</b><br>{hw_detail}"
            )
        else:
            hover_text = (
                f"<b>{test_name}</b><br>"
                f"Change: {row['percent_change']:+.1f}%<br>"
                f"{baseline_version}: {row['baseline_mean']:.2f}<br>"
                f"{comparison_version}: {row['comparison_mean']:.2f}"
            )
        hover_texts.append(hover_text)

    def _fmt_bar_pct(val) -> str:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "N/A"
        return f"{val:+.1f}%"

    fig = go.Figure(data=[
        go.Bar(
            y=comparison_df_sorted['test_label'],
            x=comparison_df_sorted['percent_change'],
            orientation='h',
            marker=dict(
                color=colors,
                pattern_shape=patterns,
                pattern_fillmode='overlay',
                pattern_size=8,
                pattern_solidity=0.3,
                line=dict(width=1, color='rgba(0,0,0,0.3)')
            ),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts,
            text=comparison_df_sorted['percent_change'].apply(_fmt_bar_pct),
            textposition='outside'
        )
    ])
    
    # Add legend annotation explaining the color/pattern scheme
    # Build legend dynamically from palette
    if colorblind_mode:
        # Colorblind palette uses Vermillion and Blue
        regression_label = "Vermillion"
        improvement_label = "Blue"
    else:
        # Standard palette uses Red and Green
        regression_label = "Dark Red"
        improvement_label = "Green"

    legend_text = (
        "<b>Legend:</b><br>"
        f"■ <span style='color:{palette.semantic.regression}'>{regression_label}</span>: All configs regressed<br>"
        f"▤ <span style='color:{palette.semantic.mixed_regression}'>Orange striped</span>: Mixed, net regression<br>"
        f"■ <span style='color:{palette.semantic.stable}'>Gray</span>: Stable (±5%)<br>"
        f"▤ <span style='color:{palette.semantic.mixed_improvement}'>Amber striped</span>: Mixed, net improvement<br>"
        f"■ <span style='color:{palette.semantic.improvement}'>{improvement_label}</span>: All configs improved"
    )
    
    fig.add_annotation(
        text=legend_text,
        xref="paper", yref="paper",
        x=1.02, y=1.0,
        showarrow=False,
        font=dict(size=10),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=6,
        xanchor="left",
        yanchor="top"
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Performance Change (%)",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(400, len(comparison_df_sorted) * 30),
        showlegend=False,
        xaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'),
        margin=dict(r=250)  # Extra right margin for legend
    )
    
    return fig


def create_peer_os_comparison_chart(
    comparison_df: pd.DataFrame,
    baseline_os: str = "RHEL",
    title: str = "RHEL vs Peer Operating Systems",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a grouped bar chart comparing RHEL against peer OSes.

    Args:
        comparison_df: DataFrame with comparison data
        baseline_os: Name of baseline OS
        title: Chart title
        colorblind_mode: Use colorblind-safe colors

    Returns:
        Plotly Figure
    """
    from src.color_palettes import get_palette

    if comparison_df.empty:
        return create_empty_figure("No peer comparison data available")

    BENCHMARK_GROUPS = benchmark_groups()
    palette = get_palette(colorblind_mode)

    # Group by benchmark category
    fig = go.Figure()

    peer_os_list = sorted(comparison_df['peer_os'].unique())
    # Sort categories alphabetically but put "Other" last
    all_categories = sorted(comparison_df['benchmark_category'].unique())
    categories = [c for c in all_categories if c != 'Other'] + [c for c in all_categories if c == 'Other']

    # Create grouped bars by benchmark category
    for peer_os in peer_os_list:
        peer_data = comparison_df[comparison_df['peer_os'] == peer_os]

        y_values = []
        x_labels = []
        colors = []
        hover_texts = []

        for category in categories:
            cat_data = peer_data[peer_data['benchmark_category'] == category]
            if not cat_data.empty:
                # Average relative performance for this category
                avg_rel_perf = cat_data['relative_performance'].mean()
                y_values.append(avg_rel_perf)
                x_labels.append(category)

                # Color: competitive, moderate, or significant difference
                if avg_rel_perf >= 90 and avg_rel_perf <= 110:
                    colors.append(palette.semantic.improvement)  # Competitive
                elif avg_rel_perf >= 80 and avg_rel_perf <= 120:
                    colors.append(palette.semantic.moderate_difference)  # Moderate difference
                else:
                    colors.append(palette.semantic.regression)  # Significant difference
                
                # Build hover text with benchmark list
                benchmarks_in_category = BENCHMARK_GROUPS.get(category, ['Unknown'])
                # Also show which benchmarks actually have data in this category
                actual_tests = cat_data['test_name'].unique().tolist()
                hover_text = (
                    f"<b>{category}</b><br>"
                    f"Relative Performance: {avg_rel_perf:.1f}%<br>"
                    f"<br><b>Benchmarks in category:</b><br>"
                    f"{', '.join(benchmarks_in_category)}<br>"
                    f"<br><b>Tests with data:</b><br>"
                    f"{', '.join(actual_tests)}"
                )
                hover_texts.append(hover_text)
        
        fig.add_trace(go.Bar(
            name=peer_os,
            x=x_labels,
            y=y_values,
            text=[f"{v:.0f}%" for v in y_values],
            textposition='outside',
            marker_color=colors,
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts
        ))
    
    # Add baseline reference line at 100%
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"{baseline_os} baseline (100%)",
        annotation_position="right"
    )

    # Add competitive zone (90-110%)
    fig.add_hrect(
        y0=90, y1=110,
        fillcolor=palette.semantic.improvement,
        opacity=0.1,
        line_width=0,
        annotation_text="Competitive zone",
        annotation_position="top right"
    )
    
    # Add legend annotation explaining the color scheme
    competitive_label = "Blue" if colorblind_mode else "Green"
    significant_label = "Vermillion" if colorblind_mode else "Red"

    legend_text = (
        "<b>Color Legend:</b><br>"
        f"■ <span style='color:{palette.semantic.improvement}'>{competitive_label}</span>: Competitive (90-110%)<br>"
        f"■ <span style='color:{palette.semantic.moderate_difference}'>Amber</span>: Moderate diff (80-120%)<br>"
        f"■ <span style='color:{palette.semantic.regression}'>{significant_label}</span>: Significant diff (<80% or >120%)"
    )
    
    fig.add_annotation(
        text=legend_text,
        xref="paper", yref="paper",
        x=1.02, y=0.5,
        showarrow=False,
        font=dict(size=10),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=6,
        xanchor="left",
        yanchor="middle"
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Benchmark Category",
        yaxis_title=f"Performance Relative to {baseline_os} (%)",
        barmode='group',
        template='plotly_white',
        height=500,
        hovermode='x unified',
        legend=dict(
            title="Peer OS",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(r=250)  # Extra right margin for color legend
    )
    
    return fig


def create_cloud_scaling_chart(
    scaling_df: pd.DataFrame,
    title: str = "Performance Scaling Across Instance Sizes",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a line chart showing how performance scales with instance size.
    
    Shows scaling efficiency as a percentage of ideal linear scaling, making it
    easy to compare different benchmarks regardless of their native units.
    
    - 100% = Perfect linear scaling (performance doubles when cores double)
    - >100% = Super-linear scaling (better than expected)
    - <100% = Sub-linear scaling (diminishing returns)
    
    Uses evenly-spaced categorical X-axis for readability (not linear by CPU cores).
    
    Args:
        scaling_df: DataFrame with scaling analysis data
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if scaling_df.empty:
        return create_empty_figure("No scaling data available")
    
    fig = go.Figure()
    
    # Group by benchmark category or test name
    if 'benchmark_category' in scaling_df.columns:
        group_col = 'benchmark_category'
    else:
        group_col = 'test_name'
    
    categories = sorted(scaling_df[group_col].unique())
    x_title = "Instance Type"
    
    # Check if we have CPU cores data
    has_cpu_cores = 'cpu_cores' in scaling_df.columns and scaling_df['cpu_cores'].notna().any()
    has_memory = 'memory_gb' in scaling_df.columns and scaling_df['memory_gb'].notna().any()

    # Build ordered list of unique instances sorted by CPU cores for even spacing
    # This creates categorical X-axis labels instead of numeric
    if has_cpu_cores and 'instance_type' in scaling_df.columns:
        # Get unique instances sorted by CPU cores
        # Only include memory_gb column if it exists
        columns_to_select = ['instance_type', 'cpu_cores']
        if has_memory:
            columns_to_select.append('memory_gb')
        instance_order_df = scaling_df[columns_to_select].drop_duplicates()
        # Drop rows with null cpu_cores to prevent int() cast errors
        instance_order_df = instance_order_df.dropna(subset=['cpu_cores'])
        instance_order_df = instance_order_df.sort_values('cpu_cores')
        
        # Create tick labels with instance name, cores, and RAM
        tick_labels = []
        for _, row in instance_order_df.iterrows():
            inst_name = row['instance_type']
            cores = int(row['cpu_cores'])
            memory = row.get('memory_gb', None)
            if memory is not None and pd.notna(memory):
                label = f"{inst_name}<br>{cores} vCPU, {int(memory)} GB"
            else:
                label = f"{inst_name}<br>{cores} vCPU"
            tick_labels.append(label)
        
        # Map instance types to their index position (0, 1, 2, ...) for even spacing
        instance_to_index = {row['instance_type']: i for i, (_, row) in enumerate(instance_order_df.iterrows())}
        cores_list = instance_order_df['cpu_cores'].tolist()
    else:
        instance_to_index = {}
        tick_labels = []
        cores_list = []
    
    # Track all efficiency values for dynamic y-axis range
    all_efficiency_values = []
    
    for category in categories:
        cat_data = scaling_df[scaling_df[group_col] == category].copy()
        
        # Aggregate multiple test results per instance within each category
        # This prevents multiple data points per instance causing confusing zigzag lines
        if has_cpu_cores and 'instance_type' in cat_data.columns:
            # Group by instance_type and aggregate performance values
            agg_dict = {
                'mean_performance': 'mean',  # Average across tests in this category
                'cpu_cores': 'first',
            }
            # Only aggregate memory_gb if the column exists
            if has_memory:
                agg_dict['memory_gb'] = 'first'
            agg_data = cat_data.groupby('instance_type').agg(agg_dict).reset_index()
            agg_data = agg_data.sort_values('cpu_cores')
            
            x_values = [instance_to_index.get(inst, 0) for inst in agg_data['instance_type']]
            cores_values = agg_data['cpu_cores'].tolist()
            instance_types = agg_data['instance_type'].tolist()
            memory_values = agg_data['memory_gb'].tolist() if has_memory else [None] * len(agg_data)
            perf_values = agg_data['mean_performance'].tolist()
        else:
            # Fallback for non-CPU-cores case
            if 'instance_type' in cat_data.columns:
                agg_data = cat_data.groupby('instance_type').agg({
                    'mean_performance': 'mean'
                }).reset_index()
                agg_data = agg_data.sort_values('instance_type')
            else:
                agg_data = cat_data
            
            x_values = list(range(len(agg_data)))
            cores_values = [None] * len(agg_data)
            instance_types = agg_data['instance_type'].tolist() if 'instance_type' in agg_data.columns else []
            memory_values = agg_data['memory_gb'].tolist() if 'memory_gb' in agg_data.columns else []
            perf_values = agg_data['mean_performance'].tolist() if 'mean_performance' in agg_data.columns else []
        
        # Skip if no performance data
        if not perf_values:
            continue
        
        # Calculate scaling efficiency as percentage of ideal linear scaling
        if has_cpu_cores and len(cores_values) > 0 and len(perf_values) > 0:
            baseline_perf = perf_values[0]
            baseline_cores = cores_values[0]

            if (pd.notna(baseline_cores) and baseline_cores > 0 and
                pd.notna(baseline_perf) and baseline_perf > 0):
                # Calculate efficiency: (actual / expected) * 100
                # Expected = baseline_perf * (current_cores / baseline_cores)
                efficiency_values = []
                hover_texts = []
                
                for i, (perf, cores) in enumerate(zip(perf_values, cores_values)):
                    if pd.notna(cores) and cores > 0:
                        expected_perf = baseline_perf * (cores / baseline_cores)
                        efficiency = (perf / expected_perf) * 100
                        efficiency_values.append(efficiency)
                        
                        # Get instance info for hover
                        inst_name = instance_types[i] if i < len(instance_types) else "Unknown"
                        mem_gb = memory_values[i] if i < len(memory_values) else None
                        mem_str = f"<br>Memory: {mem_gb:.0f} GB" if mem_gb is not None and pd.notna(mem_gb) else ""
                        
                        # Create detailed hover text
                        hover_texts.append(
                            f"<b>{category}</b><br>"
                            f"Instance: {inst_name}<br>"
                            f"CPU Cores: {int(cores)}{mem_str}<br>"
                            f"Scaling Efficiency: {efficiency:.1f}%<br>"
                            f"Raw Performance: {perf:,.0f}<br>"
                            f"Expected (linear): {expected_perf:,.0f}"
                        )
                    else:
                        efficiency_values.append(None)
                        hover_texts.append("")
                
                y_values = efficiency_values
                # Track for dynamic y-axis range
                all_efficiency_values.extend([v for v in efficiency_values if v is not None])
            else:
                # Fallback to raw values if baseline is invalid
                y_values = perf_values
                hover_texts = [f"{category}: {v:,.0f}" for v in perf_values]
        else:
            # For non-CPU-cores case, normalize to first value = 100%
            if len(perf_values) > 0 and perf_values[0] > 0:
                baseline = perf_values[0]
                y_values = [(v / baseline) * 100 for v in perf_values]
                hover_texts = [
                    f"<b>{category}</b><br>"
                    f"Instance: {inst}<br>"
                    f"Relative Performance: {(v/baseline)*100:.1f}%<br>"
                    f"Raw Value: {v:,.0f}"
                    for inst, v in zip(instance_types, perf_values)
                ]
                # Track for dynamic y-axis range
                all_efficiency_values.extend(y_values)
            else:
                y_values = perf_values
                hover_texts = [f"{category}: {v:,.0f}" for v in perf_values]
        
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='lines+markers',
            name=category,
            line=dict(width=3),
            marker=dict(size=10),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts
        ))
    
    # Add ideal linear scaling reference line at 100%
    if has_cpu_cores and len(instance_to_index) > 0:
        # Span the full width of the categorical axis
        fig.add_trace(go.Scatter(
            x=[0, len(instance_to_index) - 1],
            y=[100, 100],
            mode='lines',
            name='Ideal Linear (100%)',
            line=dict(dash='dash', color='rgba(100, 100, 100, 0.7)', width=2),
            showlegend=True,
            hoverinfo='skip'
        ))
        
        # Add shaded regions for context
        fig.add_hrect(
            y0=85, y1=115,
            fillcolor="rgba(76, 175, 80, 0.1)",
            line_width=0,
            annotation_text="Good scaling (85-115%)",
            annotation_position="top right",
            annotation=dict(font_size=10, font_color="rgba(76, 175, 80, 0.8)")
        )
    
    # Add annotation explaining the metric
    fig.add_annotation(
        text=(
            "<b>How to read this chart:</b><br>"
            "100% = ideal linear scaling<br>"
            ">100% = super-linear (great!)<br>"
            "<100% = diminishing returns"
        ),
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=4
    )
    
    # Configure evenly-spaced categorical X-axis with instance labels
    if tick_labels:
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(len(tick_labels))),
                ticktext=tick_labels,
                tickangle=45,
                tickfont=dict(size=9)
            )
        )
    
    # Calculate dynamic y-axis range based on actual data
    if all_efficiency_values:
        max_efficiency = max(all_efficiency_values)
        min_efficiency = min(all_efficiency_values)
        # Add 10% padding and ensure we show at least 0-120%
        y_max = max(120, max_efficiency * 1.1)
        y_min = min(0, min_efficiency * 0.9)
    else:
        y_max = 150
        y_min = 0
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="Scaling Efficiency (% of ideal linear)",
        template='plotly_white',
        height=600,  # Increased height for rotated labels
        hovermode='x unified',
        legend=dict(
            title="Benchmark Category",
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.9)"
        ),
        yaxis=dict(
            ticksuffix="%",
            range=[y_min, y_max]  # Dynamic range based on actual data
        ),
        margin=dict(b=120)  # Extra bottom margin for rotated labels
    )
    
    return fig


def create_investigation_detail_chart(
    baseline_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    test_name: str,
    baseline_label: str,
    comparison_label: str,
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a detailed comparison chart for investigation drill-down.
    
    Args:
        baseline_df: DataFrame with baseline data
        comparison_df: DataFrame with comparison data
        test_name: Name of the test being investigated
        baseline_label: Label for baseline data
        comparison_label: Label for comparison data
        
    Returns:
        Plotly Figure with side-by-side box plots
    """
    fig = go.Figure()
    
    # Baseline box plot
    if not baseline_df.empty and 'primary_metric_value' in baseline_df.columns:
        fig.add_trace(go.Box(
            y=baseline_df['primary_metric_value'],
            name=baseline_label,
            marker_color='lightblue',
            boxmean='sd'
        ))
    
    # Comparison box plot
    if not comparison_df.empty and 'primary_metric_value' in comparison_df.columns:
        fig.add_trace(go.Box(
            y=comparison_df['primary_metric_value'],
            name=comparison_label,
            marker_color='lightcoral',
            boxmean='sd'
        ))
    
    fig.update_layout(
        title=f"Performance Distribution: {test_name}",
        yaxis_title="Performance Metric",
        template='plotly_white',
        height=400,
        showlegend=True
    )
    
    return fig


def create_category_benchmark_detail_chart(
    comparison_df: pd.DataFrame,
    category: str,
    baseline_os: str = "RHEL",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a horizontal bar chart showing individual benchmark performance within a category.

    Args:
        comparison_df: DataFrame with comparison data (filtered to single category)
        category: The benchmark category name
        baseline_os: Name of baseline OS
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure with horizontal bars for each benchmark
    """
    from src.color_palettes import get_palette

    if comparison_df.empty:
        return create_empty_figure(f"No benchmark data available for {category}")

    palette = get_palette(colorblind_mode)

    # Group by test_name and calculate average relative performance across hardware
    benchmark_summary = comparison_df.groupby('test_name').agg({
        'relative_performance': 'mean',
        'instance_type': 'nunique',
        'is_competitive': 'mean'  # Percentage of hardware where competitive
    }).reset_index()

    benchmark_summary = benchmark_summary.sort_values('relative_performance', ascending=True)

    # Determine colors based on performance
    colors = []
    for perf in benchmark_summary['relative_performance']:
        if perf >= 90 and perf <= 110:
            colors.append(palette.semantic.improvement)  # Competitive
        elif perf >= 80 and perf <= 120:
            colors.append(palette.semantic.moderate_difference)  # Moderate
        else:
            colors.append(palette.semantic.regression)  # Significant difference
    
    # Create hover text
    hover_texts = []
    for _, row in benchmark_summary.iterrows():
        competitive_pct = row['is_competitive'] * 100
        hover_texts.append(
            f"<b>{row['test_name']}</b><br>"
            f"Relative Performance: {row['relative_performance']:.1f}%<br>"
            f"Hardware Configs Tested: {int(row['instance_type'])}<br>"
            f"Competitive on {competitive_pct:.0f}% of hardware"
        )
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=benchmark_summary['test_name'],
        x=benchmark_summary['relative_performance'],
        orientation='h',
        marker_color=colors,
        text=[f"{v:.1f}%" for v in benchmark_summary['relative_performance']],
        textposition='outside',
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts
    ))
    
    # Add baseline reference line at 100%
    fig.add_vline(
        x=100,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"{baseline_os} baseline",
        annotation_position="top"
    )

    # Add competitive zone (90-110%)
    fig.add_vrect(
        x0=90, x1=110,
        fillcolor=palette.semantic.improvement,
        opacity=0.1,
        line_width=0
    )
    
    fig.update_layout(
        title=f"{category} Benchmarks - Detailed Performance",
        xaxis_title=f"Performance Relative to {baseline_os} (%)",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(250, len(benchmark_summary) * 50 + 100),  # Dynamic height
        margin=dict(l=150, r=50, t=50, b=50),
        xaxis=dict(range=[min(50, benchmark_summary['relative_performance'].min() - 10), 
                          max(150, benchmark_summary['relative_performance'].max() + 10)])
    )
    
    return fig


def create_category_hardware_heatmap(
    comparison_df: pd.DataFrame,
    category: str,
    baseline_os: str = "RHEL",
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create a heatmap showing benchmark × hardware performance matrix.

    Args:
        comparison_df: DataFrame with comparison data (filtered to single category)
        category: The benchmark category name
        baseline_os: Name of baseline OS
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure with heatmap
    """
    from src.color_palettes import get_palette

    if comparison_df.empty:
        return create_empty_figure(f"No hardware data available for {category}")

    palette = get_palette(colorblind_mode)

    # Pivot to create benchmark × hardware matrix
    pivot_df = comparison_df.pivot_table(
        index='test_name',
        columns='instance_type',
        values='relative_performance',
        aggfunc='mean'
    )

    if pivot_df.empty:
        return create_empty_figure(f"Insufficient data for hardware breakdown")

    # Create custom hover text
    hover_text = []
    for test in pivot_df.index:
        row_text = []
        for hw in pivot_df.columns:
            val = pivot_df.loc[test, hw]
            if pd.notna(val):
                status = "✓ Competitive" if 90 <= val <= 110 else ("⚠ Moderate" if 80 <= val <= 120 else "✗ Significant diff")
                row_text.append(f"<b>{test}</b><br>Hardware: {hw}<br>Relative Perf: {val:.1f}%<br>{status}")
            else:
                row_text.append(f"<b>{test}</b><br>Hardware: {hw}<br>No data")
        hover_text.append(row_text)

    # Use colorblind-safe colorscale from palette
    colorscale = palette.hardware_heatmap_scale.scale
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale=colorscale,
        zmid=100,  # Center on 100%
        zmin=70,
        zmax=130,
        text=[[f"{v:.0f}%" if pd.notna(v) else "-" for v in row] for row in pivot_df.values],
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_text,
        colorbar=dict(
            title="Relative<br>Performance",
            ticksuffix="%"
        )
    ))
    
    fig.update_layout(
        title=f"{category} - Performance by Hardware",
        xaxis_title="Instance Type",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(300, len(pivot_df) * 40 + 150),
        margin=dict(l=150, r=100, t=50, b=100),
        xaxis=dict(tickangle=45)
    )
    
    return fig

