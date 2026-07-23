"""
Tests for point drill-down callback in Investigate mode (RPOPC-1184).

Tests the handle_point_drilldown callback end-to-end with proper dash.ctx mocking.
"""

import sys
from unittest.mock import MagicMock, patch
import pytest


def _import_app_fresh(monkeypatch):
    """Import app after clearing module cache."""
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app as app_module  # noqa: E402
    return app_module


def test_handle_point_drilldown_open_modal_synthetic_mode(monkeypatch):
    """Happy path: modal opens with chart in synthetic mode."""
    app = _import_app_fresh(monkeypatch)

    # Mock dash.ctx to simulate button click
    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-view-points.n_clicks', 'value': 1}]

        # Mock synthetic fetch
        mock_points = [
            {
                "metadata": {
                    "timeseries_id": "uperf_abc123_timeseries",
                    "document_id": "doc001",
                    "sequence": 0,
                    "test_timestamp": "2026-01-25T10:00:00Z"
                },
                "results": {
                    "point_metrics": {"throughput": 1000.0}
                }
            }
        ]

        drilldown_data = {
            "doc001": {
                "metric_name": "throughput",
                "metric_unit": "Gb/s",
                "summary_value": 950.0,
                "timestamp": "2026-01-25T10:00:00Z",
                "instance_type": "m5.large",
                "cloud_provider": "aws"
            }
        }

        with patch('src.data_processing.fetch_synthetic_timeseries_for_document',
                   return_value=mock_points):
            is_open, title, body, discover_link = app.handle_point_drilldown(
                view_clicks=1,
                close_clicks=0,
                is_open=False,
                selected_value="doc001",
                colorblind_mode=False,
                drilldown_data=drilldown_data,
                nav_state={'view': 'investigation'}
            )

    assert is_open is True, "Modal should open"
    assert "2026-01-25" in title, "Title should include timestamp"
    assert "m5.large" in title, "Title should include instance type"
    assert "aws" in title, "Title should include cloud provider"
    assert body is not None, "Body should contain chart"


def test_handle_point_drilldown_close_modal(monkeypatch):
    """Clicking close button should close modal."""
    app = _import_app_fresh(monkeypatch)

    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-point-drilldown-close.n_clicks', 'value': 1}]

        is_open, title, body, discover_link = app.handle_point_drilldown(
            view_clicks=0,
            close_clicks=1,
            is_open=False,
            selected_value=None,
            colorblind_mode=False,
            drilldown_data={},
            nav_state={'view': 'investigation'}
        )

    assert is_open is False, "Modal should close"
    assert title == "", "Title should be empty"
    assert body == "", "Body should be empty"
    assert discover_link == "", "Discover link should be empty"


def test_handle_point_drilldown_no_points_returns_warning(monkeypatch):
    """When fetch returns no points, modal shows warning."""
    app = _import_app_fresh(monkeypatch)

    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-view-points.n_clicks', 'value': 1}]

        drilldown_data = {
            "doc001": {
                "metric_name": "throughput",
                "metric_unit": "Gb/s",
                "summary_value": 950.0,
                "timestamp": "2026-01-25T10:00:00Z",
                "instance_type": "m5.large",
                "cloud_provider": "aws"
            }
        }

        # Mock fetch to return empty list
        with patch('src.data_processing.fetch_synthetic_timeseries_for_document',
                   return_value=[]):
            is_open, title, body, discover_link = app.handle_point_drilldown(
                view_clicks=1,
                close_clicks=0,
                is_open=False,
                selected_value="doc001",
                colorblind_mode=False,
                drilldown_data=drilldown_data,
                nav_state={'view': 'investigation'}
            )

    assert is_open is True, "Modal should open"
    body_str = str(body)
    assert "No Data" in body_str or "No point-level data" in body_str, \
        "Body should contain no-data warning"


def test_handle_point_drilldown_validates_document_id_against_drilldown_data(monkeypatch):
    """Attempting to view a document_id not in drilldown_data should show error."""
    app = _import_app_fresh(monkeypatch)

    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-view-points.n_clicks', 'value': 1}]

        drilldown_data = {
            "doc001": {
                "metric_name": "throughput",
                "metric_unit": "Gb/s",
                "summary_value": 950.0,
                "timestamp": "2026-01-25T10:00:00Z",
                "instance_type": "m5.large",
                "cloud_provider": "aws"
            }
        }

        # Try to view a different document_id (not in drilldown_data)
        is_open, title, body, discover_link = app.handle_point_drilldown(
            view_clicks=1,
            close_clicks=0,
            is_open=False,
            selected_value="tampered_doc_999",
            colorblind_mode=False,
            drilldown_data=drilldown_data,
            nav_state={'view': 'investigation'}
        )

    # Validation should reject tampered document_id and open modal with error
    assert is_open is True, "Modal should open with error"
    assert title == "Error", "Title should be Error"
    body_str = str(body).lower()
    assert "error" in body_str or "invalid" in body_str or "not found" in body_str, \
        "Body should contain error message"


def test_handle_point_drilldown_sanitizes_exceptions(monkeypatch):
    """Exceptions from fetch should not leak internal details."""
    app = _import_app_fresh(monkeypatch)

    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-view-points.n_clicks', 'value': 1}]

        drilldown_data = {
            "doc001": {
                "metric_name": "throughput",
                "metric_unit": "Gb/s",
                "summary_value": 950.0,
                "timestamp": "2026-01-25T10:00:00Z",
                "instance_type": "m5.large",
                "cloud_provider": "aws"
            }
        }

        # Mock fetch to raise exception with sensitive details
        with patch('src.data_processing.fetch_synthetic_timeseries_for_document',
                   side_effect=RuntimeError("INTERNAL_DATABASE_PASSWORD=secret123")):
            is_open, title, body, discover_link = app.handle_point_drilldown(
                view_clicks=1,
                close_clicks=0,
                is_open=False,
                selected_value="doc001",
                colorblind_mode=False,
                drilldown_data=drilldown_data,
                nav_state={'view': 'investigation'}
            )

    assert is_open is True, "Modal should open with error"
    assert title == "Error", "Title should be Error"
    body_str = str(body)
    assert "INTERNAL_DATABASE_PASSWORD" not in body_str, \
        "Sensitive details should not leak to UI"
    assert "secret123" not in body_str, \
        "Sensitive details should not leak to UI"
    assert ("error" in body_str.lower() or "failed" in body_str.lower()), \
        "Body should contain generic error/failed message"


def test_handle_point_drilldown_handles_null_metadata_safely(monkeypatch):
    """Points with None or missing metadata should not crash the chart."""
    app = _import_app_fresh(monkeypatch)

    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-view-points.n_clicks', 'value': 1}]

        # Mock points with None metadata
        mock_points = [
            {
                "metadata": None,  # Null metadata
                "results": {
                    "point_metrics": {"throughput": 1000.0}
                }
            },
            {
                "metadata": {
                    "timeseries_id": "uperf_abc123_timeseries",
                    "document_id": "doc001",
                    "sequence": 1,
                    "test_timestamp": "2026-01-25T10:00:30Z"
                },
                "results": {
                    "point_metrics": {"throughput": 1050.0}
                }
            }
        ]

        drilldown_data = {
            "doc001": {
                "metric_name": "throughput",
                "metric_unit": "Gb/s",
                "summary_value": 1000.0,
                "timestamp": "2026-01-25T10:00:00Z",
                "instance_type": "m5.large",
                "cloud_provider": "aws"
            }
        }

        with patch('src.data_processing.fetch_synthetic_timeseries_for_document',
                   return_value=mock_points):
            is_open, title, body, discover_link = app.handle_point_drilldown(
                view_clicks=1,
                close_clicks=0,
                is_open=False,
                selected_value="doc001",
                colorblind_mode=False,
                drilldown_data=drilldown_data,
                nav_state={'view': 'investigation'}
            )

    # Should not crash, should open modal
    assert is_open is True, "Modal should open despite null metadata"
    assert body is not None, "Chart should be created"


def test_handle_point_drilldown_opensearch_mode_error_sanitized(monkeypatch):
    """OpenSearch mode exceptions should be sanitized."""
    # Set DATA_MODE to opensearch (simulates opensearch mode)
    monkeypatch.setenv("DATA_MODE", "opensearch")

    sys.modules.pop("app", None)
    import app as app_module  # noqa: E402

    # Force OpenSearch mode by resetting error flags
    # (Import may have set OPENSEARCH_LOAD_ERROR if connection failed at startup)
    app_module.OPENSEARCH_LOAD_ERROR = None
    app_module.SYNTHETIC_AFTER_OPENSEARCH_FAILURE = False

    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-view-points.n_clicks', 'value': 1}]

        drilldown_data = {
            "doc001": {
                "metric_name": "throughput",
                "metric_unit": "Gb/s",
                "summary_value": 950.0,
                "timestamp": "2026-01-25T10:00:00Z",
                "instance_type": "m5.large",
                "cloud_provider": "aws"
            }
        }

        # Patch BenchmarkDataSource where it's used (in app_module namespace)
        with patch.object(app_module, 'BenchmarkDataSource') as mock_client_class:
            mock_client = MagicMock()
            mock_client.fetch_timeseries_for_document.side_effect = \
                ConnectionError("Connection to 192.168.1.1:9200 failed")
            mock_client_class.return_value = mock_client

            is_open, title, body, discover_link = app_module.handle_point_drilldown(
                view_clicks=1,
                close_clicks=0,
                is_open=False,
                selected_value="doc001",
                colorblind_mode=False,
                drilldown_data=drilldown_data,
                nav_state={'view': 'investigation'}
            )

    # Verify modal opens with error
    assert is_open is True, "Modal should open with error message"
    assert title == "Error", f"Title should be 'Error', got '{title}'"

    # Verify error message is sanitized (no sensitive details leaked)
    body_str = str(body)
    assert "192.168.1.1" not in body_str, \
        "Internal IP should not leak to UI"
    assert "9200" not in body_str, \
        "Internal port should not leak to UI"

    # Verify generic error message is present
    body_lower = body_str.lower()
    assert any(phrase in body_lower for phrase in ["error", "failed", "could not"]), \
        f"Body should contain generic error message, got: {body_str}"


def test_handle_point_drilldown_no_selection_returns_no_op(monkeypatch):
    """No selection (None) means no action - modal stays closed."""
    app = _import_app_fresh(monkeypatch)

    with patch('dash.ctx') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'btn-view-points.n_clicks', 'value': 1}]

        drilldown_data = {
            "doc001": {
                "metric_name": "throughput",
                "metric_unit": "Gb/s",
                "summary_value": 950.0,
                "timestamp": "2026-01-25T10:00:00Z",
                "instance_type": "m5.large",
                "cloud_provider": "aws"
            }
        }

        # Test None selection - the callback condition requires selected_value to be truthy
        is_open, title, body, discover_link = app.handle_point_drilldown(
            view_clicks=1,
            close_clicks=0,
            is_open=False,
            selected_value=None,
            colorblind_mode=False,
            drilldown_data=drilldown_data,
            nav_state={'view': 'investigation'}
        )

    # None selection means the condition fails, returns is_open unchanged (False)
    assert is_open is False, "Modal should stay closed when no selection"
    assert title == "", "Title should be empty"
    assert body == "", "Body should be empty"
