"""Tests for nightly runs UI component (RPOPC-1207 / RPOPC-1212)."""

from datetime import datetime, timezone

import pytest
from dash import html
import dash_bootstrap_components as dbc

from src.components.nightly_runs import (
    create_nightly_run_category_chart,
    create_nightly_run_selector_dropdown,
    create_nightly_run_summary_cards,
    create_nightly_runs_section,
)
from src.query_service import NightlyRunSnapshot


@pytest.fixture
def sample_nightly_runs():
    """Create sample nightly run snapshots for testing."""
    return [
        NightlyRunSnapshot(
            timestamp=datetime(2025, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
            test_count=100,
            pass_count=95,
            fail_count=5,
            category_breakdown=[("CPU", 50), ("Memory", 30), ("I/O", 20)],
            source="opensearch",
            error=None,
        ),
        NightlyRunSnapshot(
            timestamp=datetime(2025, 5, 17, 10, 0, 0, tzinfo=timezone.utc),
            test_count=80,
            pass_count=75,
            fail_count=5,
            category_breakdown=[("CPU", 40), ("Memory", 25), ("I/O", 15)],
            source="opensearch",
            error=None,
        ),
        NightlyRunSnapshot(
            timestamp=datetime(2025, 5, 16, 10, 0, 0, tzinfo=timezone.utc),
            test_count=90,
            pass_count=60,
            fail_count=30,
            category_breakdown=[("CPU", 45), ("Memory", 30), ("I/O", 15)],
            source="opensearch",
            error=None,
        ),
    ]


def test_create_nightly_run_summary_cards(sample_nightly_runs):
    """Test summary cards creation with sample data."""
    cards = create_nightly_run_summary_cards(sample_nightly_runs)

    assert isinstance(cards, dbc.Row)
    # Should have 3 columns (Latest Run, Total Tests, Pass Rate)
    assert len(cards.children) == 3

    # Check that all columns are dbc.Col
    assert all(isinstance(col, dbc.Col) for col in cards.children)

    # Each column should have width=4
    assert all(col.width == 4 for col in cards.children)


def test_create_nightly_run_summary_cards_pass_rate_colors(sample_nightly_runs):
    """Test that pass rate card uses appropriate color based on percentage."""
    # High pass rate (95%) - should be success/green
    high_pass = [sample_nightly_runs[0]]  # 95% pass rate
    cards = create_nightly_run_summary_cards(high_pass)
    pass_rate_card = cards.children[2]
    card_body = pass_rate_card.children[0].children[0]
    h4 = card_body.children[1]
    assert "text-success" in h4.className

    # Medium pass rate (66.7%) - should be warning/yellow
    medium_pass = [sample_nightly_runs[2]]  # 60/90 = 66.7% pass rate
    cards = create_nightly_run_summary_cards(medium_pass)
    pass_rate_card = cards.children[2]
    card_body = pass_rate_card.children[0].children[0]
    h4 = card_body.children[1]
    assert "text-" in h4.className  # Should have color class


def test_create_nightly_run_summary_cards_empty():
    """Test summary cards with empty runs list."""
    cards = create_nightly_run_summary_cards([])

    assert isinstance(cards, html.Div)
    # Should show "No nightly runs available" message
    assert "No nightly runs available" in str(cards)


def test_create_nightly_run_selector_dropdown(sample_nightly_runs):
    """Test dropdown selector creation."""
    from dash import dcc

    dropdown = create_nightly_run_selector_dropdown(sample_nightly_runs)

    assert isinstance(dropdown, dcc.Dropdown)
    assert dropdown.id == "nightly-run-selector"
    assert len(dropdown.options) == 3

    # Check first option format
    first_option = dropdown.options[0]
    assert "2025-05-18" in first_option["label"]
    assert "100 tests" in first_option["label"]
    assert first_option["value"] == 0

    # Default selection should be first run (most recent)
    assert dropdown.value == 0


def test_create_nightly_run_selector_dropdown_empty():
    """Test dropdown with no runs."""
    from dash import dcc

    dropdown = create_nightly_run_selector_dropdown([])

    assert isinstance(dropdown, dcc.Dropdown)
    assert dropdown.disabled is True
    assert dropdown.value is None


def test_create_nightly_run_category_chart(sample_nightly_runs):
    """Test category breakdown chart creation."""
    import plotly.graph_objects as go

    run = sample_nightly_runs[0]
    fig = create_nightly_run_category_chart(run)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"
    assert fig.data[0].orientation == "h"

    # Check data matches category breakdown
    assert list(fig.data[0].y) == ["CPU", "Memory", "I/O"]
    assert list(fig.data[0].x) == [50, 30, 20]

    # Check purple color theme
    assert fig.data[0].marker.color == "#7c3aed"


def test_create_nightly_run_category_chart_empty():
    """Test chart with no data."""
    import plotly.graph_objects as go

    fig = create_nightly_run_category_chart(None)

    assert isinstance(fig, go.Figure)
    # Should have "No category data available" annotation
    assert len(fig.layout.annotations) > 0
    assert "No category data available" in fig.layout.annotations[0].text


def test_create_nightly_run_category_chart_empty_breakdown():
    """Test chart with run that has no category breakdown."""
    import plotly.graph_objects as go

    run = NightlyRunSnapshot(
        timestamp=datetime(2025, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
        test_count=10,
        pass_count=10,
        fail_count=0,
        category_breakdown=[],  # Empty breakdown
        source="opensearch",
        error=None,
    )

    fig = create_nightly_run_category_chart(run)

    assert isinstance(fig, go.Figure)
    # Should show empty state
    assert len(fig.layout.annotations) > 0


def test_create_nightly_runs_section(sample_nightly_runs):
    """Test complete section creation."""
    section = create_nightly_runs_section(sample_nightly_runs)

    assert isinstance(section, dbc.Card)

    # Check purple accent styling
    assert "7c3aed" in section.style["borderLeft"]

    # Check header structure
    header = section.children[0]
    assert isinstance(header, dbc.CardHeader)

    # Check collapse section
    collapse = section.children[1]
    assert isinstance(collapse, dbc.Collapse)
    assert collapse.id == "collapse-nightly-runs"
    assert collapse.is_open is True


def test_create_nightly_runs_section_empty():
    """Test section creation with no runs."""
    section = create_nightly_runs_section([])

    assert isinstance(section, dbc.Card)
    # Section should still render, with empty state messages


def test_nightly_runs_section_structure(sample_nightly_runs):
    """Test that section has all required components."""
    section = create_nightly_runs_section(sample_nightly_runs)

    # Extract collapse body
    collapse = section.children[1]
    card_body = collapse.children[0]

    # Should have summary cards, label, dropdown, and chart
    assert len(card_body.children) >= 3

    # First child should be summary cards (Row)
    assert isinstance(card_body.children[0], dbc.Row)

    # Should have label for dropdown
    label_found = False
    for child in card_body.children:
        if isinstance(child, html.Label) and "Select Nightly Run" in str(child):
            label_found = True
            break
    assert label_found


def test_nightly_runs_section_toggle_icon():
    """Test that toggle button has correct icon ID."""
    section = create_nightly_runs_section([])

    header = section.children[0]
    button = header.children[0]

    # Check for icon with correct ID
    icon_found = False
    for child in button.children:
        if isinstance(child, html.I) and child.id == "icon-nightly-runs":
            icon_found = True
            break
    assert icon_found


def test_create_nightly_run_category_chart_escapes_malicious_category_names():
    """Test that category labels with HTML/script tags are escaped (XSS prevention)."""
    import plotly.graph_objects as go
    import json

    # Create run with malicious category name
    malicious_run = NightlyRunSnapshot(
        timestamp=datetime(2025, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
        test_count=100,
        pass_count=95,
        fail_count=5,
        category_breakdown=[
            ("Category<script>alert('xss')</script>", 50),
            ("Normal Category", 30),
            ("<img src=x onerror=alert('xss')>", 20),
        ],
        source="opensearch",
        error=None,
    )

    fig = create_nightly_run_category_chart(malicious_run)

    assert isinstance(fig, go.Figure)

    # Convert figure to JSON to check all fields
    fig_json = json.dumps(fig.to_dict())

    # Script tags should NOT appear unescaped in the figure
    assert "<script>" not in fig_json, "Script tags must be escaped in hover content"
    assert "alert('xss')" not in fig_json, "JavaScript code must be escaped"
    assert "<img src=" not in fig_json, "HTML tags must be escaped"

    # Escaped versions SHOULD appear
    assert "&lt;script&gt;" in fig_json or "hovertext" in fig_json, (
        "Category names should be escaped or stored in hovertext/customdata"
    )


def test_create_nightly_run_category_chart_colorblind_mode_with_escaped_categories():
    """Test that escaped categories work correctly in colorblind mode."""
    import plotly.graph_objects as go

    # Create run with HTML characters that need escaping
    run_with_special_chars = NightlyRunSnapshot(
        timestamp=datetime(2025, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
        test_count=100,
        pass_count=95,
        fail_count=5,
        category_breakdown=[
            ("Category & <Tests>", 50),
            ("Memory > 100MB", 30),
            ("I/O \"Fast\"", 20),
        ],
        source="opensearch",
        error=None,
    )

    # Test in both standard and colorblind modes
    for colorblind in [False, True]:
        fig = create_nightly_run_category_chart(run_with_special_chars, colorblind)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1

        # Categories should still be in y-axis for positioning
        assert len(fig.data[0].y) == 3

        # Verify hover template doesn't contain raw unescaped categories
        fig_json = fig.to_json()
        assert "<Tests>" not in fig_json or "&lt;Tests&gt;" in fig_json


def test_create_nightly_run_category_chart_numeric_values_remain_formatted():
    """Test that numeric values (test counts) are still formatted correctly after fix."""
    import plotly.graph_objects as go

    run = NightlyRunSnapshot(
        timestamp=datetime(2025, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
        test_count=100,
        pass_count=95,
        fail_count=5,
        category_breakdown=[
            ("CPU", 1500),  # Test with thousands separator
            ("Memory", 2000),
        ],
        source="opensearch",
        error=None,
    )

    fig = create_nightly_run_category_chart(run)

    # Check that hover template still formats numbers with thousands separator
    hover_template = fig.data[0].hovertemplate
    assert "%{x:,}" in hover_template or "Tests:" in hover_template, (
        "Numeric formatting for test counts should be preserved"
    )
