"""Tests for server-side aggregation helpers (P0-C, P2-A category KPIs)."""

import pandas as pd
from unittest.mock import MagicMock, patch

from src.benchmark_categories import category_for_test_name
from src.comparison_policy import ValidationResult
from src.pulse_policy import validate_pulse_request
from src.query_service import (
    MAX_TEST_NAME_TERMS_FOR_CATEGORY_KPI,
    PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
    CategoryKpiSnapshot,
    ResultsOverviewSnapshot,
    aggregate_category_kpis_from_dataframe,
    aggregate_results_overview_from_dataframe,
    build_results_overview_aggregation_body,
    build_results_test_name_terms_aggregation_body,
    fetch_results_category_kpis,
    fetch_results_overview_aggregates,
    parse_overview_aggregation_response,
    parse_test_name_buckets_to_category_counts,
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


def test_build_results_test_name_terms_aggregation_body():
    body = build_results_test_name_terms_aggregation_body()
    assert body["size"] == 0
    assert body["aggs"]["by_test_name"]["terms"]["field"] == "test.name.keyword"
    assert body["aggs"]["by_test_name"]["terms"]["size"] == MAX_TEST_NAME_TERMS_FOR_CATEGORY_KPI


def test_parse_test_name_buckets_to_category_counts_merges_same_category():
    resp = {
        "aggregations": {
            "by_test_name": {
                "buckets": [
                    {"key": "pyperf", "doc_count": 3},
                    {"key": "pyperf_scenario_a", "doc_count": 2},
                ]
            }
        }
    }
    pairs = parse_test_name_buckets_to_category_counts(resp)
    assert pairs == [("Other", 5)]


def test_aggregate_category_kpis_from_dataframe():
    df = pd.DataFrame(
        {
            "test_name": ["streams", "streams", "coremark"],
            "cloud_provider": ["aws", "aws", "aws"],
        }
    )
    snap = aggregate_category_kpis_from_dataframe(df)
    assert isinstance(snap, CategoryKpiSnapshot)
    assert snap.source == "synthetic"
    assert snap.error is None
    assert snap.by_category[0] == (
        category_for_test_name("streams"),
        2,
    )
    assert snap.by_category[1][0] == category_for_test_name("coremark")
    assert snap.by_category[1][1] == 1


def test_fetch_results_category_kpis_success():
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "aggregations": {
            "by_test_name": {
                "buckets": [
                    {"key": "streams", "doc_count": 10},
                    {"key": "coremark", "doc_count": 5},
                ]
            }
        }
    }
    snap = fetch_results_category_kpis(mock_client)
    assert snap.source == "opensearch"
    assert snap.error is None
    assert snap.by_category == [
        (category_for_test_name("streams"), 10),
        (category_for_test_name("coremark"), 5),
    ]
    mock_client.search_results.assert_called_once()


def test_fetch_results_category_kpis_malformed_buckets_surfaces_error():
    """Parsing failures must return CategoryKpiSnapshot.error, not raise."""
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "aggregations": {
            "by_test_name": {
                "buckets": [
                    {"key": "streams", "doc_count": "not_a_number"},
                ]
            }
        }
    }
    snap = fetch_results_category_kpis(mock_client)
    assert snap.source == "opensearch"
    assert snap.error is not None
    assert snap.by_category == []


def test_fetch_results_category_kpis_skips_search_when_pulse_policy_fails():
    mock_client = MagicMock()
    with patch("src.query_service.validate_pulse_request") as vp:
        vp.return_value = ValidationResult(False, ("policy block",))
        snap = fetch_results_category_kpis(mock_client)
    assert snap.source == "opensearch"
    assert snap.error is not None
    assert "Pulse policy" in snap.error
    mock_client.search_results.assert_not_called()


def test_pulse_category_kpi_uses_same_template_as_overview():
    """Category KPI and overview snapshot share the Pulse policy anchor."""
    vr_o = validate_pulse_request(PULSE_RESULTS_OVERVIEW_TEMPLATE_ID, {})
    assert vr_o.ok
