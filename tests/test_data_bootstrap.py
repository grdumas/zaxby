"""Tests for startup benchmark document loading (P1-F OpenSearch failure behavior)."""

from unittest.mock import MagicMock, patch

from src.data_bootstrap import load_initial_benchmark_documents


def test_synthetic_mode_loads_synthetic_no_error():
    fake = [{"metadata": {"document_id": "x"}}]
    with patch("src.data_processing.load_synthetic_data", return_value=fake):
        docs, err, syn_after = load_initial_benchmark_documents("synthetic")
    assert docs is fake
    assert err is None
    assert syn_after is False


def test_opensearch_success_returns_documents():
    fake_docs = [{"metadata": {"document_id": "a"}}]
    mock_client = MagicMock()
    mock_client.scroll_results = MagicMock(return_value=fake_docs)
    with patch("src.opensearch_client.BenchmarkDataSource", return_value=mock_client):
        docs, err, syn_after = load_initial_benchmark_documents("opensearch")
    assert docs == fake_docs
    assert err is None
    assert syn_after is False
    mock_client.scroll_results.assert_called_once_with(max_docs=5000)


def test_opensearch_failure_returns_empty_without_opt_in():
    with patch("src.opensearch_client.BenchmarkDataSource", side_effect=ConnectionError("refused")):
        docs, err, syn_after = load_initial_benchmark_documents(
            "opensearch",
            use_synthetic_after_opensearch_failure=False,
        )
    assert docs == []
    assert "refused" in (err or "")
    assert syn_after is False


def test_opensearch_failure_empty_exception_message_still_returns_error_sentinel():
    """str(exc) can be '' — callers must use `err is not None`, not truthiness."""
    with patch("src.opensearch_client.BenchmarkDataSource", side_effect=ConnectionError()):
        docs, err, syn_after = load_initial_benchmark_documents(
            "opensearch",
            use_synthetic_after_opensearch_failure=False,
        )
    assert docs == []
    assert err == ""
    assert err is not None
    assert syn_after is False


def test_opensearch_failure_loads_synthetic_when_opt_in():
    synthetic = [{"metadata": {"document_id": "s1"}}]
    with patch("src.opensearch_client.BenchmarkDataSource", side_effect=RuntimeError("boom")):
        with patch("src.data_processing.load_synthetic_data", return_value=synthetic):
            docs, err, syn_after = load_initial_benchmark_documents(
                "opensearch",
                use_synthetic_after_opensearch_failure=True,
            )
    assert docs == synthetic
    assert err == "boom"
    assert syn_after is True


def test_synthetic_mode_does_not_load_timeseries():
    """Verify that bootstrap only loads result documents, not timeseries.

    Timeseries are loaded lazily on-demand via get_synthetic_timeseries_index(),
    not eagerly at startup. This test confirms the separation.
    """
    fake_results = [
        {"metadata": {"document_id": "result_001", "test_timestamp": "2026-01-25T10:00:00Z"}},
        {"metadata": {"document_id": "result_002", "test_timestamp": "2026-01-25T11:00:00Z"}}
    ]

    with patch("src.data_processing.load_synthetic_data", return_value=fake_results) as mock_load_results:
        with patch("src.data_processing.load_synthetic_timeseries") as mock_load_timeseries:
            docs, err, syn_after = load_initial_benchmark_documents("synthetic")

    # Should load results
    mock_load_results.assert_called_once()
    assert docs == fake_results

    # Should NOT load timeseries (that's lazy-loaded later)
    mock_load_timeseries.assert_not_called()

    assert err is None
    assert syn_after is False
