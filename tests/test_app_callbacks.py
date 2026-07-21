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
