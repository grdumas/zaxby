"""Tests for Pulse KPI bundle (P2-A)."""

import pandas as pd
from unittest.mock import MagicMock

from src.pulse_kpis import (
    PULSE_KPI_DEFINITION_VERSION,
    aggregate_pulse_kpi_bundle_from_dataframe,
    fetch_pulse_kpi_bundle,
    pulse_kpi_bundle_from_connection_error,
)
from src.query_service import PULSE_RESULTS_OVERVIEW_TEMPLATE_ID


def test_pulse_kpi_bundle_from_connection_error_sets_all_slots():
    b = pulse_kpi_bundle_from_connection_error("connection refused", source="opensearch")
    assert b.definition_version == PULSE_KPI_DEFINITION_VERSION
    assert b.policy_template_id == PULSE_RESULTS_OVERVIEW_TEMPLATE_ID
    assert b.overview.error == "connection refused"
    assert b.category_mix.error == "connection refused"
    assert b.activity_timeline.error == "connection refused"
    assert b.scope.error == "connection refused"


def test_aggregate_pulse_kpi_bundle_from_dataframe_matches_components():
    df = pd.DataFrame(
        {
            "cloud_provider": ["aws", "aws"],
            "test_name": ["coremark", "streams"],
            "timestamp": pd.to_datetime(["2025-03-15", "2025-04-10"], utc=True),
        }
    )
    b = aggregate_pulse_kpi_bundle_from_dataframe(df)
    assert b.overview.total == 2
    assert b.overview.source == "synthetic"
    assert b.category_mix.by_category
    assert b.activity_timeline.by_month
    assert b.scope.document_count == 2
    assert b.definition_version == PULSE_KPI_DEFINITION_VERSION


def test_fetch_pulse_kpi_bundle_calls_search_four_times():
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "hits": {"total": {"value": 1}},
        "aggregations": {
            "by_cloud": {"buckets": []},
            "by_test_name": {"buckets": []},
            "runs_by_month": {"buckets": []},
            "run_time_stats": {"count": 0, "min": None, "max": None},
        },
    }
    b = fetch_pulse_kpi_bundle(mock_client)
    assert mock_client.search_results.call_count == 4
    assert b.policy_template_id == PULSE_RESULTS_OVERVIEW_TEMPLATE_ID
    assert b.overview.source == "opensearch"
