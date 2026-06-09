"""
Nightly runs UI component for Recent Nightly Runs section (RPOPC-1207).

Provides collapsible section with summary cards showing latest nightly run metrics.
"""

from typing import List, Optional

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from src.query_service import NightlyRunSnapshot


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
                html.Div(id="nightly-runs-dropdown-container"),
                html.Div(id="nightly-runs-chart-container"),
            ])
        ], id="collapse-nightly-runs", is_open=True)
    ], className="mb-4", style={
        "borderLeft": "5px solid #7c3aed",
        "borderRadius": "0.75rem"
    })
