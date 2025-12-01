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
    title: str = "Performance Trends Over Time"
) -> go.Figure:
    """
    Create a time series line chart.
    
    Args:
        df: DataFrame with time series data
        x_col: Column for x-axis (timestamp)
        y_col: Column for y-axis (metric values)
        color_col: Column to use for line colors
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No time series data available")
    
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
    title: str = "Performance Heatmap"
) -> go.Figure:
    """
    Create a heatmap for regression analysis.
    
    Args:
        df: DataFrame with benchmark data
        row_dim: Dimension for rows
        col_dim: Dimension for columns
        value_col: Column containing values for heatmap
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for heatmap")
    
    # Create pivot table
    pivot = df.pivot_table(
        values=value_col,
        index=row_dim,
        columns=col_dim,
        aggfunc='mean'
    )
    
    if pivot.empty:
        return create_empty_figure("Insufficient data for heatmap")
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale='RdYlGn',
        text=pivot.values.round(0),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Metric Value")
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
    title: str = "Performance Distribution"
) -> go.Figure:
    """
    Create a box plot showing distribution of performance metrics.
    
    Args:
        df: DataFrame with benchmark data
        x_col: Column for x-axis categories
        y_col: Column for y-axis values
        color_col: Optional column for color grouping
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for distribution plot")
    
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

