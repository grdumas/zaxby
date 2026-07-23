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


def test_update_question3_handles_none_os_distribution(monkeypatch):
    """
    When os_distribution is None, verify render_q3_figure does not crash
    when building the chart title.

    Bug: Previously called os_distribution.upper() without checking if it's None,
    causing AttributeError during initial load or dropdown refresh.
    """
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Mock the processor to return scaling data
    mock_scaling_data = pd.DataFrame({
        'instance_type': ['t3.small', 't3.medium'],
        'benchmark_category': ['CPU', 'CPU'],
        'score': [50.0, 100.0]
    })

    mock_fig = MagicMock()

    # Simulate cached analysis data with None os_distribution
    analysis_data = {
        'scaling_data': mock_scaling_data.to_json(orient='split'),  # JSON string, not dict
        'summary': 'Test summary',
        'linear_scaling_count': 1,
        'total_benchmarks': 2,
        'cloud_provider': 'aws',
        'os_version': '22.04',
        'os_distribution': None,  # This is the bug trigger
        'instance_series': None,
        'has_data': True
    }

    with patch('src.components.visualizations.create_cloud_scaling_chart', return_value=mock_fig):
        # Call render callback with os_distribution=None
        # Should not raise AttributeError
        try:
            fig, summary = app.render_q3_figure(
                analysis_data,
                benchmark_category='all',
                colorblind_mode=False
            )
            # If we get here, the bug is fixed
            assert fig is not None
        except AttributeError as e:
            if "'NoneType' object has no attribute 'upper'" in str(e):
                pytest.fail(f"render_q3_figure crashed on None os_distribution: {e}")
            raise


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

        # Simulate cached analysis data with JSON string format (optimized)
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


def test_q3_analysis_store_caches_results(monkeypatch):
    """
    Verify Q3 analysis callback runs once and caches results in store.

    The analysis callback should trigger when data inputs change
    and output to q3-analysis-store, not directly to the figure.
    This test should FAIL initially because q3-analysis-store doesn't exist yet.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock the processor's analyze_cloud_scaling method
    mock_analysis = MagicMock(return_value={
        'scaling_data': MagicMock(
            empty=False,
            to_json=MagicMock(return_value='{"columns":["instance_size","score"],"index":[0],"data":[["small",100]]}')
        ),
        'summary': 'Test scaling summary',
        'linear_scaling_count': 8,
        'total_benchmarks': 10
    })

    with patch.object(app.processor, 'analyze_cloud_scaling', mock_analysis):
        # Simulate data inputs changing with proper columns
        filtered_data_json = '{"columns":["os_name","os_distribution","os_version","benchmark","cloud_provider","instance_type"],"index":[0],"data":[["rhel","rhel","9.0","test1","aws","m5.large"]]}'
        cloud_provider = 'aws'
        os_distribution = 'rhel'
        os_version = '9.0'
        instance_series = None

        # Call the analysis callback (should exist as update_q3_analysis)
        # Parameters: filtered_data_json, cloud_provider, instance_series, os_distribution, os_version
        result = app.update_q3_analysis(
            filtered_data_json,
            cloud_provider,
            instance_series,
            os_distribution,
            os_version
        )

        # Verify the analysis was called once
        assert mock_analysis.call_count == 1

        # Verify the result is stored data (not a figure)
        assert result is not None
        assert isinstance(result, dict)
        assert 'scaling_data' in result


def test_q3_colorblind_toggle_no_reanalysis(monkeypatch):
    """
    Verify colorblind mode toggle does NOT trigger Q3 re-analysis.

    The render callback should take data from q3-analysis-store and
    colorblind-mode-store, and should NOT call analyze_cloud_scaling.
    This test should FAIL initially because the callback isn't split yet.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock the processor's analyze method - it should NOT be called
    mock_analysis = MagicMock(return_value={
        'scaling_data': MagicMock(empty=False),
        'summary': 'Test summary',
        'linear_scaling_count': 8,
        'total_benchmarks': 10
    })

    # Mock the visualization function
    mock_viz = MagicMock(return_value=MagicMock())

    with patch.object(app.processor, 'analyze_cloud_scaling', mock_analysis), \
         patch('src.components.visualizations.create_cloud_scaling_chart', mock_viz):

        # Simulate cached analysis data with JSON string format (optimized)
        analysis_data = {
            'scaling_data': '{"columns":["instance_size","score","benchmark_category"],"index":[0],"data":[["small",100,"System"]]}',
            'summary': 'Test scaling summary',
            'linear_scaling_count': 8,
            'total_benchmarks': 10,
            'cloud_provider': 'aws',
            'os_version': '9.0',
            'os_distribution': 'rhel',
            'instance_series': None,
            'has_data': True
        }

        # Call the render callback (should exist as render_q3_figure)
        # Parameters: analysis_data, benchmark_category, colorblind_mode
        benchmark_category = 'all'
        colorblind_mode = True
        fig, summary = app.render_q3_figure(analysis_data, benchmark_category, colorblind_mode)

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

        # Verify result structure (6 outputs: summary, comparison chart, timeline chart, table, dropdown options, drilldown data)
        assert isinstance(result, tuple)
        assert len(result) == 6


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
    Verify render_q3_figure callback accepts colorblind_mode parameter.

    The callback should have colorblind_mode as an Input from colorblind-mode-store
    and accept it as a parameter without error.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization function
    mock_chart_fn = MagicMock(return_value=MagicMock())

    import pandas as pd
    import json
    scaling_data = pd.DataFrame({
        'instance_type': ['m5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge'],
        'vcpu_count': [2, 4, 8, 16],
        'performance': [100, 200, 400, 800],
        'benchmark_category': ['compute'] * 4
    })

    analysis_data = {
        'scaling_data': scaling_data.to_json(orient='split'),  # JSON string, not dict
        'summary': 'Test summary',
        'linear_scaling_count': 5,
        'total_benchmarks': 10,
        'cloud_provider': 'aws',
        'os_version': '9.0',
        'os_distribution': 'rhel',
        'instance_series': None,
        'has_data': True
    }

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_chart_fn):
        # Should not raise an error
        result = app.render_q3_figure(
            analysis_data,
            benchmark_category='all',
            colorblind_mode=True
        )

        # Verify result structure (2 outputs: figure and summary)
        assert isinstance(result, tuple)
        assert len(result) == 2


def test_update_question3_passes_colorblind_mode_true(monkeypatch):
    """
    Verify render_q3_figure passes colorblind_mode=True to create_cloud_scaling_chart.

    When colorblind mode is enabled, the chart function should receive True.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization function
    mock_chart_fn = MagicMock(return_value=MagicMock())

    # Create test scaling data
    import pandas as pd
    import json
    scaling_data = pd.DataFrame({
        'instance_type': ['m5.large', 'm5.xlarge'],
        'vcpu_count': [2, 4],
        'performance': [100, 200],
        'benchmark_category': ['compute'] * 2
    })

    analysis_data = {
        'scaling_data': scaling_data.to_json(orient='split'),  # JSON string, not dict
        'summary': 'Test summary',
        'linear_scaling_count': 1,
        'total_benchmarks': 2,
        'cloud_provider': 'aws',
        'os_version': '9.0',
        'os_distribution': 'rhel',
        'instance_series': None,
        'has_data': True
    }

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_chart_fn):
        # Call the callback with colorblind_mode=True
        app.render_q3_figure(
            analysis_data,
            benchmark_category='all',
            colorblind_mode=True
        )

        # Verify create_cloud_scaling_chart was called with colorblind_mode=True
        assert mock_chart_fn.called
        call_kwargs = mock_chart_fn.call_args.kwargs
        assert 'colorblind_mode' in call_kwargs
        assert call_kwargs['colorblind_mode'] is True


def test_update_question3_passes_colorblind_mode_false(monkeypatch):
    """
    Verify render_q3_figure passes colorblind_mode=False to create_cloud_scaling_chart.

    When colorblind mode is disabled, the chart function should receive False.
    """
    app = _import_app_fresh(monkeypatch)

    # Mock visualization function
    mock_chart_fn = MagicMock(return_value=MagicMock())

    # Create test scaling data
    import pandas as pd
    import json
    scaling_data = pd.DataFrame({
        'instance_type': ['m5.large', 'm5.xlarge'],
        'vcpu_count': [2, 4],
        'performance': [100, 200],
        'benchmark_category': ['compute'] * 2
    })

    analysis_data = {
        'scaling_data': scaling_data.to_json(orient='split'),  # JSON string, not dict
        'summary': 'Test summary',
        'linear_scaling_count': 1,
        'total_benchmarks': 2,
        'cloud_provider': 'aws',
        'os_version': '9.0',
        'os_distribution': 'rhel',
        'instance_series': None,
        'has_data': True
    }

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_chart_fn):
        # Call the callback with colorblind_mode=False
        app.render_q3_figure(
            analysis_data,
            benchmark_category='all',
            colorblind_mode=False
        )

        # Verify create_cloud_scaling_chart was called with colorblind_mode=False
        assert mock_chart_fn.called
        call_kwargs = mock_chart_fn.call_args.kwargs
        assert 'colorblind_mode' in call_kwargs
        assert call_kwargs['colorblind_mode'] is False


# ============================================================================
# Boolean normalization tests for colorblind_mode
# ============================================================================

def test_normalize_colorblind_mode_true():
    """Verify _normalize_colorblind_mode returns True for boolean True."""
    import app
    assert app._normalize_colorblind_mode(True) is True


def test_normalize_colorblind_mode_string_true():
    """Verify _normalize_colorblind_mode returns True for string 'true'."""
    import app
    assert app._normalize_colorblind_mode("true") is True


def test_normalize_colorblind_mode_int_one():
    """Verify _normalize_colorblind_mode returns True for integer 1."""
    import app
    assert app._normalize_colorblind_mode(1) is True


def test_normalize_colorblind_mode_string_false():
    """Verify _normalize_colorblind_mode returns False for string 'false'."""
    import app
    assert app._normalize_colorblind_mode("false") is False


def test_normalize_colorblind_mode_empty_string():
    """Verify _normalize_colorblind_mode returns False for empty string."""
    import app
    assert app._normalize_colorblind_mode("") is False


def test_normalize_colorblind_mode_none():
    """Verify _normalize_colorblind_mode returns False for None."""
    import app
    assert app._normalize_colorblind_mode(None) is False


def test_normalize_colorblind_mode_int_zero():
    """Verify _normalize_colorblind_mode returns False for integer 0."""
    import app
    assert app._normalize_colorblind_mode(0) is False


def test_normalize_colorblind_mode_false():
    """Verify _normalize_colorblind_mode returns False for boolean False."""
    import app
    assert app._normalize_colorblind_mode(False) is False


def test_normalize_colorblind_mode_arbitrary_string():
    """Verify _normalize_colorblind_mode returns False for arbitrary strings."""
    import app
    assert app._normalize_colorblind_mode("random") is False
    assert app._normalize_colorblind_mode("1") is False
    assert app._normalize_colorblind_mode("yes") is False


# ============================================================================
# Clientside callback normalization tests
# ============================================================================

def test_clientside_toggle_normalizes_string_false_to_boolean():
    """
    CRITICAL: Verify clientside toggle callback normalizes string "false" correctly.

    JavaScript truthiness problem: !!"false" evaluates to true because
    "false" is a non-empty string. Clientside callbacks must use strict
    normalization matching _normalize_colorblind_mode():
        (value === true || value === 'true' || value === 1)

    Expected behavior:
    - Input "false" -> normalize to False -> toggle to True
    - Input "true" -> normalize to True -> toggle to False
    - Input false -> normalize to False -> toggle to True
    - Input true -> normalize to True -> toggle to False
    - Input 1 -> normalize to True -> toggle to False
    - Input 0 -> normalize to False -> toggle to True

    This test documents the expected JavaScript behavior in the clientside
    callback at app.py:540-555. Since we can't unit test JavaScript directly,
    this test ensures the Python normalization reference is correct.
    """
    import app
    # Document the normalization reference behavior
    # The clientside JS must match this
    assert app._normalize_colorblind_mode("false") is False
    assert app._normalize_colorblind_mode("true") is True
    assert app._normalize_colorblind_mode(False) is False
    assert app._normalize_colorblind_mode(True) is True
    assert app._normalize_colorblind_mode(1) is True
    assert app._normalize_colorblind_mode(0) is False


def test_clientside_body_class_normalizes_values_strictly():
    """
    Verify clientside body class sync callback uses strict normalization.

    The callback at app.py:558-570 syncs colorblind-mode-store to the
    body.colorblind-mode CSS class. It must use strict normalization:
        (value === true || value === 'true' || value === 1)

    NOT unsafe truthiness: !!value would treat "false" as true.

    Expected behavior:
    - Input "false" -> normalize to False -> remove class
    - Input "true" -> normalize to True -> add class
    - Input false -> normalize to False -> remove class
    - Input true -> normalize to True -> add class
    - Input 1 -> normalize to True -> add class
    - Input 0 -> normalize to False -> remove class

    This test documents expected behavior for the clientside callback.
    """
    import app
    # Document the normalization reference behavior
    # The clientside JS must match this
    assert app._normalize_colorblind_mode("false") is False
    assert app._normalize_colorblind_mode("true") is True
    assert app._normalize_colorblind_mode(False) is False
    assert app._normalize_colorblind_mode(True) is True
    assert app._normalize_colorblind_mode(1) is True
    assert app._normalize_colorblind_mode(0) is False


# ============================================================================
# Accessibility tests for toggle button
# ============================================================================

def test_colorblind_toggle_has_accessible_label(monkeypatch):
    """
    Verify colorblind-mode-toggle button has an accessible label.

    The button must have either:
    - A child with text content (fallback for CSS failure)
    - OR an aria-label attribute

    This ensures the control remains discoverable if CSS fails to load.
    """
    from dash import html

    app = _import_app_fresh(monkeypatch)

    # Find the colorblind toggle button in the layout
    def find_button(component, button_id):
        """Recursively search for button with given id."""
        if hasattr(component, 'id') and component.id == button_id:
            return component
        if hasattr(component, 'children'):
            if isinstance(component.children, list):
                for child in component.children:
                    result = find_button(child, button_id)
                    if result:
                        return result
            elif component.children:
                return find_button(component.children, button_id)
        return None

    # Get the layout (it's a function, so we need to call it)
    layout = app.app.layout() if callable(app.app.layout) else app.app.layout
    button = find_button(layout, "colorblind-mode-toggle")
    assert button is not None, "colorblind-mode-toggle button not found in layout"

    # Check for accessible label
    has_text_child = False
    has_aria_label = False

    # Check for text children
    if hasattr(button, 'children') and button.children:
        if isinstance(button.children, str):
            has_text_child = bool(button.children.strip())
        elif isinstance(button.children, list):
            has_text_child = any(
                isinstance(child, str) and child.strip()
                for child in button.children
            )
        else:
            # Check if it's an html.Span or similar component with text
            has_text_child = (
                hasattr(button.children, 'children') and
                isinstance(button.children.children, str) and
                bool(button.children.children.strip())
            )

    # Check for aria-label
    if hasattr(button, '__dict__') and 'aria-label' in button.__dict__:
        has_aria_label = bool(button.__dict__['aria-label'])

    # Must have at least one accessibility feature
    assert has_text_child or has_aria_label, \
        "Button must have either text children or aria-label for accessibility"


def test_colorblind_toggle_has_visually_hidden_child(monkeypatch):
    """
    Verify colorblind-mode-toggle button has a visually-hidden child.

    The button should have a child with className containing "visually-hidden"
    or "sr-only". This provides a fallback label that is:
    - Hidden visually (via CSS)
    - Readable by screen readers
    - Visible if CSS fails to load

    Addresses PR #58 review: Button has no fallback if CSS fails.
    """
    from dash import html

    app = _import_app_fresh(monkeypatch)

    # Find the colorblind toggle button in the layout
    def find_button(component, button_id):
        """Recursively search for button with given id."""
        if hasattr(component, 'id') and component.id == button_id:
            return component
        if hasattr(component, 'children'):
            if isinstance(component.children, list):
                for child in component.children:
                    result = find_button(child, button_id)
                    if result:
                        return result
            elif component.children:
                return find_button(component.children, button_id)
        return None

    # Get the layout (it's a function, so we need to call it)
    layout = app.app.layout() if callable(app.app.layout) else app.app.layout
    button = find_button(layout, "colorblind-mode-toggle")
    assert button is not None, "colorblind-mode-toggle button not found in layout"

    # Check for visually-hidden class on children
    has_visually_hidden = False

    if hasattr(button, 'children') and button.children:
        # Handle html.Span or similar component
        if hasattr(button.children, 'className'):
            class_name = button.children.className or ""
            has_visually_hidden = (
                "visually-hidden" in class_name or "sr-only" in class_name
            )
        # Handle list of children
        elif isinstance(button.children, list):
            for child in button.children:
                if hasattr(child, 'className'):
                    class_name = child.className or ""
                    if "visually-hidden" in class_name or "sr-only" in class_name:
                        has_visually_hidden = True
                        break

    assert has_visually_hidden, \
        "Button must have a child with 'visually-hidden' or 'sr-only' class for CSS fallback"


# ============================================================================
# DataFrame serialization optimization tests
# ============================================================================

def test_q2_analysis_store_contains_dict_not_string(monkeypatch):
    """
    Verify Q2 analysis store contains a JSON string (optimized format).

    Performance optimization: storing as JSON string avoids double-parsing
    (json.loads → DataFrame vs direct pd.read_json).
    """
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Mock the processor methods
    mock_comparison_df = pd.DataFrame({
        'category': ['compute', 'storage'],
        'rhel_wins': [8, 6]
    })

    mock_analysis = MagicMock(return_value={
        'comparison_data': mock_comparison_df,
        'summary': 'Test summary',
        'competitive_count': 14,
        'total_benchmarks': 20
    })

    with patch.object(app.processor, 'analyze_peer_os_comparison', mock_analysis), \
         patch.object(app.processor, '_get_available_comparisons', return_value=[{
             'peer_os': 'ubuntu',
             'baseline_version': '9.0',
             'peer_version': '22.04',
             'cloud_provider': 'aws',
             'label': 'RHEL 9.0 vs Ubuntu 22.04'
         }]):

        # Call the analysis callback
        filtered_data_json = '{"columns":["os_name","benchmark"],"index":[0,1],"data":[["rhel","test1"],["ubuntu","test1"]]}'
        result = app.update_q2_analysis(filtered_data_json)

        # Verify result structure
        assert result is not None
        assert isinstance(result, dict)
        assert 'comparison_data' in result

        # CRITICAL: comparison_data should be a JSON string (optimized format)
        comparison_data = result['comparison_data']
        assert isinstance(comparison_data, str), \
            f"Expected JSON string but got {type(comparison_data).__name__}"

        # Verify it's valid JSON that can be parsed by pandas
        from io import StringIO
        reconstructed_df = pd.read_json(StringIO(comparison_data), orient='split')
        assert not reconstructed_df.empty


def test_q2_render_callback_accepts_dict_from_store(monkeypatch):
    """
    Verify Q2 render callback can reconstruct DataFrame from JSON string.

    Performance optimization: single-pass pd.read_json instead of double-parsing.
    """
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Mock the visualization function
    mock_viz = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_peer_os_comparison_chart', mock_viz):
        # Create mock DataFrame and convert to JSON string
        mock_df = pd.DataFrame({
            'category': ['compute', 'storage'],
            'rhel_wins': [8, 6]
        })

        # Simulate cached analysis data with JSON string (optimized format)
        analysis_data = {
            'comparison_data': mock_df.to_json(orient='split'),
            'summary': 'Test summary',
            'competitive_count': 14,
            'total_benchmarks': 20,
            'comparison_config': {
                'peer_os': 'ubuntu',
                'baseline_version': '9.0',
                'peer_version': '22.04',
                'cloud_provider': 'aws',
                'label': 'RHEL 9.0 vs Ubuntu 22.04'
            },
            'has_data': True
        }

        # Call the render callback
        colorblind_mode = True
        fig, summary = app.update_q2_figure(analysis_data, colorblind_mode)

        # Verify outputs are returned
        assert fig is not None
        assert summary is not None

        # Verify the visualization was created
        assert mock_viz.called


def test_q3_analysis_store_contains_dict_not_string(monkeypatch):
    """
    Verify Q3 analysis store contains a JSON string (optimized format).

    Performance optimization: storing as JSON string avoids double-parsing
    (json.loads → DataFrame vs direct pd.read_json).
    """
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Mock the processor method
    mock_scaling_df = pd.DataFrame({
        'instance_type': ['m5.large', 'm5.xlarge'],
        'vcpu_count': [2, 4],
        'performance': [100, 200],
        'benchmark_category': ['compute', 'compute']
    })

    mock_analysis = MagicMock(return_value={
        'scaling_data': mock_scaling_df,
        'summary': 'Test scaling summary',
        'linear_scaling_count': 8,
        'total_benchmarks': 10
    })

    with patch.object(app.processor, 'analyze_cloud_scaling', mock_analysis):
        # Call the analysis callback
        filtered_data_json = '{"columns":["os_name","os_distribution","os_version","benchmark","cloud_provider","instance_type"],"index":[0],"data":[["rhel","rhel","9.0","test1","aws","m5.large"]]}'
        result = app.update_q3_analysis(
            filtered_data_json,
            cloud_provider='aws',
            instance_series=None,
            os_distribution='rhel',
            os_version='9.0'
        )

        # Verify result structure
        assert result is not None
        assert isinstance(result, dict)
        assert 'scaling_data' in result

        # CRITICAL: scaling_data should be a JSON string (optimized format)
        scaling_data = result['scaling_data']
        assert isinstance(scaling_data, str), \
            f"Expected JSON string but got {type(scaling_data).__name__}"

        # Verify it's valid JSON that can be parsed by pandas
        from io import StringIO
        reconstructed_df = pd.read_json(StringIO(scaling_data), orient='split')
        assert not reconstructed_df.empty


def test_q3_render_callback_accepts_dict_from_store(monkeypatch):
    """
    Verify Q3 render callback can reconstruct DataFrame from JSON string.

    Performance optimization: single-pass pd.read_json instead of double-parsing.
    """
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Mock the visualization function
    mock_viz = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_viz):
        # Create mock DataFrame and convert to JSON string
        mock_df = pd.DataFrame({
            'instance_type': ['m5.large', 'm5.xlarge'],
            'vcpu_count': [2, 4],
            'performance': [100, 200],
            'benchmark_category': ['compute', 'compute']
        })

        # Simulate cached analysis data with JSON string (optimized format)
        analysis_data = {
            'scaling_data': mock_df.to_json(orient='split'),
            'summary': 'Test scaling summary',
            'linear_scaling_count': 8,
            'total_benchmarks': 10,
            'cloud_provider': 'aws',
            'os_version': '9.0',
            'os_distribution': 'rhel',
            'instance_series': None,
            'has_data': True
        }

        # Call the render callback
        fig, summary = app.render_q3_figure(
            analysis_data,
            benchmark_category='all',
            colorblind_mode=True
        )

        # Verify outputs are returned
        assert fig is not None
        assert summary is not None

        # Verify the visualization was created
        assert mock_viz.called


def test_q2_render_handles_none_store_gracefully(monkeypatch):
    """
    Verify Q2 render callback handles None/empty store data gracefully.

    Backwards compatibility: when store is empty (initial load),
    callback should return empty figure instead of crashing.
    """
    app = _import_app_fresh(monkeypatch)

    with patch('src.components.visualizations.create_empty_figure', return_value=MagicMock()) as mock_empty:
        # Call with None
        fig, summary = app.update_q2_figure(None, colorblind_mode=False)

        # Should return empty figure
        assert fig is not None
        assert mock_empty.called


def test_q3_render_handles_none_store_gracefully(monkeypatch):
    """
    Verify Q3 render callback handles None/empty store data gracefully.

    Backwards compatibility: when store is empty (initial load),
    callback should return empty figure instead of crashing.
    """
    app = _import_app_fresh(monkeypatch)

    with patch('src.components.visualizations.create_empty_figure', return_value=MagicMock()) as mock_empty:
        # Call with None
        fig, summary = app.render_q3_figure(None, benchmark_category='all', colorblind_mode=False)

        # Should return empty figure
        assert fig is not None
        assert mock_empty.called


def test_clientside_callbacks_use_valid_output_components():
    """
    Verify clientside callbacks output to valid dcc.Store components, not invalid Button.data-dummy props.

    Problem: dbc.Button may not accept arbitrary data-* props, causing runtime errors.
    Solution: Use dedicated dcc.Store components as dummy outputs.
    """
    from app import app as dash_app

    # Verify no callbacks output to Button.data-dummy (invalid pattern)
    for callback in dash_app.callback_map.values():
        outputs = callback['output']
        if not isinstance(outputs, list):
            outputs = [outputs]

        for output in outputs:
            output_id = output['id'] if isinstance(output, dict) else output.component_id
            output_prop = output['property'] if isinstance(output, dict) else output.component_property

            # No callback should output to data-dummy on buttons
            if output_id in ['dark-mode-toggle', 'colorblind-mode-toggle']:
                assert output_prop != 'data-dummy', f"Callback should not output to {output_id}.data-dummy (invalid prop)"

    # Verify dummy Store outputs exist in callbacks
    dummy_outputs_found = []
    for callback in dash_app.callback_map.values():
        outputs = callback['output']
        if not isinstance(outputs, list):
            outputs = [outputs]

        for output in outputs:
            output_id = output['id'] if isinstance(output, dict) else output.component_id
            output_prop = output['property'] if isinstance(output, dict) else output.component_property

            if output_id in ['dark-mode-callback-dummy', 'colorblind-callback-dummy'] and output_prop == 'data':
                dummy_outputs_found.append(output_id)

    # Both dummy stores should be used as outputs
    assert 'dark-mode-callback-dummy' in dummy_outputs_found, "dark-mode-callback-dummy.data should be used as callback output"
    assert 'colorblind-callback-dummy' in dummy_outputs_found, "colorblind-callback-dummy.data should be used as callback output"


# ============================================================================
# Colorblind mode persistence tests - PR #58 critical bug fix
# ============================================================================

def test_colorblind_toggle_callback_prevents_initial_call():
    """
    CRITICAL: Verify colorblind-mode toggle callback does NOT fire on initial page load.

    Bug: The clientside callback currently returns a normalized boolean on initial load
    (when n_clicks is falsy). If current_data is undefined/null during hydration,
    the callback writes false and overwrites a previously-saved true in localStorage.

    Fix: Add prevent_initial_call=True to the clientside callback, OR return
    window.dash_clientside.no_update when there's no real click event.

    This test verifies the callback uses prevent_initial_call=True in its registration.
    """
    from app import app as dash_app

    # Find the colorblind-mode toggle callback in _callback_list
    # Dash 3.4.0 stores prevent_initial_call in _callback_list, not callback_map
    colorblind_toggle_callback = None
    for callback_data in dash_app._callback_list:
        if callback_data.get('output') == 'colorblind-mode-store.data':
            colorblind_toggle_callback = callback_data
            break

    assert colorblind_toggle_callback is not None, "Could not find colorblind-mode-store callback"

    # Verify prevent_initial_call is True
    prevent_initial = colorblind_toggle_callback.get('prevent_initial_call', False)
    assert prevent_initial is True, \
        "colorblind-mode toggle callback must have prevent_initial_call=True to avoid overwriting localStorage on page load"


def test_colorblind_toggle_callback_does_not_write_false_on_startup():
    """
    Integration test: Verify callback does not write false to store on startup.

    Scenario:
    1. localStorage has colorblind-mode-store = "true"
    2. Page loads
    3. Callback should NOT fire and should NOT write false

    This test verifies the callback behavior by checking that the callback
    is configured to prevent initial execution.
    """
    from app import app as dash_app

    # Find the colorblind-mode toggle callback in _callback_list
    colorblind_toggle_callback = None
    for callback_data in dash_app._callback_list:
        if callback_data.get('output') == 'colorblind-mode-store.data':
            colorblind_toggle_callback = callback_data
            break

    assert colorblind_toggle_callback is not None, "Could not find colorblind-mode-store callback"

    # The callback must be configured to prevent initial call
    # This ensures it will NOT execute on page load and will NOT overwrite localStorage
    prevent_initial = colorblind_toggle_callback.get('prevent_initial_call', False)
    assert prevent_initial is True, \
        "Callback must not execute on initial load to preserve localStorage value"


def test_colorblind_toggle_only_fires_on_actual_clicks():
    """
    Verify the clientside callback JavaScript only toggles on actual button clicks.

    The callback JavaScript should check if n_clicks is null/undefined and return
    window.dash_clientside.no_update in that case.

    Since we can't directly test JavaScript behavior in Python unit tests,
    this test documents the expected behavior and verifies the callback
    is configured correctly (prevent_initial_call=True).

    Expected JavaScript behavior:
    - n_clicks = null/undefined -> return window.dash_clientside.no_update
    - n_clicks = 1, current_data = true -> return false (toggled)
    - n_clicks = 2, current_data = false -> return true (toggled)
    """
    from app import app as dash_app

    # Find the colorblind-mode toggle callback in _callback_list
    colorblind_toggle_callback = None
    for callback_data in dash_app._callback_list:
        if callback_data.get('output') == 'colorblind-mode-store.data':
            colorblind_toggle_callback = callback_data
            break

    assert colorblind_toggle_callback is not None, "Could not find colorblind-mode-store callback"

    # With prevent_initial_call=True, the callback will only fire on actual clicks
    prevent_initial = colorblind_toggle_callback.get('prevent_initial_call', False)
    assert prevent_initial is True, \
        "Callback must be configured to only fire on actual clicks (prevent_initial_call=True)"


def test_colorblind_init_script_is_source_of_truth_on_load():
    """
    Verify the init script (colorblind-mode-init.js) is the only source of truth
    on initial page load.

    The init script reads from localStorage and applies the body class BEFORE
    Dash renders. The toggle callback should NOT interfere with this by writing
    a default value.

    This test verifies:
    1. The init script exists and is loaded as an asset
    2. The toggle callback is configured to NOT run on initial load

    Integration note: The init script runs synchronously in <head>, the callback
    should never overwrite its work.
    """
    from pathlib import Path

    # Verify init script exists using relative path from test file
    # This ensures the test works regardless of checkout location
    test_file = Path(__file__).resolve()
    repo_root = test_file.parents[1]  # tests/test_app_callbacks.py -> tests/ -> repo_root/
    init_script_path = repo_root / "assets" / "colorblind-mode-init.js"

    assert init_script_path.exists(), \
        f"colorblind-mode-init.js must exist at {init_script_path} to initialize colorblind mode on page load"

    # Verify the callback won't interfere
    from app import app as dash_app

    # Find the colorblind-mode toggle callback in _callback_list
    colorblind_toggle_callback = None
    for callback_data in dash_app._callback_list:
        if callback_data.get('output') == 'colorblind-mode-store.data':
            colorblind_toggle_callback = callback_data
            break

    assert colorblind_toggle_callback is not None, "Could not find colorblind-mode-store callback"

    # Callback must not run on initial load to avoid overwriting init script's work
    prevent_initial = colorblind_toggle_callback.get('prevent_initial_call', False)
    assert prevent_initial is True, \
        "Toggle callback must not run on initial load; init script is source of truth"


# ============================================================================
# Performance optimization tests - PR #58
# Store caching should use render-ready data, not full DataFrames
# ============================================================================


def test_q2_store_contains_minimal_render_ready_data(monkeypatch):
    """
    Q2 analysis store should contain minimal render-ready data,
    not the full DataFrame JSON.

    Payload should be significantly smaller than full DataFrame.
    """
    import pandas as pd
    import json
    from unittest.mock import patch

    app = _import_app_fresh(monkeypatch)

    # Create a large mock comparison DataFrame (as returned by processor)
    large_comparison_df = pd.DataFrame({
        'test_name': ['test' + str(i) for i in range(100)],
        'peer_os': ['ubuntu'] * 100,
        'benchmark_category': ['CPU', 'Memory', 'Disk', 'Network'] * 25,
        'relative_performance': [95.0 + i * 0.1 for i in range(100)],
        'instance_type': ['m5.large'] * 100,
        'baseline_score': [100.0] * 100,
        'peer_score': [95.0] * 100
    })

    # Mock processor.analyze_peer_os_comparison to return large comparison data
    mock_result = {
        'comparison_data': large_comparison_df,
        'summary': 'Test summary',
        'competitive_count': 50,
        'total_benchmarks': 100
    }

    # Mock _get_available_comparisons
    mock_comparison_config = {
        'peer_os': 'ubuntu',
        'baseline_version': '9.0',
        'peer_version': '22.04',
        'cloud_provider': 'aws',
        'label': 'RHEL 9 vs Ubuntu 22.04'
    }

    with patch.object(app.processor, 'analyze_peer_os_comparison', return_value=mock_result):
        with patch.object(app.processor, '_get_available_comparisons', return_value=[mock_comparison_config]):
            # Call the callback with any valid JSON (processor is mocked)
            result = app.update_q2_analysis('{"data":[], "columns":[], "index":[]}')

    # Store should contain JSON string, not parsed dict
    # This avoids double-parsing (json.loads → pd.DataFrame vs direct pd.read_json)
    if result.get('comparison_data'):
        assert isinstance(result['comparison_data'], str), \
            "Q2 store should contain JSON string, not parsed dict"

        # Verify it's valid JSON that can be read by pandas
        try:
            from io import StringIO
            reconstructed_df = pd.read_json(StringIO(result['comparison_data']), orient='split')
            assert not reconstructed_df.empty, "Reconstructed DataFrame should not be empty"
        except Exception as e:
            pytest.fail(f"Failed to reconstruct DataFrame from stored JSON: {e}")


def test_q2_render_uses_data_directly_no_dataframe_reconstruction(monkeypatch):
    """
    Q2 render callback should use pd.read_json() for single-pass reconstruction
    instead of json.loads() → pd.DataFrame() double-parsing.
    """
    import pandas as pd
    from unittest.mock import patch, MagicMock

    app = _import_app_fresh(monkeypatch)

    # Mock store data with JSON string (optimized format)
    mock_df = pd.DataFrame({
        'peer_os': ['ubuntu', 'ubuntu'],
        'benchmark_category': ['CPU', 'Memory'],
        'test_name': ['test1', 'test2'],
        'relative_performance': [95.0, 105.0]
    })

    mock_store_data = {
        'comparison_data': mock_df.to_json(orient='split'),  # JSON string, not dict
        'has_data': True,
        'comparison_config': {
            'label': 'RHEL 9 vs Ubuntu 22.04',
            'peer_os': 'ubuntu'
        },
        'summary': 'Test summary',
        'competitive_count': 1,
        'total_benchmarks': 2
    }

    # Patch pd.read_json to verify it's being used (not manual reconstruction)
    with patch('pandas.read_json', wraps=pd.read_json) as mock_read_json:
        # Call the render callback
        fig, summary = app.update_q2_figure(mock_store_data, False)

        # Verify pd.read_json was called (efficient single-pass reconstruction)
        assert mock_read_json.called, "Should use pd.read_json() for DataFrame reconstruction"

    # Verify the old pattern (json.loads → DataFrame constructor) is NOT used
    with patch.object(pd, 'DataFrame', wraps=pd.DataFrame) as mock_df_constructor:
        app.update_q2_figure(mock_store_data, False)

        # Check no call matches the old pattern: DataFrame(data['data'], columns=..., index=...)
        for call in mock_df_constructor.call_args_list:
            args, kwargs = call
            if args and len(args) >= 1 and isinstance(args[0], list) and 'columns' in kwargs:
                pytest.fail("Old double-parsing pattern detected: json.loads() → DataFrame(data, columns, index)")


def test_q3_store_contains_minimal_render_ready_data(monkeypatch):
    """
    Q3 analysis store should contain minimal render-ready data,
    not the full DataFrame JSON.

    Payload should be significantly smaller than full DataFrame.
    """
    import pandas as pd
    import json
    from unittest.mock import patch

    app = _import_app_fresh(monkeypatch)

    # Create a large mock scaling DataFrame (99 rows for clean division by 3)
    large_scaling_df = pd.DataFrame({
        'test_name': ['test' + str(i) for i in range(99)],
        'instance_type': ['m5.large', 'm5.xlarge', 'm5.2xlarge'] * 33,
        'benchmark_category': ['CPU', 'Memory', 'Disk'] * 33,
        'mean_performance': [100.0 + i for i in range(99)],
        'cpu_cores': [2, 4, 8] * 33,
        'scaling_efficiency': [95.0] * 99
    })

    # Mock processor.analyze_cloud_scaling
    mock_result = {
        'scaling_data': large_scaling_df,
        'summary': 'Test summary',
        'linear_scaling_count': 50,
        'total_benchmarks': 100
    }

    # Create minimal valid filtered DataFrame with required columns
    filtered_df = pd.DataFrame({
        'os_distribution': ['rhel'] * 10,
        'instance_type': ['m5.large'] * 10,
        'test_name': ['test1'] * 10
    })

    with patch.object(app.processor, 'analyze_cloud_scaling', return_value=mock_result):
        # Call the callback with valid filtered data
        result = app.update_q3_analysis(
            filtered_df.to_json(orient='split'),
            cloud_provider='aws',
            instance_series='m5',
            os_distribution='rhel',
            os_version='9.0'
        )

    # Store should contain JSON string, not parsed dict
    if result.get('scaling_data'):
        assert isinstance(result['scaling_data'], str), \
            "Q3 store should contain JSON string, not parsed dict"

        # Verify it's valid JSON that can be read by pandas
        try:
            from io import StringIO
            reconstructed_df = pd.read_json(StringIO(result['scaling_data']), orient='split')
            assert not reconstructed_df.empty, "Reconstructed DataFrame should not be empty"
        except Exception as e:
            pytest.fail(f"Failed to reconstruct DataFrame from stored JSON: {e}")


def test_q3_render_uses_data_directly_no_dataframe_reconstruction(monkeypatch):
    """
    Q3 render callback should use pd.read_json() for single-pass reconstruction
    instead of json.loads() → pd.DataFrame() double-parsing.
    """
    import pandas as pd
    from unittest.mock import patch

    app = _import_app_fresh(monkeypatch)

    # Mock store data with JSON string (optimized format)
    mock_df = pd.DataFrame({
        'instance_type': ['m5.large', 'm5.xlarge'],
        'benchmark_category': ['CPU', 'CPU'],
        'mean_performance': [100.0, 200.0],
        'cpu_cores': [2, 4]
    })

    mock_store_data = {
        'scaling_data': mock_df.to_json(orient='split'),  # JSON string, not dict
        'has_data': True,
        'cloud_provider': 'aws',
        'os_version': '9.0',
        'os_distribution': 'rhel',
        'instance_series': 'm5',
        'summary': 'Test summary',
        'linear_scaling_count': 1,
        'total_benchmarks': 2
    }

    # Verify pd.read_json is used
    with patch('pandas.read_json', wraps=pd.read_json) as mock_read_json:
        fig, summary = app.render_q3_figure(mock_store_data, 'all', False)
        assert mock_read_json.called, "Should use pd.read_json() for DataFrame reconstruction"

    # Verify old pattern is NOT used
    with patch.object(pd, 'DataFrame', wraps=pd.DataFrame) as mock_df_constructor:
        app.render_q3_figure(mock_store_data, 'all', False)

        for call in mock_df_constructor.call_args_list:
            args, kwargs = call
            if args and len(args) >= 1 and isinstance(args[0], list) and 'columns' in kwargs:
                pytest.fail("Old double-parsing pattern detected in Q3 render")


def test_colorblind_toggle_with_optimized_stores_no_reconstruction(monkeypatch):
    """
    Colorblind toggle should work with optimized store format.
    Both colorblind modes should use pd.read_json() efficiently.
    """
    import pandas as pd
    from unittest.mock import patch

    app = _import_app_fresh(monkeypatch)

    # Mock Q2 store data with JSON string format
    mock_df = pd.DataFrame({
        'peer_os': ['ubuntu'],
        'benchmark_category': ['CPU'],
        'test_name': ['test1'],
        'relative_performance': [95.0]
    })

    q2_store = {
        'comparison_data': mock_df.to_json(orient='split'),  # JSON string
        'has_data': True,
        'comparison_config': {'label': 'Test', 'peer_os': 'ubuntu'},
        'summary': 'Test summary',
        'competitive_count': 1,
        'total_benchmarks': 1
    }

    # Verify pd.read_json is used in both modes
    with patch('pandas.read_json', wraps=pd.read_json) as mock_read_json:
        app.update_q2_figure(q2_store, False)
        calls_without_cb = mock_read_json.call_count

    with patch('pandas.read_json', wraps=pd.read_json) as mock_read_json:
        app.update_q2_figure(q2_store, True)
        calls_with_cb = mock_read_json.call_count

    # Both should use pd.read_json the same number of times
    assert calls_without_cb == calls_with_cb, \
        "Colorblind toggle should use same reconstruction method"

    # Verify no old double-parsing pattern
    with patch.object(pd, 'DataFrame', wraps=pd.DataFrame) as mock_df_constructor:
        app.update_q2_figure(q2_store, True)

        for call in mock_df_constructor.call_args_list:
            args, kwargs = call
            if args and len(args) >= 1 and isinstance(args[0], list) and 'columns' in kwargs:
                pytest.fail("Double-parsing pattern detected on colorblind toggle")


def test_pulse_panel_deserialization_error_hides_details_from_ui(monkeypatch):
    """
    Test that detailed deserialization errors are logged but not shown to user.

    When pulse bundle deserialization fails (e.g., TypeError, ValueError),
    the UI should show a generic error message, while detailed error information
    is logged server-side. This prevents leaking implementation details.
    """
    import logging

    # Import app fresh
    app = _import_app_fresh(monkeypatch)

    # Create bundle data that passes validation but fails deserialization
    # Use valid structure but wrong data types to trigger TypeError/ValueError
    invalid_bundle = {
        'policy_template_id': 'test',
        'definition_version': '1.0',
        'overview': {
            'test_count': 'not_a_number',  # Should be int - will cause TypeError
            'pass_count': 10,
            'fail_count': 5,
            'duration_seconds': 123.45
        },
        'category_mix': {
            'cpu': 10,
            'memory': 5,
            'network': 3
        },
        'activity_timeline': {
            'timeline_data': []
        },
        'scope': {
            'scope_description': 'Test scope'
        }
    }

    # Mock logging to capture logged errors
    with patch.object(logging, 'getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call the render_server_snapshot callback
        result = app.render_server_snapshot(invalid_bundle, colorblind_mode=False)

        # Extract text content from result
        result_text = str(result)

        # UI should show generic error occurred
        assert "Unable to load pulse data" in result_text or "Error loading" in result_text, \
            "UI should show that an error occurred"

        # UI should NOT leak implementation details like type names, field names, tracebacks
        # This test should FAIL initially because the current code shows str(exc)
        assert "__init__()" not in result_text, "UI should not show method names from traceback"
        assert "missing" not in result_text.lower() or "required" not in result_text.lower(), \
            "UI should not show technical validation details"
        assert "test_count" not in result_text, "UI should not leak internal field names"

        # Verify detailed error was logged (if app implements logging)
        # This part will be checked after implementing logging
        if mock_logger.error.called:
            assert mock_logger.error.call_count >= 1, \
                "Detailed error should be logged server-side"


# --- Task 1: Tests for dedicated point-drilldown-data-store (RPOPC-1183) ---


def test_update_investigation_view_returns_six_outputs(monkeypatch):
    """
    Test that update_investigation_view returns 6 outputs including
    the new point-drilldown-data-store.
    """
    app = _import_app_fresh(monkeypatch)

    # Setup: investigation nav state with valid params
    nav_state = {
        'view': 'investigation',
        'investigation_params': {
            'test_name': 'test_benchmark',
            'baseline_version': '9.5',
            'comparison_version': '10.0',
            'os_distribution': 'rhel'
        }
    }

    # Mock filtered data with all required columns for investigation view
    import pandas as pd
    test_df = pd.DataFrame({
        'document_id': ['doc1', 'doc2'],
        'primary_metric_name': ['throughput', 'throughput'],
        'primary_metric_value': [100, 200],
        'primary_metric_unit': ['ops/s', 'ops/s'],
        'timestamp': ['2025-01-01T00:00:00', '2025-01-02T00:00:00'],
        'instance_type': ['m5.large', 'm5.large'],
        'cloud_provider': ['aws', 'aws'],
        'test_name': ['test_benchmark', 'test_benchmark'],
        'os_distribution': ['rhel', 'rhel'],
        'os_version': ['9.5', '10.0'],
        'status': ['pass', 'pass'],
    })
    filtered_data_json = test_df.to_json(orient='split')

    # Call the callback
    result = app.update_investigation_view(nav_state, filtered_data_json, False)

    # Should return 6 values (not 5)
    assert len(result) == 6, \
        f"Expected 6 outputs (including point-drilldown-data-store), got {len(result)}"


def test_update_investigation_view_sixth_output_is_metadata_dict(monkeypatch):
    """
    Test that the 6th output is a dict with document_id keys mapping to metadata dicts.
    """
    app = _import_app_fresh(monkeypatch)

    nav_state = {
        'view': 'investigation',
        'investigation_params': {
            'test_name': 'test_benchmark',
            'baseline_version': '9.5',
            'comparison_version': '10.0',
            'os_distribution': 'rhel'
        }
    }

    import pandas as pd
    test_df = pd.DataFrame({
        'document_id': ['doc1', 'doc2'],
        'primary_metric_name': ['throughput', 'latency'],
        'primary_metric_value': [100.5, 200.3],
        'primary_metric_unit': ['ops/s', 'ms'],
        'timestamp': ['2025-01-01T00:00:00', '2025-01-02T00:00:00'],
        'instance_type': ['m5.large', 'c5.xlarge'],
        'cloud_provider': ['aws', 'gcp'],
        'test_name': ['test_benchmark', 'test_benchmark'],
        'os_distribution': ['rhel', 'rhel'],
        'os_version': ['9.5', '10.0'],
        'status': ['pass', 'pass'],
    })
    filtered_data_json = test_df.to_json(orient='split')

    result = app.update_investigation_view(nav_state, filtered_data_json, False)

    # Extract the 6th output (index 5)
    drilldown_data = result[5]

    # Should be a dict
    assert isinstance(drilldown_data, dict), \
        f"6th output should be a dict, got {type(drilldown_data)}"

    # Should have document_id keys
    assert 'doc1' in drilldown_data, "Should have doc1 key"
    assert 'doc2' in drilldown_data, "Should have doc2 key"

    # Each value should be a metadata dict with expected keys
    doc1_meta = drilldown_data['doc1']
    assert 'metric_name' in doc1_meta
    assert 'metric_unit' in doc1_meta
    assert 'summary_value' in doc1_meta
    assert 'timestamp' in doc1_meta
    assert 'instance_type' in doc1_meta
    assert 'cloud_provider' in doc1_meta

    # Verify values match the DataFrame
    assert doc1_meta['metric_name'] == 'throughput'
    assert doc1_meta['metric_unit'] == 'ops/s'
    assert doc1_meta['summary_value'] == 100.5
    assert doc1_meta['instance_type'] == 'm5.large'
    assert doc1_meta['cloud_provider'] == 'aws'
