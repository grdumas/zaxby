"""
Tests for point drill-down validation logic (RPOPC-1183).

Tests document_id comparison and dtype handling to ensure
the validation works correctly when pandas infers numeric dtypes.
"""

import pandas as pd
import pytest


def test_document_id_comparison_bug_without_normalization():
    """Demonstrate the bug: numeric dtype causes comparison to fail."""
    test_df = pd.DataFrame({
        'document_id': [123, 456, 789],  # numeric
    })

    document_id = "456"

    # Without dtype normalization, this returns empty
    matching_rows_buggy = test_df[test_df['document_id'] == document_id]
    assert len(matching_rows_buggy) == 0  # BUG: no match found

    # With dtype normalization, it works
    matching_rows_fixed = test_df[test_df['document_id'].astype(str) == document_id]
    assert len(matching_rows_fixed) == 1  # Fixed: match found


def test_document_id_comparison_handles_numeric_dtype():
    """Ensure document_id comparison works when DataFrame column is numeric."""
    # Simulate DataFrame with numeric document_id column
    test_df = pd.DataFrame({
        'document_id': [123, 456, 789],  # numeric
        'timestamp': pd.date_range('2025-01-01', periods=3),
        'primary_metric_value': [100.0, 200.0, 300.0],
    })

    # String document_id from dropdown
    document_id = "456"

    # This should find the match after dtype normalization
    matching_rows = test_df[test_df['document_id'].astype(str) == document_id]

    assert len(matching_rows) == 1
    assert matching_rows.iloc[0]['primary_metric_value'] == 200.0


def test_document_id_comparison_handles_string_dtype():
    """Ensure document_id comparison works when DataFrame column is already string."""
    # Simulate DataFrame with string document_id column
    test_df = pd.DataFrame({
        'document_id': ['123', '456', '789'],  # already string
        'timestamp': pd.date_range('2025-01-01', periods=3),
        'primary_metric_value': [100.0, 200.0, 300.0],
    })

    # String document_id from dropdown
    document_id = "456"

    # This should find the match (astype(str) on string is idempotent)
    matching_rows = test_df[test_df['document_id'].astype(str) == document_id]

    assert len(matching_rows) == 1
    assert matching_rows.iloc[0]['primary_metric_value'] == 200.0


def test_document_id_comparison_handles_mixed_dtype():
    """Ensure document_id comparison works when DataFrame has mixed types."""
    # Simulate DataFrame with object dtype (mixed numeric/string)
    test_df = pd.DataFrame({
        'document_id': [123, '456', 789],  # mixed
        'timestamp': pd.date_range('2025-01-01', periods=3),
        'primary_metric_value': [100.0, 200.0, 300.0],
    })

    # String document_id from dropdown
    document_id = "456"

    # This should find the match after dtype normalization
    matching_rows = test_df[test_df['document_id'].astype(str) == document_id]

    assert len(matching_rows) == 1
    assert matching_rows.iloc[0]['primary_metric_value'] == 200.0


def test_document_id_not_found_returns_empty():
    """Ensure comparison returns empty DataFrame when document_id not found."""
    test_df = pd.DataFrame({
        'document_id': [123, 456, 789],
        'timestamp': pd.date_range('2025-01-01', periods=3),
        'primary_metric_value': [100.0, 200.0, 300.0],
    })

    # Non-existent document_id
    document_id = "999"

    matching_rows = test_df[test_df['document_id'].astype(str) == document_id]

    assert len(matching_rows) == 0


# --- Tests for pure validation function (Task 3, RPOPC-1183 refactor) ---


def test_validate_point_drilldown_request_success(monkeypatch):
    """Validation should succeed when document_id is in drilldown_data."""
    import sys
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app  # noqa: E402

    drilldown_data = {
        'doc123': {
            'metric_name': 'latency',
            'metric_unit': 'ms',
            'summary_value': 100.5,
            'timestamp': '2025-01-01T00:00:00',
            'instance_type': 'm5.large',
            'cloud_provider': 'aws'
        }
    }

    metadata, error = app.validate_point_drilldown_request('doc123', drilldown_data)

    assert error is None
    assert metadata is not None
    assert metadata['metric_name'] == 'latency'
    assert metadata['metric_unit'] == 'ms'
    assert metadata['summary_value'] == 100.5


def test_validate_point_drilldown_request_none_data(monkeypatch):
    """Validation should fail with appropriate error when drilldown_data is None."""
    import sys
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app  # noqa: E402

    metadata, error = app.validate_point_drilldown_request('doc123', None)

    assert metadata is None
    assert error is not None
    assert 'drill-down data' in error.lower()
    assert 'refresh' in error.lower()


def test_validate_point_drilldown_request_empty_data(monkeypatch):
    """Validation should fail when drilldown_data is empty dict."""
    import sys
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app  # noqa: E402

    metadata, error = app.validate_point_drilldown_request('doc123', {})

    assert metadata is None
    assert error is not None
    assert 'drill-down data' in error.lower()


def test_validate_point_drilldown_request_document_not_found(monkeypatch):
    """Validation should fail when document_id is not in drilldown_data."""
    import sys
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app  # noqa: E402

    drilldown_data = {
        'doc123': {
            'metric_name': 'latency',
            'metric_unit': 'ms',
            'summary_value': 100.5,
            'timestamp': '2025-01-01T00:00:00',
            'instance_type': 'm5.large',
            'cloud_provider': 'aws'
        }
    }

    metadata, error = app.validate_point_drilldown_request('doc999', drilldown_data)

    assert metadata is None
    assert error is not None
    assert 'not found' in error.lower()
    assert 'current view' in error.lower()


def test_validate_point_drilldown_request_none_document_id(monkeypatch):
    """Validation should fail gracefully when document_id is None."""
    import sys
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app  # noqa: E402

    drilldown_data = {'doc123': {}}

    metadata, error = app.validate_point_drilldown_request(None, drilldown_data)

    assert metadata is None
    assert error is not None
    assert 'no test run selected' in error.lower()


def test_validate_point_drilldown_request_empty_document_id(monkeypatch):
    """Validation should fail when document_id is empty string."""
    import sys
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app  # noqa: E402

    drilldown_data = {'doc123': {}}

    metadata, error = app.validate_point_drilldown_request('', drilldown_data)

    assert metadata is None
    assert error is not None
    assert 'no test run selected' in error.lower()
