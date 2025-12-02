"""
Performance Engineering Dashboard - Redesigned

Main Dash application for visualizing benchmark results with a focus on
answering three key questions:
1. Did RHEL regress between OS versions?
2. Is RHEL performing competitively with peer operating systems?
3. How does performance scale across cloud instance classes?
"""

import os
import json
from datetime import datetime
from io import StringIO
from dash import Dash, html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

# Import local modules
from src.opensearch_client import BenchmarkDataSource
from src.data_processing import BenchmarkDataProcessor, load_synthetic_data
from src.components import filters, visualizations
from src.components.summaries import (
    format_regression_summary,
    format_peer_comparison_summary,
    format_scaling_summary,
    get_status_icon,
    summarize_investigation_details,
    format_investigation_summary_text
)

# Load environment variables
load_dotenv()

# Initialize app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "Performance Engineering Dashboard"

# Determine data mode
DATA_MODE = os.getenv('DATA_MODE', 'synthetic').lower()

# Initialize data processor
processor = BenchmarkDataProcessor()

# Load initial data
def load_data():
    """Load data based on configured mode."""
    if DATA_MODE == 'opensearch':
        try:
            client = BenchmarkDataSource()
            documents = client.get_all_documents(max_docs=5000)
            print(f"Loaded {len(documents)} documents from OpenSearch")
            return documents
        except Exception as e:
            print(f"Failed to load from OpenSearch: {e}")
            print("Falling back to synthetic data...")
            return load_synthetic_data()
    else:
        return load_synthetic_data()

# Load and process data
print(f"Loading data in {DATA_MODE} mode...")
raw_documents = load_data()
df = processor.documents_to_dataframe(raw_documents)
print(f"Processed {len(df)} records")

# Extract filter options
os_versions = processor.get_unique_values(df, 'os_version')
instance_types = processor.get_unique_values(df, 'instance_type')
test_names = processor.get_unique_values(df, 'test_name')
cloud_providers = processor.get_unique_values(df, 'cloud_provider')
min_date = df['timestamp'].min().strftime('%Y-%m-%d') if len(df) > 0 else '2025-01-01'
max_date = df['timestamp'].max().strftime('%Y-%m-%d') if len(df) > 0 else '2025-12-31'

# App Layout
app.layout = dbc.Container([
    # Store for filtered data and analysis results
    dcc.Store(id='filtered-data-store'),
    dcc.Store(id='analysis-results-store'),
    dcc.Store(id='navigation-state', data={'view': 'overview', 'investigation_params': None}),
    
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Performance Engineering Dashboard", className="text-primary mb-2"),
            html.P(
                f"Benchmark Results Viewer | Mode: {DATA_MODE.upper()} | Records: {len(df)}",
                className="text-muted mb-3"
            ),
        ], width=8),
        dbc.Col([
            html.Div([
                html.Label("Date Range:", className="small mb-1"),
                dcc.DatePickerRange(
                    id='header-date-range',
                    start_date=min_date,
                    end_date=max_date,
                    display_format='YYYY-MM-DD',
                    className="mb-2"
                ),
                dbc.Button("Advanced Filters", id="btn-show-filters", size="sm", color="secondary", className="w-100"),
            ])
        ], width=4)
    ], className="mb-3 mt-3"),
    
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
                    max_date=max_date
                )
            ])
        ], className="mb-3")
    ], id="collapse-filters", is_open=False),
    
    # Main Content - switches between overview and investigation
    html.Div(id="main-content")
    
], fluid=True)


def create_overview_layout():
    """Create the main three-question overview layout."""
    return html.Div([
        # Question 1: OS Version Regressions
        dbc.Card([
            dbc.CardHeader([
                html.H4([
                    "RHEL Version Regression Analysis",
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            dcc.Graph(id='q1-heatmap'),
                            type="default"
                        )
                    ], width=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Div(id='q1-summary', className="mt-3")
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Question 2: Peer OS Comparison
        dbc.Card([
            dbc.CardHeader([
                html.H4([
                    "Competitive OS Performance Analysis",
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            dcc.Graph(id='q2-comparison'),
                            type="default"
                        )
                    ], width=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Div(id='q2-summary', className="mt-3")
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Question 3: Cloud Scaling
        dbc.Card([
            dbc.CardHeader([
                html.H4([
                    "Cloud Instance Scaling Analysis",
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Cloud Provider:"),
                        dcc.Dropdown(
                            id='q3-cloud-provider',
                            options=[{'label': cp, 'value': cp} for cp in cloud_providers],
                            value=cloud_providers[0] if cloud_providers else None,
                            clearable=False
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("OS Version:"),
                        dcc.Dropdown(
                            id='q3-os-version',
                            options=[{'label': osv, 'value': osv} for osv in os_versions],
                            value=os_versions[-1] if os_versions else None,
                            clearable=False
                        )
                    ], width=3)
                ], className="mb-3"),
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
        ], className="mb-4"),
        
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
                    ], width=4),
                    dbc.Col([
                        dbc.Button(
                            "Compare Configurations →",
                            id="btn-view-comparisons",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Button(
                            "View Detailed Table →",
                            id="btn-view-table",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=4)
                ])
            ])
        ])
    ])


def create_investigation_layout(test_name, baseline_version, comparison_version):
    """Create the investigation drill-down layout."""
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
                html.H3(f"Investigating: {test_name}", className="mt-2")
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
    """Update the filtered dataset based on filter selections."""
    
    # Convert date strings to timezone-aware datetime objects
    date_range_param = None
    if start_date and end_date:
        from datetime import timezone
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        date_range_param = (start_dt, end_dt)
    
    filtered_df = processor.filter_data(
        df,
        os_versions=os_vers if os_vers else None,
        instance_types=inst_types if inst_types else None,
        test_names=tests if tests else None,
        cloud_providers=clouds if clouds else None,
        date_range=date_range_param,
        status_filter=statuses if statuses else None
    )
    
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
    
    # Question 1: OS Version Regressions
    try:
        results['q1'] = processor.analyze_os_version_regressions(filtered_df)
    except Exception as e:
        print(f"Error in Q1 analysis: {e}")
        results['q1'] = {'summary': 'Analysis error', 'regressions': [], 'heatmap_data': pd.DataFrame()}
    
    # Question 2: Peer OS Comparison
    try:
        results['q2'] = processor.analyze_peer_os_comparison(filtered_df, baseline_os='RHEL')
    except Exception as e:
        print(f"Error in Q2 analysis: {e}")
        results['q2'] = {'summary': 'Analysis error', 'comparison_data': pd.DataFrame()}
    
    # Question 3: Cloud Scaling (will be done dynamically based on user selection)
    results['q3'] = {}
    
    # Serialize DataFrames to JSON
    if 'heatmap_data' in results['q1'] and isinstance(results['q1']['heatmap_data'], pd.DataFrame):
        results['q1']['heatmap_data'] = results['q1']['heatmap_data'].to_json(orient='split')
    
    if 'comparison_data' in results['q1'] and isinstance(results['q1']['comparison_data'], pd.DataFrame):
        results['q1']['comparison_data'] = results['q1']['comparison_data'].to_json(orient='split')
    
    if 'comparison_data' in results['q2'] and isinstance(results['q2']['comparison_data'], pd.DataFrame):
        results['q2']['comparison_data'] = results['q2']['comparison_data'].to_json(orient='split')
    
    return json.dumps(results)


@app.callback(
    [Output('q1-heatmap', 'figure'),
     Output('q1-summary', 'children')],
    Input('analysis-results-store', 'data')
)
def update_question1(analysis_json):
    """Update Question 1 visualizations."""
    import pandas as pd
    
    if not analysis_json:
        empty_fig = visualizations.create_empty_figure("Loading...")
        return empty_fig, "Analyzing..."
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    
    # Recreate DataFrame from JSON
    if 'heatmap_data' in q1_data and q1_data['heatmap_data']:
        heatmap_df = pd.read_json(StringIO(q1_data['heatmap_data']), orient='split')
        fig = visualizations.create_regression_heatmap(heatmap_df)
    else:
        fig = visualizations.create_empty_figure("No regression data available")
    
    # Format summary
    summary_text = format_regression_summary(q1_data)
    num_regressions = q1_data.get('num_regressions', 0)
    icon = get_status_icon(num_regressions)
    
    summary_component = dbc.Alert([
        html.H5([icon, f" Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color="warning" if num_regressions > 0 else "success")
    
    return fig, summary_component


@app.callback(
    [Output('q2-comparison', 'figure'),
     Output('q2-summary', 'children')],
    Input('analysis-results-store', 'data')
)
def update_question2(analysis_json):
    """Update Question 2 visualizations."""
    import pandas as pd
    
    if not analysis_json:
        empty_fig = visualizations.create_empty_figure("Loading...")
        return empty_fig, "Analyzing..."
    
    analysis = json.loads(analysis_json)
    q2_data = analysis.get('q2', {})
    
    # Recreate DataFrame from JSON
    if 'comparison_data' in q2_data and q2_data['comparison_data']:
        comparison_df = pd.read_json(StringIO(q2_data['comparison_data']), orient='split')
        fig = visualizations.create_peer_os_comparison_chart(comparison_df, baseline_os="RHEL")
    else:
        fig = visualizations.create_empty_figure("No peer comparison data available")
    
    # Format summary
    summary_text = format_peer_comparison_summary(q2_data)
    competitive_count = q2_data.get('competitive_count', 0)
    total_benchmarks = q2_data.get('total_benchmarks', 0)
    
    is_competitive = competitive_count >= (total_benchmarks * 0.7) if total_benchmarks > 0 else True
    
    summary_component = dbc.Alert([
        html.H5([get_status_icon(0 if is_competitive else 3), " Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color="success" if is_competitive else "warning")
    
    return fig, summary_component


@app.callback(
    [Output('q3-scaling', 'figure'),
     Output('q3-summary', 'children')],
    [Input('q3-cloud-provider', 'value'),
     Input('q3-os-version', 'value'),
     Input('filtered-data-store', 'data')]
)
def update_question3(cloud_provider, os_version, filtered_data_json):
    """Update Question 3 visualizations."""
    import pandas as pd
    
    if not filtered_data_json or not cloud_provider or not os_version:
        empty_fig = visualizations.create_empty_figure("Select cloud provider and OS version")
        return empty_fig, ""
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Run scaling analysis
    q3_result = processor.analyze_cloud_scaling(
        filtered_df,
        cloud_provider=cloud_provider,
        os_version=os_version
    )
    
    # Create visualization
    if not q3_result['scaling_data'].empty:
        fig = visualizations.create_cloud_scaling_chart(
            q3_result['scaling_data'],
            title=f"Performance Scaling: {os_version} on {cloud_provider}"
        )
    else:
        fig = visualizations.create_empty_figure("No scaling data available for selected configuration")
    
    # Format summary
    summary_text = format_scaling_summary(q3_result)
    linear_count = q3_result.get('linear_scaling_count', 0)
    total = q3_result.get('total_benchmarks', 0)
    
    good_scaling = linear_count >= (total * 0.7) if total > 0 else True
    
    summary_component = dbc.Alert([
        html.H5([get_status_icon(0 if good_scaling else 2), " Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color="success" if good_scaling else "info")
    
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
        return create_investigation_layout(
            test_name=params.get('test_name', 'Unknown'),
            baseline_version=params.get('baseline_version', 'N/A'),
            comparison_version=params.get('comparison_version', 'N/A')
        )
    else:
        return create_overview_layout()


@app.callback(
    Output('navigation-state', 'data'),
    [Input('q1-heatmap', 'clickData'),
     Input('btn-back-to-overview', 'n_clicks'),
     Input('btn-view-benchmarks', 'n_clicks'),
     Input('btn-view-comparisons', 'n_clicks'),
     Input('btn-view-table', 'n_clicks')],
    State('navigation-state', 'data'),
    prevent_initial_call=True
)
def handle_navigation(heatmap_click, back_click, benchmarks_click, comparisons_click, table_click, current_nav):
    """Handle navigation between views."""
    from dash import ctx
    
    if not ctx.triggered:
        return current_nav
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Back to overview
    if trigger_id == 'btn-back-to-overview':
        return {'view': 'overview', 'investigation_params': None}
    
    # Heatmap cell click - drill into investigation
    if trigger_id == 'q1-heatmap' and heatmap_click:
        # Extract test name and versions from click data
        try:
            point = heatmap_click['points'][0]
            test_name = point.get('y', 'Unknown')
            version_transition = point.get('x', '')
            
            # Parse version transition (e.g., "9.5→9.6")
            if '→' in version_transition:
                versions = version_transition.split('→')
                baseline_version = versions[0].strip()
                comparison_version = versions[1].strip()
            else:
                baseline_version = 'N/A'
                comparison_version = 'N/A'
            
            return {
                'view': 'investigation',
                'investigation_params': {
                    'test_name': test_name,
                    'baseline_version': baseline_version,
                    'comparison_version': comparison_version
                }
            }
        except Exception as e:
            print(f"Error parsing heatmap click: {e}")
            return current_nav
    
    # Other navigation buttons - stay on overview for now (future: navigate to specific tabs)
    return current_nav


@app.callback(
    [Output('investigation-summary', 'children'),
     Output('investigation-comparison-chart', 'figure'),
     Output('investigation-timeline-chart', 'figure'),
     Output('investigation-table', 'children')],
    [Input('navigation-state', 'data'),
     Input('filtered-data-store', 'data')],
    prevent_initial_call=True
)
def update_investigation_view(nav_state, filtered_data_json):
    """Update investigation drill-down view."""
    import pandas as pd
    
    if not nav_state or nav_state['view'] != 'investigation' or not filtered_data_json:
        empty_fig = visualizations.create_empty_figure("No investigation data")
        return "", empty_fig, empty_fig, ""
    
    params = nav_state.get('investigation_params', {})
    test_name = params.get('test_name', 'Unknown')
    baseline_version = params.get('baseline_version', 'N/A')
    comparison_version = params.get('comparison_version', 'N/A')
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Filter data for this specific test
    test_df = filtered_df[filtered_df['test_name'] == test_name]
    
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
    
    summary_component = dbc.Alert([
        html.H4([status_icon, f" {summary_data.get('status_text', 'Analysis')}"], className="mb-3"),
        dcc.Markdown(summary_text)
    ], color=alert_color)
    
    # Create comparison chart
    comparison_fig = visualizations.create_investigation_detail_chart(
        baseline_df, comparison_df, test_name, baseline_version, comparison_version
    )
    
    # Create timeline chart
    timeline_fig = visualizations.create_time_series_chart(
        test_df,
        x_col='timestamp',
        y_col='primary_metric_value',
        color_col='os_version',
        title=f"Performance Trend: {test_name}",
        use_facets=False
    )
    
    # Create detailed table
    table_df = test_df[[
        'timestamp', 'os_version', 'instance_type', 'cloud_provider',
        'primary_metric_value', 'primary_metric_unit', 'status'
    ]].sort_values('timestamp', ascending=False).head(50)
    
    table_fig = visualizations.create_metrics_table(
        table_df,
        title=f"Recent Test Runs (showing {len(table_df)} of {len(test_df)} total)"
    )
    
    table_component = dcc.Graph(figure=table_fig)
    
    return summary_component, comparison_fig, timeline_fig, table_component


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
    return os_versions, instance_types, test_names, cloud_providers, ['PASS', 'FAIL', 'UNKNOWN']


# Run the app
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8050))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print("\n" + "="*60)
    print("Performance Engineering Dashboard (Redesigned)")
    print("="*60)
    print(f"Data Mode: {DATA_MODE.upper()}")
    print(f"Records Loaded: {len(df)}")
    print(f"Server: http://127.0.0.1:{port}")
    print(f"Debug Mode: {debug}")
    print("="*60 + "\n")
    
    app.run(debug=debug, port=port, host='0.0.0.0')

