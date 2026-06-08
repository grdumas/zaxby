"""
AI Widget component for dashboard (RPOPC-1014).

Provides an interactive AI analysis widget that captures current dashboard state
(filters, benchmark type, system config, selected dataset) and displays AI-powered
insights inline in the dashboard.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dash import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def create_ai_widget() -> dbc.Card:
    """
    Create the AI analysis widget component.

    Returns:
        Dash Bootstrap Card containing the AI widget UI
    """
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-robot me-2"),
                html.Span("AI Performance Assistant", className="fw-bold")
            ], className="d-flex align-items-center")
        ]),
        dbc.CardBody([
            # Status indicator
            html.Div(id='ai-widget-status', className="mb-3"),

            # Persona selector
            html.Div([
                html.Label("Analysis Perspective:", className="fw-bold small mb-1"),
                dbc.RadioItems(
                    id='ai-widget-persona',
                    options=[
                        {
                            'label': html.Span([
                                html.Strong('Executive'),
                                html.Span(' - High-level verdict & action items', className="text-muted small ms-1")
                            ]),
                            'value': 'executive'
                        },
                        {
                            'label': html.Span([
                                html.Strong('Tech Lead'),
                                html.Span(' - Trends & bottleneck analysis', className="text-muted small ms-1")
                            ]),
                            'value': 'tech_lead'
                        },
                        {
                            'label': html.Span([
                                html.Strong('Expert'),
                                html.Span(' - Deep technical dive', className="text-muted small ms-1")
                            ]),
                            'value': 'expert'
                        }
                    ],
                    value='tech_lead',
                    className="mb-3"
                )
            ]),

            # Analysis type selector
            html.Div([
                html.Label("Analysis Type:", className="fw-bold small mb-1"),
                dbc.RadioItems(
                    id='ai-widget-analysis-type',
                    options=[
                        {'label': 'Regression Analysis', 'value': 'regression'},
                        {'label': 'Peer Comparison', 'value': 'peer'},
                        {'label': 'Scaling Efficiency', 'value': 'scaling'},
                        {'label': 'Custom Query', 'value': 'custom'}
                    ],
                    value='regression',
                    className="mb-3"
                )
            ]),

            # Custom query input (shown when analysis type is 'custom')
            html.Div([
                html.Label("Your Question:", className="fw-bold small mb-1"),
                dbc.Textarea(
                    id='ai-widget-custom-query',
                    placeholder="Ask a question about the current dataset...\nExample: What are the top 3 performance bottlenecks in RHEL 9.6?",
                    rows=3,
                    className="mb-3"
                )
            ], id='ai-widget-custom-query-container', style={'display': 'none'}),

            # Analyze button
            dbc.Button(
                [html.I(className="bi bi-lightbulb me-2"), "Analyze"],
                id='ai-widget-analyze-btn',
                color="primary",
                className="w-100 mb-3"
            ),

            # Current context summary (shows what filters are active)
            dbc.Collapse([
                dbc.Alert([
                    html.Div([
                        html.I(className="bi bi-funnel me-2"),
                        html.Strong("Active Context:")
                    ], className="mb-2"),
                    html.Div(id='ai-widget-context-summary', className="small")
                ], color="light", className="mb-0")
            ], id='ai-widget-context-collapse', is_open=False),

            # Results display
            dcc.Loading(
                html.Div(id='ai-widget-results', className="mt-3"),
                type="default"
            )
        ])
    ], className="mb-4", style={
        "borderLeft": "5px solid #6366f1",
        "borderRadius": "0.75rem"
    })


def format_context_summary(
    os_versions: List[str],
    instance_types: List[str],
    test_names: List[str],
    cloud_providers: List[str],
    date_range: tuple[str, str],
    data_mode: str
) -> html.Div:
    """
    Format the current dashboard context for display in the AI widget.

    Args:
        os_versions: Selected OS versions
        instance_types: Selected instance types
        test_names: Selected benchmark types
        cloud_providers: Selected cloud providers
        date_range: (start_date, end_date) tuple
        data_mode: 'opensearch' or 'synthetic'

    Returns:
        Formatted context summary
    """
    context_items = []

    if os_versions:
        os_display = ', '.join(os_versions[:3])
        if len(os_versions) > 3:
            os_display += f' (+{len(os_versions) - 3} more)'
        context_items.append(html.Li([html.Strong("OS: "), os_display]))

    if instance_types:
        hw_display = ', '.join(instance_types[:3])
        if len(instance_types) > 3:
            hw_display += f' (+{len(instance_types) - 3} more)'
        context_items.append(html.Li([html.Strong("Hardware: "), hw_display]))

    if test_names:
        test_display = ', '.join(test_names[:3])
        if len(test_names) > 3:
            test_display += f' (+{len(test_names) - 3} more)'
        context_items.append(html.Li([html.Strong("Benchmarks: "), test_display]))

    if cloud_providers:
        cloud_display = ', '.join([c.upper() for c in cloud_providers])
        context_items.append(html.Li([html.Strong("Clouds: "), cloud_display]))

    if date_range and len(date_range) == 2:
        context_items.append(html.Li([
            html.Strong("Date Range: "),
            f"{date_range[0]} to {date_range[1]}"
        ]))

    context_items.append(html.Li([
        html.Strong("Data Source: "),
        data_mode.upper()
    ]))

    return html.Ul(context_items, className="mb-0", style={"listStyle": "none", "paddingLeft": "0"})


def format_ai_analysis_result(
    analysis_text: Optional[str],
    error: Optional[str] = None,
    persona: str = 'tech_lead'
) -> html.Div:
    """
    Format AI analysis results for display.

    Args:
        analysis_text: AI-generated analysis text
        error: Error message if analysis failed
        persona: The persona used for analysis

    Returns:
        Formatted results display
    """
    if error:
        return dbc.Alert([
            html.I(className="bi bi-exclamation-triangle me-2"),
            html.Strong("Analysis Error: "),
            html.Span(error)
        ], color="warning")

    if not analysis_text:
        return dbc.Alert([
            html.I(className="bi bi-info-circle me-2"),
            "AI analysis is not available. Ensure ANTHROPIC_API_KEY is configured in .env"
        ], color="info")

    # Determine color scheme based on persona
    persona_colors = {
        'executive': '#dc2626',  # red
        'tech_lead': '#2563eb',  # blue
        'expert': '#7c3aed'      # purple
    }
    border_color = persona_colors.get(persona, '#6366f1')

    persona_labels = {
        'executive': 'Executive Summary',
        'tech_lead': 'Technical Lead Analysis',
        'expert': 'Expert Deep Dive'
    }
    label = persona_labels.get(persona, 'AI Analysis')

    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-cpu me-2"),
            html.Strong(label)
        ], style={"backgroundColor": border_color, "color": "white"}),
        dbc.CardBody([
            dcc.Markdown(analysis_text, className="mb-0")
        ])
    ], className="border-0", style={"borderLeft": f"4px solid {border_color}"})


def extract_dashboard_context(
    filtered_df,
    os_versions: List[str],
    instance_types: List[str],
    test_names: List[str],
    cloud_providers: List[str],
    date_range: tuple[str, str],
    analysis_type: str
) -> Dict[str, Any]:
    """
    Extract relevant context from dashboard state for AI analysis.

    Args:
        filtered_df: Current filtered dataframe
        os_versions: Selected OS versions
        instance_types: Selected instance types
        test_names: Selected benchmark types
        cloud_providers: Selected cloud providers
        date_range: (start_date, end_date) tuple
        analysis_type: Type of analysis requested

    Returns:
        Dictionary containing context for AI analysis
    """
    import pandas as pd

    context = {
        'filters': {
            'os_versions': os_versions,
            'instance_types': instance_types,
            'test_names': test_names,
            'cloud_providers': cloud_providers,
            'date_range': date_range
        },
        'analysis_type': analysis_type,
        'dataset_stats': {}
    }

    if filtered_df is not None and not filtered_df.empty:
        # Basic dataset statistics
        context['dataset_stats'] = {
            'total_runs': len(filtered_df),
            'unique_tests': filtered_df['test_name'].nunique() if 'test_name' in filtered_df.columns else 0,
            'unique_os': filtered_df['os_version'].nunique() if 'os_version' in filtered_df.columns else 0,
            'unique_hardware': filtered_df['hardware_config'].nunique() if 'hardware_config' in filtered_df.columns else 0,
            'date_range': (
                str(filtered_df['run_date'].min()) if 'run_date' in filtered_df.columns else None,
                str(filtered_df['run_date'].max()) if 'run_date' in filtered_df.columns else None
            )
        }

        # Calculate pass rate
        if 'test_status' in filtered_df.columns:
            pass_rate = (filtered_df['test_status'] == 'PASS').sum() / len(filtered_df) * 100
            context['dataset_stats']['pass_rate'] = f"{pass_rate:.1f}%"

        # Analysis-specific context
        if analysis_type == 'regression' and 'is_regression' in filtered_df.columns:
            regressions = filtered_df[filtered_df['is_regression'] == True]
            context['dataset_stats']['regression_count'] = len(regressions)
            if not regressions.empty and 'test_name' in regressions.columns:
                context['dataset_stats']['top_regressions'] = regressions['test_name'].value_counts().head(5).to_dict()

        elif analysis_type == 'peer' and 'os_distribution' in filtered_df.columns:
            context['dataset_stats']['os_distributions'] = filtered_df['os_distribution'].value_counts().to_dict()

        elif analysis_type == 'scaling' and 'instance_class' in filtered_df.columns:
            context['dataset_stats']['instance_classes'] = filtered_df['instance_class'].value_counts().to_dict()

    return context
