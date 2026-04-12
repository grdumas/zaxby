"""Tests for comparison template validation (COMPARISON_POLICY.md §4–5)."""

import pytest

from src.comparison_policy import (
    PULSE_ALLOWED_TEMPLATE_IDS,
    VALID_TEMPLATE_IDS,
    validate_comparison_request,
)


def test_valid_template_investigate_ok():
    r = validate_comparison_request("TPL_RHEL_MINOR_SAME_HW", {}, mode="investigate")
    assert r.ok is True
    assert r.errors == ()


def test_empty_template_id_rejected():
    r = validate_comparison_request("", {})
    assert r.ok is False
    assert "required" in r.errors[0].lower()


def test_unknown_template_rejected():
    r = validate_comparison_request("TPL_NOT_REAL", {}, mode="investigate")
    assert r.ok is False
    assert "Unknown" in r.errors[0]


def test_investigate_allows_non_pulse_template():
    """TPL_PEER_OS is Investigate-only per policy table."""
    r = validate_comparison_request("TPL_PEER_OS", {}, mode="investigate")
    assert r.ok is True


@pytest.mark.parametrize(
    "tid",
    sorted(PULSE_ALLOWED_TEMPLATE_IDS),
)
def test_pulse_allows_all_pulse_template_ids(tid):
    r = validate_comparison_request(tid, {}, mode="pulse")
    assert r.ok is True, (tid, r.errors)


def test_pulse_rejects_peer_os():
    r = validate_comparison_request("TPL_PEER_OS", {}, mode="pulse")
    assert r.ok is False
    assert "Pulse" in r.errors[0] or "pulse" in r.errors[0].lower()


def test_pulse_rejects_iteration_repeatability():
    r = validate_comparison_request("TPL_ITERATION_REPEATABILITY", {}, mode="pulse")
    assert r.ok is False


def test_valid_template_ids_count_matches_policy():
    """COMPARISON_POLICY §5 lists 13 templates."""
    assert len(VALID_TEMPLATE_IDS) == 13


def test_pulse_allowed_subset_of_valid():
    assert PULSE_ALLOWED_TEMPLATE_IDS <= VALID_TEMPLATE_IDS
