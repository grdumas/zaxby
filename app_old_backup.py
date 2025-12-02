"""
Performance Engineering Dashboard

Main Dash application for visualizing benchmark results from OpenSearch.
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
    # Store for filtered data
    dcc.Store(id='filtered-data-store'),
    
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Performance Engineering Dashboard", className="text-primary mb-2"),
            html.P(
                f"Benchmark Results Viewer | Mode: {DATA_MODE.upper()} | Records: {len(df)}",
                className="text-muted"
            ),
        ])
    ], className="mb-4 mt-3"),
    
    # Summary Cards
    dbc.Row(id='summary-cards-row', className="mb-4"),
    
    # Main Content
    dbc.Row([
        # Left Sidebar - Filters
        dbc.Col([
            filters.create_filter_panel(
                os_versions=os_versions,
                instance_types=instance_types,
                test_names=test_names,
                cloud_providers=cloud_providers,
                min_date=min_date,
                max_date=max_date
            ),
            filters.create_comparison_controls()
        ], width=3),
        
        # Main Content Area
        dbc.Col([
            # Tabs for different views
            dbc.Tabs([
                dbc.Tab(label="Overview", tab_id="tab-overview"),
                dbc.Tab(label="By Benchmark", tab_id="tab-by-benchmark"),
                dbc.Tab(label="Comparisons", tab_id="tab-comparisons"),
                dbc.Tab(label="Time Series", tab_id="tab-timeseries"),
                dbc.Tab(label="Heatmap", tab_id="tab-heatmap"),
                dbc.Tab(label="Detailed Table", tab_id="tab-table"),
            ], id="tabs", active_tab="tab-overview", className="mb-3"),
            
            # Tab content
            html.Div(id="tab-content")
        ], width=9)
    ])
], fluid=True)


# Callbacks

@app.callback(
    Output('filtered-data-store', 'data'),
    [
        Input('filter-os-version', 'value'),
        Input('filter-instance-type', 'value'),
        Input('filter-test-name', 'value'),
        Input('filter-cloud-provider', 'value'),
        Input('filter-date-range', 'start_date'),
        Input('filter-date-range', 'end_date'),
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
    Output('summary-cards-row', 'children'),
    Input('filtered-data-store', 'data')
)
def update_summary_cards(filtered_data_json):
    """Update summary statistic cards."""
    import pandas as pd
    
    if not filtered_data_json:
        return []
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    summary = visualizations.create_summary_cards_data(filtered_df)
    
    cards = [
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{summary['total_tests']}", className="text-primary"),
                    html.P("Total Tests", className="mb-0")
                ])
            ])
        ], width=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{summary['unique_configs']}", className="text-info"),
                    html.P("Unique Configs", className="mb-0")
                ])
            ])
        ], width=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{summary['pass_rate']:.1f}%", className="text-success"),
                    html.P("Pass Rate", className="mb-0")
                ])
            ])
        ], width=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"{summary['avg_metric']:.0f}", className="text-warning"),
                    html.P("Avg Metric", className="mb-0")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Small(f"{summary['date_range']}", className="text-muted"),
                    html.P("Date Range", className="mb-0 small")
                ])
            ])
        ], width=3),
    ]
    
    return cards


@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'active_tab'),
     Input('filtered-data-store', 'data')]
)
def render_tab_content(active_tab, filtered_data_json):
    """Render content based on active tab."""
    import pandas as pd
    
    if not filtered_data_json:
        return html.Div("No data available", className="alert alert-warning")
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    if filtered_df.empty:
        return html.Div("No data matches the current filters", className="alert alert-info")
    
    if active_tab == "tab-overview":
        # Overview with multiple charts
        # Check if we have multiple test types with different scales
        has_multiple_tests = len(filtered_df['test_name'].unique()) > 1
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        figure=visualizations.create_box_plot(
                            filtered_df,
                            x_col='test_name',
                            y_col='primary_metric_value',
                            title="Performance Distribution by Benchmark Type",
                            use_facets=has_multiple_tests
                        )
                    )
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        figure=visualizations.create_box_plot(
                            filtered_df,
                            x_col='os_version',
                            y_col='primary_metric_value',
                            color_col='test_name',
                            title="Performance by OS Version (All Tests Combined)",
                            use_facets=False
                        )
                    )
                ], width=6),
                dbc.Col([
                    dcc.Graph(
                        figure=visualizations.create_box_plot(
                            filtered_df,
                            x_col='cloud_provider',
                            y_col='primary_metric_value',
                            color_col='test_name',
                            title="Performance by Cloud Provider (All Tests Combined)",
                            use_facets=False
                        )
                    )
                ], width=6)
            ])
        ])
    
    elif active_tab == "tab-by-benchmark":
        # Separate views for each benchmark to handle different scales
        graphs = []
        
        # Create separate box plots for each test by OS version
        os_figs = visualizations.create_separate_test_charts(
            filtered_df,
            chart_type='box',
            x_col='os_version',
            y_col='primary_metric_value',
            title_prefix="Performance by OS Version"
        )
        
        for fig in os_figs:
            graphs.append(dbc.Row([
                dbc.Col([dcc.Graph(figure=fig)], width=12)
            ]))
        
        # Add spacing
        if graphs:
            graphs.append(html.Hr())
        
        # Create separate box plots for each test by instance type
        instance_figs = visualizations.create_separate_test_charts(
            filtered_df,
            chart_type='box',
            x_col='instance_type',
            y_col='primary_metric_value',
            title_prefix="Performance by Instance Type"
        )
        
        for fig in instance_figs:
            graphs.append(dbc.Row([
                dbc.Col([dcc.Graph(figure=fig)], width=12)
            ]))
        
        return html.Div(graphs) if graphs else html.Div(
            "No data available for benchmark-specific views",
            className="alert alert-info"
        )
    
    elif active_tab == "tab-comparisons":
        # Comparison view
        if len(filtered_df['os_version'].unique()) >= 2:
            # Auto-compare first two OS versions
            os_list = sorted(filtered_df['os_version'].unique())
            comparison = processor.calculate_comparison(
                filtered_df,
                baseline_filters={'os_versions': [os_list[0]]},
                comparison_filters={'os_versions': [os_list[1]]},
                group_by='test_name'
            )
            
            return html.Div([
                html.H4(f"Comparison: {os_list[0]} vs {os_list[1]}", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(
                            figure=visualizations.create_comparison_chart(
                                comparison,
                                title=f"Performance: {os_list[0]} (baseline) vs {os_list[1]}"
                            )
                        )
                    ], width=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(
                            figure=visualizations.create_performance_delta_chart(
                                comparison,
                                title="Percentage Change"
                            )
                        )
                    ], width=12)
                ])
            ])
        else:
            return html.Div(
                "Need at least 2 OS versions in filtered data for comparison",
                className="alert alert-info"
            )
    
    elif active_tab == "tab-timeseries":
        # Time series view
        has_multiple_tests = len(filtered_df['test_name'].unique()) > 1
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        figure=visualizations.create_time_series_chart(
                            filtered_df,
                            x_col='timestamp',
                            y_col='primary_metric_value',
                            color_col='test_name',
                            title="Performance Trends Over Time (by Benchmark)",
                            use_facets=has_multiple_tests
                        )
                    )
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        figure=visualizations.create_time_series_chart(
                            filtered_df.groupby(['timestamp', 'os_version'])['primary_metric_value'].mean().reset_index(),
                            x_col='timestamp',
                            y_col='primary_metric_value',
                            color_col='os_version',
                            title="Average Performance by OS Version Over Time",
                            use_facets=False
                        )
                    )
                ], width=12)
            ])
        ])
    
    elif active_tab == "tab-heatmap":
        # Heatmap view
        has_multiple_tests = len(filtered_df['test_name'].unique()) > 1
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        figure=visualizations.create_heatmap(
                            filtered_df,
                            row_dim='os_version',
                            col_dim='instance_type',
                            value_col='primary_metric_value',
                            title="Performance Heatmap: OS Version × Instance Type (Normalized %)",
                            normalize_by_test=has_multiple_tests
                        )
                    )
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        figure=visualizations.create_heatmap(
                            filtered_df,
                            row_dim='test_name',
                            col_dim='cloud_provider',
                            value_col='primary_metric_value',
                            title="Performance Heatmap: Benchmark × Cloud Provider (Normalized %)",
                            normalize_by_test=has_multiple_tests
                        )
                    )
                ], width=12)
            ])
        ])
    
    elif active_tab == "tab-table":
        # Detailed table view
        display_cols = [
            'test_name', 'os_version', 'instance_type', 'cloud_provider',
            'timestamp', 'status', 'primary_metric_value', 'primary_metric_unit'
        ]
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        
        return html.Div([
            html.H4("Detailed Test Results", className="mb-3"),
            dcc.Graph(
                figure=visualizations.create_metrics_table(
                    filtered_df[available_cols].head(100),
                    title=f"Showing {min(100, len(filtered_df))} of {len(filtered_df)} records"
                )
            )
        ])
    
    return html.Div("Unknown tab")


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
    print("Performance Engineering Dashboard")
    print("="*60)
    print(f"Data Mode: {DATA_MODE.upper()}")
    print(f"Records Loaded: {len(df)}")
    print(f"Server: http://127.0.0.1:{port}")
    print(f"Debug Mode: {debug}")
    print("="*60 + "\n")
    
    app.run(debug=debug, port=port, host='0.0.0.0')

