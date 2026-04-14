"""Tests for investigation drill-down breadcrumb (P1-C); helper lives in app.py."""

from app import investigation_drill_breadcrumb


def test_investigation_drill_breadcrumb_three_levels():
    bc = investigation_drill_breadcrumb("Networking", "uperf")
    items = bc.items
    assert len(items) == 3
    assert items[0]["label"] == "RHEL Regression Analysis"
    assert items[1]["label"] == "Networking"
    assert items[2]["label"] == "uperf"
    assert items[2].get("active") is True
