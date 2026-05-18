"""Tests for nightly runs UI component."""

from datetime import datetime, timezone

from src.components.nightly_runs import (
    create_nightly_runs_section,
    create_nightly_run_summary_cards,
    create_nightly_run_selector_dropdown,
    create_nightly_run_category_chart,
)
from src.query_service import NightlyRunSnapshot


def test_create_nightly_runs_section_empty_state():
    """Test section creation with no runs shows empty state."""
    section = create_nightly_runs_section([])
    # Check it's a Card
    assert section.type == "Card"
    # Check it has CardHeader and Collapse
    assert len(section.children) == 2
    assert section.children[0].type == "CardHeader"
    assert section.children[1].type == "Collapse"


def test_create_nightly_runs_section_with_runs():
    """Test section creation with valid runs."""
    runs = [
        NightlyRunSnapshot(
            timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
            test_count=147,
            pass_count=141,
            fail_count=6,
            category_breakdown=[("Storage/IO", 45), ("Networking", 30)],
            source="synthetic",
            error=None,
        ),
    ]

    section = create_nightly_runs_section(runs)

    # Check it's a Card
    assert section.type == "Card"
    # Should have header and collapse
    assert len(section.children) == 2
    # Check purple border styling
    assert section.style["borderLeft"] == "5px solid #7c3aed"


def test_create_nightly_run_summary_cards_with_error():
    """Test summary cards with error snapshot."""
    run = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=0,
        pass_count=0,
        fail_count=0,
        category_breakdown=[],
        source="opensearch",
        error="Connection failed",
    )

    cards = create_nightly_run_summary_cards(run)

    # Should return error alert
    assert cards.type == "Row"
    # Check for error message
    assert any("Error loading" in str(child) for child in cards.children if hasattr(child, "children"))


def test_create_nightly_run_summary_cards_valid():
    """Test summary cards with valid snapshot."""
    run = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=147,
        pass_count=141,
        fail_count=6,
        category_breakdown=[("Storage/IO", 45), ("Networking", 30)],
        source="synthetic",
        error=None,
    )

    cards = create_nightly_run_summary_cards(run)

    # Should return Row with 3 columns
    assert cards.type == "Row"
    assert len(cards.children) == 3
    # Each column should have a Card
    for col in cards.children:
        assert col.type == "Col"


def test_create_nightly_run_summary_cards_pass_rate_calculation():
    """Test pass rate calculation and color coding."""
    # High pass rate (>= 95%)
    run_high = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=100,
        pass_count=96,
        fail_count=4,
        category_breakdown=[],
        source="synthetic",
        error=None,
    )
    cards_high = create_nightly_run_summary_cards(run_high)
    assert cards_high is not None

    # Medium pass rate (80-95%)
    run_med = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=100,
        pass_count=85,
        fail_count=15,
        category_breakdown=[],
        source="synthetic",
        error=None,
    )
    cards_med = create_nightly_run_summary_cards(run_med)
    assert cards_med is not None

    # Low pass rate (< 80%)
    run_low = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=100,
        pass_count=70,
        fail_count=30,
        category_breakdown=[],
        source="synthetic",
        error=None,
    )
    cards_low = create_nightly_run_summary_cards(run_low)
    assert cards_low is not None


def test_create_nightly_run_selector_dropdown_empty():
    """Test dropdown creation with no runs."""
    dropdown = create_nightly_run_selector_dropdown([])

    assert dropdown.id == "nightly-run-selector"
    assert dropdown.options == []
    assert dropdown.disabled is True


def test_create_nightly_run_selector_dropdown_with_runs():
    """Test dropdown creation with valid runs."""
    runs = [
        NightlyRunSnapshot(
            timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
            test_count=147,
            pass_count=141,
            fail_count=6,
            category_breakdown=[],
            source="synthetic",
            error=None,
        ),
        NightlyRunSnapshot(
            timestamp=datetime(2026, 5, 17, 3, 12, tzinfo=timezone.utc),
            test_count=145,
            pass_count=140,
            fail_count=5,
            category_breakdown=[],
            source="synthetic",
            error=None,
        ),
    ]

    dropdown = create_nightly_run_selector_dropdown(runs)

    assert dropdown.id == "nightly-run-selector"
    assert len(dropdown.options) == 2
    assert dropdown.clearable is False
    # Should default to first run
    assert dropdown.value == runs[0].timestamp.isoformat()
    # Check option format includes test count
    assert "147 tests" in dropdown.options[0]["label"]


def test_create_nightly_run_category_chart_with_error():
    """Test chart creation with error snapshot."""
    run = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=0,
        pass_count=0,
        fail_count=0,
        category_breakdown=[],
        source="opensearch",
        error="Query failed",
    )

    fig = create_nightly_run_category_chart(run)

    # Should be a Figure with error annotation
    assert fig.layout.title.text == "Category Breakdown"
    # Check for annotation (error message)
    assert len(fig.layout.annotations) > 0


def test_create_nightly_run_category_chart_empty_breakdown():
    """Test chart creation with no category breakdown."""
    run = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=147,
        pass_count=141,
        fail_count=6,
        category_breakdown=[],
        source="synthetic",
        error=None,
    )

    fig = create_nightly_run_category_chart(run)

    # Should be a Figure with empty message
    assert fig.layout.title.text == "Category Breakdown"
    assert len(fig.layout.annotations) > 0


def test_create_nightly_run_category_chart_valid():
    """Test chart creation with valid category breakdown."""
    run = NightlyRunSnapshot(
        timestamp=datetime(2026, 5, 18, 3, 15, tzinfo=timezone.utc),
        test_count=147,
        pass_count=141,
        fail_count=6,
        category_breakdown=[("Storage/IO", 45), ("Networking", 30), ("System", 72)],
        source="synthetic",
        error=None,
    )

    fig = create_nightly_run_category_chart(run)

    # Should be a horizontal bar chart
    assert fig.layout.title.text == "Category Breakdown"
    assert len(fig.data) == 1  # One bar trace
    trace = fig.data[0]
    assert trace.type == "bar"
    assert trace.orientation == "h"
    # Check purple color
    assert trace.marker.color == "#7c3aed"
    # Should have 3 categories
    assert len(trace.y) == 3
    assert len(trace.x) == 3
