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


def test_whitespace_only_template_id_rejected():
    r = validate_comparison_request("   ", {})
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


@pytest.mark.parametrize(
    "bad_mode",
    ["Pulse", "PULSE", "investigate ", "pulse ", "foo", ""],
)
def test_invalid_mode_raises_value_error(bad_mode):
    with pytest.raises(ValueError, match="mode must be"):
        validate_comparison_request("TPL_RHEL_MINOR_SAME_HW", {}, mode=bad_mode)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tid",
    sorted(VALID_TEMPLATE_IDS - PULSE_ALLOWED_TEMPLATE_IDS),
)
def test_pulse_rejects_all_non_pulse_allowed_templates(tid):
    r = validate_comparison_request(tid, {}, mode="pulse")
    assert r.ok is False, tid


def test_valid_template_ids_count_matches_policy():
    """COMPARISON_POLICY §5 lists 13 templates."""
    assert len(VALID_TEMPLATE_IDS) == 13


def test_pulse_allowed_subset_of_valid():
    assert PULSE_ALLOWED_TEMPLATE_IDS <= VALID_TEMPLATE_IDS


# --- Pulse §3.1 — no cross–public-cloud comparative params ---


def test_pulse_rejects_baseline_vs_candidate_different_public_clouds():
    r = validate_comparison_request(
        "TPL_RHEL_MINOR_SAME_HW",
        {
            "baseline_cloud_provider": "aws",
            "candidate_cloud_provider": "azure",
        },
        mode="pulse",
    )
    assert r.ok is False
    assert any("baseline vs candidate" in e.lower() for e in r.errors)


def test_pulse_allows_baseline_vs_candidate_same_public_cloud():
    r = validate_comparison_request(
        "TPL_RHEL_MINOR_SAME_HW",
        {
            "baseline_cloud_provider": "aws",
            "candidate_cloud_provider": "aws",
        },
        mode="pulse",
    )
    assert r.ok is True


def test_investigate_allows_cross_public_cloud_params():
    """§3.1 applies to Pulse surfaces; Investigate may pass stricter templates separately."""
    r = validate_comparison_request(
        "TPL_RHEL_MINOR_SAME_HW",
        {
            "baseline_cloud_provider": "aws",
            "candidate_cloud_provider": "gcp",
        },
        mode="investigate",
    )
    assert r.ok is True


def test_pulse_rejects_multi_public_cloud_in_cloud_providers_list():
    r = validate_comparison_request(
        "TPL_CATEGORY_ROLLUP",
        {"cloud_providers": ["aws", "azure"]},
        mode="pulse",
    )
    assert r.ok is False
    assert any("multiple public" in e.lower() for e in r.errors)


def test_pulse_allows_single_public_cloud_in_cloud_providers_list():
    r = validate_comparison_request(
        "TPL_CATEGORY_ROLLUP",
        {"cloud_providers": ["aws", "aws"]},
        mode="pulse",
    )
    assert r.ok is True


def test_pulse_cloud_providers_non_public_values_do_not_trigger_multi_cloud_error():
    """Only recognized hyperscaler slugs count toward §3.1."""
    r = validate_comparison_request(
        "TPL_CATEGORY_ROLLUP",
        {"cloud_providers": ["on-prem-a", "on-prem-b"]},
        mode="pulse",
    )
    assert r.ok is True
