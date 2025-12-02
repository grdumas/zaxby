"""
Visualization components for the dashboard.

Provides Plotly-based visualizations for benchmark data.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List


def create_comparison_chart(
    df: pd.DataFrame,
    group_by: str = 'test_name',
    title: str = "Performance Comparison"
) -> go.Figure:
    """
    Create a side-by-side bar chart for comparing configurations.
    
    Args:
        df: DataFrame with comparison data (must have baseline_mean, comparison_mean)
        group_by: Column used for grouping
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for comparison")
    
    fig = go.Figure()
    
    # Baseline bars
    fig.add_trace(go.Bar(
        x=df[group_by],
        y=df['baseline_mean'],
        name='Baseline',
        marker_color='lightblue',
        error_y=dict(type='data', array=df['baseline_std']) if 'baseline_std' in df.columns else None
    ))
    
    # Comparison bars
    fig.add_trace(go.Bar(
        x=df[group_by],
        y=df['comparison_mean'],
        name='Comparison',
        marker_color='lightcoral',
        error_y=dict(type='data', array=df['comparison_std']) if 'comparison_std' in df.columns else None
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=group_by.replace('_', ' ').title(),
        yaxis_title="Performance Metric",
        barmode='group',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    return fig


def create_time_series_chart(
    df: pd.DataFrame,
    x_col: str = 'timestamp',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = 'test_name',
    title: str = "Performance Trends Over Time",
    use_facets: bool = False
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
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No time series data available")
    
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
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Performance Metric",
            hovermode='x unified',
            height=500
        )
    
    fig.update_traces(mode='lines+markers')
    
    return fig


def create_heatmap(
    df: pd.DataFrame,
    row_dim: str = 'os_version',
    col_dim: str = 'instance_type',
    value_col: str = 'primary_metric_value',
    title: str = "Performance Heatmap",
    normalize_by_test: bool = True
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
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for heatmap")
    
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
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale='RdYlGn',
        text=pivot.values.round(1),
        hovertext=hover_text,
        hovertemplate='%{y} × %{x}<br>%{hovertext}<extra></extra>',
        texttemplate='%{text}' + text_suffix,
        textfont={"size": 10},
        colorbar=dict(title=colorbar_title)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=col_dim.replace('_', ' ').title(),
        yaxis_title=row_dim.replace('_', ' ').title(),
        template='plotly_white',
        height=500
    )
    
    return fig


def create_box_plot(
    df: pd.DataFrame,
    x_col: str = 'test_name',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = None,
    title: str = "Performance Distribution",
    use_facets: bool = False
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
        
        fig.update_layout(
            height=500,
            showlegend=True
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
    title: str = "Performance Scatter Plot"
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
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for scatter plot")
    
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
    
    fig.update_layout(
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title=y_col.replace('_', ' ').title(),
        height=500
    )
    
    return fig


def create_performance_delta_chart(
    df: pd.DataFrame,
    x_col: str = 'test_name',
    title: str = "Performance Change (%)"
) -> go.Figure:
    """
    Create a bar chart showing percentage changes with color coding.
    
    Args:
        df: DataFrame with percent_change column
        x_col: Column for x-axis labels
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty or 'percent_change' not in df.columns:
        return create_empty_figure("No comparison data available")
    
    # Color bars based on change direction
    colors = ['red' if x < -10 else 'green' if x > 10 else 'gray' 
              for x in df['percent_change']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=df[x_col],
            y=df['percent_change'],
            marker_color=colors,
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
    
    # Add zones
    fig.add_hrect(y0=-10, y1=10, fillcolor="gray", opacity=0.1, line_width=0)
    
    return fig


def create_metrics_table(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    title: str = "Detailed Metrics"
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
    title: str = "OS Version Regressions by Benchmark"
) -> go.Figure:
    """
    Create a heatmap showing percentage changes between OS versions.
    
    Args:
        pct_change_df: DataFrame with test_name as index, version transitions as columns
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if pct_change_df.empty:
        return create_empty_figure("No regression data available")
    
    # Define color scale: red for regressions, green for improvements, gray for stable
    colorscale = [
        [0.0, '#d73027'],    # Strong regression (red)
        [0.4, '#fee090'],    # Mild regression (yellow)
        [0.5, '#e0e0e0'],    # Stable (gray)
        [0.6, '#e0f3db'],    # Mild improvement (light green)
        [1.0, '#1a9850']     # Strong improvement (green)
    ]
    
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
            ticksuffix="%"
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="OS Version Transition",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(400, len(pct_change_df.index) * 40),
        xaxis={'side': 'bottom'},
        yaxis={'autorange': 'reversed'}  # Top to bottom
    )
    
    return fig


def create_version_comparison_bar_chart(
    comparison_df: pd.DataFrame,
    baseline_version: str,
    comparison_version: str,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a bar chart comparing performance between two OS versions.
    
    Args:
        comparison_df: DataFrame with comparison data (must have columns:
                      test_name, baseline_mean, comparison_mean, percent_change, is_regression,
                      hardware_config (optional))
        baseline_version: Baseline version name
        comparison_version: Comparison version name
        title: Chart title (auto-generated if None)
        
    Returns:
        Plotly Figure
    """
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
            'is_regression': 'any',  # If any hardware config shows regression
            'baseline_mean': 'mean',
            'comparison_mean': 'mean'
        }).reset_index()
        
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
        comparison_df_sorted = comparison_df.sort_values('percent_change')
        comparison_df_sorted['test_label'] = comparison_df_sorted['test_name']
    
    # Color bars based on regression status
    colors = ['#d73027' if is_reg else '#1a9850' if pct > 5 else '#e0e0e0' 
              for is_reg, pct in zip(comparison_df_sorted['is_regression'], 
                                     comparison_df_sorted['percent_change'])]
    
    # Build hover template
    hover_texts = []
    for idx, row in comparison_df_sorted.iterrows():
        test_name = row['test_name']
        if has_hardware:
            # Show all hardware configs for this test
            test_hw_data = comparison_df[comparison_df['test_name'] == test_name]
            hw_lines = []
            for _, hw_row in test_hw_data.iterrows():
                hw_lines.append(
                    f"  {hw_row['hardware_config']}: {hw_row['percent_change']:+.1f}% "
                    f"({hw_row['baseline_mean']:.2f} → {hw_row['comparison_mean']:.2f})"
                )
            hw_detail = "<br>".join(hw_lines)
            hover_text = (
                f"<b>{test_name}</b><br>"
                f"Average change: {row['percent_change']:+.1f}%<br>"
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
    
    fig = go.Figure(data=[
        go.Bar(
            y=comparison_df_sorted['test_label'],
            x=comparison_df_sorted['percent_change'],
            orientation='h',
            marker=dict(color=colors),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts,
            text=comparison_df_sorted['percent_change'].apply(lambda x: f'{x:+.1f}%'),
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="Performance Change (%)",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(400, len(comparison_df_sorted) * 30),
        showlegend=False,
        xaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black')
    )
    
    return fig


def create_peer_os_comparison_chart(
    comparison_df: pd.DataFrame,
    baseline_os: str = "RHEL",
    title: str = "RHEL vs Peer Operating Systems"
) -> go.Figure:
    """
    Create a grouped bar chart comparing RHEL against peer OSes.
    
    Args:
        comparison_df: DataFrame with comparison data
        baseline_os: Name of baseline OS
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if comparison_df.empty:
        return create_empty_figure("No peer comparison data available")
    
    # Benchmark category to benchmarks mapping (for hover tooltips)
    # This should match BENCHMARK_GROUPS in data_processing.py
    BENCHMARK_GROUPS = {
        'Networking': ['uperf'],
        'Storage/IO': ['fio'],
        'HPC/Compute': ['streams', 'specjbb', 'auto_hpl'],
        'System': ['sysbench', 'coremark_pro', 'pig', 'coremark', 'phoronix', 'passmark']
    }
    
    # Group by benchmark category
    fig = go.Figure()
    
    peer_os_list = sorted(comparison_df['peer_os'].unique())
    categories = sorted(comparison_df['benchmark_category'].unique())
    
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
                
                # Color: green if within 10%, yellow if within 20%, red otherwise
                if avg_rel_perf >= 90 and avg_rel_perf <= 110:
                    colors.append('#1a9850')  # Green - competitive
                elif avg_rel_perf >= 80 and avg_rel_perf <= 120:
                    colors.append('#fee090')  # Yellow - moderate difference
                else:
                    colors.append('#d73027')  # Red - significant difference
                
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
        fillcolor="green",
        opacity=0.1,
        line_width=0,
        annotation_text="Competitive zone",
        annotation_position="top right"
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
        )
    )
    
    return fig


def create_cloud_scaling_chart(
    scaling_df: pd.DataFrame,
    title: str = "Performance Scaling Across Instance Sizes"
) -> go.Figure:
    """
    Create a line chart showing how performance scales with instance size.
    
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
    
    for category in categories:
        cat_data = scaling_df[scaling_df[group_col] == category]
        
        # Sort by CPU cores or instance type
        if 'cpu_cores' in cat_data.columns and cat_data['cpu_cores'].notna().any():
            cat_data = cat_data.sort_values('cpu_cores')
            x_values = cat_data['cpu_cores']
            x_title = "CPU Cores"
        else:
            cat_data = cat_data.sort_values('instance_type')
            x_values = cat_data['instance_type']
            x_title = "Instance Type"
        
        # Average performance if multiple tests per category
        if 'mean_performance' in cat_data.columns:
            y_values = cat_data['mean_performance']
        else:
            y_values = cat_data.groupby(x_title)['mean_performance'].mean()
        
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='lines+markers',
            name=category,
            line=dict(width=3),
            marker=dict(size=10)
        ))
    
    # Add ideal linear scaling line if we have CPU cores
    if 'cpu_cores' in scaling_df.columns and scaling_df['cpu_cores'].notna().any():
        min_cores = scaling_df['cpu_cores'].min()
        max_cores = scaling_df['cpu_cores'].max()
        
        # Use first category's first point as baseline
        if not scaling_df.empty:
            first_cat = categories[0]
            first_data = scaling_df[scaling_df[group_col] == first_cat].sort_values('cpu_cores')
            if not first_data.empty:
                baseline_perf = first_data.iloc[0]['mean_performance']
                baseline_cores = first_data.iloc[0]['cpu_cores']
                
                if baseline_cores and baseline_cores > 0:
                    ideal_x = [min_cores, max_cores]
                    ideal_y = [
                        baseline_perf * (min_cores / baseline_cores),
                        baseline_perf * (max_cores / baseline_cores)
                    ]
                    
                    fig.add_trace(go.Scatter(
                        x=ideal_x,
                        y=ideal_y,
                        mode='lines',
                        name='Ideal Linear Scaling',
                        line=dict(dash='dash', color='gray', width=2),
                        showlegend=True
                    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title if 'cpu_cores' in scaling_df.columns else "Instance Type",
        yaxis_title="Performance (mean metric value)",
        template='plotly_white',
        height=500,
        hovermode='x unified',
        legend=dict(
            title="Benchmark",
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )
    
    return fig


def create_investigation_detail_chart(
    baseline_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    test_name: str,
    baseline_label: str,
    comparison_label: str
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

