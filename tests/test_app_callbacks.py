"""Tests for app.py callback functions."""

import sys
from unittest.mock import MagicMock, patch

import pytest


def _import_app_fresh(monkeypatch):
    """Import app after clearing module cache."""
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app as app_module  # noqa: E402
    return app_module


def test_update_nightly_run_chart_out_of_range_passes_colorblind_mode(monkeypatch):
    """
    When selected_idx is out of range, verify colorblind_mode is passed
    to create_nightly_run_category_chart.

    Addresses PR #58 review feedback - nightly fallback branch should be
    consistent with other branches.
    """
    # Import app
    app = _import_app_fresh(monkeypatch)

    # Mock the visualization function to track how it was called
    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.nightly_runs.create_nightly_run_category_chart', mock_chart_fn):
        # Call callback with out-of-range index
        runs_data = [
            {'timestamp': '2025-01-01T00:00:00', 'test_count': 10,
             'pass_count': 8, 'fail_count': 2, 'category_breakdown': {},
             'source': 'test'}
        ]
        selected_idx = 5  # Out of range (only 1 item in runs_data)
        colorblind_mode = True

        app.update_nightly_run_chart(selected_idx, colorblind_mode, runs_data)

    # Verify the function was called with colorblind_mode parameter
    mock_chart_fn.assert_called_once_with(None, colorblind_mode=True)


def test_update_nightly_run_chart_out_of_range_respects_colorblind_false(monkeypatch):
    """
    When selected_idx is out of range and colorblind_mode is False,
    verify False is passed to create_nightly_run_category_chart.
    """
    app = _import_app_fresh(monkeypatch)

    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.nightly_runs.create_nightly_run_category_chart', mock_chart_fn):
        runs_data = [
            {'timestamp': '2025-01-01T00:00:00', 'test_count': 10,
             'pass_count': 8, 'fail_count': 2, 'category_breakdown': {},
             'source': 'test'}
        ]
        selected_idx = 10  # Out of range
        colorblind_mode = False

        app.update_nightly_run_chart(selected_idx, colorblind_mode, runs_data)

    mock_chart_fn.assert_called_once_with(None, colorblind_mode=False)


def test_update_nightly_run_chart_negative_index_returns_empty_chart(monkeypatch):
    """
    When selected_idx is -1 (negative), verify it returns the empty-data
    fallback chart instead of indexing from the end of the list.

    Bug: Negative indices are treated as valid Python list indices
    (indexing from the end) rather than being rejected as invalid input.
    """
    app = _import_app_fresh(monkeypatch)

    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.nightly_runs.create_nightly_run_category_chart', mock_chart_fn):
        runs_data = [
            {'timestamp': '2025-01-01T00:00:00', 'test_count': 10,
             'pass_count': 8, 'fail_count': 2, 'category_breakdown': {},
             'source': 'test'},
            {'timestamp': '2025-01-02T00:00:00', 'test_count': 12,
             'pass_count': 10, 'fail_count': 2, 'category_breakdown': {},
             'source': 'test'}
        ]
        selected_idx = -1  # Negative index
        colorblind_mode = True

        app.update_nightly_run_chart(selected_idx, colorblind_mode, runs_data)

    # Should call with None (empty data fallback), not use the negative index
    mock_chart_fn.assert_called_once_with(None, colorblind_mode=True)


def test_update_nightly_run_chart_large_negative_index_returns_empty_chart(monkeypatch):
    """
    When selected_idx is a large negative value like -5, verify it returns
    the empty-data fallback chart.

    This test ensures we guard against all negative values, not just -1.
    """
    app = _import_app_fresh(monkeypatch)

    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.nightly_runs.create_nightly_run_category_chart', mock_chart_fn):
        runs_data = [
            {'timestamp': '2025-01-01T00:00:00', 'test_count': 10,
             'pass_count': 8, 'fail_count': 2, 'category_breakdown': {},
             'source': 'test'}
        ]
        selected_idx = -5  # Large negative index
        colorblind_mode = False

        app.update_nightly_run_chart(selected_idx, colorblind_mode, runs_data)

    # Should call with None (empty data fallback), not attempt to use -5
    mock_chart_fn.assert_called_once_with(None, colorblind_mode=False)


def test_update_rhel9_sequential_passes_colorblind_mode(monkeypatch):
    """
    Verify update_rhel9_sequential accepts colorblind_mode parameter
    and passes it to create_version_comparison_bar_chart.

    Bug fix: callback was calling create_version_comparison_bar_chart
    with colorblind_mode but didn't have it as an Input or parameter.
    """
    app = _import_app_fresh(monkeypatch)

    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_version_comparison_bar_chart', mock_chart_fn):
        analysis_json = '{"q1": {"rhel9_sequential": {"comparison_data": "{\\"columns\\":[],\\"index\\":[],\\"data\\":[]}", "baseline_version": "9.0", "comparison_version": "9.1", "num_regressions": 0, "num_comparisons": 0, "summary": "Test", "hardware_summary": "HW"}}}'
        colorblind_mode = True

        app.update_rhel9_sequential(analysis_json, colorblind_mode)

    # Verify the function was called with colorblind_mode=True
    assert mock_chart_fn.called
    call_kwargs = mock_chart_fn.call_args.kwargs
    assert 'colorblind_mode' in call_kwargs
    assert call_kwargs['colorblind_mode'] is True


def test_update_rhel9_sequential_respects_colorblind_false(monkeypatch):
    """
    Verify update_rhel9_sequential respects colorblind_mode=False.
    """
    app = _import_app_fresh(monkeypatch)

    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_version_comparison_bar_chart', mock_chart_fn):
        analysis_json = '{"q1": {"rhel9_sequential": {"comparison_data": "{\\"columns\\":[],\\"index\\":[],\\"data\\":[]}", "baseline_version": "9.0", "comparison_version": "9.1", "num_regressions": 0, "num_comparisons": 0, "summary": "Test", "hardware_summary": "HW"}}}'
        colorblind_mode = False

        app.update_rhel9_sequential(analysis_json, colorblind_mode)

    assert mock_chart_fn.called
    call_kwargs = mock_chart_fn.call_args.kwargs
    assert 'colorblind_mode' in call_kwargs
    assert call_kwargs['colorblind_mode'] is False


def test_update_rhel10_sequential_passes_colorblind_mode(monkeypatch):
    """
    Verify update_rhel10_sequential accepts colorblind_mode parameter
    and passes it to create_version_comparison_bar_chart.

    Bug fix: callback was calling create_version_comparison_bar_chart
    with colorblind_mode but didn't have it as an Input or parameter.
    """
    app = _import_app_fresh(monkeypatch)

    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_version_comparison_bar_chart', mock_chart_fn):
        analysis_json = '{"q1": {"rhel10_sequential": {"comparison_data": "{\\"columns\\":[],\\"index\\":[],\\"data\\":[]}", "baseline_version": "10.0", "comparison_version": "10.1", "num_regressions": 0, "num_comparisons": 0, "summary": "Test", "hardware_summary": "HW"}}}'
        colorblind_mode = True

        app.update_rhel10_sequential(analysis_json, colorblind_mode)

    # Verify the function was called with colorblind_mode=True
    assert mock_chart_fn.called
    call_kwargs = mock_chart_fn.call_args.kwargs
    assert 'colorblind_mode' in call_kwargs
    assert call_kwargs['colorblind_mode'] is True


def test_update_rhel10_sequential_respects_colorblind_false(monkeypatch):
    """
    Verify update_rhel10_sequential respects colorblind_mode=False.
    """
    app = _import_app_fresh(monkeypatch)

    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_version_comparison_bar_chart', mock_chart_fn):
        analysis_json = '{"q1": {"rhel10_sequential": {"comparison_data": "{\\"columns\\":[],\\"index\\":[],\\"data\\":[]}", "baseline_version": "10.0", "comparison_version": "10.1", "num_regressions": 0, "num_comparisons": 0, "summary": "Test", "hardware_summary": "HW"}}}'
        colorblind_mode = False

        app.update_rhel10_sequential(analysis_json, colorblind_mode)

    assert mock_chart_fn.called
    call_kwargs = mock_chart_fn.call_args.kwargs
    assert 'colorblind_mode' in call_kwargs
    assert call_kwargs['colorblind_mode'] is False


def test_pulse_bundle_validation_rejects_invalid_structure(monkeypatch):
    """
    When bundle_data has malformed structure (not a dict or missing critical type),
    render_server_snapshot should return error message instead of crashing.
    """
    app = _import_app_fresh(monkeypatch)

    # Test with non-dict data
    result = app.render_server_snapshot("not a dict", False)
    assert result is not None
    # Should return an error Div, not crash
    assert hasattr(result, 'children')

    # Test with list instead of dict
    result = app.render_server_snapshot([1, 2, 3], False)
    assert result is not None
    assert hasattr(result, 'children')


def test_pulse_bundle_validation_handles_missing_keys(monkeypatch):
    """
    When bundle_data is missing required keys (overview, category_mix, etc.),
    render_server_snapshot should return error message gracefully.
    """
    app = _import_app_fresh(monkeypatch)

    # Missing all keys
    incomplete_bundle = {}
    result = app.render_server_snapshot(incomplete_bundle, False)
    assert result is not None
    assert hasattr(result, 'children')

    # Missing some keys
    incomplete_bundle = {
        'overview': {'total': 100, 'by_cloud': [], 'source': 'test'},
        # Missing category_mix, activity_timeline, scope, etc.
    }
    result = app.render_server_snapshot(incomplete_bundle, False)
    assert result is not None
    assert hasattr(result, 'children')


def test_pulse_bundle_validation_accepts_valid_bundle(monkeypatch):
    """
    When bundle_data has all required keys with valid structure,
    render_server_snapshot should process it successfully.
    """
    app = _import_app_fresh(monkeypatch)

    valid_bundle = {
        'overview': {
            'total': 100,
            'by_cloud': [('AWS', 50), ('Azure', 30), ('GCP', 20)],
            'source': 'test',
            'error': None,
            'from_cache': False,
            'cache_timestamp': None,
        },
        'category_mix': {
            'by_category': [('Storage', 40), ('Network', 30), ('CPU', 30)],
            'source': 'test',
            'error': None,
            'from_cache': False,
            'cache_timestamp': None,
        },
        'activity_timeline': {
            'by_month': [('2025-01', 50), ('2025-02', 50)],
            'source': 'test',
            'error': None,
            'from_cache': False,
            'cache_timestamp': None,
        },
        'scope': {
            'document_count': 100,
            'run_date_min_utc': '2025-01-01T00:00:00Z',
            'run_date_max_utc': '2025-02-28T23:59:59Z',
            'source': 'test',
            'error': None,
            'from_cache': False,
            'cache_timestamp': None,
        },
        'policy_template_id': 'test-template',
        'definition_version': '1.0-test',
    }

    # Should not raise an exception
    with patch('src.pulse_ui.render_pulse_v1_panel', return_value=MagicMock()):
        result = app.render_server_snapshot(valid_bundle, False)
        assert result is not None


def test_q2_analysis_store_caches_results(monkeypatch):
    """
    Verify Q2 analysis callback runs once and caches results in store.

    The analysis callback should trigger when filtered_data_store changes
    and output to q2-analysis-store, not directly to the figure.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock the processor's analyze_peer_os_comparison method
    mock_analysis = MagicMock(return_value={
        'comparison_data': MagicMock(empty=False, to_json=MagicMock(return_value='{"test": "data"}')),
        'summary': 'Test summary',
        'competitive_count': 5,
        'total_benchmarks': 10
    })

    with patch.object(app.processor, 'analyze_peer_os_comparison', mock_analysis), \
         patch.object(app.processor, '_get_available_comparisons', return_value=[{
             'peer_os': 'ubuntu',
             'baseline_version': '9.0',
             'peer_version': '22.04',
             'cloud_provider': 'aws',
             'label': 'RHEL 9.0 vs Ubuntu 22.04'
         }]):

        # Simulate filtered data changing
        filtered_data_json = '{"columns":["os_name","benchmark"],"index":[0,1],"data":[["rhel","test1"],["ubuntu","test1"]]}'

        # Call the analysis callback (should exist as update_q2_analysis)
        result = app.update_q2_analysis(filtered_data_json)

        # Verify the analysis was called once
        assert mock_analysis.call_count == 1

        # Verify the result is stored data (not a figure)
        assert result is not None
        assert isinstance(result, dict)


def test_q2_colorblind_toggle_no_reanalysis(monkeypatch):
    """
    Verify colorblind mode toggle does NOT trigger re-analysis.

    The render callback should take data from q2-analysis-store and
    colorblind-mode-store, and should NOT call analyze_peer_os_comparison.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock the processor's analyze method - it should NOT be called
    mock_analysis = MagicMock(return_value={
        'comparison_data': MagicMock(empty=False),
        'summary': 'Test summary',
        'competitive_count': 5,
        'total_benchmarks': 10
    })

    # Mock the visualization function
    mock_viz = MagicMock(return_value=MagicMock())

    with patch.object(app.processor, 'analyze_peer_os_comparison', mock_analysis), \
         patch('src.components.visualizations.create_peer_os_comparison_chart', mock_viz):

        # Simulate cached analysis data
        analysis_data = {
            'comparison_data': '{"columns":["category","rhel_wins"],"index":[0],"data":[["compute",8]]}',
            'summary': 'Test summary',
            'competitive_count': 5,
            'total_benchmarks': 10,
            'comparison_config': {
                'peer_os': 'ubuntu',
                'baseline_version': '9.0',
                'peer_version': '22.04',
                'cloud_provider': 'aws',
                'label': 'RHEL 9.0 vs Ubuntu 22.04'
            },
            'has_data': True
        }

        # Call the render callback (should exist as update_q2_figure)
        colorblind_mode = True
        fig, summary = app.update_q2_figure(analysis_data, colorblind_mode)

        # Verify the analysis method was NOT called
        assert mock_analysis.call_count == 0

        # Verify the visualization was created with colorblind mode
        assert mock_viz.called
        call_kwargs = mock_viz.call_args.kwargs
        assert call_kwargs['colorblind_mode'] is True

        # Verify outputs are returned
        assert fig is not None
        assert summary is not None


def test_investigation_view_accepts_colorblind_mode(monkeypatch):
    """
    Verify update_investigation_view callback accepts colorblind_mode parameter.

    The callback should have colorblind_mode as an Input from colorblind-mode-store
    and accept it as a parameter without error.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization functions
    mock_detail_chart = MagicMock(return_value=MagicMock())
    mock_time_series = MagicMock(return_value=MagicMock())
    mock_metrics_table = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_investigation_detail_chart', mock_detail_chart), \
         patch('src.components.visualizations.create_time_series_chart', mock_time_series), \
         patch('src.components.visualizations.create_metrics_table', mock_metrics_table):

        # Prepare callback inputs
        nav_state = {
            'view': 'investigation',
            'investigation_params': {
                'test_name': 'test_benchmark',
                'baseline_version': '9.0',
                'comparison_version': '9.1',
                'os_distribution': 'rhel'
            }
        }

        # Create minimal test data
        import pandas as pd
        from io import StringIO
        test_data = pd.DataFrame({
            'test_name': ['test_benchmark'] * 4,
            'os_distribution': ['rhel'] * 4,
            'os_version': ['9.0', '9.0', '9.1', '9.1'],
            'timestamp': pd.date_range('2025-01-01', periods=4),
            'primary_metric_value': [100, 105, 110, 115],
            'primary_metric_unit': ['ms'] * 4,
            'instance_type': ['m5.large'] * 4,
            'cloud_provider': ['aws'] * 4,
            'status': ['pass'] * 4
        })
        filtered_data_json = test_data.to_json(orient='split')

        colorblind_mode = True

        # Should not raise an error
        result = app.update_investigation_view(nav_state, filtered_data_json, colorblind_mode)

        # Verify result structure (4 outputs: summary, comparison chart, timeline chart, table)
        assert isinstance(result, tuple)
        assert len(result) == 4


def test_investigation_view_passes_colorblind_to_charts(monkeypatch):
    """
    Verify update_investigation_view passes colorblind_mode to all chart functions.

    Tests that colorblind_mode is correctly passed to:
    - create_investigation_detail_chart()
    - create_time_series_chart()
    - create_metrics_table()
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization functions
    mock_detail_chart = MagicMock(return_value=MagicMock())
    mock_time_series = MagicMock(return_value=MagicMock())
    mock_metrics_table = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_investigation_detail_chart', mock_detail_chart), \
         patch('src.components.visualizations.create_time_series_chart', mock_time_series), \
         patch('src.components.visualizations.create_metrics_table', mock_metrics_table):

        # Prepare callback inputs
        nav_state = {
            'view': 'investigation',
            'investigation_params': {
                'test_name': 'test_benchmark',
                'baseline_version': '9.0',
                'comparison_version': '9.1',
                'os_distribution': 'rhel'
            }
        }

        # Create minimal test data
        import pandas as pd
        test_data = pd.DataFrame({
            'test_name': ['test_benchmark'] * 4,
            'os_distribution': ['rhel'] * 4,
            'os_version': ['9.0', '9.0', '9.1', '9.1'],
            'timestamp': pd.date_range('2025-01-01', periods=4),
            'primary_metric_value': [100, 105, 110, 115],
            'primary_metric_unit': ['ms'] * 4,
            'instance_type': ['m5.large'] * 4,
            'cloud_provider': ['aws'] * 4,
            'status': ['pass'] * 4
        })
        filtered_data_json = test_data.to_json(orient='split')

        colorblind_mode = True

        # Call the callback
        app.update_investigation_view(nav_state, filtered_data_json, colorblind_mode)

        # Verify create_investigation_detail_chart was called with colorblind_mode=True
        assert mock_detail_chart.called
        detail_kwargs = mock_detail_chart.call_args.kwargs
        assert 'colorblind_mode' in detail_kwargs
        assert detail_kwargs['colorblind_mode'] is True

        # Verify create_time_series_chart was called with colorblind_mode=True
        assert mock_time_series.called
        time_series_kwargs = mock_time_series.call_args.kwargs
        assert 'colorblind_mode' in time_series_kwargs
        assert time_series_kwargs['colorblind_mode'] is True

        # Verify create_metrics_table was called with colorblind_mode=True
        assert mock_metrics_table.called
        metrics_kwargs = mock_metrics_table.call_args.kwargs
        assert 'colorblind_mode' in metrics_kwargs
        assert metrics_kwargs['colorblind_mode'] is True


def test_investigation_view_respects_colorblind_false(monkeypatch):
    """
    Verify update_investigation_view respects colorblind_mode=False.

    When colorblind mode is disabled, all chart functions should receive False.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization functions
    mock_detail_chart = MagicMock(return_value=MagicMock())
    mock_time_series = MagicMock(return_value=MagicMock())
    mock_metrics_table = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_time_series_chart', mock_time_series), \
         patch('src.components.visualizations.create_investigation_detail_chart', mock_detail_chart), \
         patch('src.components.visualizations.create_metrics_table', mock_metrics_table):

        # Prepare callback inputs
        nav_state = {
            'view': 'investigation',
            'investigation_params': {
                'test_name': 'test_benchmark',
                'baseline_version': '9.0',
                'comparison_version': '9.1',
                'os_distribution': 'rhel'
            }
        }

        # Create minimal test data
        import pandas as pd
        test_data = pd.DataFrame({
            'test_name': ['test_benchmark'] * 4,
            'os_distribution': ['rhel'] * 4,
            'os_version': ['9.0', '9.0', '9.1', '9.1'],
            'timestamp': pd.date_range('2025-01-01', periods=4),
            'primary_metric_value': [100, 105, 110, 115],
            'primary_metric_unit': ['ms'] * 4,
            'instance_type': ['m5.large'] * 4,
            'cloud_provider': ['aws'] * 4,
            'status': ['pass'] * 4
        })
        filtered_data_json = test_data.to_json(orient='split')

        colorblind_mode = False

        # Call the callback
        app.update_investigation_view(nav_state, filtered_data_json, colorblind_mode)

        # Verify all chart functions were called with colorblind_mode=False
        assert mock_detail_chart.call_args.kwargs['colorblind_mode'] is False
        assert mock_time_series.call_args.kwargs['colorblind_mode'] is False
        assert mock_metrics_table.call_args.kwargs['colorblind_mode'] is False


def test_update_question3_accepts_colorblind_mode(monkeypatch):
    """
    Verify update_question3 callback accepts colorblind_mode parameter.

    The callback should have colorblind_mode as an Input from colorblind-mode-store
    and accept it as a parameter without error.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization function
    mock_chart_fn = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_chart_fn), \
         patch.object(app.processor, 'analyze_cloud_scaling', return_value={
             'scaling_data': MagicMock(empty=False),
             'summary': 'Test summary',
             'linear_scaling_count': 5,
             'total_benchmarks': 10
         }):

        # Prepare callback inputs
        import pandas as pd
        test_data = pd.DataFrame({
            'cloud_provider': ['aws'] * 4,
            'os_distribution': ['rhel'] * 4,
            'os_version': ['9.0'] * 4,
            'instance_type': ['m5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge'],
            'benchmark_category': ['compute'] * 4
        })
        filtered_data_json = test_data.to_json(orient='split')

        cloud_provider = 'aws'
        instance_series = None
        os_distribution = 'rhel'
        os_version = '9.0'
        benchmark_category = 'all'
        colorblind_mode = True

        # Should not raise an error
        result = app.update_question3(
            cloud_provider,
            instance_series,
            os_distribution,
            os_version,
            benchmark_category,
            filtered_data_json,
            colorblind_mode
        )

        # Verify result structure (2 outputs: figure and summary)
        assert isinstance(result, tuple)
        assert len(result) == 2


def test_update_question3_passes_colorblind_mode_true(monkeypatch):
    """
    Verify update_question3 passes colorblind_mode=True to create_cloud_scaling_chart.

    When colorblind mode is enabled, the chart function should receive True.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization function
    mock_chart_fn = MagicMock(return_value=MagicMock())

    # Create test scaling data
    import pandas as pd
    scaling_data = pd.DataFrame({
        'instance_type': ['m5.large', 'm5.xlarge'],
        'vcpu_count': [2, 4],
        'performance': [100, 200],
        'benchmark_category': ['compute'] * 2
    })

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_chart_fn), \
         patch.object(app.processor, 'analyze_cloud_scaling', return_value={
             'scaling_data': scaling_data,
             'summary': 'Test summary',
             'linear_scaling_count': 1,
             'total_benchmarks': 2
         }):

        # Prepare callback inputs
        test_data = pd.DataFrame({
            'cloud_provider': ['aws'] * 2,
            'os_distribution': ['rhel'] * 2,
            'os_version': ['9.0'] * 2,
            'instance_type': ['m5.large', 'm5.xlarge'],
            'benchmark_category': ['compute'] * 2
        })
        filtered_data_json = test_data.to_json(orient='split')

        # Call the callback with colorblind_mode=True
        app.update_question3(
            cloud_provider='aws',
            instance_series=None,
            os_distribution='rhel',
            os_version='9.0',
            benchmark_category='all',
            filtered_data_json=filtered_data_json,
            colorblind_mode=True
        )

        # Verify create_cloud_scaling_chart was called with colorblind_mode=True
        assert mock_chart_fn.called
        call_kwargs = mock_chart_fn.call_args.kwargs
        assert 'colorblind_mode' in call_kwargs
        assert call_kwargs['colorblind_mode'] is True


def test_update_question3_passes_colorblind_mode_false(monkeypatch):
    """
    Verify update_question3 passes colorblind_mode=False to create_cloud_scaling_chart.

    When colorblind mode is disabled, the chart function should receive False.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization function
    mock_chart_fn = MagicMock(return_value=MagicMock())

    # Create test scaling data
    import pandas as pd
    scaling_data = pd.DataFrame({
        'instance_type': ['m5.large', 'm5.xlarge'],
        'vcpu_count': [2, 4],
        'performance': [100, 200],
        'benchmark_category': ['compute'] * 2
    })

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_chart_fn), \
         patch.object(app.processor, 'analyze_cloud_scaling', return_value={
             'scaling_data': scaling_data,
             'summary': 'Test summary',
             'linear_scaling_count': 1,
             'total_benchmarks': 2
         }):

        # Prepare callback inputs
        test_data = pd.DataFrame({
            'cloud_provider': ['aws'] * 2,
            'os_distribution': ['rhel'] * 2,
            'os_version': ['9.0'] * 2,
            'instance_type': ['m5.large', 'm5.xlarge'],
            'benchmark_category': ['compute'] * 2
        })
        filtered_data_json = test_data.to_json(orient='split')

        # Call the callback with colorblind_mode=False
        app.update_question3(
            cloud_provider='aws',
            instance_series=None,
            os_distribution='rhel',
            os_version='9.0',
            benchmark_category='all',
            filtered_data_json=filtered_data_json,
            colorblind_mode=False
        )

        # Verify create_cloud_scaling_chart was called with colorblind_mode=False
        assert mock_chart_fn.called
        call_kwargs = mock_chart_fn.call_args.kwargs
        assert 'colorblind_mode' in call_kwargs
        assert call_kwargs['colorblind_mode'] is False
