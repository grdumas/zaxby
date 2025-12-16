"""
Filter components for the dashboard.

Provides multi-axis filtering controls for benchmark data.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import List, Any, Dict, Optional
import pandas as pd


def create_grouped_os_version_options(
    os_version_map: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """
    Create grouped dropdown options for OS versions by distribution.
    
    Args:
        os_version_map: Dictionary mapping OS distribution to list of versions
                       e.g., {'rhel': ['9.4', '9.5'], 'ubuntu': ['22.04', '24.04']}
    
    Returns:
        List of dropdown options with grouping labels
    """
    options = []
    
    # Sort distributions alphabetically, but put RHEL first as primary focus
    distributions = sorted(os_version_map.keys())
    if 'rhel' in distributions:
        distributions.remove('rhel')
        distributions.insert(0, 'rhel')
    
    for dist in distributions:
        versions = os_version_map[dist]
        if not versions:
            continue
            
        # Sort versions numerically where possible
        try:
            sorted_versions = sorted(versions, key=lambda v: [float(x) for x in str(v).split('.')])
        except (ValueError, AttributeError):
            sorted_versions = sorted(versions)
        
        # Add each version with the full OS name as label
        dist_display = dist.upper()
        for version in sorted_versions:
            # Create combined value that includes both distribution and version
            combined_value = f"{dist}:{version}"
            options.append({
                'label': f"{dist_display} {version}",
                'value': combined_value
            })
    
    return options


def create_filter_panel(
    os_versions: List[str],
    instance_types: List[str],
    test_names: List[str],
    cloud_providers: List[str],
    min_date: str,
    max_date: str,
    os_version_map: Optional[Dict[str, List[str]]] = None
) -> html.Div:
    """
    Create the main filter panel with all filter controls.
    
    Args:
        os_versions: List of available OS versions (legacy, for backward compatibility)
        instance_types: List of available instance types
        test_names: List of available test names
        cloud_providers: List of available cloud providers
        min_date: Minimum date in dataset
        max_date: Maximum date in dataset
        os_version_map: Dictionary mapping OS distribution to list of versions
                       (preferred over os_versions for clearer display)
        
    Returns:
        Dash HTML Div containing all filter controls
    """
    
    # Create OS version options - prefer grouped format if available
    if os_version_map:
        os_options = create_grouped_os_version_options(os_version_map)
        os_default_values = [opt['value'] for opt in os_options]
    else:
        # Fallback to simple version list (backward compatibility)
        os_options = [{'label': v, 'value': v} for v in os_versions]
        os_default_values = os_versions
    
    return html.Div([
        html.H4("Filters", className="mb-3"),
        
        # OS Version Filter (with distribution context)
        html.Div([
            html.Label("OS Version", className="fw-bold"),
            dcc.Dropdown(
                id='filter-os-version',
                options=os_options,
                value=os_default_values,
                multi=True,
                placeholder="Select OS versions..."
            )
        ], className="mb-3"),
        
        # Instance Type Filter
        html.Div([
            html.Label("Instance Type", className="fw-bold"),
            dcc.Dropdown(
                id='filter-instance-type',
                options=[{'label': i, 'value': i} for i in instance_types],
                value=instance_types,
                multi=True,
                placeholder="Select instance types..."
            )
        ], className="mb-3"),
        
        # Test Type Filter
        html.Div([
            html.Label("Benchmark Type", className="fw-bold"),
            dcc.Dropdown(
                id='filter-test-name',
                options=[{'label': t, 'value': t} for t in test_names],
                value=test_names,
                multi=True,
                placeholder="Select benchmarks..."
            )
        ], className="mb-3"),
        
        # Cloud Provider Filter
        html.Div([
            html.Label("Cloud Provider", className="fw-bold"),
            dcc.Dropdown(
                id='filter-cloud-provider',
                options=[{'label': c.upper(), 'value': c} for c in cloud_providers],
                value=cloud_providers,
                multi=True,
                placeholder="Select cloud providers..."
            )
        ], className="mb-3"),
        
        # Date Range Filter
        html.Div([
            html.Label("Date Range", className="fw-bold"),
            dcc.DatePickerRange(
                id='filter-date-range',
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                start_date=min_date,
                end_date=max_date,
                display_format='YYYY-MM-DD'
            )
        ], className="mb-3"),
        
        # Status Filter
        html.Div([
            html.Label("Test Status", className="fw-bold"),
            dcc.Checklist(
                id='filter-status',
                options=[
                    {'label': ' PASS', 'value': 'PASS'},
                    {'label': ' FAIL', 'value': 'FAIL'},
                    {'label': ' UNKNOWN', 'value': 'UNKNOWN'}
                ],
                value=['PASS', 'FAIL', 'UNKNOWN'],
                inline=True
            )
        ], className="mb-3"),
        
        # Reset Button
        html.Div([
            html.Button(
                "Reset Filters",
                id='btn-reset-filters',
                className="btn btn-secondary w-100"
            )
        ], className="mt-3")
        
    ], className="p-3 bg-light border rounded")


def create_comparison_controls() -> html.Div:
    """
    Create controls for comparison mode.
    
    Returns:
        Dash HTML Div with comparison controls
    """
    
    return html.Div([
        html.H5("Comparison Mode", className="mb-3"),
        
        dbc.Switch(
            id='switch-comparison-mode',
            label="Enable Comparison",
            value=False,
            className="mb-3"
        ),
        
        html.Div(id='comparison-controls-container', children=[
            # Baseline Configuration
            html.Div([
                html.H6("Baseline", className="text-primary"),
                dcc.Dropdown(
                    id='comparison-baseline-os',
                    placeholder="Select OS version...",
                    className="mb-2"
                ),
                dcc.Dropdown(
                    id='comparison-baseline-instance',
                    placeholder="Select instance type...",
                    className="mb-2"
                )
            ], className="p-2 border rounded mb-3"),
            
            # Comparison Configuration
            html.Div([
                html.H6("Compare To", className="text-success"),
                dcc.Dropdown(
                    id='comparison-target-os',
                    placeholder="Select OS version...",
                    className="mb-2"
                ),
                dcc.Dropdown(
                    id='comparison-target-instance',
                    placeholder="Select instance type...",
                    className="mb-2"
                )
            ], className="p-2 border rounded")
        ], style={'display': 'none'})
        
    ], className="p-3 bg-light border rounded mt-3")

