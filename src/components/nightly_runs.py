"""
Nightly runs UI component for Recent Nightly Runs section (RPOPC-1207).

Provides collapsible section with summary cards showing latest nightly run metrics.
"""

from typing import List, Optional

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from src.query_service import NightlyRunSnapshot
from src.components.visualizations import _escape_html


def create_nightly_run_selector_dropdown(runs: List[NightlyRunSnapshot]) -> dcc.Dropdown:
    """
    Create dropdown selector for choosing which nightly run to visualize.

    Dropdown options show run date/time and test count. Most recent run is selected by default.

    Args:
        runs: List of NightlyRunSnapshot objects (sorted descending by timestamp).

    Returns:
        Dash Dropdown component.
    """
    if not runs:
        return dcc.Dropdown(
            id="nightly-run-selector",
            options=[],
            value=None,
            placeholder="No runs available",
            disabled=True,
            className="mb-3"
        )

    options = []
    for idx, run in enumerate(runs):
        label = f"{run.timestamp.strftime('%Y-%m-%d %H:%M UTC')} ({run.test_count} tests)"
        options.append({"label": label, "value": idx})

    return dcc.Dropdown(
        id="nightly-run-selector",
        options=options,
        value=0 if options else None,
        placeholder="Select a nightly run",
        className="mb-3"
    )


def create_nightly_run_category_chart(
    run: Optional[NightlyRunSnapshot],
    colorblind_mode: bool = False
) -> go.Figure:
    """
    Create horizontal bar chart showing test counts by benchmark category.

    Args:
        run: NightlyRunSnapshot object with category breakdown.
        colorblind_mode: If True, use colorblind-safe palette

    Returns:
        Plotly Figure with horizontal bar chart.
    """
    from src.color_palettes import get_palette

    palette = get_palette(colorblind_mode)
    if run is None or not run.category_breakdown:
        fig = go.Figure()
        fig.add_annotation(
            text="No category data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="#64748b"),
        )
        fig.update_layout(
            title="Category Breakdown",
            template="plotly_white",
            height=280,
            margin=dict(l=140, r=20, t=50, b=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    # Extract categories and counts
    categories = [cat for cat, _ in run.category_breakdown]
    counts = [count for _, count in run.category_breakdown]

    # Escape category labels to prevent XSS injection in hover tooltips and axis labels
    escaped_categories = [_escape_html(cat) for cat in categories]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=escaped_categories,  # Use escaped labels for y-axis
            orientation="h",
            marker=dict(color=palette.branding.nightly),
            hovertemplate="%{y}<br>Tests: %{x:,}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text="Category Breakdown", font=dict(size=14)),
        template="plotly_white",
        height=280,
        margin=dict(l=140, r=20, t=50, b=40),
        xaxis=dict(title="Test Count"),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )

    return fig


def create_nightly_run_summary_cards(runs: List[NightlyRunSnapshot]) -> html.Div:
    """
    Create KPI summary cards for the most recent nightly run.

    Displays three cards: Latest Run timestamp, Total Tests, and Pass Rate.

    Args:
        runs: List of NightlyRunSnapshot objects (assumes sorted descending by timestamp).

    Returns:
        Div containing three KPI cards in a row.
    """
    if not runs:
        return html.Div(
            html.P("No nightly runs available", className="text-muted"),
            className="mb-3"
        )

    latest_run = runs[0]

    # Format timestamp
    timestamp_str = latest_run.timestamp.strftime("%Y-%m-%d %H:%M UTC")

    # Calculate pass rate
    total_tests = latest_run.test_count
    pass_rate = (
        (latest_run.pass_count / total_tests * 100)
        if total_tests > 0
        else 0.0
    )

    # Determine pass rate color
    if pass_rate >= 90:
        pass_rate_color = "success"
    elif pass_rate >= 70:
        pass_rate_color = "warning"
    else:
        pass_rate_color = "danger"

    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Latest Run", className="text-muted mb-2"),
                    html.H4(timestamp_str, className="mb-0"),
                ])
            ], className="text-center")
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total Tests", className="text-muted mb-2"),
                    html.H4(f"{total_tests:,}", className="mb-0"),
                ])
            ], className="text-center")
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Pass Rate", className="text-muted mb-2"),
                    html.H4(
                        f"{pass_rate:.1f}%",
                        className=f"mb-0 text-{pass_rate_color}"
                    ),
                ])
            ], className="text-center")
        ], width=4),
    ], className="mb-3")


def create_nightly_runs_section(runs: List[NightlyRunSnapshot]) -> dbc.Card:
    """
    Create the complete nightly runs collapsible section.

    Includes header with toggle button, summary cards, dropdown selector,
    and category breakdown chart placeholder.

    Args:
        runs: List of NightlyRunSnapshot objects.

    Returns:
        Bootstrap Card component with purple accent theme.
    """
    return dbc.Card([
        dbc.CardHeader([
            dbc.Button(
                [
                    html.I(id="icon-nightly-runs", className="bi bi-chevron-down me-2"),
                    html.Span("🌙", style={"fontSize": "1.5rem", "marginRight": "0.75rem"}),
                    html.Span("Recent Nightly Runs", style={"fontSize": "1.25rem", "fontWeight": "500"})
                ],
                id="btn-toggle-nightly-runs",
                color="link",
                className="text-start w-100 text-decoration-none p-3",
                style={"color": "#7c3aed", "fontWeight": "600"}
            )
        ], style={
            "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
            "borderBottom": "3px solid #7c3aed",
            "padding": "0"
        }),
        dbc.Collapse([
            dbc.CardBody([
                create_nightly_run_summary_cards(runs),
                html.Label("Select Nightly Run:", className="fw-bold mb-2"),
                create_nightly_run_selector_dropdown(runs),
                dcc.Loading(
                    dcc.Graph(id="nightly-run-chart"),
                    type="default"
                ),
            ])
        ], id="collapse-nightly-runs", is_open=True)
    ], className="mb-4", style={
        "borderLeft": "5px solid #7c3aed",
        "borderRadius": "0.75rem"
    })
