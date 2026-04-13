"""Tests for OpenSearch retry UI wiring (dashboard PR #21)."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from dash import no_update
from dash.exceptions import PreventUpdate

# One document sufficient for BenchmarkDataProcessor.documents_to_dataframe (valid timestamp, etc.)
_MIN_VALID_BENCHMARK_DOC = {
    "metadata": {
        "document_id": "test_retry_1",
        "test_timestamp": "2025-11-01T10:00:00Z",
        "os_vendor": "rhel",
        "cloud_provider": "aws",
        "instance_type": "m5.large",
        "scenario_name": "scn",
    },
    "test": {"name": "coremark", "version": "v1.0"},
    "system_under_test": {
        "hardware": {"cpu": {"model": "x", "cores": 4, "architecture": "x86_64"}, "memory": {"total_gb": 8}},
        "operating_system": {"distribution": "rhel", "version": "9.5", "kernel_version": "5.14.0"},
    },
    "results": {
        "status": "PASS",
        "primary_metric": {"name": "score", "value": 1.0, "unit": "x"},
        "runs": {"run_0": {"metrics": {"multicore_score": 1.0}}},
    },
}


def _import_app_fresh(monkeypatch, *, data_mode: str, bootstrap_mock: MagicMock):
    """Import ``app`` after applying ``bootstrap_mock`` to startup loading."""
    monkeypatch.setenv("DATA_MODE", data_mode)
    sys.modules.pop("app", None)
    with patch("src.data_bootstrap.load_initial_benchmark_documents", bootstrap_mock):
        import app as app_module  # noqa: E402 — import after env and cache clear

    return app_module


def test_refresh_bootstrap_opensearch_success_updates_globals(monkeypatch):
    mock_load = MagicMock(return_value=([_MIN_VALID_BENCHMARK_DOC], None, False))
    app = _import_app_fresh(monkeypatch, data_mode="opensearch", bootstrap_mock=mock_load)

    assert app.OPENSEARCH_LOAD_ERROR is None
    assert len(app.raw_documents) == 1
    assert app.MODE_BADGE_LABEL == "OPENSEARCH"
    assert app.df is not None
    assert len(app.df) == 1


def test_refresh_bootstrap_opensearch_failure_sets_error(monkeypatch):
    mock_load = MagicMock(return_value=([], "refused", False))
    app = _import_app_fresh(monkeypatch, data_mode="opensearch", bootstrap_mock=mock_load)

    assert app.OPENSEARCH_LOAD_ERROR is not None
    assert "refused" in (app.OPENSEARCH_LOAD_ERROR or "")
    assert app.MODE_BADGE_LABEL == "OPENSEARCH (load failed — no data)"


def test_retry_callback_success_returns_empty_and_reload_href(monkeypatch):
    mock_load = MagicMock(return_value=([_MIN_VALID_BENCHMARK_DOC], None, False))
    app = _import_app_fresh(monkeypatch, data_mode="opensearch", bootstrap_mock=mock_load)

    status, href = app.retry_opensearch_connection(1)
    assert status == ""
    assert href == "/"


def test_retry_callback_failure_returns_alert_and_no_update(monkeypatch):
    mock_load = MagicMock(
        side_effect=[
            ([_MIN_VALID_BENCHMARK_DOC], None, False),
            ([], "still down", False),
        ]
    )
    app = _import_app_fresh(monkeypatch, data_mode="opensearch", bootstrap_mock=mock_load)

    status, href = app.retry_opensearch_connection(1)
    assert href is no_update
    assert "still down" in str(status)


def test_retry_callback_non_opensearch_raises_prevent_update(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "synthetic")
    sys.modules.pop("app", None)
    import app as app_module  # noqa: E402

    with pytest.raises(PreventUpdate):
        app_module.retry_opensearch_connection(1)
