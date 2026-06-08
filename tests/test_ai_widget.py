"""
Tests for AI widget component (RPOPC-1014).
"""

import pytest
from dash import html
import dash_bootstrap_components as dbc
from src.components.ai_widget import (
    create_ai_widget,
    format_context_summary,
    format_ai_analysis_result,
    extract_dashboard_context
)
import pandas as pd


class TestCreateAIWidget:
    """Tests for create_ai_widget function."""

    def test_creates_card_component(self):
        """Test that widget creates a Bootstrap Card."""
        widget = create_ai_widget()
        assert isinstance(widget, dbc.Card)

    def test_has_persona_selector(self):
        """Test that widget includes persona radio buttons."""
        widget = create_ai_widget()
        # Convert to string to search for persona options
        widget_str = str(widget)
        assert 'executive' in widget_str.lower()
        assert 'tech_lead' in widget_str.lower()
        assert 'expert' in widget_str.lower()

    def test_has_analysis_type_selector(self):
        """Test that widget includes analysis type options."""
        widget = create_ai_widget()
        widget_str = str(widget)
        assert 'regression' in widget_str.lower()
        assert 'peer' in widget_str.lower() or 'competitive' in widget_str.lower()
        assert 'scaling' in widget_str.lower()
        assert 'custom' in widget_str.lower()

    def test_has_analyze_button(self):
        """Test that widget includes analyze button."""
        widget = create_ai_widget()
        widget_str = str(widget)
        assert 'ai-widget-analyze-btn' in widget_str

    def test_has_results_container(self):
        """Test that widget includes results display container."""
        widget = create_ai_widget()
        widget_str = str(widget)
        assert 'ai-widget-results' in widget_str


class TestFormatContextSummary:
    """Tests for format_context_summary function."""

    def test_formats_os_versions(self):
        """Test OS version formatting in context."""
        result = format_context_summary(
            os_versions=['RHEL 9.5', 'RHEL 9.6'],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            data_mode='synthetic'
        )
        result_str = str(result)
        assert 'RHEL 9.5' in result_str
        assert 'RHEL 9.6' in result_str

    def test_truncates_long_lists(self):
        """Test that long filter lists are truncated with +N more."""
        result = format_context_summary(
            os_versions=['v1', 'v2', 'v3', 'v4', 'v5'],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            data_mode='synthetic'
        )
        result_str = str(result)
        assert '+2 more' in result_str

    def test_formats_hardware(self):
        """Test hardware formatting in context."""
        result = format_context_summary(
            os_versions=[],
            instance_types=['m5.xlarge', 'm5.2xlarge'],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            data_mode='synthetic'
        )
        result_str = str(result)
        assert 'm5.xlarge' in result_str

    def test_formats_cloud_providers(self):
        """Test cloud provider formatting (uppercased)."""
        result = format_context_summary(
            os_versions=[],
            instance_types=[],
            test_names=[],
            cloud_providers=['aws', 'azure'],
            date_range=('2024-01-01', '2024-12-31'),
            data_mode='synthetic'
        )
        result_str = str(result)
        assert 'AWS' in result_str
        assert 'AZURE' in result_str

    def test_formats_date_range(self):
        """Test date range formatting."""
        result = format_context_summary(
            os_versions=[],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            data_mode='synthetic'
        )
        result_str = str(result)
        assert '2024-01-01' in result_str
        assert '2024-12-31' in result_str

    def test_shows_data_mode(self):
        """Test that data mode is displayed."""
        result = format_context_summary(
            os_versions=[],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            data_mode='opensearch'
        )
        result_str = str(result)
        assert 'OPENSEARCH' in result_str


class TestFormatAIAnalysisResult:
    """Tests for format_ai_analysis_result function."""

    def test_formats_successful_analysis(self):
        """Test formatting of successful AI analysis."""
        result = format_ai_analysis_result(
            analysis_text="**Verdict**: ✅ PASS\nPerformance is stable.",
            persona='executive'
        )
        assert isinstance(result, dbc.Card)
        result_str = str(result)
        assert 'PASS' in result_str
        assert 'stable' in result_str

    def test_formats_error_message(self):
        """Test formatting of error message."""
        result = format_ai_analysis_result(
            analysis_text=None,
            error="API key not configured"
        )
        result_str = str(result)
        assert 'API key not configured' in result_str

    def test_formats_no_analysis_available(self):
        """Test formatting when analysis is not available."""
        result = format_ai_analysis_result(
            analysis_text=None
        )
        result_str = str(result)
        assert 'not available' in result_str.lower()

    def test_persona_styling_executive(self):
        """Test that executive persona has appropriate styling."""
        result = format_ai_analysis_result(
            analysis_text="Test content",
            persona='executive'
        )
        result_str = str(result)
        assert 'Executive' in result_str

    def test_persona_styling_tech_lead(self):
        """Test that tech_lead persona has appropriate styling."""
        result = format_ai_analysis_result(
            analysis_text="Test content",
            persona='tech_lead'
        )
        result_str = str(result)
        assert 'Technical Lead' in result_str or 'Tech Lead' in result_str

    def test_persona_styling_expert(self):
        """Test that expert persona has appropriate styling."""
        result = format_ai_analysis_result(
            analysis_text="Test content",
            persona='expert'
        )
        result_str = str(result)
        assert 'Expert' in result_str


class TestExtractDashboardContext:
    """Tests for extract_dashboard_context function."""

    def test_extracts_basic_stats_from_empty_df(self):
        """Test extraction from empty dataframe."""
        empty_df = pd.DataFrame()
        context = extract_dashboard_context(
            filtered_df=empty_df,
            os_versions=['rhel:9.5'],
            instance_types=['m5.xlarge'],
            test_names=['coremark'],
            cloud_providers=['aws'],
            date_range=('2024-01-01', '2024-12-31'),
            analysis_type='regression'
        )
        assert 'filters' in context
        assert 'dataset_stats' in context
        assert context['analysis_type'] == 'regression'

    def test_extracts_filters(self):
        """Test that filters are extracted correctly."""
        df = pd.DataFrame({
            'test_name': ['test1', 'test2'],
            'os_version': ['9.5', '9.6']
        })
        context = extract_dashboard_context(
            filtered_df=df,
            os_versions=['rhel:9.5', 'rhel:9.6'],
            instance_types=['m5.xlarge'],
            test_names=['coremark'],
            cloud_providers=['aws'],
            date_range=('2024-01-01', '2024-12-31'),
            analysis_type='regression'
        )
        assert context['filters']['os_versions'] == ['rhel:9.5', 'rhel:9.6']
        assert context['filters']['instance_types'] == ['m5.xlarge']

    def test_calculates_dataset_stats(self):
        """Test that dataset statistics are calculated."""
        df = pd.DataFrame({
            'test_name': ['test1', 'test2', 'test1'],
            'os_version': ['9.5', '9.6', '9.5'],
            'hardware_config': ['m5.xlarge', 'm5.2xlarge', 'm5.xlarge'],
            'run_date': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
            'test_status': ['PASS', 'PASS', 'FAIL']
        })
        context = extract_dashboard_context(
            filtered_df=df,
            os_versions=['rhel:9.5'],
            instance_types=['m5.xlarge'],
            test_names=['test1'],
            cloud_providers=['aws'],
            date_range=('2024-01-01', '2024-12-31'),
            analysis_type='regression'
        )
        assert context['dataset_stats']['total_runs'] == 3
        assert context['dataset_stats']['unique_tests'] == 2
        assert context['dataset_stats']['unique_os'] == 2
        assert context['dataset_stats']['unique_hardware'] == 2

    def test_calculates_pass_rate(self):
        """Test that pass rate is calculated correctly."""
        df = pd.DataFrame({
            'test_name': ['test1', 'test2', 'test3', 'test4'],
            'test_status': ['PASS', 'PASS', 'PASS', 'FAIL']
        })
        context = extract_dashboard_context(
            filtered_df=df,
            os_versions=[],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            analysis_type='regression'
        )
        assert context['dataset_stats']['pass_rate'] == '75.0%'

    def test_regression_analysis_context(self):
        """Test regression-specific context extraction."""
        df = pd.DataFrame({
            'test_name': ['test1', 'test2', 'test1'],
            'is_regression': [True, False, True]
        })
        context = extract_dashboard_context(
            filtered_df=df,
            os_versions=[],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            analysis_type='regression'
        )
        assert 'regression_count' in context['dataset_stats']
        assert context['dataset_stats']['regression_count'] == 2
        assert 'top_regressions' in context['dataset_stats']

    def test_peer_analysis_context(self):
        """Test peer comparison context extraction."""
        df = pd.DataFrame({
            'test_name': ['test1', 'test2'],
            'os_distribution': ['rhel', 'ubuntu']
        })
        context = extract_dashboard_context(
            filtered_df=df,
            os_versions=[],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            analysis_type='peer'
        )
        assert 'os_distributions' in context['dataset_stats']
        assert context['dataset_stats']['os_distributions']['rhel'] == 1
        assert context['dataset_stats']['os_distributions']['ubuntu'] == 1

    def test_scaling_analysis_context(self):
        """Test scaling analysis context extraction."""
        df = pd.DataFrame({
            'test_name': ['test1', 'test2', 'test3'],
            'instance_class': ['small', 'medium', 'small']
        })
        context = extract_dashboard_context(
            filtered_df=df,
            os_versions=[],
            instance_types=[],
            test_names=[],
            cloud_providers=[],
            date_range=('2024-01-01', '2024-12-31'),
            analysis_type='scaling'
        )
        assert 'instance_classes' in context['dataset_stats']
        assert context['dataset_stats']['instance_classes']['small'] == 2
        assert context['dataset_stats']['instance_classes']['medium'] == 1
