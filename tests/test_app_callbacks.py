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
