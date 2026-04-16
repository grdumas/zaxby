"""
Pulse KPI bundle (Phase 2, P2-A).

Single contract for executive-style **descriptive** metrics loaded via bounded
OpenSearch aggregations (``size: 0``) or mirrored from the in-memory sample in
synthetic mode. These are **not** baseline-vs-candidate performance comparisons;
see :mod:`src.comparison_policy` and ``docs/guides/COMPARISON_POLICY.md``.

Human-facing definitions and review status: ``docs/guides/PULSE_KPIS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.query_service import (
    PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
    ActivityTimelineSnapshot,
    CategoryKpiSnapshot,
    PulseScopeFootnote,
    ResultsOverviewSnapshot,
    aggregate_activity_timeline_from_dataframe,
    aggregate_category_kpis_from_dataframe,
    aggregate_pulse_scope_footnote_from_dataframe,
    aggregate_results_overview_from_dataframe,
    fetch_pulse_scope_footnote,
    fetch_results_activity_timeline,
    fetch_results_category_kpis,
    fetch_results_overview_aggregates,
)

# Bump when KPI shapes or aggregation semantics change (docs + tests).
PULSE_KPI_DEFINITION_VERSION = "1.0-draft"


@dataclass(frozen=True)
class PulseKpiBundle:
    """
    All Pulse overview KPI snapshots for one load, plus policy and version metadata.

    ``policy_template_id`` is the comparison-policy anchor used with
    :func:`src.pulse_policy.validate_pulse_request` (currently index-wide
    descriptive counts only — ``TPL_CATEGORY_ROLLUP``).
    """

    overview: ResultsOverviewSnapshot
    category_mix: CategoryKpiSnapshot
    activity_timeline: ActivityTimelineSnapshot
    scope: PulseScopeFootnote
    policy_template_id: str
    definition_version: str


def fetch_pulse_kpi_bundle(client: Any) -> PulseKpiBundle:
    """
    Load all Pulse KPI snapshots from OpenSearch via :mod:`src.query_service`.

    Each KPI is loaded in its own try/except so an unexpected exception in one path
    (including parse logic after ``search_results`` inside a helper) cannot abort
    the others; failed slots get ``error`` set on the snapshot, matching
    :func:`aggregate_pulse_kpi_bundle_from_dataframe` resilience.
    """
    try:
        overview = fetch_results_overview_aggregates(client)
    except Exception as exc:  # noqa: BLE001 — surface per-KPI; helpers may not catch all parse paths
        overview = ResultsOverviewSnapshot(
            total=None, by_cloud=[], source="opensearch", error=str(exc)
        )
    try:
        category_mix = fetch_results_category_kpis(client)
    except Exception as exc:  # noqa: BLE001
        category_mix = CategoryKpiSnapshot(
            by_category=[], source="opensearch", error=str(exc)
        )
    try:
        activity_timeline = fetch_results_activity_timeline(client)
    except Exception as exc:  # noqa: BLE001
        activity_timeline = ActivityTimelineSnapshot(
            by_month=[], source="opensearch", error=str(exc)
        )
    try:
        scope = fetch_pulse_scope_footnote(client)
    except Exception as exc:  # noqa: BLE001
        scope = PulseScopeFootnote(
            document_count=None,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source="opensearch",
            error=str(exc),
        )
    return PulseKpiBundle(
        overview=overview,
        category_mix=category_mix,
        activity_timeline=activity_timeline,
        scope=scope,
        policy_template_id=PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
        definition_version=PULSE_KPI_DEFINITION_VERSION,
    )


def aggregate_pulse_kpi_bundle_from_dataframe(df: pd.DataFrame) -> PulseKpiBundle:
    """Build the same bundle from the loaded benchmark DataFrame (synthetic or scroll sample)."""
    try:
        overview = aggregate_results_overview_from_dataframe(df)
    except Exception as exc:  # noqa: BLE001 — match app.py resilience
        overview = ResultsOverviewSnapshot(
            total=None, by_cloud=[], source="synthetic", error=str(exc)
        )
    try:
        category_mix = aggregate_category_kpis_from_dataframe(df)
    except Exception as exc:  # noqa: BLE001
        category_mix = CategoryKpiSnapshot(by_category=[], source="synthetic", error=str(exc))
    try:
        activity_timeline = aggregate_activity_timeline_from_dataframe(df)
    except Exception as exc:  # noqa: BLE001
        activity_timeline = ActivityTimelineSnapshot(by_month=[], source="synthetic", error=str(exc))
    try:
        scope = aggregate_pulse_scope_footnote_from_dataframe(df)
    except Exception as exc:  # noqa: BLE001
        scope = PulseScopeFootnote(
            document_count=None,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source="synthetic",
            error=str(exc),
        )
    return PulseKpiBundle(
        overview=overview,
        category_mix=category_mix,
        activity_timeline=activity_timeline,
        scope=scope,
        policy_template_id=PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
        definition_version=PULSE_KPI_DEFINITION_VERSION,
    )


def pulse_kpi_bundle_from_connection_error(error_message: str, *, source: str) -> PulseKpiBundle:
    """Use when the OpenSearch client cannot be constructed; all KPI slots carry the same error."""
    err = error_message
    return PulseKpiBundle(
        overview=ResultsOverviewSnapshot(
            total=None, by_cloud=[], source=source, error=err
        ),
        category_mix=CategoryKpiSnapshot(by_category=[], source=source, error=err),
        activity_timeline=ActivityTimelineSnapshot(by_month=[], source=source, error=err),
        scope=PulseScopeFootnote(
            document_count=None,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source=source,
            error=err,
        ),
        policy_template_id=PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
        definition_version=PULSE_KPI_DEFINITION_VERSION,
    )
