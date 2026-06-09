"""
Track mode UI components for baseline vs nightly comparison (RPOPC-1164).

Provides exception-oriented view for CPT/release owner workflow, showing only
regressions, improvements, and missing benchmarks from baseline comparison.
"""

from typing import List, Optional, Tuple

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, dcc, html

from src.query_service import BaselineComparisonSnapshot


def create_track_mode_layout() -> html.Div:
    """
    Create the main Track mode layout with baseline selector and exception view.

    Returns:
        Div containing Track mode UI components.
    """
    return html.Div([
        # Header
        dbc.Card([
            dbc.CardBody([
                html.H3([
                    html.Span("📊 ", style={"fontSize": "1.5rem"}),
                    "Track Mode: Baseline vs Nightly Comparison"
                ], className="mb-2"),
                html.P(
                    "Exception-oriented view showing regressions, improvements, and missing benchmarks",
                    className="text-muted mb-0"
                ),
            ])
        ], className="mb-4"),

        # Configuration Section
        dbc.Card([
            dbc.CardHeader(html.H5("Configuration", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Baseline Configuration:", className="fw-bold mb-2"),
                        html.P("Define baseline dataset by date range or tag filter", className="text-muted small"),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Baseline Date Range:", className="small"),
                                dcc.DatePickerRange(
                                    id='track-baseline-date-range',
                                    display_format='YYYY-MM-DD',
                                    className="mb-2"
                                ),
                            ], width=12),
                        ]),
                        html.Label("Baseline ID:", className="small mt-2"),
                        dcc.Input(
                            id='track-baseline-id',
                            type='text',
                            placeholder='e.g., rhel-9.5-baseline',
                            className="form-control mb-2"
                        ),
                    ], width=6),
                    dbc.Col([
                        html.Label("Nightly Run:", className="fw-bold mb-2"),
                        html.P("Select nightly run to compare against baseline", className="text-muted small"),
                        dcc.DatePickerRange(
                            id='track-nightly-date-range',
                            display_format='YYYY-MM-DD',
                            className="mb-2"
                        ),
                    ], width=6),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Run Comparison",
                            id="btn-run-track-comparison",
                            color="primary",
                            className="mt-3"
                        ),
                    ])
                ]),
            ])
        ], className="mb-4"),

        # Summary Metrics
        html.Div(id='track-summary-metrics'),

        # Exception Table
        dbc.Card([
            dbc.CardHeader(html.H5("Exceptions", className="mb-0")),
            dbc.CardBody([
                html.Div(id='track-exception-table')
            ])
        ], className="mb-4"),
    ])


def create_track_summary_metrics(snapshot: Optional[BaselineComparisonSnapshot]) -> html.Div:
    """
    Create summary metrics cards for Track mode comparison.

    Args:
        snapshot: BaselineComparisonSnapshot with comparison results.

    Returns:
        Div containing summary metric cards.
    """
    if snapshot is None or snapshot.error:
        error_msg = snapshot.error if snapshot else "No comparison run yet"
        return dbc.Alert(
            f"Unable to load comparison data: {error_msg}",
            color="warning",
            className="mb-3"
        )

    # Calculate metrics
    total_exceptions = snapshot.exception_count
    regression_count = len(snapshot.regressions)
    improvement_count = len(snapshot.improvements)
    missing_count = len(snapshot.missing)
    added_count = len(snapshot.added)

    # Determine overall status color
    if regression_count == 0:
        status_color = "success"
        status_text = "No Regressions"
    elif regression_count <= 5:
        status_color = "warning"
        status_text = "Minor Regressions"
    else:
        status_color = "danger"
        status_text = "Critical Regressions"

    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total Exceptions", className="text-muted mb-2"),
                    html.H3(f"{total_exceptions}", className="mb-0"),
                    html.Small(f"Baseline: {snapshot.baseline_id}", className="text-muted"),
                ])
            ], className="text-center")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Regressions", className="text-muted mb-2"),
                    html.H3(f"{regression_count}", className=f"mb-0 text-{status_color}"),
                    html.Small(status_text, className="text-muted"),
                ])
            ], className="text-center")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Improvements", className="text-muted mb-2"),
                    html.H3(f"{improvement_count}", className="mb-0 text-success"),
                    html.Small("Performance gains", className="text-muted"),
                ])
            ], className="text-center")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Missing/Added", className="text-muted mb-2"),
                    html.H3(f"{missing_count}/{added_count}", className="mb-0"),
                    html.Small("Benchmarks changed", className="text-muted"),
                ])
            ], className="text-center")
        ], width=3),
    ], className="mb-4")


def create_track_exception_table(snapshot: Optional[BaselineComparisonSnapshot]) -> html.Div:
    """
    Create exception table showing regressions, improvements, and missing benchmarks.

    Args:
        snapshot: BaselineComparisonSnapshot with comparison results.

    Returns:
        Div containing exception table or empty state message.
    """
    if snapshot is None or snapshot.error:
        return html.P("Run a comparison to see exception details", className="text-muted")

    # Build exception rows
    rows = []

    # Add regressions
    for benchmark_name, percent_change in snapshot.regressions:
        rows.append({
            'Benchmark': benchmark_name,
            'Type': 'Regression',
            'Change %': f"{percent_change:.2f}%",
            'Status': '🔴 Critical' if abs(percent_change) > 20 else '⚠️ Warning',
        })

    # Add improvements
    for benchmark_name, percent_change in snapshot.improvements:
        rows.append({
            'Benchmark': benchmark_name,
            'Type': 'Improvement',
            'Change %': f"+{percent_change:.2f}%",
            'Status': '✅ Better',
        })

    # Add missing benchmarks
    for benchmark_name in snapshot.missing:
        rows.append({
            'Benchmark': benchmark_name,
            'Type': 'Missing',
            'Change %': 'N/A',
            'Status': '❌ Removed',
        })

    # Add new benchmarks
    for benchmark_name in snapshot.added:
        rows.append({
            'Benchmark': benchmark_name,
            'Type': 'Added',
            'Change %': 'N/A',
            'Status': '➕ New',
        })

    if not rows:
        return dbc.Alert(
            "🎉 No exceptions found! All benchmarks are within acceptable thresholds.",
            color="success"
        )

    # Create DataFrame and table
    df = pd.DataFrame(rows)

    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[
            {'name': 'Benchmark', 'id': 'Benchmark'},
            {'name': 'Type', 'id': 'Type'},
            {'name': 'Change %', 'id': 'Change %'},
            {'name': 'Status', 'id': 'Status'},
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '12px',
            'fontSize': '14px',
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'borderBottom': '2px solid #dee2e6',
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{Type} = "Regression"'},
                'backgroundColor': '#fff5f5',
            },
            {
                'if': {'filter_query': '{Type} = "Improvement"'},
                'backgroundColor': '#f0fdf4',
            },
        ],
        sort_action='native',
        filter_action='native',
        page_action='native',
        page_size=20,
    )
