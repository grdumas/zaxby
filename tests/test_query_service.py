"""Tests for server-side aggregation helpers (P0-C, P2-A Pulse KPIs, P2-C scope)."""

import pandas as pd
from unittest.mock import MagicMock, patch

from src.benchmark_categories import category_for_test_name
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


# --- Nightly Runs Tests (Recent Runs Dashboard) ---


from datetime import datetime, timezone
from src.query_service import (
    NightlyRunSnapshot,
    aggregate_recent_nightly_runs_from_dataframe,
    build_nightly_runs_aggregation_body,
    fetch_recent_nightly_runs,
    parse_nightly_runs_aggregation_response,
)


def test_nightly_run_snapshot_dataclass():
    """Test NightlyRunSnapshot dataclass creation."""
    timestamp = datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc)
    snapshot = NightlyRunSnapshot(
        timestamp=timestamp,
        test_count=147,
        pass_count=141,
        fail_count=6,
        category_breakdown=[("Storage/IO", 45), ("Networking", 30)],
        source="opensearch",
        error=None,
    )
    assert snapshot.timestamp == timestamp
    assert snapshot.test_count == 147
    assert snapshot.pass_count == 141
    assert snapshot.fail_count == 6
    assert len(snapshot.category_breakdown) == 2
    assert snapshot.source == "opensearch"
    assert snapshot.error is None


def test_build_nightly_runs_aggregation_body_no_date_range():
    """Test building OpenSearch query body without date range."""
    body = build_nightly_runs_aggregation_body()
    assert body["size"] == 0
    assert body["track_total_hits"] is True
    assert body["query"] == {"match_all": {}}
    assert "runs_by_date" in body["aggs"]
    assert body["aggs"]["runs_by_date"]["date_histogram"]["calendar_interval"] == "1d"


def test_build_nightly_runs_aggregation_body_with_date_range():
    """Test building OpenSearch query body with date range filter."""
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    end = datetime(2026, 5, 31, tzinfo=timezone.utc)
    body = build_nightly_runs_aggregation_body(date_range=(start, end))
    assert "range" in body["query"]
    assert RESULTS_ACTIVITY_TIMESTAMP_FIELD in body["query"]["range"]
    assert "gte" in body["query"]["range"][RESULTS_ACTIVITY_TIMESTAMP_FIELD]
    assert "lte" in body["query"]["range"][RESULTS_ACTIVITY_TIMESTAMP_FIELD]


def test_parse_nightly_runs_aggregation_response_empty():
    """Test parsing empty aggregation response."""
    resp = {"aggregations": {"runs_by_date": {"buckets": []}}}
    snapshots = parse_nightly_runs_aggregation_response(resp)
    assert snapshots == []


def test_parse_nightly_runs_aggregation_response_filters_small_buckets():
    """Test that buckets with too few tests are filtered out."""
    resp = {
        "aggregations": {
            "runs_by_date": {
                "buckets": [
                    {
                        "key": 1715995200000,  # 2026-05-18
                        "doc_count": 5,  # Below threshold
                        "pass_count": {"doc_count": 5},
                        "fail_count": {"doc_count": 0},
                        "by_test_name": {"buckets": []},
                    }
                ]
            }
        }
    }
    snapshots = parse_nightly_runs_aggregation_response(resp, min_tests_threshold=10)
    assert snapshots == []


def test_parse_nightly_runs_aggregation_response_valid():
    """Test parsing valid aggregation response."""
    resp = {
        "aggregations": {
            "runs_by_date": {
                "buckets": [
                    {
                        "key": 1715995200000,  # 2026-05-18 00:00:00 UTC (milliseconds)
                        "doc_count": 147,
                        "pass_count": {"doc_count": 141},
                        "fail_count": {"doc_count": 6},
                        "by_test_name": {
                            "buckets": [
                                {"key": "fio", "doc_count": 45},
                                {"key": "uperf", "doc_count": 30},
                            ]
                        },
                    }
                ]
            }
        }
    }
    snapshots = parse_nightly_runs_aggregation_response(resp, n=10)
    assert len(snapshots) == 1
    assert snapshots[0].test_count == 147
    assert snapshots[0].pass_count == 141
    assert snapshots[0].fail_count == 6
    assert snapshots[0].source == "opensearch"
    assert len(snapshots[0].category_breakdown) == 2


def test_parse_nightly_runs_aggregation_response_respects_n_limit():
    """Test that parser respects n limit."""
    # Create 5 buckets but request only 3
    buckets = []
    for i in range(5):
        buckets.append({
            "key": 1715995200000 + (i * 86400000),  # Each day
            "doc_count": 100,
            "pass_count": {"doc_count": 95},
            "fail_count": {"doc_count": 5},
            "by_test_name": {"buckets": []},
        })

    resp = {"aggregations": {"runs_by_date": {"buckets": buckets}}}
    snapshots = parse_nightly_runs_aggregation_response(resp, n=3)
    assert len(snapshots) == 3


def test_fetch_recent_nightly_runs_opensearch_error():
    """Test fetch_recent_nightly_runs handles OpenSearch errors gracefully."""
    mock_client = MagicMock()
    mock_client.search_results.side_effect = Exception("Connection error")

    runs = fetch_recent_nightly_runs(mock_client)

    assert len(runs) == 1
    assert runs[0].test_count == 0
    assert runs[0].error is not None
    assert "Connection error" in runs[0].error


def test_aggregate_recent_nightly_runs_from_dataframe_empty():
    """Test DataFrame aggregation with empty DataFrame."""
    df = pd.DataFrame()
    runs = aggregate_recent_nightly_runs_from_dataframe(df)
    assert runs == []


def test_aggregate_recent_nightly_runs_from_dataframe_no_timestamp():
    """Test DataFrame aggregation without timestamp column."""
    df = pd.DataFrame({"test_name": ["fio", "uperf"]})
    runs = aggregate_recent_nightly_runs_from_dataframe(df)
    assert runs == []


def test_aggregate_recent_nightly_runs_from_dataframe_filters_small_days():
    """Test DataFrame aggregation filters days with too few tests."""
    df = pd.DataFrame({
        "timestamp": [datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc)] * 5,
        "test_name": ["fio"] * 5,
        "status": ["PASS"] * 5,
    })
    runs = aggregate_recent_nightly_runs_from_dataframe(df)
    # Should be filtered out (< 10 tests threshold)
    assert runs == []


def test_aggregate_recent_nightly_runs_from_dataframe_valid():
    """Test DataFrame aggregation with valid data."""
    timestamps = [datetime(2026, 5, 18, 3, i, tzinfo=timezone.utc) for i in range(15)]
    df = pd.DataFrame({
        "timestamp": timestamps,
        "test_name": ["fio"] * 10 + ["uperf"] * 5,
        "status": ["PASS"] * 12 + ["FAIL"] * 3,
    })
    runs = aggregate_recent_nightly_runs_from_dataframe(df)

    assert len(runs) == 1  # One day
    assert runs[0].test_count == 15
    assert runs[0].pass_count == 12
    assert runs[0].fail_count == 3
    assert runs[0].source == "synthetic"
    assert len(runs[0].category_breakdown) == 2  # fio and uperf map to different categories


def test_aggregate_recent_nightly_runs_from_dataframe_with_date_range():
    """Test DataFrame aggregation with date range filter."""
    df = pd.DataFrame({
        "timestamp": [
            datetime(2026, 5, 1, 3, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 15, 3, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 31, 3, 0, tzinfo=timezone.utc),
        ] * 10,  # Repeat to get > 10 per day
        "test_name": ["fio"] * 30,
        "status": ["PASS"] * 30,
    })

    start = datetime(2026, 5, 10, tzinfo=timezone.utc)
    end = datetime(2026, 5, 20, tzinfo=timezone.utc)
    runs = aggregate_recent_nightly_runs_from_dataframe(df, date_range=(start, end))

    # Should only include May 15
    assert len(runs) == 1
    assert runs[0].timestamp.day == 15


def test_aggregate_recent_nightly_runs_from_dataframe_respects_n():
    """Test DataFrame aggregation respects n parameter."""
    # Create data for 5 different days
    timestamps = []
    for day in range(1, 6):
        timestamps.extend([datetime(2026, 5, day, 3, i, tzinfo=timezone.utc) for i in range(15)])

    df = pd.DataFrame({
        "timestamp": timestamps,
        "test_name": ["fio"] * len(timestamps),
        "status": ["PASS"] * len(timestamps),
    })

    runs = aggregate_recent_nightly_runs_from_dataframe(df, n=3)
    # Should return only 3 most recent days (days 5, 4, 3 in desc order)
    assert len(runs) == 3
