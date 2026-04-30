"""Tests for Pulse v1 UI helpers (figures and panel layout)."""

from __future__ import annotations

from dash import html

from src.pulse_ui import (
    figure_pulse_activity_timeline,
    figure_pulse_category_mix,
    render_pulse_v1_panel,
)
from src.query_service import (
    ActivityTimelineSnapshot,
    CategoryKpiSnapshot,
    PulseScopeFootnote,
    ResultsOverviewSnapshot,
)


def test_activity_figure_empty_months():
    snap = ActivityTimelineSnapshot(by_month=[], source="opensearch", error=None)
    fig = figure_pulse_activity_timeline(snap)
    assert fig.layout.height == 240
    assert not fig.data


def test_activity_figure_with_points():
    snap = ActivityTimelineSnapshot(
        by_month=[("2025-01", 10), ("2025-02", 20)],
        source="opensearch",
        error=None,
    )
    fig = figure_pulse_activity_timeline(snap)
    assert len(fig.data) == 1
    assert list(fig.data[0].y) == [10, 20]


def test_category_figure_top_slice():
    pairs = [(f"cat{i}", i) for i in range(20)]
    snap = CategoryKpiSnapshot(by_category=pairs, source="opensearch", error=None)
    fig = figure_pulse_category_mix(snap, max_categories=5)
    assert len(fig.data[0].y) == 5


def test_render_panel_produces_div():
    panel = render_pulse_v1_panel(
        snap=ResultsOverviewSnapshot(total=100, by_cloud=[], source="synthetic", error=None),
        scope_snap=PulseScopeFootnote(
            document_count=100,
            run_date_min_utc="2025-01-01",
            run_date_max_utc="2025-06-01",
            source="synthetic",
            error=None,
        ),
        cat_snap=CategoryKpiSnapshot(by_category=[("HPC", 50)], source="synthetic", error=None),
        timeline_snap=ActivityTimelineSnapshot(
            by_month=[("2025-01", 5)],
            source="synthetic",
            error=None,
        ),
        data_mode="synthetic",
        results_index_label="",
    )
    assert isinstance(panel, html.Div)


def test_render_panel_includes_kpi_catalog_footer_when_metadata_passed():
    panel = render_pulse_v1_panel(
        snap=ResultsOverviewSnapshot(total=1, by_cloud=[], source="synthetic", error=None),
        scope_snap=PulseScopeFootnote(
            document_count=1,
            run_date_min_utc="2025-01-01",
            run_date_max_utc="2025-01-02",
            source="synthetic",
            error=None,
        ),
        cat_snap=CategoryKpiSnapshot(by_category=[], source="synthetic", error=None),
        timeline_snap=ActivityTimelineSnapshot(by_month=[], source="synthetic", error=None),
        data_mode="synthetic",
        results_index_label="idx",
        kpi_definition_version="1.0-test",
        policy_template_id="TPL_CATEGORY_ROLLUP",
    )
    inner = getattr(panel, "children", None)
    assert inner
    flat = str(inner)
    assert "PULSE_KPIS.md" in flat
    assert "TPL_CATEGORY_ROLLUP" in flat
