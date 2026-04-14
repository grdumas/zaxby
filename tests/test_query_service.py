"""Tests for server-side aggregation helpers (P0-C)."""

import pandas as pd
from unittest.mock import MagicMock, patch

from src.comparison_policy import ValidationResult
from src.pulse_policy import validate_pulse_request
from src.query_service import (
    PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
    ResultsOverviewSnapshot,
    aggregate_results_overview_from_dataframe,
    build_results_overview_aggregation_body,
    fetch_results_overview_aggregates,
    parse_overview_aggregation_response,
)


def test_build_results_overview_aggregation_body_is_size_zero_with_aggs():
    body = build_results_overview_aggregation_body()
    assert body["size"] == 0
    assert body["track_total_hits"] is True
    assert "by_cloud" in body["aggs"]
    assert body["aggs"]["by_cloud"]["terms"]["field"] == "metadata.cloud_provider.keyword"


def test_parse_overview_aggregation_response_integer_total():
    resp = {
        "hits": {"total": 42},
        "aggregations": {"by_cloud": {"buckets": [{"key": "aws", "doc_count": 40}, {"key": "gcp", "doc_count": 2}]}},
    }
    total, pairs = parse_overview_aggregation_response(resp)
    assert total == 42
    assert pairs == [("aws", 40), ("gcp", 2)]


def test_parse_overview_aggregation_response_object_total():
    resp = {
        "hits": {"total": {"value": 100, "relation": "eq"}},
        "aggregations": {"by_cloud": {"buckets": []}},
    }
    total, pairs = parse_overview_aggregation_response(resp)
    assert total == 100
    assert pairs == []


def test_aggregate_results_overview_from_dataframe_groups():
    df = pd.DataFrame(
        {
            "cloud_provider": ["aws", "aws", "gcp", None],
            "x": [1, 2, 3, 4],
        }
    )
    snap = aggregate_results_overview_from_dataframe(df)
    assert isinstance(snap, ResultsOverviewSnapshot)
    assert snap.source == "synthetic"
    assert snap.total == 4
    assert snap.by_cloud == [("aws", 2), ("gcp", 1)]


def test_aggregate_results_overview_from_dataframe_missing_column():
    df = pd.DataFrame({"x": [1, 2]})
    snap = aggregate_results_overview_from_dataframe(df)
    assert snap.total == 2
    assert snap.by_cloud == []


def test_fetch_results_overview_aggregates_success():
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "hits": {"total": {"value": 5}},
        "aggregations": {"by_cloud": {"buckets": [{"key": "aws", "doc_count": 5}]}},
    }
    snap = fetch_results_overview_aggregates(mock_client)
    assert snap.source == "opensearch"
    assert snap.total == 5
    assert snap.by_cloud == [("aws", 5)]
    assert snap.error is None
    mock_client.search_results.assert_called_once()


def test_pulse_results_overview_template_passes_pulse_policy():
    """Behavioral check: overview constant must remain Pulse-allowed in comparison_policy."""
    vr = validate_pulse_request(PULSE_RESULTS_OVERVIEW_TEMPLATE_ID, {})
    assert vr.ok, vr.errors


def test_fetch_results_overview_aggregates_skips_search_when_pulse_policy_fails():
    mock_client = MagicMock()
    with patch("src.query_service.validate_pulse_request") as vp:
        vp.return_value = ValidationResult(False, ("rejected for unit test",))
        snap = fetch_results_overview_aggregates(mock_client)
    assert snap.source == "opensearch"
    assert snap.total is None
    assert snap.by_cloud == []
    assert snap.error is not None
    assert snap.error.startswith("Pulse policy:")
    assert "rejected for unit test" in snap.error
    mock_client.search_results.assert_not_called()


def test_fetch_results_overview_aggregates_search_error():
    mock_client = MagicMock()
    mock_client.search_results.side_effect = RuntimeError("boom")
    snap = fetch_results_overview_aggregates(mock_client)
    assert snap.source == "opensearch"
    assert snap.error == "boom"
    assert snap.by_cloud == []
