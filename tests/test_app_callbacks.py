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
    import json
    analysis_data = {
        'scaling_data': json.loads(mock_scaling_data.to_json(orient='split')),
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

        # Simulate cached analysis data
        import json
        analysis_data = {
            'comparison_data': json.loads('{"columns":["category","rhel_wins"],"index":[0],"data":[["compute",8]]}'),
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

        # Simulate cached analysis data
        import json
        analysis_data = {
            'scaling_data': json.loads('{"columns":["instance_size","score","benchmark_category"],"index":[0],"data":[["small",100,"System"]]}'),
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
        'scaling_data': json.loads(scaling_data.to_json(orient='split')),
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
        'scaling_data': json.loads(scaling_data.to_json(orient='split')),
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
        'scaling_data': json.loads(scaling_data.to_json(orient='split')),
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
    Verify Q2 analysis store contains a dict (split-orient), not a JSON string.

    Performance optimization: storing as dict avoids redundant JSON parsing
    on every colorblind mode toggle. The store should contain:
    {'comparison_data': {'columns': [...], 'data': [...], 'index': [...]}, ...}
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

        # CRITICAL: comparison_data should be a dict, not a JSON string
        comparison_data = result['comparison_data']
        assert isinstance(comparison_data, dict), \
            f"Expected dict but got {type(comparison_data).__name__}"

        # Verify it has split-orient structure
        assert 'columns' in comparison_data
        assert 'data' in comparison_data
        assert 'index' in comparison_data

        # Verify it's NOT a string
        assert not isinstance(comparison_data, str), \
            "comparison_data should be dict, not JSON string"


def test_q2_render_callback_accepts_dict_from_store(monkeypatch):
    """
    Verify Q2 render callback accepts dict from store and reconstructs DataFrame
    without pd.read_json() call.

    Performance optimization: no JSON parsing on every colorblind toggle.
    """
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Mock the visualization function
    mock_viz = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_peer_os_comparison_chart', mock_viz):
        # Simulate cached analysis data with dict (NOT string)
        analysis_data = {
            'comparison_data': {
                'columns': ['category', 'rhel_wins'],
                'index': [0, 1],
                'data': [['compute', 8], ['storage', 6]]
            },
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
    Verify Q3 analysis store contains a dict (split-orient), not a JSON string.

    Performance optimization: storing as dict avoids redundant JSON parsing
    on every colorblind mode toggle or benchmark category filter.
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

        # CRITICAL: scaling_data should be a dict, not a JSON string
        scaling_data = result['scaling_data']
        assert isinstance(scaling_data, dict), \
            f"Expected dict but got {type(scaling_data).__name__}"

        # Verify it has split-orient structure
        assert 'columns' in scaling_data
        assert 'data' in scaling_data
        assert 'index' in scaling_data

        # Verify it's NOT a string
        assert not isinstance(scaling_data, str), \
            "scaling_data should be dict, not JSON string"


def test_q3_render_callback_accepts_dict_from_store(monkeypatch):
    """
    Verify Q3 render callback accepts dict from store and reconstructs DataFrame
    without pd.read_json() call.

    Performance optimization: no JSON parsing on every colorblind toggle
    or benchmark category filter.
    """
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Mock the visualization function
    mock_viz = MagicMock(return_value=MagicMock())

    with patch('src.components.visualizations.create_cloud_scaling_chart', mock_viz):
        # Simulate cached analysis data with dict (NOT string)
        analysis_data = {
            'scaling_data': {
                'columns': ['instance_type', 'vcpu_count', 'performance', 'benchmark_category'],
                'index': [0, 1],
                'data': [['m5.large', 2, 100, 'compute'], ['m5.xlarge', 4, 200, 'compute']]
            },
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
