"""Tests for server-side aggregation helpers (P0-C, P2-A Pulse KPIs, P2-C scope)."""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from src.benchmark_categories import category_for_test_name
from src.cache_service import get_cache_service
from src.comparison_policy import ValidationResult
from src.pulse_policy import validate_pulse_request
from src.query_service import (
    MAX_TEST_NAME_TERMS_FOR_CATEGORY_KPI,
    PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
    RESULTS_ACTIVITY_TIMESTAMP_FIELD,
    ActivityTimelineSnapshot,
    CategoryKpiSnapshot,
    PulseScopeFootnote,
    ResultsOverviewSnapshot,
    aggregate_activity_timeline_from_dataframe,
    aggregate_category_kpis_from_dataframe,
    aggregate_pulse_scope_footnote_from_dataframe,
    aggregate_results_overview_from_dataframe,
    build_results_monthly_activity_histogram_body,
    build_results_overview_aggregation_body,
    build_results_run_timestamp_stats_body,
    build_results_test_name_terms_aggregation_body,
    fetch_pulse_scope_footnote,
    format_pulse_scope_footnote,
    fetch_results_activity_timeline,
    fetch_results_category_kpis,
    fetch_results_overview_aggregates,
    parse_monthly_activity_histogram_response,
    parse_overview_aggregation_response,
    parse_run_timestamp_stats_response,
    parse_test_name_buckets_to_category_counts,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test to ensure isolation."""
    cache_service = get_cache_service()
    cache_service.clear()
    cache_service.reset_metrics()
    yield
    # Optionally clear after test as well
    cache_service.clear()
    cache_service.reset_metrics()


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


def test_aggregate_category_kpis_from_dataframe_ignores_missing_test_name():
    """NaN/None test_name must not break the rollup (category_for_test_name expects str-like)."""
    df = pd.DataFrame(
        {
            "test_name": ["streams", float("nan"), None, "streams"],
            "cloud_provider": ["aws", "aws", "gcp", "aws"],
        }
    )
    snap = aggregate_category_kpis_from_dataframe(df)
    assert snap.error is None
    assert snap.by_category == [(category_for_test_name("streams"), 2)]


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


def test_build_results_monthly_activity_histogram_body():
    body = build_results_monthly_activity_histogram_body()
    assert body["size"] == 0
    dh = body["aggs"]["runs_by_month"]["date_histogram"]
    assert dh["field"] == RESULTS_ACTIVITY_TIMESTAMP_FIELD
    assert dh["calendar_interval"] == "1M"
    assert dh["min_doc_count"] == 1


def test_parse_monthly_activity_histogram_response_yyyy_mm_keys():
    """Happy path: key_as_string matches format yyyy-MM from the aggregation request."""
    resp = {
        "aggregations": {
            "runs_by_month": {
                "buckets": [
                    {"key_as_string": "2025-01", "doc_count": 4},
                    {"key_as_string": "2025-02", "doc_count": 7},
                ]
            }
        }
    }
    pairs = parse_monthly_activity_histogram_response(resp)
    assert pairs == [("2025-01", 4), ("2025-02", 7)]


def test_parse_monthly_activity_histogram_response_truncates_long_key_as_string():
    """Defensive: older/alternate clients may return ISO timestamps in key_as_string."""
    resp = {
        "aggregations": {
            "runs_by_month": {
                "buckets": [
                    {"key_as_string": "2025-01-01T00:00:00.000Z", "doc_count": 4},
                    {"key_as_string": "2025-02-01T00:00:00.000Z", "doc_count": 7},
                ]
            }
        }
    }
    pairs = parse_monthly_activity_histogram_response(resp)
    assert pairs == [("2025-01", 4), ("2025-02", 7)]


def test_parse_monthly_activity_histogram_response_skips_zero_doc_count():
    resp = {
        "aggregations": {
            "runs_by_month": {
                "buckets": [
                    {"key_as_string": "2025-01", "doc_count": 0},
                    {"key_as_string": "2025-02", "doc_count": 3},
                ]
            }
        }
    }
    assert parse_monthly_activity_histogram_response(resp) == [("2025-02", 3)]


def test_aggregate_activity_timeline_from_dataframe():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2025-01-15", "2025-01-20", "2025-02-01", "2025-02-10"]
            ),
            "test_name": ["a", "b", "c", "d"],
        }
    )
    snap = aggregate_activity_timeline_from_dataframe(df)
    assert isinstance(snap, ActivityTimelineSnapshot)
    assert snap.error is None
    assert snap.by_month == [("2025-01", 2), ("2025-02", 2)]


def test_fetch_results_activity_timeline_success():
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "aggregations": {
            "runs_by_month": {
                "buckets": [
                    {"key_as_string": "2024-12", "doc_count": 1},
                ]
            }
        }
    }
    snap = fetch_results_activity_timeline(mock_client)
    assert snap.source == "opensearch"
    assert snap.error is None
    assert snap.by_month == [("2024-12", 1)]


def test_fetch_results_activity_timeline_skips_search_when_pulse_policy_fails():
    mock_client = MagicMock()
    with patch("src.query_service.validate_pulse_request") as vp:
        vp.return_value = ValidationResult(False, ("policy block",))
        snap = fetch_results_activity_timeline(mock_client)
    assert snap.source == "opensearch"
    assert "Pulse policy" in (snap.error or "")
    mock_client.search_results.assert_not_called()


def test_build_results_run_timestamp_stats_body():
    body = build_results_run_timestamp_stats_body()
    assert body["size"] == 0
    assert "track_total_hits" not in body
    assert body["aggs"]["run_time_stats"]["stats"]["field"] == RESULTS_ACTIVITY_TIMESTAMP_FIELD


def test_parse_run_timestamp_stats_response():
    resp = {
        "aggregations": {
            "run_time_stats": {
                "count": 100,
                "min": 1704067200000.0,
                "max": 1735689600000.0,
            }
        }
    }
    cnt, dmin, dmax = parse_run_timestamp_stats_response(resp)
    assert cnt == 100
    assert dmin == "2024-01-01"
    assert dmax == "2025-01-01"


def test_parse_run_timestamp_stats_response_nan_min_ignored():
    resp = {
        "aggregations": {
            "run_time_stats": {
                "count": 1,
                "min": float("nan"),
                "max": 1704067200000.0,
            }
        }
    }
    _, dmin, dmax = parse_run_timestamp_stats_response(resp)
    assert dmin is None
    assert dmax == "2024-01-01"


def test_aggregate_pulse_scope_footnote_from_dataframe():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2025-03-01", "2025-03-15"]),
            "test_name": ["a", "b"],
        }
    )
    foot = aggregate_pulse_scope_footnote_from_dataframe(df)
    assert isinstance(foot, PulseScopeFootnote)
    assert foot.document_count == 2
    assert foot.run_date_min_utc == "2025-03-01"
    assert foot.run_date_max_utc == "2025-03-15"
    assert foot.error is None


def test_aggregate_pulse_scope_footnote_excludes_rows_without_timestamp():
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2025-03-01", tz="UTC"), float("nan"), pd.Timestamp("2025-03-15", tz="UTC")],
            "test_name": ["a", "b", "c"],
        }
    )
    foot = aggregate_pulse_scope_footnote_from_dataframe(df)
    assert foot.document_count == 2
    assert foot.run_date_min_utc == "2025-03-01"
    assert foot.run_date_max_utc == "2025-03-15"


def test_aggregate_pulse_scope_footnote_no_timestamp_column():
    df = pd.DataFrame({"test_name": ["a", "b"]})
    foot = aggregate_pulse_scope_footnote_from_dataframe(df)
    assert foot.document_count == 0
    assert foot.run_date_min_utc is None


def test_aggregate_pulse_scope_footnote_all_timestamps_invalid():
    df = pd.DataFrame({"timestamp": [float("nan"), None], "test_name": ["a", "b"]})
    foot = aggregate_pulse_scope_footnote_from_dataframe(df)
    assert foot.document_count == 0


def test_fetch_pulse_scope_footnote_success():
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "aggregations": {
            "run_time_stats": {
                "count": 42,
                "min": 1704067200000.0,
                "max": 1704067200000.0,
            }
        }
    }
    foot = fetch_pulse_scope_footnote(mock_client)
    assert foot.source == "opensearch"
    assert foot.error is None
    assert foot.document_count == 42
    assert foot.run_date_min_utc == "2024-01-01"
    assert foot.run_date_max_utc == "2024-01-01"


def test_fetch_pulse_scope_footnote_skips_search_when_pulse_policy_fails():
    mock_client = MagicMock()
    with patch("src.query_service.validate_pulse_request") as vp:
        vp.return_value = ValidationResult(False, ("policy block",))
        foot = fetch_pulse_scope_footnote(mock_client)
    assert foot.source == "opensearch"
    assert "Pulse policy" in (foot.error or "")
    mock_client.search_results.assert_not_called()


def test_format_pulse_scope_footnote_returns_none_on_error():
    foot = PulseScopeFootnote(
        document_count=1,
        run_date_min_utc="2025-01-01",
        run_date_max_utc="2025-01-01",
        source="opensearch",
        error="failed",
    )
    assert format_pulse_scope_footnote(foot, data_mode="opensearch") is None


def test_format_pulse_scope_footnote_opensearch_range():
    foot = PulseScopeFootnote(
        document_count=100,
        run_date_min_utc="2024-06-01",
        run_date_max_utc="2025-01-01",
        source="opensearch",
        error=None,
    )
    s = format_pulse_scope_footnote(foot, data_mode="opensearch")
    assert s is not None
    assert "100" in s
    assert "OpenSearch stats" in s
    assert "2024-06-01" in s and "2025-01-01" in s


def test_format_pulse_scope_footnote_opensearch_single_day():
    foot = PulseScopeFootnote(
        document_count=3,
        run_date_min_utc="2025-03-01",
        run_date_max_utc="2025-03-01",
        source="opensearch",
        error=None,
    )
    s = format_pulse_scope_footnote(foot, data_mode="opensearch")
    assert s is not None
    assert "runs on 2025-03-01" in s


def test_format_pulse_scope_footnote_synthetic_copy():
    foot = PulseScopeFootnote(
        document_count=50,
        run_date_min_utc="2025-01-01",
        run_date_max_utc="2025-02-01",
        source="synthetic",
        error=None,
    )
    s = format_pulse_scope_footnote(foot, data_mode="synthetic")
    assert s is not None
    assert "loaded sample" in s
    assert "50" in s


def test_format_pulse_scope_footnote_earliest_only():
    foot = PulseScopeFootnote(
        document_count=None,
        run_date_min_utc="2024-01-01",
        run_date_max_utc=None,
        source="opensearch",
        error=None,
    )
    s = format_pulse_scope_footnote(foot, data_mode="opensearch")
    assert s is not None
    assert "earliest run" in s


def test_format_pulse_scope_footnote_empty_returns_none():
    foot = PulseScopeFootnote(
        document_count=None,
        run_date_min_utc=None,
        run_date_max_utc=None,
        source="synthetic",
        error=None,
    )
    assert format_pulse_scope_footnote(foot, data_mode="synthetic") is None


# --- Phase 3 P3-C: baseline comparison aggregates tests --------------------------


def test_baseline_comparison_snapshot_dataclass():
    """Verify BaselineComparisonSnapshot structure."""
    from src.query_service import BaselineComparisonSnapshot

    snap = BaselineComparisonSnapshot(
        baseline_id="test_baseline",
        nightly_date="2025-05-18",
        regressions=[("test1", -10.5), ("test2", -8.2)],
        improvements=[("test3", 15.0)],
        missing=["test4"],
        added=["test5"],
        delta_count=10,
        exception_count=4,
        source="synthetic",
        error=None,
    )
    assert snap.baseline_id == "test_baseline"
    assert snap.nightly_date == "2025-05-18"
    assert len(snap.regressions) == 2
    assert len(snap.improvements) == 1
    assert len(snap.missing) == 1
    assert len(snap.added) == 1
    assert snap.delta_count == 10
    assert snap.exception_count == 4


def test_build_baseline_query():
    """Test baseline query builder with various filters."""
    from src.query_service import _build_baseline_query, MAX_SEARCH_HITS

    # Single term filter
    query = _build_baseline_query({"metadata.baseline_tag.keyword": "v1.0"})
    assert query["size"] == MAX_SEARCH_HITS
    assert len(query["query"]["bool"]["must"]) == 1
    assert query["query"]["bool"]["must"][0] == {"term": {"metadata.baseline_tag.keyword": "v1.0"}}

    # Multiple filters
    query = _build_baseline_query({
        "metadata.baseline_tag.keyword": "v1.0",
        "metadata.cloud_provider.keyword": "aws",
    })
    assert len(query["query"]["bool"]["must"]) == 2

    # Terms filter (list value)
    query = _build_baseline_query({"test.name.keyword": ["coremark", "streams"]})
    assert query["query"]["bool"]["must"][0] == {"terms": {"test.name.keyword": ["coremark", "streams"]}}


def test_build_nightly_query():
    """Test nightly query builder with date range."""
    from src.query_service import _build_nightly_query, RESULTS_ACTIVITY_TIMESTAMP_FIELD, MAX_SEARCH_HITS

    query = _build_nightly_query(("2025-05-01T00:00:00Z", "2025-05-02T00:00:00Z"))
    assert query["size"] == MAX_SEARCH_HITS
    assert "range" in query["query"]
    assert RESULTS_ACTIVITY_TIMESTAMP_FIELD in query["query"]["range"]
    assert query["query"]["range"][RESULTS_ACTIVITY_TIMESTAMP_FIELD]["gte"] == "2025-05-01T00:00:00Z"
    assert query["query"]["range"][RESULTS_ACTIVITY_TIMESTAMP_FIELD]["lte"] == "2025-05-02T00:00:00Z"


def test_parse_comparison_documents_to_dataframe():
    """Test document parsing for baseline comparison."""
    from src.query_service import _parse_comparison_documents_to_dataframe

    documents = [
        {
            "metadata": {"test_timestamp": "2025-05-18T10:00:00Z"},
            "test": {"name": "coremark"},
            "results": {
                "status": "PASS",
                "primary_metric": {"value": 100.5},
            },
        },
        {
            "metadata": {"test_timestamp": "2025-05-18T11:00:00Z"},
            "test": {"name": "streams"},
            "results": {
                "status": "PASS",
                "value": 200.0,  # Fallback value location
            },
        },
        {
            "metadata": {"test_timestamp": "2025-05-18T12:00:00Z"},
            "test": {"name": "fail_test"},
            "results": {
                "status": "FAIL",
                "primary_metric": {"value": 50.0},
            },
        },
    ]

    df = _parse_comparison_documents_to_dataframe(documents)

    # Should filter out FAIL status
    assert len(df) == 2
    assert "test_name" in df.columns
    assert "test_timestamp" in df.columns
    assert "status" in df.columns
    assert "primary_metric_value" in df.columns

    # Check timestamp conversion
    assert pd.api.types.is_datetime64_any_dtype(df["test_timestamp"])

    # Check values
    assert set(df["test_name"]) == {"coremark", "streams"}


def test_parse_comparison_documents_empty():
    """Test document parsing with empty input."""
    from src.query_service import _parse_comparison_documents_to_dataframe

    df = _parse_comparison_documents_to_dataframe([])
    assert df.empty


def test_calculate_test_means():
    """Test mean calculation by test_name."""
    from src.query_service import _calculate_test_means

    df = pd.DataFrame({
        "test_name": ["coremark", "coremark", "streams", "streams", "streams"],
        "primary_metric_value": [100.0, 110.0, 200.0, 210.0, 190.0],
    })

    means = _calculate_test_means(df)

    assert len(means) == 2
    assert means["coremark"] == 105.0
    assert means["streams"] == 200.0


def test_calculate_test_means_with_non_numeric():
    """Test mean calculation handles non-numeric values."""
    from src.query_service import _calculate_test_means

    df = pd.DataFrame({
        "test_name": ["coremark", "coremark", "streams"],
        "primary_metric_value": [100.0, "invalid", 200.0],
    })

    means = _calculate_test_means(df)

    assert len(means) == 2
    assert means["coremark"] == 100.0  # Only valid value
    assert means["streams"] == 200.0


def test_calculate_test_means_empty():
    """Test mean calculation with empty DataFrame."""
    from src.query_service import _calculate_test_means

    assert _calculate_test_means(pd.DataFrame()) == {}


def test_calculate_exception_deltas_regressions():
    """Test exception delta calculation identifies regressions."""
    from src.query_service import _calculate_exception_deltas

    # Higher-is-better metric (throughput)
    baseline_df = pd.DataFrame({
        "test_name": ["coremark", "streams"],
        "test_timestamp": pd.to_datetime(["2025-05-01", "2025-05-01"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [100.0, 200.0],
    })

    nightly_df = pd.DataFrame({
        "test_name": ["coremark", "streams"],
        "test_timestamp": pd.to_datetime(["2025-05-18", "2025-05-18"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [90.0, 160.0],  # coremark: -10%, streams: -20%
    })

    result = _calculate_exception_deltas(
        baseline_df, nightly_df, "test", max_regressions=10, max_improvements=10, max_missing=10, max_added=10
    )

    assert result["nightly_date"] == "2025-05-18"
    assert len(result["regressions"]) == 2
    assert result["delta_count"] == 2
    assert len(result["improvements"]) == 0
    assert len(result["missing"]) == 0
    assert result["exception_count"] == 2

    # Check regressions are sorted worst-first (streams -20% should come before coremark -10%)
    assert result["regressions"][0][0] == "streams"  # streams: -20%
    assert result["regressions"][0][1] == -20.0
    assert result["regressions"][1][0] == "coremark"  # coremark: -10%
    assert result["regressions"][1][1] == -10.0


def test_calculate_exception_deltas_improvements():
    """Test exception delta calculation identifies improvements."""
    from src.query_service import _calculate_exception_deltas

    baseline_df = pd.DataFrame({
        "test_name": ["coremark"],
        "test_timestamp": pd.to_datetime(["2025-05-01"], utc=True),
        "status": ["PASS"],
        "primary_metric_value": [100.0],
    })

    nightly_df = pd.DataFrame({
        "test_name": ["coremark"],
        "test_timestamp": pd.to_datetime(["2025-05-18"], utc=True),
        "status": ["PASS"],
        "primary_metric_value": [120.0],  # +20% improvement
    })

    result = _calculate_exception_deltas(
        baseline_df, nightly_df, "test", max_regressions=10, max_improvements=10, max_missing=10, max_added=10
    )

    assert len(result["improvements"]) == 1
    assert result["improvements"][0] == ("coremark", 20.0)
    assert len(result["regressions"]) == 0


def test_calculate_exception_deltas_improvements_sorting():
    """Test exception delta calculation sorts improvements best-first."""
    from src.query_service import _calculate_exception_deltas

    # Higher-is-better metric (throughput): +50% is better than +10%
    baseline_df = pd.DataFrame({
        "test_name": ["coremark", "streams"],
        "test_timestamp": pd.to_datetime(["2025-05-01", "2025-05-01"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [100.0, 200.0],
    })

    nightly_df = pd.DataFrame({
        "test_name": ["coremark", "streams"],
        "test_timestamp": pd.to_datetime(["2025-05-18", "2025-05-18"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [110.0, 300.0],  # coremark: +10%, streams: +50%
    })

    result = _calculate_exception_deltas(
        baseline_df, nightly_df, "test", max_regressions=10, max_improvements=10, max_missing=10, max_added=10
    )

    assert len(result["improvements"]) == 2
    # Check improvements are sorted best-first (streams +50% should come before coremark +10%)
    assert result["improvements"][0][0] == "streams"
    assert result["improvements"][0][1] == 50.0
    assert result["improvements"][1][0] == "coremark"
    assert result["improvements"][1][1] == 10.0


def test_calculate_exception_deltas_missing_and_added():
    """Test exception delta calculation identifies missing and added benchmarks."""
    from src.query_service import _calculate_exception_deltas

    baseline_df = pd.DataFrame({
        "test_name": ["coremark", "streams"],
        "test_timestamp": pd.to_datetime(["2025-05-01", "2025-05-01"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [100.0, 200.0],
    })

    nightly_df = pd.DataFrame({
        "test_name": ["coremark", "pyperf"],  # streams missing, pyperf added
        "test_timestamp": pd.to_datetime(["2025-05-18", "2025-05-18"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [100.0, 300.0],
    })

    result = _calculate_exception_deltas(
        baseline_df, nightly_df, "test", max_regressions=10, max_improvements=10, max_missing=10, max_added=10
    )

    assert len(result["missing"]) == 1
    assert "streams" in result["missing"]
    assert len(result["added"]) == 1
    assert "pyperf" in result["added"]
    assert result["delta_count"] == 1  # Only coremark compared
    assert result["exception_count"] == 2  # missing + added (no regressions/improvements)


def test_calculate_exception_deltas_bounded_results():
    """Test exception delta calculation respects bounds."""
    from src.query_service import _calculate_exception_deltas

    # Create many regressions
    baseline_tests = [f"test{i}" for i in range(100)]
    baseline_df = pd.DataFrame({
        "test_name": baseline_tests,
        "test_timestamp": pd.to_datetime(["2025-05-01"] * 100, utc=True),
        "status": ["PASS"] * 100,
        "primary_metric_value": [100.0] * 100,
    })

    nightly_df = pd.DataFrame({
        "test_name": baseline_tests,
        "test_timestamp": pd.to_datetime(["2025-05-18"] * 100, utc=True),
        "status": ["PASS"] * 100,
        "primary_metric_value": [90.0] * 100,  # All regressed
    })

    result = _calculate_exception_deltas(
        baseline_df, nightly_df, "test",
        max_regressions=5,  # Limit to 5
        max_improvements=3,
        max_missing=2,
        max_added=2,
    )

    assert len(result["regressions"]) == 5  # Bounded


def test_calculate_exception_deltas_stable_changes_excluded():
    """Test that stable changes (within stability band) are not reported."""
    from src.query_service import _calculate_exception_deltas

    baseline_df = pd.DataFrame({
        "test_name": ["coremark"],
        "test_timestamp": pd.to_datetime(["2025-05-01"], utc=True),
        "status": ["PASS"],
        "primary_metric_value": [100.0],
    })

    nightly_df = pd.DataFrame({
        "test_name": ["coremark"],
        "test_timestamp": pd.to_datetime(["2025-05-18"], utc=True),
        "status": ["PASS"],
        "primary_metric_value": [102.0],  # Only +2%, within stability band
    })

    result = _calculate_exception_deltas(
        baseline_df, nightly_df, "test", max_regressions=10, max_improvements=10, max_missing=10, max_added=10
    )

    # Should not be in regressions or improvements
    assert len(result["regressions"]) == 0
    assert len(result["improvements"]) == 0
    assert result["delta_count"] == 1


def test_aggregate_baseline_comparison_from_dataframe():
    """Test synthetic data mode for baseline comparison."""
    from src.query_service import aggregate_baseline_comparison_from_dataframe

    baseline_df = pd.DataFrame({
        "test_name": ["coremark", "streams"],
        "test_timestamp": pd.to_datetime(["2025-05-01", "2025-05-01"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [100.0, 200.0],
    })

    nightly_df = pd.DataFrame({
        "test_name": ["coremark", "streams"],
        "test_timestamp": pd.to_datetime(["2025-05-18", "2025-05-18"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [90.0, 180.0],
    })

    snap = aggregate_baseline_comparison_from_dataframe(
        baseline_df, nightly_df, baseline_id="test_baseline"
    )

    assert snap.source == "synthetic"
    assert snap.baseline_id == "test_baseline"
    assert snap.error is None
    assert len(snap.regressions) == 2
    assert snap.delta_count == 2


def test_aggregate_baseline_comparison_from_dataframe_empty():
    """Test synthetic data mode with empty DataFrames."""
    from src.query_service import aggregate_baseline_comparison_from_dataframe

    snap = aggregate_baseline_comparison_from_dataframe(
        pd.DataFrame(), pd.DataFrame(), baseline_id="empty"
    )

    assert snap.source == "synthetic"
    assert snap.error is None
    assert len(snap.regressions) == 0
    assert len(snap.improvements) == 0
    assert snap.delta_count == 0


def test_fetch_baseline_comparison_aggregates_success():
    """Test OpenSearch fetch for baseline comparison."""
    from src.query_service import fetch_baseline_comparison_aggregates

    mock_client = MagicMock()

    # Mock baseline response
    baseline_resp = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "metadata": {"test_timestamp": "2025-05-01T10:00:00Z"},
                        "test": {"name": "coremark"},
                        "results": {
                            "status": "PASS",
                            "primary_metric": {"value": 100.0},
                        },
                    }
                },
            ]
        }
    }

    # Mock nightly response
    nightly_resp = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "metadata": {"test_timestamp": "2025-05-18T10:00:00Z"},
                        "test": {"name": "coremark"},
                        "results": {
                            "status": "PASS",
                            "primary_metric": {"value": 90.0},
                        },
                    }
                },
            ]
        }
    }

    # Configure mock to return different responses
    mock_client.search_results.side_effect = [baseline_resp, nightly_resp]

    snap = fetch_baseline_comparison_aggregates(
        mock_client,
        baseline_filter={"metadata.baseline_tag.keyword": "v1.0"},
        nightly_date_range=("2025-05-18T00:00:00Z", "2025-05-18T23:59:59Z"),
        baseline_id="test_baseline",
    )

    assert snap.source == "opensearch"
    assert snap.baseline_id == "test_baseline"
    assert snap.error is None
    assert len(snap.regressions) == 1
    assert snap.regressions[0] == ("coremark", -10.0)
    assert mock_client.search_results.call_count == 2


def test_fetch_baseline_comparison_aggregates_error_handling():
    """Test error handling in OpenSearch fetch."""
    from src.query_service import fetch_baseline_comparison_aggregates

    mock_client = MagicMock()
    mock_client.search_results.side_effect = RuntimeError("Connection failed")

    snap = fetch_baseline_comparison_aggregates(
        mock_client,
        baseline_filter={},
        nightly_date_range=("2025-05-18T00:00:00Z", "2025-05-18T23:59:59Z"),
    )

    assert snap.source == "opensearch"
    assert snap.error is not None
    assert "Connection failed" in snap.error
    assert len(snap.regressions) == 0
