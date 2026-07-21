"""
RHEL Multi Arch Performance Engineering Dashboard - Redesigned

Main Dash application for visualizing benchmark results with three key analyses:
1. RHEL Regression Analysis: Track version-to-version performance changes
2. Competitive Performance: Compare RHEL against peer operating systems
3. Cloud Scaling: Analyze performance across cloud instance classes
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from io import StringIO
from dash import Dash, html, dcc, Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
import pandas as pd

# Import local modules
from src.opensearch_client import BenchmarkDataSource
from src.data_processing import BenchmarkDataProcessor
from src.data_bootstrap import load_initial_benchmark_documents
from src.pulse_kpis import (
    aggregate_pulse_kpi_bundle_from_dataframe,
    fetch_pulse_kpi_bundle,
    pulse_kpi_bundle_from_connection_error,
)
from src.opensearch_links import opensearch_discover_url_for_document, results_index_name
from src.pulse_ui import render_pulse_v1_panel
from src.regression_detection import sort_regressions_worst_first
from src.investigation_templates import InvestigationTemplateError, fetch_investigation_documents
from src.components import filters, visualizations, ai_widget
from src.components.summaries import (
    format_regression_summary,
    format_peer_comparison_summary,
    format_scaling_summary,
    get_status_icon,
    summarize_investigation_details,
    format_investigation_summary_text
)
from src.components.nightly_runs import create_nightly_runs_section
from src.query_service import (
    fetch_recent_nightly_runs,
    aggregate_recent_nightly_runs_from_dataframe,
    fetch_baseline_comparison_aggregates,
    aggregate_baseline_comparison_from_dataframe,
)
from src.track_ui import (
    create_track_mode_layout,
    create_track_summary_metrics,
    create_track_exception_table,
)


def _normalize_colorblind_mode(value):
    """Normalize colorblind_mode value to strict boolean.

    Args:
        value: Input value from localStorage or callback (can be bool, str, int, or None)

    Returns:
        bool: True only if value is True, "true", or 1; False otherwise

    This function prevents the unsafe bool(value) pattern which treats
    non-empty strings like "false" as True.
    """
    if value is True or value == "true" or value == 1:
        return True
    return False


def competitive_performance_breadcrumb(category: str) -> dbc.Breadcrumb:
    """Category trail for Competitive Performance drill-down (P1-C)."""
    return dbc.Breadcrumb(
        items=[
            {"label": "Competitive Performance"},
            {"label": category, "active": True},
        ],
        className="mb-0 bg-transparent py-0",
    )


def investigation_drill_breadcrumb(benchmark_category: str, test_name: str) -> dbc.Breadcrumb:
    """Category → leaf trail for RHEL Regression investigation drill-down (P1-C)."""
    return dbc.Breadcrumb(
        items=[
            {"label": "RHEL Regression Analysis"},
            {"label": benchmark_category},
            {"label": test_name, "active": True},
        ],
        className="mb-2 bg-transparent py-0",
    )


def _q1_regression_discover_block(comparison_df):
    """
    Per-regression OpenSearch Discover links when OPENSEARCH_DASHBOARDS_BASE_URL
    and OPENSEARCH_INDEX_RESULTS (or OPENSEARCH_INDEX) are configured.
    """
    import pandas as pd

    dashboards_base = (os.getenv("OPENSEARCH_DASHBOARDS_BASE_URL") or "").strip()
    idx_name = results_index_name()
    if not dashboards_base or not idx_name:
        return None
    if comparison_df is None or comparison_df.empty:
        return None
    if "is_regression" not in comparison_df.columns:
        return None
    regressions = sort_regressions_worst_first(
        comparison_df[comparison_df["is_regression"]]
    )
    if regressions.empty:
        return None

    link_rows = []
    for _, row in regressions.head(10).iterrows():
        test = row.get("test_name", "test")
        hw = row.get("hardware_config", "")
        label_parts = [str(test)]
        if hw is not None and str(hw).strip():
            label_parts.append(str(hw))
        row_label = " · ".join(label_parts)

        anchors = []
        for col, leg in (
            ("baseline_document_id", "baseline"),
            ("comparison_document_id", "comparison"),
        ):
            if col not in row.index:
                continue
            doc_id = row[col]
            if doc_id is None or (isinstance(doc_id, float) and pd.isna(doc_id)):
                continue
            doc_str = str(doc_id).strip()
            if not doc_str:
                continue
            try:
                url = opensearch_discover_url_for_document(
                    dashboards_base, idx_name, doc_str
                )
            except ValueError:
                continue
            anchors.append(
                html.A(
                    f"Discover ({leg})",
                    href=url,
                    target="_blank",
                    rel="noopener noreferrer",
                    className="me-2",
                )
            )
        if anchors:
            link_rows.append(
                html.Div(
                    [
                        html.Small(row_label, className="text-muted d-block"),
                        html.Div(anchors, className="small"),
                    ],
                    className="mb-2",
                )
            )

    if not link_rows:
        return None
    return html.Div(
        [
            html.H6("Open in Discover", className="mt-2 mb-2 small text-muted"),
            *link_rows,
        ]
    )


# Load environment variables
load_dotenv()

# Initialize app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "RHEL Multi Arch Performance Engineering Dashboard"

# Determine data mode
DATA_MODE = os.getenv('DATA_MODE', 'synthetic').lower()

# P1-F: explicit opt-in only — never silently substitute synthetic when OpenSearch fails
USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE = os.getenv(
    "ZAXBY_USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE", ""
).lower() in ("1", "true", "yes")

# Initialize data processor
processor = BenchmarkDataProcessor()

# Populated by refresh_bootstrap_state() at import and after in-app OpenSearch retry
raw_documents: list = []
OPENSEARCH_LOAD_ERROR = None
SYNTHETIC_AFTER_OPENSEARCH_FAILURE = False
df: pd.DataFrame | None = None
os_versions: list = []
instance_types: list = []
test_names: list = []
cloud_providers: list = []
os_distributions: list = []
min_date = "2025-01-01"
max_date = "2025-12-31"
MODE_BADGE_LABEL = ""
MODE_BADGE_COLOR = "secondary"
os_version_map: dict = {}


def refresh_bootstrap_state() -> None:
    """Load or reload benchmark documents and refresh derived globals (startup and Retry button).

    Mutates module-level state (``df``, filter metadata, etc.). Intended for a single worker
    process (e.g. ``python app.py`` or one gunicorn worker); multiple workers would not share
    these globals, and concurrent retry vs. callback reads could race.
    """
    global raw_documents, OPENSEARCH_LOAD_ERROR, SYNTHETIC_AFTER_OPENSEARCH_FAILURE
    global df, os_versions, instance_types, test_names, cloud_providers, os_distributions
    global min_date, max_date, os_version_map, MODE_BADGE_LABEL, MODE_BADGE_COLOR

    print(f"Loading data in {DATA_MODE} mode...")
    raw_documents, OPENSEARCH_LOAD_ERROR, SYNTHETIC_AFTER_OPENSEARCH_FAILURE = (
        load_initial_benchmark_documents(
            DATA_MODE,
            use_synthetic_after_opensearch_failure=USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE,
            max_opensearch_docs=5000,
        )
    )
    if DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is None:
        print(f"Loaded {len(raw_documents)} documents from OpenSearch")
    elif DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is not None and SYNTHETIC_AFTER_OPENSEARCH_FAILURE:
        print(
            "OpenSearch load failed; loaded synthetic data per "
            "ZAXBY_USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE=1"
        )
    elif DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is not None:
        print(f"OpenSearch load failed: {OPENSEARCH_LOAD_ERROR or '(no message)'}")
    df = processor.documents_to_dataframe(raw_documents)
    print(f"Processed {len(df)} records")

    os_versions = processor.get_unique_values(df, "os_version")
    instance_types = processor.get_unique_values(df, "instance_type")
    test_names = processor.get_unique_values(df, "test_name")
    cloud_providers = processor.get_unique_values(df, "cloud_provider")
    os_distributions = processor.get_unique_values(df, "os_distribution")
    min_date = df["timestamp"].min().strftime("%Y-%m-%d") if len(df) > 0 else "2025-01-01"
    max_date = df["timestamp"].max().strftime("%Y-%m-%d") if len(df) > 0 else "2025-12-31"

    if SYNTHETIC_AFTER_OPENSEARCH_FAILURE:
        MODE_BADGE_LABEL = "SYNTHETIC (after OpenSearch failure — env opt-in)"
        MODE_BADGE_COLOR = "warning"
    elif DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is not None:
        MODE_BADGE_LABEL = "OPENSEARCH (load failed — no data)"
        MODE_BADGE_COLOR = "danger"
    else:
        MODE_BADGE_LABEL = DATA_MODE.upper()
        MODE_BADGE_COLOR = "secondary"

    os_version_map = {}
    if len(df) > 0:
        for dist in df["os_distribution"].dropna().unique():
            versions = df[df["os_distribution"] == dist]["os_version"].dropna().unique().tolist()
            os_version_map[dist] = sorted(versions, key=lambda v: [float(x) for x in str(v).split(".")] if v else [0])


refresh_bootstrap_state()


def _opensearch_alert_banners() -> list:
    """Top-of-page alerts for OpenSearch load issues (content reflects current globals)."""
    banners: list = []
    if DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is not None and SYNTHETIC_AFTER_OPENSEARCH_FAILURE:
        banners.append(
            dbc.Alert(
                [
                    html.Strong("OpenSearch unavailable — showing synthetic sample data. "),
                    "You set ",
                    html.Code("ZAXBY_USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE=1"),
                    ". Underlying error: ",
                    html.Code(OPENSEARCH_LOAD_ERROR or "(unknown)"),
                ],
                color="warning",
                className="mb-3",
            )
        )
    elif DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is not None:
        banners.append(
            dbc.Alert(
                [
                    html.H4("Could not load benchmark data from OpenSearch", className="alert-heading"),
                    html.P(
                        [
                            "With ",
                            html.Code("DATA_MODE=opensearch"),
                            ", the app does not silently switch to synthetic data. ",
                            "Fix the connection or choose an explicit recovery option below.",
                        ]
                    ),
                    html.Hr(),
                    html.P([html.Strong("Error: "), html.Code(OPENSEARCH_LOAD_ERROR or "(unknown)")]),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    "Use ",
                                    html.Strong("Retry OpenSearch"),
                                    " in the header after fixing credentials, network, or index settings ",
                                    "(or restart the app if the problem persists).",
                                ]
                            ),
                            html.Li(
                                [
                                    "Offline demo: set ",
                                    html.Code("DATA_MODE=synthetic"),
                                    " in ",
                                    html.Code(".env"),
                                    " and restart.",
                                ]
                            ),
                            html.Li(
                                [
                                    "Keep ",
                                    html.Code("DATA_MODE=opensearch"),
                                    " but load synthetic only after a failed OpenSearch attempt: set ",
                                    html.Code("ZAXBY_USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE=1"),
                                    " and restart. The header will show that data is not live OpenSearch.",
                                ]
                            ),
                        ],
                        className="mb-0",
                    ),
                ],
                color="danger",
                className="mb-3",
            )
        )
    return banners


def serve_layout():
    """Callable layout so a full reload after Retry picks up refreshed benchmark state."""
    show_opensearch_retry = DATA_MODE == "opensearch" and (
        OPENSEARCH_LOAD_ERROR is not None or SYNTHETIC_AFTER_OPENSEARCH_FAILURE
    )
    return dbc.Container(
        [
            dcc.Location(id="opensearch-retry-reload", refresh=True),
            *_opensearch_alert_banners(),
            # Store for filtered data and analysis results
            dcc.Store(id='filtered-data-store'),
            dcc.Store(id='analysis-results-store'),
            dcc.Store(id='navigation-state', data={'view': 'overview', 'investigation_params': None}),
            dcc.Store(id='nightly-runs-store'),
            dcc.Store(id='pulse-kpi-bundle-store'),
            dcc.Store(id='colorblind-mode-store', storage_type='local'),
            dcc.Store(id='dark-mode-callback-dummy'),  # Dummy output for dark mode clientside callback
            dcc.Store(id='colorblind-callback-dummy'),  # Dummy output for colorblind clientside callback

            # Header
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H1([
                                    html.Span("🔬 ", style={"fontSize": "2rem"}),
                                    "RHEL Multi Arch Performance Engineering Dashboard"
                                ], className="mb-2"),
                                html.P(
                                    "Benchmark Analysis & Regression Detection",
                                    className="text-muted mb-0",
                                    style={"fontSize": "1.1rem"}
                                ),
                            ]),
                        ], width=7),
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    [
                                        html.I(className="bi bi-arrow-repeat me-1"),
                                        "Retry OpenSearch",
                                    ],
                                    id="btn-retry-opensearch",
                                    color="outline-primary",
                                    size="sm",
                                    className="me-2"
                                    + ("" if show_opensearch_retry else " d-none"),
                                ),
                                dbc.Button(
                                    id="dark-mode-toggle",
                                    color="link",
                                    className="me-3 p-0",
                                    children=html.Span(
                                        "Toggle dark mode",
                                        className="visually-hidden"
                                    ),
                                    style={
                                        "border": "none",
                                        "textDecoration": "none"
                                    }
                                ),
                                dbc.Button(
                                    id="colorblind-mode-toggle",
                                    color="link",
                                    className="me-3 p-0",
                                    children=html.Span(
                                        "Toggle colorblind mode",
                                        className="visually-hidden"
                                    ),
                                    style={
                                        "border": "none",
                                        "textDecoration": "none"
                                    }
                                ),
                                dbc.Badge(
                                    f"📊 {len(df):,} Records",
                                    color="primary",
                                    className="me-2 px-3 py-2",
                                    style={"fontSize": "0.9rem"}
                                ),
                                dbc.Badge(
                                    f"Mode: {MODE_BADGE_LABEL}",
                                    color=MODE_BADGE_COLOR,
                                    className="px-3 py-2",
                                    style={"fontSize": "0.9rem"}
                                ),
                            ], className="d-flex justify-content-end align-items-center h-100")
                        ], width=5)
                    ]),
                    html.Hr(className="my-3", style={"borderTop": "2px solid #e5e7eb"}),
                    dbc.Row([
                        dbc.Col([
                            html.Label("📅 Date Range:", className="fw-bold text-muted small mb-1"),
                            dcc.DatePickerRange(
                                id='header-date-range',
                                start_date=min_date,
                                end_date=max_date,
                                display_format='YYYY-MM-DD',
                                className="mb-2"
                            ),
                        ], width=5),
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="bi bi-sliders me-2"), "Advanced Filters"],
                                id="btn-show-filters",
                                size="md",
                                color="secondary",
                                className="w-100"
                            ),
                        ], width=3, className="d-flex align-items-end")
                    ], className="mt-2"),
                    html.Div(id="opensearch-retry-status", className="text-end mt-2 small"),
                ], style={
                    "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                    "borderRadius": "0.75rem"
                })
            ], id="dashboard-header", className="mb-4 mt-3", style={"border": "none", "boxShadow": "0 4px 12px rgba(0,0,0,0.1)"}),

            # Advanced Filters Collapse
            dbc.Collapse([
                dbc.Card([
                    dbc.CardBody([
                        filters.create_filter_panel(
                            os_versions=os_versions,
                            instance_types=instance_types,
                            test_names=test_names,
                            cloud_providers=cloud_providers,
                            min_date=min_date,
                            max_date=max_date,
                            os_version_map=os_version_map
                        )
                    ])
                ], className="mb-3")
            ], id="collapse-filters", is_open=False),

            # Main Content - switches between overview and investigation
            html.Div(id="main-content")

    ], fluid=True)


app.layout = serve_layout


@app.callback(
    Output("opensearch-retry-status", "children"),
    Output("opensearch-retry-reload", "href"),
    Input("btn-retry-opensearch", "n_clicks"),
    prevent_initial_call=True,
)
def retry_opensearch_connection(_n_clicks):
    """Reload benchmark data from OpenSearch without restarting the process."""
    # Defensive: UI hides the button unless DATA_MODE is opensearch, but keep a guard if layout changes.
    if DATA_MODE != "opensearch":
        raise PreventUpdate
    refresh_bootstrap_state()
    if OPENSEARCH_LOAD_ERROR is None:
        return "", "/"
    err = OPENSEARCH_LOAD_ERROR or "(unknown)"
    return (
        dbc.Alert(
            [
                "Still cannot reach OpenSearch: ",
                html.Code(err),
            ],
            color="warning",
            className="mb-0 py-2",
            dismissable=True,
        ),
        no_update,
    )


# Clientside callback for dark mode toggle
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            // Toggle dark mode class on body
            document.body.classList.toggle('dark-mode');
            
            // Save preference to localStorage
            const isDarkMode = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode);
        } else {
            // On page load, check localStorage and apply saved preference
            const savedDarkMode = localStorage.getItem('darkMode');
            if (savedDarkMode === 'true') {
                document.body.classList.add('dark-mode');
            }
        }
        return '';
    }
    """,
    Output('dark-mode-callback-dummy', 'data'),  # Dummy output
    Input('dark-mode-toggle', 'n_clicks')
)


# Clientside callback for colorblind mode toggle
# Toggles the colorblind-mode-store value when button is clicked
# Uses strict normalization to prevent string "false" from being treated as truthy
app.clientside_callback(
    """
    function(n_clicks, current_data) {
        if (n_clicks) {
            // Strict normalization: only true, 'true', or 1 are considered enabled
            // This prevents "false" string from being truthy (!!"false" === true)
            const normalized = (current_data === true || current_data === 'true' || current_data === 1);
            return !normalized;
        }
        // On initial load, normalize and return stored value
        const normalized = (current_data === true || current_data === 'true' || current_data === 1);
        return normalized;
    }
    """,
    Output('colorblind-mode-store', 'data'),
    Input('colorblind-mode-toggle', 'n_clicks'),
    State('colorblind-mode-store', 'data')
)


# Clientside callback to sync colorblind mode to body class
# This allows CSS styling based on colorblind mode
# Uses strict normalization matching the Python _normalize_colorblind_mode() function
app.clientside_callback(
    """
    function(colorblind_mode) {
        // Strict normalization: only true, 'true', or 1 are considered enabled
        // This prevents "false" string from being truthy
        const normalized = (colorblind_mode === true || colorblind_mode === 'true' || colorblind_mode === 1);
        document.body.classList.toggle('colorblind-mode', normalized);
        return window.dash_clientside.no_update;
    }
    """,
    Output('colorblind-callback-dummy', 'data'),  # Dummy output
    Input('colorblind-mode-store', 'data')
)


def create_comparison_collapse(comparison_id, title, graph_id, summary_id):
    """Create a collapsible comparison section."""
    return dbc.Card([
        dbc.CardHeader([
            dbc.Button(
                [html.I(className="bi bi-chevron-down me-2"), title],
                id=f"btn-toggle-{comparison_id}",
                color="link",
                className="text-start w-100 text-decoration-none",
                size="sm"
            )
        ], className="p-0"),
        dbc.Collapse([
            dbc.CardBody([
                html.Div(id=summary_id, className="mb-3"),
                dcc.Loading(
                    dcc.Graph(id=graph_id),
                    type="default"
                )
            ])
        ], id=f"collapse-{comparison_id}", is_open=True)
    ], className="mb-2")


def create_overview_layout():
    """
    Pulse v1 KPI strip first; detailed analyses (three sections plus quick links)
    are in a collapse closed by default (expand via the detailed-analyses button).
    """
    return html.Div([
        # Pulse v1: bounded server-side aggregations (not the full scroll payload).
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H4("Pulse", className="mb-1"),
                        html.P(
                            "Coverage and activity: total runs, reporting window, monthly trend, and "
                            "benchmark category mix. Uses server-side aggregations in OpenSearch mode or "
                            "the loaded sample in synthetic mode.",
                            className="text-muted small mb-2",
                        ),
                        html.Div(id="server-snapshot-content", children=dbc.Spinner(size="sm")),
                    ], width=10),
                    dbc.Col([
                        dbc.Button(
                            "Refresh",
                            id="btn-refresh-server-snapshot",
                            color="secondary",
                            outline=True,
                            size="sm",
                            className="mt-4",
                        ),
                    ], width=2),
                ]),
            ]),
        ], className="mb-4 border-primary", style={"borderWidth": "2px"}),
        dcc.Interval(id="server-snapshot-init", interval=400, max_intervals=1, n_intervals=0),

        # AI Widget (RPOPC-1014)
        ai_widget.create_ai_widget(),

        # Recent Nightly Runs (RPOPC-1207)
        html.Div(id="nightly-runs-section"),

        dbc.Button(
            [
                html.I(className="bi bi-chevron-down me-2"),
                "Show detailed benchmark analyses",
            ],
            id="btn-toggle-detailed-analyses",
            color="secondary",
            outline=True,
            className="mb-3",
        ),
        dbc.Collapse(
            [
                # Section 1: RHEL Regression Analysis (Collapsible)
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Button(
                            [
                                html.I(id="icon-section-rhel", className="bi bi-chevron-down me-2"),
                                html.Span("📊", style={"fontSize": "1.5rem", "marginRight": "0.75rem"}),
                                html.Span("RHEL Regression Analysis", style={"fontSize": "1.25rem", "fontWeight": "500"})
                    ],
                    id="btn-toggle-section-rhel",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#1e3a8a", "fontWeight": "600"}
                )
            ], style={
                "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                "borderBottom": "3px solid #3b82f6",
                "padding": "0"
            }),
            dbc.Collapse([
                dbc.CardBody([
                    html.Div(id='q1-overall-summary', className="mb-3"),
                    # Major Release Comparison (9.X vs 10.X)
                    create_comparison_collapse(
                        "major-release",
                        "Compare Latest Major Releases (9.X vs 10.X)",
                        "q1-major-graph",
                        "q1-major-summary"
                    ),
                    # RHEL 9.X Sequential Comparison
                    create_comparison_collapse(
                        "rhel9-seq",
                        "Compare RHEL 9.X Versions (Sequential)",
                        "q1-rhel9-graph",
                        "q1-rhel9-summary"
                    ),
                    # RHEL 10.X Sequential Comparison
                    create_comparison_collapse(
                        "rhel10-seq",
                        "Compare RHEL 10.X Versions (Sequential)",
                        "q1-rhel10-graph",
                        "q1-rhel10-summary"
                    )
                ])
            ], id="collapse-section-rhel", is_open=True)
        ], className="mb-4", style={
            "borderLeft": "5px solid #1e3a8a",
            "borderRadius": "0.75rem"
        }),
        
        # Section 2: Competitive Performance (Collapsible)
        dbc.Card([
            dbc.CardHeader([
                dbc.Button(
                    [
                        html.I(id="icon-section-competitive", className="bi bi-chevron-down me-2"),
                        html.Span("📈", style={"fontSize": "1.5rem", "marginRight": "0.75rem"}),
                        html.Span("Competitive Performance", style={"fontSize": "1.25rem", "fontWeight": "500"})
                    ],
                    id="btn-toggle-section-competitive",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#0e7490", "fontWeight": "600"}
                )
            ], style={
                "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                "borderBottom": "3px solid #3b82f6",
                "padding": "0"
            }),
            dbc.Collapse([
                dbc.CardBody([
                    html.Div([
                        html.P([
                            "Comparing RHEL performance against peer operating systems on the same hardware. ",
                            html.Strong("Click any category bar to see individual benchmarks.", style={"color": "#0e7490"})
                        ], className="text-muted mb-3"),
                        html.Div(id='q2-comparison-selector', className="mb-4"),
                        dcc.Store(id='q2-analysis-store'),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dcc.Loading(
                                dcc.Graph(id='q2-comparison', style={"cursor": "pointer"}),
                                type="default"
                            )
                        ], width=12)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Div(id='q2-summary', className="mt-3")
                        ])
                    ]),
                    # Inline Category Detail Panel (hidden by default)
                    html.Div(
                        id='q2-category-detail-container',
                        children=[
                            dbc.Card([
                                dbc.CardHeader([
                                    dbc.Row([
                                        dbc.Col([
                                            html.Div([
                                                html.I(className="bi bi-chevron-down me-2"),
                                                html.Strong(id='q2-detail-category-title', children="Category Details")
                                            ], className="d-flex align-items-center")
                                        ], width=8),
                                        dbc.Col([
                                            dbc.ButtonGroup([
                                                dbc.Button(
                                                    [html.I(className="bi bi-arrows-fullscreen me-1"), "Full Details"],
                                                    id="btn-q2-open-modal",
                                                    color="primary",
                                                    size="sm",
                                                    outline=True
                                                ),
                                                dbc.Button(
                                                    [html.I(className="bi bi-x-lg")],
                                                    id="btn-q2-close-detail",
                                                    color="secondary",
                                                    size="sm",
                                                    outline=True
                                                )
                                            ], className="float-end")
                                        ], width=4, className="text-end")
                                    ])
                                ], style={"background": "#f8fafc", "borderBottom": "2px solid #06b6d4"}),
                                dbc.CardBody([
                                    dcc.Loading([
                                        # Summary stats row
                                        html.Div(id='q2-detail-summary', className="mb-3"),
                                        # Benchmark detail chart
                                        dcc.Graph(id='q2-detail-benchmark-chart'),
                                    ], type="default")
                                ])
                            ], className="mt-3", style={"border": "1px solid #06b6d4", "borderRadius": "0.5rem"})
                        ],
                        style={"display": "none"}  # Hidden by default
                    )
                ])
            ], id="collapse-section-competitive", is_open=True)
        ], className="mb-4", style={
            "borderLeft": "5px solid #06b6d4",
            "borderRadius": "0.75rem"
        }),
        
        # Category Detail Modal (for full deep-dive analysis)
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle(id="q2-modal-title", children="Category Deep Dive")
            ], close_button=True),
            dbc.ModalBody([
                dcc.Loading([
                    # Modal summary section
                    html.Div(id='q2-modal-summary', className="mb-4"),
                    
                    # Tabs for different views
                    dbc.Tabs([
                        dbc.Tab(label="Benchmark Breakdown", tab_id="tab-benchmarks"),
                        dbc.Tab(label="Hardware Matrix", tab_id="tab-hardware"),
                        dbc.Tab(label="Raw Data", tab_id="tab-data"),
                    ], id="q2-modal-tabs", active_tab="tab-benchmarks", className="mb-3"),
                    
                    # Tab content
                    html.Div(id='q2-modal-tab-content')
                ], type="default")
            ]),
            dbc.ModalFooter([
                html.Div([
                    html.Small("💡 Tip: Use the Hardware Matrix tab to identify specific instance types with performance gaps.", 
                              className="text-muted me-auto")
                ], className="flex-grow-1"),
                dbc.Button("Close", id="btn-q2-modal-close", color="secondary")
            ])
        ], id="q2-category-modal", size="xl", is_open=False, scrollable=True),
        
        # Store for selected category data
        dcc.Store(id='q2-selected-category-store'),
        
        # Section 3: Cloud Scaling (Collapsible)
        dbc.Card([
            dbc.CardHeader([
                dbc.Button(
                    [
                        html.I(id="icon-section-cloud", className="bi bi-chevron-down me-2"),
                        html.Span("☁️", style={"fontSize": "1.5rem", "marginRight": "0.75rem"}),
                        html.Span("Cloud Scaling", style={"fontSize": "1.25rem", "fontWeight": "500"})
                    ],
                    id="btn-toggle-section-cloud",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#047857", "fontWeight": "600"}
                )
            ], style={
                "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                "borderBottom": "3px solid #3b82f6",
                "padding": "0"
            }),
            dbc.Collapse([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Cloud Provider:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-cloud-provider',
                                options=[{'label': cp.upper(), 'value': cp} for cp in cloud_providers],
                                value=cloud_providers[0] if cloud_providers else None,
                                clearable=False
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label("Instance Series:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-instance-series',
                                options=[],  # Populated by callback based on cloud provider and available data
                                value=None,
                                placeholder="Select instance series...",
                                clearable=True
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label("OS:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-os-distribution',
                                options=[],  # Populated by callback based on available data
                                value=None,
                                placeholder="Select OS...",
                                clearable=False
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label("OS Version:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-os-version',
                                options=[],  # Populated by callback based on OS distribution and available data
                                value=None,
                                placeholder="Select version...",
                                clearable=False
                            )
                        ], width=3)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Benchmark Category:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-benchmark-category',
                                options=[
                                    {'label': 'All Categories', 'value': 'all'},
                                    {'label': 'Networking', 'value': 'Networking'},
                                    {'label': 'Storage/IO', 'value': 'Storage/IO'},
                                    {'label': 'HPC/Compute', 'value': 'HPC/Compute'},
                                    {'label': 'System', 'value': 'System'},
                                    {'label': 'Other', 'value': 'Other'}
                                ],
                                value='all',
                                clearable=False
                            )
                        ], width=3),
                        dbc.Col([], width=9)  # Empty column for spacing
                    ], className="mb-3"),
                    dcc.Store(id='q3-analysis-store'),
                    dbc.Alert([
                        html.Strong("How Scaling Efficiency is Measured: "),
                        html.Span(
                            "Scaling efficiency compares actual performance against ideal linear scaling. "
                            "The smallest instance serves as the baseline (100%). For larger instances, "
                            "we calculate expected performance assuming linear scaling (e.g., 2× cores = 2× performance), "
                            "then measure actual vs. expected. "
                        ),
                        html.Strong("100%"),
                        html.Span(" = perfect linear scaling, "),
                        html.Strong(">100%"),
                        html.Span(" = super-linear (better than expected), "),
                        html.Strong("<100%"),
                        html.Span(" = sub-linear (diminishing returns).")
                    ], color="light", className="mb-3 small", style={"borderLeft": "3px solid #10b981"}),
                    dbc.Row([
                        dbc.Col([
                            dcc.Loading(
                                dcc.Graph(id='q3-scaling'),
                                type="default"
                            )
                        ], width=12)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Div(id='q3-summary', className="mt-3")
                        ])
                    ])
                ])
            ], id="collapse-section-cloud", is_open=True)
        ], className="mb-4", style={
            "borderLeft": "5px solid #10b981",
            "borderRadius": "0.75rem"
        }),
        
        # Quick Links to Detailed Views
        dbc.Card([
            dbc.CardBody([
                html.H5("Detailed Analysis", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "View All Benchmarks →",
                            id="btn-view-benchmarks",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Button(
                            "Compare Configurations →",
                            id="btn-view-comparisons",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Button(
                            "View Detailed Table →",
                            id="btn-view-table",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Button(
                            "📊 Track Mode →",
                            id="btn-track-mode",
                            color="info",
                            outline=True,
                            className="w-100"
                        )
                    ], width=3)
                ])
            ])
        ])
        ],
            id="collapse-detailed-analyses",
            is_open=False,
        ),
    ])


def create_investigation_layout(
    test_name,
    baseline_version,
    comparison_version,
    benchmark_category,
    os_distribution='rhel',
):
    """Create the investigation drill-down layout (category → benchmark per P1-C).

    ``benchmark_category`` is required so call sites cannot omit category resolution
    and accidentally show a misleading default in the breadcrumb.
    """
    return html.Div([
        # Breadcrumb / Back button
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "← Back to Overview",
                    id="btn-back-to-overview",
                    color="link",
                    size="sm"
                ),
                investigation_drill_breadcrumb(benchmark_category, test_name),
                html.H3(f"Investigating: {test_name}", className="mt-1"),
                html.P(f"OS: {os_distribution.upper()} | Comparing {baseline_version} → {comparison_version}",
                       className="text-muted mb-0"),
            ])
        ], className="mb-3"),
        
        # Investigation content
        dbc.Card([
            dbc.CardBody([
                html.Div(id='investigation-summary', className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            dcc.Graph(id='investigation-comparison-chart'),
                            type="default"
                        )
                    ], width=6),
                    dbc.Col([
                        dcc.Loading(
                            dcc.Graph(id='investigation-timeline-chart'),
                            type="default"
                        )
                    ], width=6)
                ]),
                html.Hr(),
                html.H5("Test Run Details", className="mt-3 mb-3"),
                dcc.Loading(
                    html.Div(id='investigation-table'),
                    type="default"
                )
            ])
        ])
    ])


# Callbacks


def _validate_pulse_bundle_structure(bundle_data):
    """Validate Pulse KPI bundle structure before deserialization.

    Args:
        bundle_data: Data from pulse-kpi-bundle-store (expected to be dict).

    Returns:
        str: Error message if validation fails, None if valid.
    """
    # Check that bundle_data is a dict
    if not isinstance(bundle_data, dict):
        return f"Bundle data must be a dict, got {type(bundle_data).__name__}"

    # Check for required top-level keys
    required_keys = [
        'overview',
        'category_mix',
        'activity_timeline',
        'scope',
        'policy_template_id',
        'definition_version',
    ]
    missing_keys = [key for key in required_keys if key not in bundle_data]
    if missing_keys:
        return f"Bundle missing required keys: {', '.join(missing_keys)}"

    # Check that snapshot fields are dicts (they will be unpacked with **)
    snapshot_keys = ['overview', 'category_mix', 'activity_timeline', 'scope']
    for key in snapshot_keys:
        if not isinstance(bundle_data[key], dict):
            return f"Bundle['{key}'] must be a dict, got {type(bundle_data[key]).__name__}"

    # Check that metadata fields are strings
    if not isinstance(bundle_data['policy_template_id'], str):
        return f"Bundle['policy_template_id'] must be a str, got {type(bundle_data['policy_template_id']).__name__}"
    if not isinstance(bundle_data['definition_version'], str):
        return f"Bundle['definition_version'] must be a str, got {type(bundle_data['definition_version']).__name__}"

    return None


@app.callback(
    Output('pulse-kpi-bundle-store', 'data'),
    [Input("server-snapshot-init", "n_intervals"),
     Input("btn-refresh-server-snapshot", "n_clicks")],
    prevent_initial_call=True,
)
def fetch_server_snapshot(_n_intervals, _n_clicks):
    """Fetch Pulse KPI bundle from OpenSearch or synthetic data.

    prevent_initial_call avoids doubling work with server-snapshot-init (initial n_intervals=0 plus first tick).
    First load runs once when the one-shot Interval increments n_intervals; Refresh triggers further loads.
    """
    from dataclasses import asdict

    if DATA_MODE == "opensearch":
        try:
            client = BenchmarkDataSource()
        except Exception as exc:  # noqa: BLE001 — client construction
            bundle = pulse_kpi_bundle_from_connection_error(str(exc), source="opensearch")
        else:
            bundle = fetch_pulse_kpi_bundle(client)
    else:
        bundle = aggregate_pulse_kpi_bundle_from_dataframe(df)

    # Serialize bundle to JSON-compatible dict
    return {
        'overview': asdict(bundle.overview),
        'category_mix': asdict(bundle.category_mix),
        'activity_timeline': asdict(bundle.activity_timeline),
        'scope': asdict(bundle.scope),
        'policy_template_id': bundle.policy_template_id,
        'definition_version': bundle.definition_version,
    }


@app.callback(
    Output("server-snapshot-content", "children"),
    [Input('pulse-kpi-bundle-store', 'data'),
     Input('colorblind-mode-store', 'data')],
)
def render_server_snapshot(bundle_data, colorblind_mode):
    """Render Pulse KPI panel from cached bundle data.

    Colorblind toggle only triggers this render callback, not the expensive fetch.
    """
    from src.query_service import (
        ResultsOverviewSnapshot,
        CategoryKpiSnapshot,
        ActivityTimelineSnapshot,
        PulseScopeFootnote,
    )

    if not bundle_data:
        return html.Div("Loading server snapshot...", className="text-muted")

    # Validate bundle structure before deserializing
    validation_error = _validate_pulse_bundle_structure(bundle_data)
    if validation_error:
        return html.Div(
            [
                html.P("Error loading Pulse KPI data:", className="text-danger fw-bold"),
                html.P(validation_error, className="text-muted"),
            ],
            className="alert alert-danger",
        )

    # Deserialize bundle from JSON dict
    try:
        snap = ResultsOverviewSnapshot(**bundle_data['overview'])
        cat_snap = CategoryKpiSnapshot(**bundle_data['category_mix'])
        timeline_snap = ActivityTimelineSnapshot(**bundle_data['activity_timeline'])
        scope_snap = PulseScopeFootnote(**bundle_data['scope'])
    except (TypeError, ValueError) as exc:
        return html.Div(
            [
                html.P("Error deserializing Pulse KPI bundle:", className="text-danger fw-bold"),
                html.P(str(exc), className="text-muted"),
            ],
            className="alert alert-danger",
        )

    colorblind_mode = _normalize_colorblind_mode(colorblind_mode)

    return render_pulse_v1_panel(
        snap=snap,
        scope_snap=scope_snap,
        cat_snap=cat_snap,
        timeline_snap=timeline_snap,
        data_mode=DATA_MODE,
        results_index_label=results_index_name(),
        kpi_definition_version=bundle_data['definition_version'],
        policy_template_id=bundle_data['policy_template_id'],
        colorblind_mode=colorblind_mode,
    )


@app.callback(
    Output('collapse-filters', 'is_open'),
    Input('btn-show-filters', 'n_clicks'),
    State('collapse-filters', 'is_open'),
    prevent_initial_call=True
)
def toggle_filters(n_clicks, is_open):
    """Toggle advanced filters panel."""
    return not is_open


@app.callback(
    Output("collapse-detailed-analyses", "is_open"),
    Input("btn-toggle-detailed-analyses", "n_clicks"),
    State("collapse-detailed-analyses", "is_open"),
    prevent_initial_call=True,
)
def toggle_detailed_analyses(_n_clicks, is_open):
    """Expand or collapse RHEL / Competitive / Cloud sections and quick links below Pulse."""
    return not is_open


# Callbacks for major section toggles
@app.callback(
    [Output('collapse-section-rhel', 'is_open'),
     Output('icon-section-rhel', 'className')],
    Input('btn-toggle-section-rhel', 'n_clicks'),
    State('collapse-section-rhel', 'is_open'),
    prevent_initial_call=True
)
def toggle_section_rhel(n_clicks, is_open):
    """Toggle RHEL Regression Analysis section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class


@app.callback(
    [Output('collapse-section-competitive', 'is_open'),
     Output('icon-section-competitive', 'className')],
    Input('btn-toggle-section-competitive', 'n_clicks'),
    State('collapse-section-competitive', 'is_open'),
    prevent_initial_call=True
)
def toggle_section_competitive(n_clicks, is_open):
    """Toggle Competitive Performance section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class


@app.callback(
    [Output('collapse-section-cloud', 'is_open'),
     Output('icon-section-cloud', 'className')],
    Input('btn-toggle-section-cloud', 'n_clicks'),
    State('collapse-section-cloud', 'is_open'),
    prevent_initial_call=True
)
def toggle_section_cloud(n_clicks, is_open):
    """Toggle Cloud Scaling section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class


@app.callback(
    [Output('collapse-nightly-runs', 'is_open'),
     Output('icon-nightly-runs', 'className')],
    Input('btn-toggle-nightly-runs', 'n_clicks'),
    State('collapse-nightly-runs', 'is_open'),
    prevent_initial_call=True
)
def toggle_nightly_runs(n_clicks, is_open):
    """Toggle Recent Nightly Runs section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class


# Callbacks for subsection toggles within RHEL Regression Analysis
@app.callback(
    Output('collapse-major-release', 'is_open'),
    Input('btn-toggle-major-release', 'n_clicks'),
    State('collapse-major-release', 'is_open'),
    prevent_initial_call=True
)
def toggle_major_release(n_clicks, is_open):
    """Toggle major release comparison."""
    return not is_open


@app.callback(
    Output('collapse-rhel9-seq', 'is_open'),
    Input('btn-toggle-rhel9-seq', 'n_clicks'),
    State('collapse-rhel9-seq', 'is_open'),
    prevent_initial_call=True
)
def toggle_rhel9_seq(n_clicks, is_open):
    """Toggle RHEL 9 sequential comparison."""
    return not is_open


@app.callback(
    Output('collapse-rhel10-seq', 'is_open'),
    Input('btn-toggle-rhel10-seq', 'n_clicks'),
    State('collapse-rhel10-seq', 'is_open'),
    prevent_initial_call=True
)
def toggle_rhel10_seq(n_clicks, is_open):
    """Toggle RHEL 10 sequential comparison."""
    return not is_open


@app.callback(
    [Output('nightly-runs-store', 'data'),
     Output('nightly-runs-section', 'children')],
    [Input('header-date-range', 'start_date'),
     Input('header-date-range', 'end_date')],
)
def update_nightly_runs(start_date, end_date):
    """
    Fetch nightly runs and populate both the store and the section.

    Respects header date range filter. Uses OpenSearch or DataFrame aggregation
    based on DATA_MODE.
    """
    from datetime import datetime
    import json

    # Parse date range
    date_range = None
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            date_range = (start_dt, end_dt)
        except (ValueError, AttributeError):
            date_range = None

    # Fetch nightly runs based on data mode
    if DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is None:
        try:
            client = BenchmarkDataSource()
            runs = fetch_recent_nightly_runs(client, max_runs=10, date_range=date_range)
        except Exception as exc:
            logger.error(f"Failed to fetch nightly runs from OpenSearch: {exc}")
            runs = []
    else:
        # Use DataFrame aggregation for synthetic mode
        runs = aggregate_recent_nightly_runs_from_dataframe(
            df, max_runs=10, date_range=date_range
        )

    # Serialize runs for store
    runs_data = [
        {
            'timestamp': run.timestamp.isoformat(),
            'test_count': run.test_count,
            'pass_count': run.pass_count,
            'fail_count': run.fail_count,
            'category_breakdown': run.category_breakdown,
            'source': run.source,
            'error': run.error,
        }
        for run in runs
    ]

    # Create section component
    section = create_nightly_runs_section(runs)

    return runs_data, section


@app.callback(
    Output('nightly-run-chart', 'figure'),
    [Input('nightly-run-selector', 'value'),
     Input('colorblind-mode-store', 'data')],
    [State('nightly-runs-store', 'data')],
)
def update_nightly_run_chart(selected_idx, colorblind_mode, runs_data):
    """
    Update category breakdown chart when user selects a different nightly run.
    """
    from src.components.nightly_runs import create_nightly_run_category_chart
    from src.query_service import NightlyRunSnapshot
    from datetime import datetime

    colorblind_mode = _normalize_colorblind_mode(colorblind_mode)

    if runs_data is None or selected_idx is None:
        return create_nightly_run_category_chart(None, colorblind_mode=colorblind_mode)

    if selected_idx < 0 or selected_idx >= len(runs_data):
        return create_nightly_run_category_chart(None, colorblind_mode=colorblind_mode)

    # Deserialize selected run
    run_dict = runs_data[selected_idx]
    run = NightlyRunSnapshot(
        timestamp=datetime.fromisoformat(run_dict['timestamp']),
        test_count=run_dict['test_count'],
        pass_count=run_dict['pass_count'],
        fail_count=run_dict['fail_count'],
        category_breakdown=run_dict['category_breakdown'],
        source=run_dict['source'],
        error=run_dict.get('error'),
    )

    return create_nightly_run_category_chart(run, colorblind_mode=colorblind_mode)


def parse_os_version_filters(os_vers):
    """
    Parse combined OS version filters in format 'distribution:version'.

    Args:
        os_vers: List of combined values like ['rhel:9.5', 'ubuntu:22.04']

    Returns:
        Set of (distribution, version) tuples for filtering
    """
    if not os_vers:
        return None

    parsed = set()
    for val in os_vers:
        if ':' in str(val):
            dist, version = val.split(':', 1)
            parsed.add((dist, version))
        else:
            # Legacy format - just version, match any distribution
            parsed.add((None, val))

    return parsed if parsed else None


@app.callback(
    Output('filtered-data-store', 'data'),
    [
        Input('filter-os-version', 'value'),
        Input('filter-instance-type', 'value'),
        Input('filter-test-name', 'value'),
        Input('filter-cloud-provider', 'value'),
        Input('header-date-range', 'start_date'),
        Input('header-date-range', 'end_date'),
        Input('filter-status', 'value'),
    ]
)
def update_filtered_data(os_vers, inst_types, tests, clouds, start_date, end_date, statuses):
    """Update the filtered dataset based on filter selections.

    Invalidates relevant cache entries when filters change to prevent stale data.
    """
    from src.cache_service import get_cache_service
    import logging

    logger = logging.getLogger(__name__)

    # Invalidate cache for all query types when filters change
    # This ensures fresh data is loaded with the new filter criteria
    cache_service = get_cache_service()
    invalidated = cache_service.clear()
    if invalidated:
        logger.info("Cache cleared due to filter change")

    # Convert date strings to timezone-aware datetime objects
    date_range_param = None
    if start_date and end_date:
        from datetime import timezone, timedelta
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        # Set end_dt to end of day (23:59:59) to include all records on that date
        end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
        date_range_param = (start_dt, end_dt)
    
    # Parse combined OS version filters (format: 'distribution:version')
    os_filter_pairs = parse_os_version_filters(os_vers)
    
    # Start with base filtering (everything except OS version)
    filtered_df = processor.filter_data(
        df,
        os_versions=None,  # We'll handle this separately
        instance_types=inst_types if inst_types else None,
        test_names=tests if tests else None,
        cloud_providers=clouds if clouds else None,
        date_range=date_range_param,
        status_filter=statuses if statuses else None
    )
    
    # Apply OS version filtering with distribution context
    if os_filter_pairs:
        import pandas as pd
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for dist, version in os_filter_pairs:
            if dist is None:
                # Legacy format - match any distribution with this version
                mask |= (filtered_df['os_version'] == version)
            else:
                # Combined format - match both distribution and version
                mask |= (
                    (filtered_df['os_distribution'] == dist) & 
                    (filtered_df['os_version'] == version)
                )
        filtered_df = filtered_df[mask]
    
    # Convert to JSON-serializable format
    return filtered_df.to_json(date_format='iso', orient='split')


@app.callback(
    Output('analysis-results-store', 'data'),
    Input('filtered-data-store', 'data')
)
def analyze_filtered_data(filtered_data_json):
    """Perform all three analyses on filtered data."""
    import pandas as pd
    
    if not filtered_data_json:
        return {}
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    if filtered_df.empty:
        return {}
    
    # Run all three analyses
    results = {}
    
    # Section 1: RHEL Regression Analysis
    try:
        results['q1'] = processor.analyze_rhel_simplified_regressions(filtered_df)
    except Exception as e:
        print(f"Error in RHEL Regression analysis: {e}")
        results['q1'] = {
            'summary': 'Analysis error', 
            'major_release_comparison': None,
            'rhel9_sequential': None,
            'rhel10_sequential': None,
            'total_regressions': 0
        }
    
    # Section 2: Competitive Performance (computed on-demand per user selection)
    # Just store a placeholder since we'll compute this when user selects a comparison
    results['q2'] = {'computed': 'on_demand'}
    
    # Section 3: Cloud Scaling (will be done dynamically based on user selection)
    results['q3'] = {}
    
    # Serialize DataFrames to JSON
    # Q1 simplified comparisons
    for comp_key in ['major_release_comparison', 'rhel9_sequential', 'rhel10_sequential']:
        if comp_key in results['q1'] and results['q1'][comp_key]:
            comp = results['q1'][comp_key]
            if 'comparison_data' in comp and isinstance(comp['comparison_data'], pd.DataFrame):
                comp['comparison_data'] = comp['comparison_data'].to_json(orient='split')
    
    # Q2 is computed on-demand, no serialization needed
    
    return json.dumps(results)


@app.callback(
    Output('q1-overall-summary', 'children'),
    Input('analysis-results-store', 'data')
)
def update_q1_overall_summary(analysis_json):
    """Update overall Q1 summary."""
    import pandas as pd
    
    if not analysis_json:
        return "Analyzing..."
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    
    total_regressions = q1_data.get('total_regressions', 0)
    summary_text = q1_data.get('summary', 'No data available')
    icon = get_status_icon(total_regressions)
    
    return dbc.Alert([
        html.H5([icon, " Overall Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color="warning" if total_regressions > 0 else "success")


@app.callback(
    [Output('q1-major-graph', 'figure'),
     Output('q1-major-summary', 'children')],
    [Input('analysis-results-store', 'data'),
     Input('colorblind-mode-store', 'data')]
)
def update_major_release_comparison(analysis_json, colorblind_mode):
    """Update major release comparison (9.X vs 10.X)."""
    import pandas as pd

    colorblind_mode = _normalize_colorblind_mode(colorblind_mode)

    if not analysis_json:
        return visualizations.create_empty_figure("Loading..."), ""
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    comp_data = q1_data.get('major_release_comparison')
    
    if not comp_data:
        return visualizations.create_empty_figure("No data available for this comparison"), dbc.Alert("No data available", color="info")
    
    # Recreate DataFrame from JSON
    comparison_df = None
    if comp_data.get('comparison_data'):
        comparison_df = pd.read_json(StringIO(comp_data['comparison_data']), orient='split')
        fig = visualizations.create_version_comparison_bar_chart(
            comparison_df,
            comp_data['baseline_version'],
            comp_data['comparison_version'],
            colorblind_mode=colorblind_mode
        )
    else:
        fig = visualizations.create_empty_figure("No data available")
    
    # Format summary with hardware information
    num_regressions = comp_data.get('num_regressions', 0)
    num_comparisons = comp_data.get('num_comparisons', 0)
    summary_text = comp_data.get('summary', 'No analysis available')
    hw_summary = comp_data.get('hardware_summary', '')
    icon = get_status_icon(num_regressions)
    discover_block = _q1_regression_discover_block(comparison_df)
    
    summary_component = dbc.Alert([
        html.Strong([icon, f" {num_regressions} regression(s) detected"]),
        html.Br(),
        html.Small(f"{num_comparisons} test×hardware comparison(s) | {hw_summary}", className="text-muted"),
        html.Hr(className="my-2"),
        dcc.Markdown(summary_text),
        *([html.Hr(className="my-2"), discover_block] if discover_block else []),
    ], color="warning" if num_regressions > 0 else "success")
    
    return fig, summary_component


@app.callback(
    [Output('q1-rhel9-graph', 'figure'),
     Output('q1-rhel9-summary', 'children')],
    [Input('analysis-results-store', 'data'),
     Input('colorblind-mode-store', 'data')]
)
def update_rhel9_sequential(analysis_json, colorblind_mode):
    """Update RHEL 9 sequential comparison."""
    import pandas as pd

    colorblind_mode = _normalize_colorblind_mode(colorblind_mode)

    if not analysis_json:
        return visualizations.create_empty_figure("Loading..."), ""
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    comp_data = q1_data.get('rhel9_sequential')
    
    if not comp_data:
        return visualizations.create_empty_figure("No data available for this comparison"), dbc.Alert("No data available", color="info")
    
    # Recreate DataFrame from JSON
    comparison_df = None
    if comp_data.get('comparison_data'):
        comparison_df = pd.read_json(StringIO(comp_data['comparison_data']), orient='split')
        fig = visualizations.create_version_comparison_bar_chart(
            comparison_df,
            comp_data['baseline_version'],
            comp_data['comparison_version'],
            colorblind_mode=colorblind_mode
        )
    else:
        fig = visualizations.create_empty_figure("No data available")
    
    # Format summary with hardware information
    num_regressions = comp_data.get('num_regressions', 0)
    num_comparisons = comp_data.get('num_comparisons', 0)
    summary_text = comp_data.get('summary', 'No analysis available')
    hw_summary = comp_data.get('hardware_summary', '')
    icon = get_status_icon(num_regressions)
    discover_block = _q1_regression_discover_block(comparison_df)
    
    summary_component = dbc.Alert([
        html.Strong([icon, f" {num_regressions} regression(s) detected"]),
        html.Br(),
        html.Small(f"{num_comparisons} test×hardware comparison(s) | {hw_summary}", className="text-muted"),
        html.Hr(className="my-2"),
        dcc.Markdown(summary_text),
        *([html.Hr(className="my-2"), discover_block] if discover_block else []),
    ], color="warning" if num_regressions > 0 else "success")
    
    return fig, summary_component


@app.callback(
    [Output('q1-rhel10-graph', 'figure'),
     Output('q1-rhel10-summary', 'children')],
    [Input('analysis-results-store', 'data'),
     Input('colorblind-mode-store', 'data')]
)
def update_rhel10_sequential(analysis_json, colorblind_mode):
    """Update RHEL 10 sequential comparison."""
    import pandas as pd

    colorblind_mode = _normalize_colorblind_mode(colorblind_mode)

    if not analysis_json:
        return visualizations.create_empty_figure("Loading..."), ""
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    comp_data = q1_data.get('rhel10_sequential')
    
    if not comp_data:
        return visualizations.create_empty_figure("No data available for this comparison"), dbc.Alert("No data available", color="info")
    
    # Recreate DataFrame from JSON
    comparison_df = None
    if comp_data.get('comparison_data'):
        comparison_df = pd.read_json(StringIO(comp_data['comparison_data']), orient='split')
        fig = visualizations.create_version_comparison_bar_chart(
            comparison_df,
            comp_data['baseline_version'],
            comp_data['comparison_version'],
            colorblind_mode=colorblind_mode
        )
    else:
        fig = visualizations.create_empty_figure("No data available")
    
    # Format summary with hardware information
    num_regressions = comp_data.get('num_regressions', 0)
    num_comparisons = comp_data.get('num_comparisons', 0)
    summary_text = comp_data.get('summary', 'No analysis available')
    hw_summary = comp_data.get('hardware_summary', '')
    icon = get_status_icon(num_regressions)
    discover_block = _q1_regression_discover_block(comparison_df)
    
    summary_component = dbc.Alert([
        html.Strong([icon, f" {num_regressions} regression(s) detected"]),
        html.Br(),
        html.Small(f"{num_comparisons} test×hardware comparison(s) | {hw_summary}", className="text-muted"),
        html.Hr(className="my-2"),
        dcc.Markdown(summary_text),
        *([html.Hr(className="my-2"), discover_block] if discover_block else []),
    ], color="warning" if num_regressions > 0 else "success")
    
    return fig, summary_component


@app.callback(
    Output('q2-comparison-selector', 'children'),
    Input('filtered-data-store', 'data')
)
def update_q2_comparison_selector(filtered_data_json):
    """Display the latest competitive comparison info (no selection needed)."""
    import pandas as pd
    
    if not filtered_data_json:
        return html.Div("Loading comparison...", className="text-muted")
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Get available comparisons
    available_comparisons = processor._get_available_comparisons(filtered_df, 'rhel')
    
    if not available_comparisons:
        return dbc.Alert([
            html.Strong("⚠️ No competitive comparisons available"),
            html.Br(),
            html.Small("Competitive comparisons require both RHEL and peer OS data on the same hardware.", 
                      className="text-muted")
        ], color="warning")
    
    # Use the latest comparison (first in the sorted list)
    latest_comp = available_comparisons[0]
    
    return html.Div([
        dbc.Badge("Latest", color="info", className="me-2"),
        html.Strong(latest_comp['label'], style={"color": "#0e7490"})
    ], className="mb-2 d-flex align-items-center")


@app.callback(
    Output('q2-analysis-store', 'data'),
    Input('filtered-data-store', 'data')
)
def update_q2_analysis(filtered_data_json):
    """Run Q2 competitive analysis and cache results.

    This callback performs the expensive analyze_peer_os_comparison operation
    and stores the result. Colorblind mode changes do not trigger this callback,
    avoiding redundant analysis.
    """
    import pandas as pd

    if not filtered_data_json:
        return None

    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')

    # Get available comparisons and use the latest one
    available_comparisons = processor._get_available_comparisons(filtered_df, 'rhel')

    if not available_comparisons:
        return {
            'comparison_data': None,
            'summary': 'No summary available',
            'competitive_count': 0,
            'total_benchmarks': 0,
            'comparison_config': None,
            'has_data': False
        }

    # Use the latest comparison (first in the sorted list)
    comp_config = available_comparisons[0]

    # Run targeted competitive analysis
    q2_result = processor.analyze_peer_os_comparison(
        filtered_df,
        baseline_os='rhel',
        peer_os_list=[comp_config['peer_os']],
        baseline_version=comp_config['baseline_version'],
        peer_version=comp_config['peer_version'],
        cloud_provider=comp_config['cloud_provider'],
        instance_type=None  # Don't filter to single HW, show all common HW
    )

    # Serialize comparison_data to JSON for storage
    comparison_df = q2_result['comparison_data']
    has_data = not comparison_df.empty

    return {
        'comparison_data': json.loads(comparison_df.to_json(orient='split')) if has_data else None,
        'summary': q2_result.get('summary', 'No summary available'),
        'competitive_count': q2_result.get('competitive_count', 0),
        'total_benchmarks': q2_result.get('total_benchmarks', 0),
        'comparison_config': comp_config,
        'has_data': has_data
    }


@app.callback(
    [Output('q2-comparison', 'figure'),
     Output('q2-summary', 'children')],
    [Input('q2-analysis-store', 'data'),
     Input('colorblind-mode-store', 'data')]
)
def update_q2_figure(analysis_data, colorblind_mode):
    """Render Q2 figure from cached analysis data.

    This callback only creates the visualization from pre-computed results.
    Colorblind mode toggle only triggers this render callback, not the expensive
    analysis callback.
    """
    import pandas as pd

    if not analysis_data:
        empty_fig = visualizations.create_empty_figure("Loading comparison data...")
        return empty_fig, ""

    if not analysis_data['has_data']:
        empty_fig = visualizations.create_empty_figure("No competitive comparisons available")
        return empty_fig, dbc.Alert([
            html.Strong("⚠️ No competitive comparisons available"),
            html.Br(),
            html.Small("Competitive comparisons require both RHEL and peer OS data on the same hardware.",
                      className="text-muted")
        ], color="warning")

    # Deserialize comparison_data from dict
    comparison_data = analysis_data['comparison_data']
    comparison_df = pd.DataFrame(
        comparison_data['data'],
        columns=comparison_data['columns'],
        index=comparison_data.get('index')
    )
    comp_config = analysis_data['comparison_config']

    # Create visualization
    fig = visualizations.create_peer_os_comparison_chart(
        comparison_df,
        baseline_os="RHEL",
        title=f"Performance Comparison: {comp_config['label']}",
        colorblind_mode=_normalize_colorblind_mode(colorblind_mode)
    )

    # Format summary
    summary_text = analysis_data['summary']
    competitive_count = analysis_data['competitive_count']
    total_benchmarks = analysis_data['total_benchmarks']

    # Determine status based on data availability and competitiveness
    if total_benchmarks == 0:
        # No data available - show warning status
        status_icon = "⚠️"
        alert_color = "warning"
    else:
        # Data available - check competitiveness
        is_competitive = competitive_count >= (total_benchmarks * 0.7)
        status_icon = get_status_icon(0 if is_competitive else 3)
        alert_color = "success" if is_competitive else "info"

    summary_component = dbc.Alert([
        html.H5([status_icon, " Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color=alert_color)

    return fig, summary_component


# ============================================================================
# Competitive Performance Category Drill-Down Callbacks
# ============================================================================

@app.callback(
    [Output('q2-category-detail-container', 'style'),
     Output('q2-detail-category-title', 'children'),
     Output('q2-detail-summary', 'children'),
     Output('q2-detail-benchmark-chart', 'figure'),
     Output('q2-selected-category-store', 'data')],
    [Input('q2-comparison', 'clickData'),
     Input('btn-q2-close-detail', 'n_clicks')],
    [State('filtered-data-store', 'data')],
    prevent_initial_call=True
)
def handle_category_click(click_data, close_clicks, filtered_data_json):
    """Handle click on category bar to show inline detail panel."""
    import pandas as pd
    from dash import ctx
    
    # Check what triggered the callback
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # If close button clicked, hide the panel
    if trigger_id == 'btn-q2-close-detail':
        empty_fig = visualizations.create_empty_figure("")
        return {"display": "none"}, "", "", empty_fig, None
    
    # If no click data or no filtered data, hide panel
    if not click_data or not filtered_data_json:
        empty_fig = visualizations.create_empty_figure("")
        return {"display": "none"}, "", "", empty_fig, None
    
    # Extract clicked category
    try:
        category = click_data['points'][0]['x']
    except (KeyError, IndexError):
        empty_fig = visualizations.create_empty_figure("")
        return {"display": "none"}, "", "", empty_fig, None
    
    # Load filtered data and run comparison analysis
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Get available comparisons and use the latest one
    available_comparisons = processor._get_available_comparisons(filtered_df, 'rhel')
    
    if not available_comparisons:
        empty_fig = visualizations.create_empty_figure("No comparison data")
        return {"display": "none"}, "", "", empty_fig, None
    
    comp_config = available_comparisons[0]
    
    # Run competitive analysis
    q2_result = processor.analyze_peer_os_comparison(
        filtered_df,
        baseline_os='rhel',
        peer_os_list=[comp_config['peer_os']],
        baseline_version=comp_config['baseline_version'],
        peer_version=comp_config['peer_version'],
        cloud_provider=comp_config['cloud_provider'],
        instance_type=None
    )
    
    if q2_result['comparison_data'].empty:
        empty_fig = visualizations.create_empty_figure("No data for this category")
        return {"display": "none"}, "", "", empty_fig, None
    
    comparison_df = q2_result['comparison_data']
    
    # Filter to selected category
    category_df = comparison_df[comparison_df['benchmark_category'] == category]
    
    if category_df.empty:
        empty_fig = visualizations.create_empty_figure(f"No benchmarks found in {category}")
        return {"display": "none"}, "", "", empty_fig, None
    
    # Create summary stats
    num_benchmarks = category_df['test_name'].nunique()
    num_hardware = category_df['instance_type'].nunique()
    avg_perf = category_df['relative_performance'].mean()
    competitive_pct = (category_df['is_competitive'].sum() / len(category_df)) * 100
    
    # Determine status color
    if competitive_pct >= 80:
        status_color = "success"
        status_icon = "✅"
    elif competitive_pct >= 50:
        status_color = "warning"
        status_icon = "⚠️"
    else:
        status_color = "danger"
        status_icon = "❌"
    
    summary_content = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(num_benchmarks, className="mb-0 text-primary"),
                    html.Small("Benchmarks", className="text-muted")
                ], className="text-center py-2")
            ], className="h-100")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(num_hardware, className="mb-0 text-info"),
                    html.Small("Hardware Configs", className="text-muted")
                ], className="text-center py-2")
            ], className="h-100")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{avg_perf:.1f}%", className="mb-0", 
                           style={"color": "#1a9850" if 90 <= avg_perf <= 110 else "#d97706"}),
                    html.Small("Avg. Relative Perf", className="text-muted")
                ], className="text-center py-2")
            ], className="h-100")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4([status_icon, f" {competitive_pct:.0f}%"], className="mb-0"),
                    html.Small("Competitive Rate", className="text-muted")
                ], className="text-center py-2")
            ], className="h-100", color=status_color, outline=True)
        ], width=3),
    ], className="g-2")
    
    # Create benchmark detail chart
    detail_fig = visualizations.create_category_benchmark_detail_chart(
        category_df, category, baseline_os="RHEL"
    )
    
    # Store category data for modal
    store_data = {
        'category': category,
        'comp_config': comp_config,
        'category_data': category_df.to_json(orient='split')
    }
    
    detail_header = html.Div([
        competitive_performance_breadcrumb(category),
        html.Div(f"📊 {category} benchmarks", className="fw-semibold mt-1"),
    ])
    
    return {"display": "block"}, detail_header, summary_content, detail_fig, store_data


@app.callback(
    [Output('q2-category-modal', 'is_open'),
     Output('q2-modal-title', 'children'),
     Output('q2-modal-summary', 'children')],
    [Input('btn-q2-open-modal', 'n_clicks'),
     Input('btn-q2-modal-close', 'n_clicks')],
    [State('q2-category-modal', 'is_open'),
     State('q2-selected-category-store', 'data')],
    prevent_initial_call=True
)
def toggle_category_modal(open_clicks, close_clicks, is_open, store_data):
    """Open/close the category detail modal."""
    import pandas as pd
    from dash import ctx
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    if trigger_id == 'btn-q2-modal-close':
        return False, "", ""
    
    if trigger_id == 'btn-q2-open-modal' and store_data:
        category = store_data.get('category', 'Unknown')
        comp_config = store_data.get('comp_config', {})
        category_data_json = store_data.get('category_data')
        
        if category_data_json:
            category_df = pd.read_json(StringIO(category_data_json), orient='split')
            
            # Build modal summary
            num_benchmarks = category_df['test_name'].nunique()
            num_hardware = category_df['instance_type'].nunique()
            total_comparisons = len(category_df)
            competitive_count = category_df['is_competitive'].sum()
            
            # Find best and worst performers
            benchmark_perf = category_df.groupby('test_name')['relative_performance'].mean().sort_values()
            
            worst_benchmark = benchmark_perf.index[0] if len(benchmark_perf) > 0 else "N/A"
            worst_perf = benchmark_perf.iloc[0] if len(benchmark_perf) > 0 else 0
            best_benchmark = benchmark_perf.index[-1] if len(benchmark_perf) > 0 else "N/A"
            best_perf = benchmark_perf.iloc[-1] if len(benchmark_perf) > 0 else 0
            
            summary_content = html.Div([
                dbc.Alert([
                    html.H5(f"📈 {category} - Detailed Analysis", className="mb-3"),
                    html.P([
                        f"Comparing ",
                        html.Strong(f"RHEL {comp_config.get('baseline_version', '?')}"),
                        " vs ",
                        html.Strong(f"{comp_config.get('peer_os', '?').upper()} {comp_config.get('peer_version', '?')}"),
                        f" on {comp_config.get('cloud_provider', '?').upper()}"
                    ], className="mb-2"),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Strong(f"{num_benchmarks}"),
                            html.Span(" benchmarks tested", className="text-muted")
                        ], width=4),
                        dbc.Col([
                            html.Strong(f"{num_hardware}"),
                            html.Span(" hardware configurations", className="text-muted")
                        ], width=4),
                        dbc.Col([
                            html.Strong(f"{competitive_count}/{total_comparisons}"),
                            html.Span(" competitive results", className="text-muted")
                        ], width=4),
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Strong("🏆 Best Performer: ", className="text-success"),
                                html.Span(f"{best_benchmark} ({best_perf:.1f}%)")
                            ])
                        ], width=6),
                        dbc.Col([
                            html.Div([
                                html.Strong("⚠️ Needs Attention: ", className="text-warning"),
                                html.Span(f"{worst_benchmark} ({worst_perf:.1f}%)")
                            ])
                        ], width=6),
                    ])
                ], color="info")
            ])
            
            title = html.Div([
                competitive_performance_breadcrumb(category),
                html.Div(f"{category} — deep dive analysis", className="fw-semibold mt-1"),
            ])
            return True, title, summary_content
    
    return is_open, "", ""


@app.callback(
    Output('q2-modal-tab-content', 'children'),
    [Input('q2-modal-tabs', 'active_tab'),
     Input('q2-category-modal', 'is_open')],
    [State('q2-selected-category-store', 'data')],
    prevent_initial_call=True
)
def update_modal_tab_content(active_tab, is_open, store_data):
    """Update modal content based on selected tab."""
    import pandas as pd
    
    if not is_open or not store_data:
        return html.Div()
    
    category = store_data.get('category', 'Unknown')
    category_data_json = store_data.get('category_data')
    
    if not category_data_json:
        return dbc.Alert("No data available", color="warning")
    
    category_df = pd.read_json(StringIO(category_data_json), orient='split')
    
    if active_tab == "tab-benchmarks":
        # Benchmark breakdown chart
        fig = visualizations.create_category_benchmark_detail_chart(
            category_df, category, baseline_os="RHEL"
        )
        return dcc.Graph(figure=fig)
    
    elif active_tab == "tab-hardware":
        # Hardware matrix heatmap
        fig = visualizations.create_category_hardware_heatmap(
            category_df, category, baseline_os="RHEL"
        )
        return dcc.Graph(figure=fig)
    
    elif active_tab == "tab-data":
        # Raw data table
        display_df = category_df[[
            'test_name', 'instance_type', 'baseline_value', 'peer_value', 
            'relative_performance', 'is_competitive'
        ]].copy()
        
        display_df['relative_performance'] = display_df['relative_performance'].round(1)
        display_df['baseline_value'] = display_df['baseline_value'].round(2)
        display_df['peer_value'] = display_df['peer_value'].round(2)
        display_df['is_competitive'] = display_df['is_competitive'].map({True: '✅', False: '❌'})
        
        display_df.columns = ['Benchmark', 'Hardware', 'RHEL Value', 'Peer Value', 
                             'Relative %', 'Competitive']
        
        # Sort by relative performance
        display_df = display_df.sort_values('Relative %', ascending=True)
        
        return dbc.Table.from_dataframe(
            display_df,
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="small"
        )
    
    return html.Div()


def extract_instance_series(instance_type: str, cloud_provider: str) -> str:
    """
    Extract the instance series/family from a full instance type name.
    
    Examples:
        - AWS: "m5.24xlarge" -> "m5"
        - Azure: "Standard_D96s_v3" -> "Standard_Ds_v3"
        - GCP: "c4-standard-96" -> "c4-standard"
    """
    import re
    
    if not instance_type:
        return instance_type
    
    if cloud_provider == 'aws':
        # AWS format: m5.24xlarge -> m5
        # Split on dot and take the first part (family)
        return instance_type.split('.')[0]
    
    elif cloud_provider == 'azure':
        # Azure format: Standard_D96s_v3 -> Standard_Ds_v3
        # Remove the numeric size portion but keep the series letter and version
        match = re.match(r'(Standard_[A-Z])(\d+)(s?)(_v\d+)?', instance_type)
        if match:
            prefix, _, s_suffix, version = match.groups()
            return f"{prefix}{s_suffix or ''}{version or ''}"
        return instance_type
    
    elif cloud_provider == 'gcp':
        # GCP format: c4-standard-96 -> c4-standard
        # Remove the trailing number (vCPU count)
        parts = instance_type.rsplit('-', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
        return instance_type
    
    return instance_type


# Cascading dropdown callbacks for Cloud Scaling section
@app.callback(
    [Output('q3-instance-series', 'options'),
     Output('q3-instance-series', 'value')],
    [Input('q3-cloud-provider', 'value'),
     Input('filtered-data-store', 'data')],
    [State('q3-instance-series', 'value')]
)
def update_instance_series_options(cloud_provider, filtered_data_json, current_value):
    """Update instance series dropdown options based on selected cloud provider and available data."""
    import pandas as pd
    
    if not cloud_provider or not filtered_data_json:
        return [], None
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Filter to selected cloud provider and get available instance types
    cloud_df = filtered_df[filtered_df['cloud_provider'] == cloud_provider]
    instance_types = cloud_df['instance_type'].dropna().unique().tolist()
    
    if not instance_types:
        return [], None
    
    # Extract unique instance series from instance types
    instance_series = set()
    for it in instance_types:
        series = extract_instance_series(it, cloud_provider)
        if series:
            instance_series.add(series)
    
    instance_series = sorted(instance_series)
    
    if not instance_series:
        return [], None
    
    options = [{'label': series, 'value': series} for series in instance_series]
    
    # Keep current value if still valid, otherwise default to first
    if current_value in instance_series:
        default_value = current_value
    else:
        default_value = instance_series[0]
    
    return options, default_value


@app.callback(
    [Output('q3-os-version', 'options'),
     Output('q3-os-version', 'value')],
    [Input('q3-os-distribution', 'value'),
     Input('q3-cloud-provider', 'value'),
     Input('q3-instance-series', 'value'),
     Input('filtered-data-store', 'data')],
    [State('q3-os-version', 'value')]
)
def update_os_version_options(os_distribution, cloud_provider, instance_series, filtered_data_json, current_value):
    """Update OS version dropdown options based on selected OS and available data."""
    import pandas as pd
    
    if not os_distribution or not filtered_data_json:
        return [], None
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Apply filters to find what OS versions have data for the current selection
    os_df = filtered_df[filtered_df['os_distribution'] == os_distribution]
    
    if cloud_provider:
        os_df = os_df[os_df['cloud_provider'] == cloud_provider]
    
    if instance_series:
        # Filter by instance series (match instances that start with the series prefix)
        os_df = os_df[os_df['instance_type'].apply(
            lambda x: extract_instance_series(x, cloud_provider) == instance_series if pd.notna(x) else False
        )]
    
    versions = sorted(os_df['os_version'].dropna().unique().tolist())
    
    if not versions:
        return [], None
    
    options = [{'label': v, 'value': v} for v in versions]
    
    # Keep current value if still valid, otherwise default to latest (last in sorted list)
    if current_value in versions:
        default_value = current_value
    else:
        default_value = versions[-1]
    
    return options, default_value


@app.callback(
    [Output('q3-os-distribution', 'options'),
     Output('q3-os-distribution', 'value')],
    [Input('q3-cloud-provider', 'value'),
     Input('q3-instance-series', 'value'),
     Input('filtered-data-store', 'data')],
    [State('q3-os-distribution', 'value')]
)
def update_os_distribution_options(cloud_provider, instance_series, filtered_data_json, current_value):
    """Update OS distribution dropdown options based on available data."""
    import pandas as pd
    
    if not filtered_data_json:
        return [], None
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Apply filters to find what OS distributions have data
    if cloud_provider:
        filtered_df = filtered_df[filtered_df['cloud_provider'] == cloud_provider]
    
    if instance_series:
        # Filter by instance series (match instances that belong to this series)
        filtered_df = filtered_df[filtered_df['instance_type'].apply(
            lambda x: extract_instance_series(x, cloud_provider) == instance_series if pd.notna(x) else False
        )]
    
    distributions = sorted(filtered_df['os_distribution'].dropna().unique().tolist())
    
    if not distributions:
        return [], None
    
    options = [{'label': dist.upper(), 'value': dist} for dist in distributions]
    
    # Keep current value if still valid, otherwise default to first
    if current_value in distributions:
        default_value = current_value
    else:
        default_value = distributions[0]
    
    return options, default_value


@app.callback(
    Output('q3-analysis-store', 'data'),
    [Input('filtered-data-store', 'data'),
     Input('q3-cloud-provider', 'value'),
     Input('q3-instance-series', 'value'),
     Input('q3-os-distribution', 'value'),
     Input('q3-os-version', 'value')],
    prevent_initial_call=True
)
def update_q3_analysis(filtered_data_json, cloud_provider, instance_series, os_distribution, os_version):
    """Run Q3 cloud scaling analysis and cache results.

    This callback performs the expensive analyze_cloud_scaling operation
    and stores the result. Colorblind mode changes and benchmark category
    filters do not trigger this callback, avoiding redundant analysis.
    """
    import pandas as pd

    if not filtered_data_json or not cloud_provider or not os_version:
        return {
            'scaling_data': None,
            'summary': 'No summary available',
            'linear_scaling_count': 0,
            'total_benchmarks': 0,
            'cloud_provider': cloud_provider,
            'os_version': os_version,
            'os_distribution': os_distribution,
            'instance_series': instance_series,
            'has_data': False
        }

    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')

    # Apply additional filters for OS distribution and instance series
    if os_distribution:
        filtered_df = filtered_df[filtered_df['os_distribution'] == os_distribution]

    if instance_series:
        # Filter by instance series (match instances that belong to this series)
        filtered_df = filtered_df[filtered_df['instance_type'].apply(
            lambda x: extract_instance_series(x, cloud_provider) == instance_series if pd.notna(x) else False
        )]

    # Run scaling analysis
    q3_result = processor.analyze_cloud_scaling(
        filtered_df,
        cloud_provider=cloud_provider,
        os_version=os_version
    )

    # Serialize scaling_data to JSON for storage
    scaling_data = q3_result['scaling_data']
    has_data = not scaling_data.empty

    return {
        'scaling_data': json.loads(scaling_data.to_json(orient='split')) if has_data else None,
        'summary': q3_result.get('summary', 'No summary available'),
        'linear_scaling_count': q3_result.get('linear_scaling_count', 0),
        'total_benchmarks': q3_result.get('total_benchmarks', 0),
        'cloud_provider': cloud_provider,
        'os_version': os_version,
        'os_distribution': os_distribution,
        'instance_series': instance_series,
        'has_data': has_data
    }


@app.callback(
    [Output('q3-scaling', 'figure'),
     Output('q3-summary', 'children')],
    [Input('q3-analysis-store', 'data'),
     Input('q3-benchmark-category', 'value'),
     Input('colorblind-mode-store', 'data')]
)
def render_q3_figure(analysis_data, benchmark_category, colorblind_mode):
    """Render Q3 figure from cached analysis data.

    This callback only creates the visualization from pre-computed results.
    Colorblind mode toggle and benchmark category filter only trigger this
    render callback, not the expensive analysis callback.
    """
    import pandas as pd

    colorblind_mode = _normalize_colorblind_mode(colorblind_mode)

    if not analysis_data:
        empty_fig = visualizations.create_empty_figure("Loading...")
        return empty_fig, ""

    if not analysis_data['has_data']:
        empty_fig = visualizations.create_empty_figure("Select cloud provider and OS version")
        return empty_fig, ""

    # Deserialize scaling_data from dict
    scaling_dict = analysis_data['scaling_data']
    scaling_data = pd.DataFrame(
        scaling_dict['data'],
        columns=scaling_dict['columns'],
        index=scaling_dict.get('index')
    )

    # Filter scaling data by benchmark category if specified
    if not scaling_data.empty and benchmark_category and benchmark_category != 'all':
        scaling_data = scaling_data[scaling_data['benchmark_category'] == benchmark_category]

    # Create visualization
    if not scaling_data.empty:
        # Build descriptive title
        cloud_provider = analysis_data['cloud_provider']
        os_version = analysis_data['os_version']
        os_distribution = analysis_data['os_distribution']
        instance_series = analysis_data['instance_series']

        title_parts = [f"Performance Scaling: {(os_distribution or 'ALL').upper()} {os_version}"]
        title_parts.append(f"on {cloud_provider.upper()}")
        if instance_series:
            title_parts.append(f"({instance_series})")
        if benchmark_category and benchmark_category != 'all':
            title_parts.append(f"- {benchmark_category}")
        chart_title = " ".join(title_parts)

        fig = visualizations.create_cloud_scaling_chart(
            scaling_data,
            title=chart_title,
            colorblind_mode=colorblind_mode
        )
    else:
        fig = visualizations.create_empty_figure("No scaling data available for selected configuration")

    # Format summary
    summary_text = analysis_data['summary']
    linear_count = analysis_data.get('linear_scaling_count', 0)
    total = analysis_data.get('total_benchmarks', 0)

    # Determine status based on data availability and scaling quality
    if total == 0:
        # No data available - show warning status
        status_icon = "⚠️"
        alert_color = "warning"
    else:
        # Data available - check scaling quality
        good_scaling = linear_count >= (total * 0.7)
        status_icon = get_status_icon(0 if good_scaling else 2)
        alert_color = "success" if good_scaling else "info"

    summary_component = dbc.Alert([
        html.H5([status_icon, " Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color=alert_color)

    return fig, summary_component


@app.callback(
    Output('main-content', 'children'),
    Input('navigation-state', 'data')
)
def render_main_content(nav_state):
    """Render main content based on navigation state."""
    if not nav_state or nav_state['view'] == 'overview':
        return create_overview_layout()
    elif nav_state['view'] == 'investigation':
        params = nav_state.get('investigation_params', {})
        test_name = params.get('test_name', 'Unknown')
        benchmark_category = processor.get_benchmark_category(test_name)
        return create_investigation_layout(
            test_name=test_name,
            baseline_version=params.get('baseline_version', 'N/A'),
            comparison_version=params.get('comparison_version', 'N/A'),
            os_distribution=params.get('os_distribution', 'rhel'),
            benchmark_category=benchmark_category,
        )
    elif nav_state['view'] == 'track':
        return create_track_mode_layout()
    else:
        return create_overview_layout()


@app.callback(
    Output('navigation-state', 'data'),
    [Input('q1-major-graph', 'clickData'),
     Input('q1-rhel9-graph', 'clickData'),
     Input('q1-rhel10-graph', 'clickData'),
     Input('btn-view-benchmarks', 'n_clicks'),
     Input('btn-view-comparisons', 'n_clicks'),
     Input('btn-view-table', 'n_clicks'),
     Input('btn-track-mode', 'n_clicks')],
    [State('navigation-state', 'data'),
     State('analysis-results-store', 'data')],
    prevent_initial_call=True
)
def handle_navigation(major_click, rhel9_click, rhel10_click, benchmarks_click, comparisons_click, table_click, track_click, current_nav, analysis_json):
    """Handle navigation between views.

    Invalidates mode-specific cache when switching between Pulse and Track modes.
    """
    from dash import ctx
    from src.cache_service import get_cache_service
    import logging

    logger = logging.getLogger(__name__)
    
    if not ctx.triggered:
        return current_nav
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Bar chart click - drill into investigation
    if trigger_id in ['q1-major-graph', 'q1-rhel9-graph', 'q1-rhel10-graph']:
        click_data = None
        comp_key = None
        
        if trigger_id == 'q1-major-graph' and major_click:
            click_data = major_click
            comp_key = 'major_release_comparison'
        elif trigger_id == 'q1-rhel9-graph' and rhel9_click:
            click_data = rhel9_click
            comp_key = 'rhel9_sequential'
        elif trigger_id == 'q1-rhel10-graph' and rhel10_click:
            click_data = rhel10_click
            comp_key = 'rhel10_sequential'
        
        if click_data and analysis_json:
            try:
                analysis = json.loads(analysis_json)
                q1_data = analysis.get('q1', {})
                comp_data = q1_data.get(comp_key)
                
                if comp_data:
                    point = click_data['points'][0]
                    test_name = point.get('y', 'Unknown')
                    
                    return {
                        'view': 'investigation',
                        'investigation_params': {
                            'test_name': test_name,
                            'baseline_version': comp_data['baseline_version'],
                            'comparison_version': comp_data['comparison_version'],
                            'os_distribution': 'rhel'
                        }
                    }
            except Exception as e:
                print(f"Error parsing bar chart click: {e}")
                return current_nav

    # Track mode button
    if trigger_id == 'btn-track-mode':
        # Invalidate Pulse cache when switching to Track mode
        cache_service = get_cache_service()
        invalidated = cache_service.invalidate_by_mode('pulse')
        logger.info(f"Switched to Track mode, invalidated {invalidated} Pulse cache entries")
        return {'view': 'track', 'investigation_params': None}

    # Other navigation buttons - stay on overview for now (future: navigate to specific tabs)
    return current_nav


@app.callback(
    Output('navigation-state', 'data', allow_duplicate=True),
    [Input('btn-back-to-overview', 'n_clicks'),
     Input('btn-back-to-overview-track', 'n_clicks')],
    prevent_initial_call=True
)
def handle_back_to_overview(investigation_back, track_back):
    """Handle back to overview navigation from investigation or track mode.

    Invalidates Track cache when returning to overview (Pulse mode).
    """
    from src.cache_service import get_cache_service
    import logging

    logger = logging.getLogger(__name__)

    # Invalidate Track cache when returning to overview
    cache_service = get_cache_service()
    invalidated = cache_service.invalidate_by_mode('track')
    logger.info(f"Returned to overview, invalidated {invalidated} Track cache entries")

    return {'view': 'overview', 'investigation_params': None}


@app.callback(
    [Output('investigation-summary', 'children'),
     Output('investigation-comparison-chart', 'figure'),
     Output('investigation-timeline-chart', 'figure'),
     Output('investigation-table', 'children')],
    [Input('navigation-state', 'data'),
     Input('filtered-data-store', 'data'),
     Input('colorblind-mode-store', 'data')],
    prevent_initial_call=True
)
def update_investigation_view(nav_state, filtered_data_json, colorblind_mode):
    """Update investigation drill-down view."""
    import pandas as pd

    # Normalize colorblind_mode to bool
    colorblind_mode = _normalize_colorblind_mode(colorblind_mode)

    empty_fig = visualizations.create_empty_figure("No investigation data")

    if not nav_state or nav_state['view'] != 'investigation':
        return "", empty_fig, empty_fig, ""

    params = nav_state.get('investigation_params', {})
    test_name = params.get('test_name', 'Unknown')
    baseline_version = params.get('baseline_version', 'N/A')
    comparison_version = params.get('comparison_version', 'N/A')
    os_distribution = params.get('os_distribution', 'rhel')

    # P1-A: bounded OpenSearch query from investigation template (not capped scroll slice)
    use_server_investigation = (
        DATA_MODE == "opensearch"
        and OPENSEARCH_LOAD_ERROR is None
        and not SYNTHETIC_AFTER_OPENSEARCH_FAILURE
    )
    investigation_scope_note = None

    if use_server_investigation:
        try:
            client = BenchmarkDataSource()
            tid, _normalized, sources = fetch_investigation_documents(params, client)
            test_df = processor.documents_to_dataframe(sources)
            investigation_scope_note = (
                f"Data: OpenSearch template {tid} ({len(test_df)} run document(s); "
                "scoped query, not limited to the overview document cap)."
            )
        except InvestigationTemplateError as exc:
            summary = dbc.Alert(
                ["Invalid investigation parameters: ", html.Code(str(exc))],
                color="danger",
            )
            return summary, empty_fig, empty_fig, ""
        except Exception as exc:  # noqa: BLE001 — OpenSearch errors vary
            summary = dbc.Alert(
                ["Investigation query failed: ", html.Code(str(exc))],
                color="warning",
            )
            return summary, empty_fig, empty_fig, ""
    else:
        if not filtered_data_json:
            return "", empty_fig, empty_fig, ""
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
        # Filter data for this specific test and OS distribution
        test_df = filtered_df[
            (filtered_df['test_name'] == test_name)
            & (filtered_df['os_distribution'].str.lower() == os_distribution.lower())
        ]

    if test_df.empty:
        empty_fig = visualizations.create_empty_figure(f"No data for {test_name}")
        summary = dbc.Alert("No data available for this test", color="warning")
        return summary, empty_fig, empty_fig, ""
    
    # Split into baseline and comparison
    baseline_df = test_df[test_df['os_version'] == baseline_version]
    comparison_df = test_df[test_df['os_version'] == comparison_version]
    
    # Generate summary
    summary_data = summarize_investigation_details(
        baseline_df, comparison_df, test_name, baseline_version, comparison_version
    )
    
    summary_text = format_investigation_summary_text(summary_data)
    
    # Determine alert color based on status
    alert_color = summary_data.get('status', 'info')
    status_icon = get_status_icon(1 if summary_data.get('is_regression', False) else 0)
    
    summary_children = [
        html.H4([status_icon, f" {summary_data.get('status_text', 'Analysis')}"], className="mb-3"),
        dcc.Markdown(summary_text),
    ]
    if investigation_scope_note:
        summary_children.append(
            html.P(investigation_scope_note, className="text-muted small mb-0")
        )
    summary_component = dbc.Alert(summary_children, color=alert_color)
    
    # Create comparison chart
    comparison_fig = visualizations.create_investigation_detail_chart(
        baseline_df, comparison_df, test_name, baseline_version, comparison_version,
        colorblind_mode=colorblind_mode
    )

    # Create timeline chart
    timeline_fig = visualizations.create_time_series_chart(
        test_df,
        x_col='timestamp',
        y_col='primary_metric_value',
        color_col='os_version',
        title=f"Performance Trend: {test_name}",
        use_facets=False,
        colorblind_mode=colorblind_mode
    )

    # Create detailed table
    table_df = test_df[[
        'timestamp', 'os_version', 'instance_type', 'cloud_provider',
        'primary_metric_value', 'primary_metric_unit', 'status'
    ]].sort_values('timestamp', ascending=False).head(50)

    table_fig = visualizations.create_metrics_table(
        table_df,
        title=f"Recent Test Runs (showing {len(table_df)} of {len(test_df)} total)",
        colorblind_mode=colorblind_mode
    )

    dashboards_base = (os.getenv("OPENSEARCH_DASHBOARDS_BASE_URL") or "").strip()
    idx_name = results_index_name() or "zathras-results"
    recent = test_df.sort_values("timestamp", ascending=False).iloc[0]
    doc_id = recent.get("document_id")
    discover_row = None
    if dashboards_base and doc_id is not None and not pd.isna(doc_id):
        try:
            discover_url = opensearch_discover_url_for_document(
                dashboards_base,
                idx_name,
                str(doc_id),
            )
            discover_row = html.Div(
                [
                    html.A(
                        "View in OpenSearch Discover (most recent run)",
                        href=discover_url,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="fw-semibold",
                    ),
                    html.Span(f" — document_id: {doc_id}", className="text-muted small ms-1"),
                ],
                className="mt-2 mb-0",
            )
        except ValueError:
            discover_row = html.P(
                "Could not build Discover link for this run.",
                className="text-muted small mt-2 mb-0",
            )
    elif not dashboards_base:
        discover_row = html.P(
            [
                html.Span("Discover link: ", className="text-muted small"),
                html.Small(
                    "Set OPENSEARCH_DASHBOARDS_BASE_URL in .env to open runs in OpenSearch Dashboards.",
                    className="text-muted",
                ),
            ],
            className="mt-2 mb-0",
        )
    else:
        discover_row = html.P(
            "No document_id on the most recent row; Discover link unavailable.",
            className="text-muted small mt-2 mb-0",
        )

    table_component = html.Div(
        [
            dcc.Graph(figure=table_fig),
            discover_row,
        ],
        className="investigation-table-block",
    )

    return summary_component, comparison_fig, timeline_fig, table_component


# --- Track Mode Callbacks (RPOPC-1165) ---


@app.callback(
    [Output('track-summary-metrics', 'children'),
     Output('track-exception-table', 'children')],
    Input('btn-run-track-comparison', 'n_clicks'),
    [State('track-baseline-date-range', 'start_date'),
     State('track-baseline-date-range', 'end_date'),
     State('track-baseline-id', 'value'),
     State('track-nightly-date-range', 'start_date'),
     State('track-nightly-date-range', 'end_date')],
    prevent_initial_call=True
)
def run_track_comparison(
    n_clicks,
    baseline_start,
    baseline_end,
    baseline_id,
    nightly_start,
    nightly_end
):
    """
    Run baseline vs nightly comparison and display results.

    Fetches baseline and nightly data, calculates deltas, and shows
    exception-oriented view (regressions, improvements, missing benchmarks).
    """
    from datetime import datetime

    # Validate inputs
    if not baseline_start or not baseline_end or not nightly_start or not nightly_end:
        return (
            dbc.Alert("Please select baseline and nightly date ranges", color="warning"),
            html.P("Configure dates to run comparison", className="text-muted")
        )

    baseline_id = baseline_id or "manual-baseline"

    # Run comparison based on data mode
    if DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is None:
        try:
            client = BenchmarkDataSource()

            # Build baseline filter by date range
            baseline_filter = {
                "range": {
                    "metadata.test_timestamp": {
                        "gte": baseline_start,
                        "lte": baseline_end,
                    }
                }
            }

            # Nightly date range
            nightly_date_range = (nightly_start, nightly_end)

            # Fetch comparison
            snapshot = fetch_baseline_comparison_aggregates(
                client,
                baseline_filter=baseline_filter,
                nightly_date_range=nightly_date_range,
                baseline_id=baseline_id,
                max_regressions=50,
                max_improvements=20,
                max_missing=10,
                max_added=10,
            )
        except Exception as exc:
            logger.error(f"Failed to fetch baseline comparison from OpenSearch: {exc}")
            return (
                dbc.Alert(f"Error: {exc}", color="danger"),
                html.P("Comparison failed", className="text-muted")
            )
    else:
        # Use synthetic data mode
        try:
            # Filter baseline data by date range
            baseline_start_dt = datetime.fromisoformat(baseline_start.replace('Z', '+00:00'))
            baseline_end_dt = datetime.fromisoformat(baseline_end.replace('Z', '+00:00'))
            baseline_df = df[
                (df['timestamp'] >= baseline_start_dt) &
                (df['timestamp'] <= baseline_end_dt)
            ]

            # Filter nightly data by date range
            nightly_start_dt = datetime.fromisoformat(nightly_start.replace('Z', '+00:00'))
            nightly_end_dt = datetime.fromisoformat(nightly_end.replace('Z', '+00:00'))
            nightly_df = df[
                (df['timestamp'] >= nightly_start_dt) &
                (df['timestamp'] <= nightly_end_dt)
            ]

            # Calculate comparison
            snapshot = aggregate_baseline_comparison_from_dataframe(
                baseline_df=baseline_df,
                nightly_df=nightly_df,
                baseline_id=baseline_id,
                max_regressions=50,
                max_improvements=20,
                max_missing=10,
                max_added=10,
            )
        except Exception as exc:
            logger.error(f"Failed to calculate baseline comparison from DataFrame: {exc}")
            return (
                dbc.Alert(f"Error: {exc}", color="danger"),
                html.P("Comparison failed", className="text-muted")
            )

    # Render results
    summary = create_track_summary_metrics(snapshot)
    table = create_track_exception_table(snapshot)

    return summary, table


@app.callback(
    [Output('filter-os-version', 'value'),
     Output('filter-instance-type', 'value'),
     Output('filter-test-name', 'value'),
     Output('filter-cloud-provider', 'value'),
     Output('filter-status', 'value')],
    Input('btn-reset-filters', 'n_clicks'),
    prevent_initial_call=True
)
def reset_filters(n_clicks):
    """Reset all filters to default values."""
    # Generate combined OS version values (distribution:version format)
    combined_os_versions = []
    for dist, versions in os_version_map.items():
        for version in versions:
            combined_os_versions.append(f"{dist}:{version}")
    
    return combined_os_versions, instance_types, test_names, cloud_providers, ['PASS', 'FAIL', 'UNKNOWN']


# AI Widget Callbacks (RPOPC-1014)

@app.callback(
    Output('ai-widget-custom-query-container', 'style'),
    Input('ai-widget-analysis-type', 'value')
)
def toggle_custom_query_input(analysis_type):
    """Show/hide custom query input based on analysis type."""
    if analysis_type == 'custom':
        return {'display': 'block'}
    return {'display': 'none'}


@app.callback(
    Output('ai-widget-context-collapse', 'is_open'),
    Input('ai-widget-analyze-btn', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_context_summary(n_clicks):
    """Show context summary on Analyze button click."""
    if n_clicks:
        return True
    return False


@app.callback(
    Output('ai-widget-context-summary', 'children'),
    Input('filter-os-version', 'value'),
    Input('filter-instance-type', 'value'),
    Input('filter-test-name', 'value'),
    Input('filter-cloud-provider', 'value'),
    Input('header-date-range', 'start_date'),
    Input('header-date-range', 'end_date')
)
def update_context_summary(os_versions, instance_types, test_names, cloud_providers, start_date, end_date):
    """Update the context summary display with current filter state."""
    # Parse OS versions (they're in "dist:version" format)
    os_display_list = []
    if os_versions:
        for ov in os_versions[:3]:
            if ':' in str(ov):
                dist, ver = ov.split(':', 1)
                os_display_list.append(f"{dist.upper()} {ver}")
            else:
                os_display_list.append(str(ov))

    return ai_widget.format_context_summary(
        os_versions=os_display_list,
        instance_types=instance_types or [],
        test_names=test_names or [],
        cloud_providers=cloud_providers or [],
        date_range=(start_date, end_date),
        data_mode=DATA_MODE
    )


@app.callback(
    [Output('ai-widget-results', 'children'),
     Output('ai-widget-status', 'children')],
    Input('ai-widget-analyze-btn', 'n_clicks'),
    [State('ai-widget-persona', 'value'),
     State('ai-widget-analysis-type', 'value'),
     State('ai-widget-custom-query', 'value'),
     State('filter-os-version', 'value'),
     State('filter-instance-type', 'value'),
     State('filter-test-name', 'value'),
     State('filter-cloud-provider', 'value'),
     State('header-date-range', 'start_date'),
     State('header-date-range', 'end_date'),
     State('filtered-data-store', 'data')],
    prevent_initial_call=True
)
def analyze_with_ai(n_clicks, persona, analysis_type, custom_query, os_versions,
                   instance_types, test_names, cloud_providers, start_date, end_date,
                   filtered_data_json):
    """
    Perform AI analysis based on current dashboard context and user selections.
    """
    if not n_clicks:
        raise PreventUpdate

    # Import AI service
    try:
        from src.ai_analysis import get_ai_analysis_service
    except ImportError:
        error_msg = "AI analysis not available: anthropic package not installed"
        return ai_widget.format_ai_analysis_result(None, error=error_msg, persona=persona), None

    service = get_ai_analysis_service()
    if service is None:
        status = dbc.Alert([
            html.I(className="bi bi-info-circle me-2"),
            "AI analysis requires ANTHROPIC_API_KEY in .env"
        ], color="info", className="mb-0 py-2")
        return ai_widget.format_ai_analysis_result(None, error="API key not configured", persona=persona), status

    # Show processing status
    status = dbc.Alert([
        dbc.Spinner(size="sm", className="me-2"),
        "Analyzing with AI..."
    ], color="info", className="mb-0 py-2")

    try:
        # Load filtered data
        if filtered_data_json:
            filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
        else:
            filtered_df = df.copy()

        # Build context for AI
        context = ai_widget.extract_dashboard_context(
            filtered_df=filtered_df,
            os_versions=os_versions or [],
            instance_types=instance_types or [],
            test_names=test_names or [],
            cloud_providers=cloud_providers or [],
            date_range=(start_date, end_date),
            analysis_type=analysis_type
        )

        # Prepare data for AI analysis based on analysis type
        baseline_data = {}
        comparison_data = {}
        metadata = {
            'analysis_type': analysis_type,
            'filters': context['filters'],
            'dataset_size': context['dataset_stats'].get('total_runs', 0)
        }

        if analysis_type == 'regression':
            # Extract regression statistics
            if 'regression_count' in context['dataset_stats']:
                baseline_data['regression_count'] = context['dataset_stats']['regression_count']
                comparison_data['total_tests'] = context['dataset_stats'].get('unique_tests', 0)
                metadata['top_regressions'] = context['dataset_stats'].get('top_regressions', {})

        elif analysis_type == 'peer':
            # Extract peer OS comparison data
            if 'os_distributions' in context['dataset_stats']:
                baseline_data = {'os_distributions': context['dataset_stats']['os_distributions']}
                comparison_data = {'test_coverage': context['dataset_stats'].get('unique_tests', 0)}

        elif analysis_type == 'scaling':
            # Extract scaling data
            if 'instance_classes' in context['dataset_stats']:
                baseline_data = {'instance_distribution': context['dataset_stats']['instance_classes']}
                comparison_data = {'scaling_metrics': 'available'}

        elif analysis_type == 'custom' and custom_query:
            # Custom query - include query in metadata
            metadata['custom_query'] = custom_query
            baseline_data = context['dataset_stats']
            comparison_data = {'query': custom_query}

        # Generate AI analysis
        analysis_text = service.analyze_comparison(
            baseline_data=baseline_data,
            comparison_data=comparison_data,
            metadata=metadata,
            persona=persona
        )

        success_status = dbc.Alert([
            html.I(className="bi bi-check-circle me-2"),
            f"Analysis complete ({persona.replace('_', ' ').title()})"
        ], color="success", className="mb-0 py-2")

        return ai_widget.format_ai_analysis_result(analysis_text, persona=persona), success_status

    except Exception as e:
        logger.exception("AI analysis failed")
        error_status = dbc.Alert([
            html.I(className="bi bi-exclamation-triangle me-2"),
            f"Analysis failed: {str(e)}"
        ], color="warning", className="mb-0 py-2")
        return ai_widget.format_ai_analysis_result(None, error=str(e), persona=persona), error_status


# Run the app
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8050))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print("\n" + "="*60)
    print("RHEL Multi Arch Performance Engineering Dashboard (Redesigned)")
    print("="*60)
    print(f"Data Mode: {DATA_MODE.upper()}")
    if DATA_MODE == "opensearch" and OPENSEARCH_LOAD_ERROR is not None and not SYNTHETIC_AFTER_OPENSEARCH_FAILURE:
        print(f"OpenSearch load failed (synthetic not loaded): {OPENSEARCH_LOAD_ERROR or '(no message)'}")
    elif SYNTHETIC_AFTER_OPENSEARCH_FAILURE and OPENSEARCH_LOAD_ERROR is not None:
        print(
            "Synthetic loaded after OpenSearch failure (env opt-in). Error was: "
            f"{OPENSEARCH_LOAD_ERROR or '(no message)'}"
        )
    print(f"Records Loaded: {len(df)}")
    print(f"Server: http://127.0.0.1:{port}")
    print(f"Debug Mode: {debug}")
    print("="*60 + "\n")
    
    app.run(debug=debug, port=port, host='0.0.0.0')

