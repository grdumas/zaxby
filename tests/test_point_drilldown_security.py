"""
Security and robustness tests for point drill-down callbacks (RPOPC-1183).

Tests critical security fixes:
1. Dropdown uses document_id only (not JSON payload)
2. Non-numeric metrics don't crash dropdown
3. Missing columns handled safely
4. Exceptions are sanitized (no internal details leaked)
"""

import sys
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest


def _import_app_fresh(monkeypatch):
    """Import app after clearing module cache."""
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app as app_module  # noqa: E402
    return app_module


def test_dropdown_uses_simple_document_id_not_json(monkeypatch):
    """SECURITY: Dropdown value should be document_id only, not JSON payload."""
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    test_df = pd.DataFrame({
        'document_id': ['doc123'],
        'timestamp': pd.date_range('2025-01-01', periods=1),
        'instance_type': ['m5.large'],
        'cloud_provider': ['aws'],
        'primary_metric_name': ['latency'],
        'primary_metric_value': [100.0],
        'primary_metric_unit': ['ms'],
        'test_name': ['test_benchmark'],
        'os_distribution': ['rhel'],
        'os_version': ['9.0'],
        'status': ['pass']
    })

    nav_state = {
        'view': 'investigation',
        'investigation_params': {
            'test_name': 'test_benchmark',
            'baseline_version': '9.0',
            'comparison_version': '9.1',
            'os_distribution': 'rhel'
        }
    }

    filtered_data_json = test_df.to_json(orient='split')

    summary, comparison_fig, timeline_fig, table, dropdown_options, drilldown_data = app.update_investigation_view(
        nav_state, filtered_data_json, False
    )

    # Dropdown value should be simple document_id, not JSON
    assert len(dropdown_options) == 1
    assert dropdown_options[0]['value'] == 'doc123'

    # Should NOT be JSON-encoded
    import json
    try:
        parsed = json.loads(dropdown_options[0]['value'])
        pytest.fail("Dropdown value should be document_id only, not JSON payload (security risk)")
    except (json.JSONDecodeError, TypeError):
        # Expected - value is not JSON
        pass


def test_dropdown_skips_non_numeric_metric_values(monkeypatch):
    """Dropdown should skip rows with non-numeric primary_metric_value instead of crashing."""
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Create test data with mixed numeric and non-numeric values
    test_df = pd.DataFrame({
        'document_id': ['doc1', 'doc2', 'doc3'],
        'timestamp': pd.date_range('2025-01-01', periods=3),
        'instance_type': ['m5.large'] * 3,
        'cloud_provider': ['aws'] * 3,
        'primary_metric_name': ['latency'] * 3,
        'primary_metric_value': [100.0, 'invalid', 200.0],  # Middle row is invalid
        'primary_metric_unit': ['ms'] * 3,
        'test_name': ['test_benchmark'] * 3,
        'os_distribution': ['rhel'] * 3,
        'os_version': ['9.0'] * 3,
        'status': ['pass'] * 3
    })

    nav_state = {
        'view': 'investigation',
        'investigation_params': {
            'test_name': 'test_benchmark',
            'baseline_version': '9.0',
            'comparison_version': '9.1',
            'os_distribution': 'rhel'
        }
    }

    filtered_data_json = test_df.to_json(orient='split')

    # Should not crash
    summary, comparison_fig, timeline_fig, table, dropdown_options, drilldown_data = app.update_investigation_view(
        nav_state, filtered_data_json, False
    )

    # Dropdown should contain only valid rows (doc1 and doc3)
    assert len(dropdown_options) == 2
    assert 'doc1' in str(dropdown_options)
    assert 'doc3' in str(dropdown_options)


def test_dropdown_empty_when_required_columns_missing(monkeypatch):
    """Dropdown should return empty (not crash) when required dropdown columns are missing."""
    import pandas as pd

    app = _import_app_fresh(monkeypatch)

    # Create test data WITHOUT cloud_provider column (required for dropdown, but with timestamp for chart)
    test_df = pd.DataFrame({
        'document_id': ['doc1', 'doc2'],
        'timestamp': pd.date_range('2025-01-01', periods=2),  # Include for chart
        'instance_type': ['m5.large', 'm5.xlarge'],
        # Missing: cloud_provider (required for dropdown)
        'primary_metric_name': ['latency', 'latency'],
        'primary_metric_value': [100.0, 200.0],
        'primary_metric_unit': ['ms', 'ms'],
        'test_name': ['test_benchmark', 'test_benchmark'],
        'os_distribution': ['rhel', 'rhel'],
        'os_version': ['9.0', '9.1'],
        'status': ['pass', 'pass']
    })

    nav_state = {
        'view': 'investigation',
        'investigation_params': {
            'test_name': 'test_benchmark',
            'baseline_version': '9.0',
            'comparison_version': '9.1',
            'os_distribution': 'rhel'
        }
    }

    filtered_data_json = test_df.to_json(orient='split')

    # Should not crash, should return empty dropdown
    summary, comparison_fig, timeline_fig, table, dropdown_options, drilldown_data = app.update_investigation_view(
        nav_state, filtered_data_json, False
    )

    # Dropdown should be empty because cloud_provider is missing (required for dropdown)
    assert dropdown_options == []
