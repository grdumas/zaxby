"""Tests for Pulse v1 UI helpers (figures and panel layout)."""

from __future__ import annotations

import json

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
    # Deliberately unsorted input: top 5 by count must be cat19..cat15, not cat0..cat4.
    pairs = [(f"cat{i}", i) for i in range(20)]
    snap = CategoryKpiSnapshot(by_category=pairs, source="opensearch", error=None)
    fig = figure_pulse_category_mix(snap, max_categories=5)
    assert list(fig.data[0].y) == ["cat19", "cat18", "cat17", "cat16", "cat15"]
    assert list(fig.data[0].x) == [19, 18, 17, 16, 15]


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


# Security tests for XSS prevention in hover templates


def test_activity_timeline_escapes_malicious_month_labels():
    """
    Test that month labels containing HTML/script tags are escaped in hover text.

    Prevents XSS attacks where untrusted OpenSearch data containing malicious
    month labels could inject scripts via Plotly hover templates.
    """
    malicious_month = "Jan<script>alert('xss')</script>"
    snap = ActivityTimelineSnapshot(
        by_month=[(malicious_month, 100)],
        source="opensearch",
        error=None,
    )
    fig = figure_pulse_activity_timeline(snap)

    # Convert figure to JSON to inspect the actual hover template data
    fig_json = json.loads(fig.to_json())

    # Check that the raw script tag does NOT appear in the figure data
    fig_str = json.dumps(fig_json)
    assert "<script>" not in fig_str, "Raw script tag found in figure - XSS vulnerability!"
    assert "alert('xss')" not in fig_str, "Raw script content found in figure - XSS vulnerability!"

    # Check that escaped HTML entities ARE present (either in hovertext or customdata)
    # The exact format depends on implementation but should contain escaped versions
    assert "&lt;script&gt;" in fig_str or "&#x3C;script&#x3E;" in fig_str, \
        "Month label not properly escaped in hover content"


def test_category_mix_escapes_malicious_category_labels():
    """
    Test that category labels containing HTML tags are escaped in hover text.

    Prevents XSS attacks where untrusted OpenSearch data containing malicious
    category labels could inject HTML via Plotly hover templates.
    """
    malicious_category = "Category<b>injection</b><img src=x onerror=alert(1)>"
    snap = CategoryKpiSnapshot(
        by_category=[(malicious_category, 50), ("Safe Category", 30)],
        source="opensearch",
        error=None,
    )
    fig = figure_pulse_category_mix(snap)

    # Convert figure to JSON to inspect the actual hover template data
    fig_json = json.loads(fig.to_json())
    fig_str = json.dumps(fig_json)

    # Check that raw HTML opening tags do NOT appear (these would be executable)
    assert "<b>" not in fig_str, "Raw <b> tag found in figure - XSS vulnerability!"
    assert "<img" not in fig_str, "Raw <img> tag found in figure - XSS vulnerability!"

    # Check that escaped HTML entities ARE present
    # The malicious content should be escaped, showing &lt; and &gt; instead of < and >
    assert "&lt;b&gt;" in fig_str or "&#x3C;b&#x3E;" in fig_str, \
        "Category label not properly escaped in hover content"
    assert "&lt;img" in fig_str or "&#x3C;img" in fig_str, \
        "Malicious img tag not properly escaped"


def test_numeric_formatting_preserved_after_xss_fix():
    """
    Test that numeric values (run counts, document counts) are still properly
    formatted with commas after the XSS fix is applied.

    Ensures that the security fix does not break the existing numeric formatting.
    """
    # Test activity timeline with large numbers
    snap_timeline = ActivityTimelineSnapshot(
        by_month=[("2025-01", 1234), ("2025-02", 5678)],
        source="opensearch",
        error=None,
    )
    fig_timeline = figure_pulse_activity_timeline(snap_timeline)
    fig_json_timeline = json.loads(fig_timeline.to_json())

    # The hovertemplate should still contain the :, format specifier for numbers
    # This ensures we're still formatting the numeric count with commas
    fig_str_timeline = json.dumps(fig_json_timeline)
    assert ":," in fig_str_timeline, "Numeric formatting with commas lost in activity timeline"

    # Test category mix with large numbers
    snap_category = CategoryKpiSnapshot(
        by_category=[("HPC", 9876), ("ML", 5432)],
        source="opensearch",
        error=None,
    )
    fig_category = figure_pulse_category_mix(snap_category)
    fig_json_category = json.loads(fig_category.to_json())

    fig_str_category = json.dumps(fig_json_category)
    assert ":," in fig_str_category, "Numeric formatting with commas lost in category mix"
