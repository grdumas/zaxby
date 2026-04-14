"""Tests for investigation drill-down navigation (P1-C)."""

from src.components.investigation_nav import investigation_drill_breadcrumb


def test_investigation_drill_breadcrumb_three_levels():
    bc = investigation_drill_breadcrumb("Networking", "uperf")
    items = bc.items
    assert len(items) == 3
    assert items[0]["label"] == "RHEL Regression Analysis"
    assert items[1]["label"] == "Networking"
    assert items[2]["label"] == "uperf"
    assert items[2].get("active") is True
