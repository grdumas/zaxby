"""
Nightly Runs UI component for the dashboard.

Provides a dedicated section showing recent nightly benchmark runs with
summary cards, run selector dropdown, and category breakdown visualization.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from src.query_service import NightlyRunSnapshot


def create_nightly_runs_section(
    runs: List[NightlyRunSnapshot],
    selected_timestamp: Optional[datetime] = None,
) -> dbc.Card:
    """
    Create the Recent Nightly Runs collapsible section.

    Args:
        runs: List of NightlyRunSnapshot objects
        selected_timestamp: Currently selected run timestamp

    Returns:
        dbc.Card with section UI
    """
    if not runs:
        return _create_empty_section()

    # Select first run if none specified
    if selected_timestamp is None and runs:
        selected_run = runs[0]
    else:
        # Find matching run or default to first
        selected_run = runs[0]
        if selected_timestamp:
            for run in runs:
                if run.timestamp == selected_timestamp:
                    selected_run = run
                    break

    summary_cards = create_nightly_run_summary_cards(selected_run)
    dropdown = create_nightly_run_selector_dropdown(runs, selected_timestamp)
    chart = dcc.Graph(
        id="nightly-run-chart",
        figure=create_nightly_run_category_chart(selected_run),
        config={"displayModeBar": False},
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                dbc.Button(
                    [
                        html.I(id="icon-nightly-runs", className="bi bi-chevron-down me-2"),
                        html.Span("Recent Nightly Runs", style={"fontSize": "1.25rem", "fontWeight": "500"}),
                    ],
                    id="btn-toggle-nightly-runs",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#7c3aed", "fontWeight": "600"},
                ),
                style={
                    "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                    "borderBottom": "3px solid #7c3aed",
                    "padding": "0",
                },
            ),
            dbc.Collapse(
                dbc.CardBody(
                    [
                        summary_cards,
                        html.Hr(className="my-3"),
                        html.Label("Select Nightly Run:", className="form-label text-muted small"),
                        dropdown,
                        html.Hr(className="my-3"),
                        chart,
                    ],
                    className="p-4",
                ),
                id="collapse-nightly-runs",
                is_open=True,  # Open by default
            ),
        ],
        className="mb-4",
        style={"borderLeft": "5px solid #7c3aed"},
    )


def _create_empty_section() -> dbc.Card:
    """Create section for empty state (no nightly runs available)."""
    return dbc.Card(
        [
            dbc.CardHeader(
                dbc.Button(
                    [
                        html.I(id="icon-nightly-runs", className="bi bi-chevron-down me-2"),
                        html.Span("Recent Nightly Runs", style={"fontSize": "1.25rem", "fontWeight": "500"}),
                    ],
                    id="btn-toggle-nightly-runs",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#7c3aed", "fontWeight": "600"},
                ),
                style={
                    "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                    "borderBottom": "3px solid #7c3aed",
                    "padding": "0",
                },
            ),
            dbc.Collapse(
                dbc.CardBody(
                    html.Div(
                        [
                            html.P(
                                "No nightly runs found in the selected date range.",
                                className="text-muted mb-2",
                            ),
                            html.P(
                                "Try expanding the date range or adjusting filters.",
                                className="text-muted small mb-0",
                            ),
                        ],
                        className="alert alert-info",
                    ),
                    className="p-4",
                ),
                id="collapse-nightly-runs",
                is_open=True,
            ),
        ],
        className="mb-4",
        style={"borderLeft": "5px solid #7c3aed"},
    )


def create_nightly_run_summary_cards(run: NightlyRunSnapshot) -> dbc.Row:
    """
    Create KPI summary cards showing latest run metrics.

    Args:
        run: NightlyRunSnapshot for the selected run

    Returns:
        dbc.Row with three KPI cards
    """
    if run.error:
        return dbc.Row(
            dbc.Col(
                html.Div(
                    f"Error loading nightly run data: {run.error}",
                    className="alert alert-warning",
                )
            )
        )

    # Format timestamp
    timestamp_str = run.timestamp.strftime("%Y-%m-%d %H:%M UTC")

    # Calculate pass rate
    pass_rate = 0.0
    if run.test_count > 0:
        pass_rate = (run.pass_count / run.test_count) * 100

    # Determine pass rate color
    if pass_rate >= 95:
        pass_rate_color = "text-success"
    elif pass_rate >= 80:
        pass_rate_color = "text-warning"
    else:
        pass_rate_color = "text-danger"

    return dbc.Row(
        [
            # Latest Run timestamp card
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Latest Run", className="text-muted small mb-1"),
                            html.H5(timestamp_str, className="mb-0"),
                        ],
                    ),
                    className="h-100 border-purple",
                    style={"borderColor": "#c4b5fd"},
                ),
                md=4,
                className="mb-3 mb-md-0",
            ),
            # Total Tests card
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Total Tests", className="text-muted small mb-1"),
                            html.H5(f"{run.test_count:,}", className="mb-0 text-primary"),
                            html.P(
                                [
                                    html.Span(f"{run.pass_count} passed", className="text-success small me-2"),
                                    html.Span(f"{run.fail_count} failed", className="text-danger small"),
                                ],
                                className="mb-0 mt-2",
                            ),
                        ],
                    ),
                    className="h-100 border-purple",
                    style={"borderColor": "#c4b5fd"},
                ),
                md=4,
                className="mb-3 mb-md-0",
            ),
            # Pass Rate card
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Pass Rate", className="text-muted small mb-1"),
                            html.H5(f"{pass_rate:.1f}%", className=f"mb-0 {pass_rate_color}"),
                        ],
                    ),
                    className="h-100 border-purple",
                    style={"borderColor": "#c4b5fd"},
                ),
                md=4,
            ),
        ],
        className="g-3",
    )


def create_nightly_run_selector_dropdown(
    runs: List[NightlyRunSnapshot],
    selected_timestamp: Optional[datetime] = None,
) -> dcc.Dropdown:
    """
    Create dropdown to select which nightly run to view.

    Args:
        runs: List of NightlyRunSnapshot objects
        selected_timestamp: Currently selected timestamp

    Returns:
        dcc.Dropdown component
    """
    if not runs:
        return dcc.Dropdown(
            id="nightly-run-selector",
            options=[],
            placeholder="No runs available",
            disabled=True,
        )

    options = []
    for run in runs:
        label = f"{run.timestamp.strftime('%Y-%m-%d %H:%M UTC')} ({run.test_count} tests)"
        options.append({
            "label": label,
            "value": run.timestamp.isoformat(),
        })

    value = None
    if selected_timestamp:
        value = selected_timestamp.isoformat()
    elif runs:
        value = runs[0].timestamp.isoformat()

    return dcc.Dropdown(
        id="nightly-run-selector",
        options=options,
        value=value,
        clearable=False,
        className="mb-3",
    )


def create_nightly_run_category_chart(run: NightlyRunSnapshot) -> go.Figure:
    """
    Create horizontal bar chart showing test counts by category.

    Args:
        run: NightlyRunSnapshot to visualize

    Returns:
        Plotly Figure
    """
    if run.error:
        return _empty_figure(
            "Category Breakdown",
            f"Error: {run.error}",
        )

    if not run.category_breakdown:
        return _empty_figure(
            "Category Breakdown",
            "No category data available",
        )

    # Extract labels and counts
    labels = [cat for cat, _ in run.category_breakdown]
    counts = [count for _, count in run.category_breakdown]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker=dict(color="#7c3aed"),
            hovertemplate="%{y}<br>Tests: %{x:,}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="Category Breakdown",
            font=dict(size=14),
        ),
        template="plotly_white",
        height=300,
        margin=dict(l=140, r=20, t=50, b=40),
        xaxis=dict(title="Test Count"),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )

    return fig


def _empty_figure(title: str, message: str) -> go.Figure:
    """Create empty figure with message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=13, color="#64748b"),
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        template="plotly_white",
        height=300,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
