"""Tests for Pulse policy wrapper (Phase 1, P1-B)."""

import pytest

from src.pulse_policy import PulsePolicyError, require_pulse_request, validate_pulse_request


def test_validate_pulse_request_delegates_to_comparison_policy():
    r = validate_pulse_request("TPL_RHEL_MINOR_SAME_HW", {})
    assert r.ok
    assert r.errors == ()


def test_validate_pulse_request_rejects_peer_os():
    r = validate_pulse_request("TPL_PEER_OS", {})
    assert not r.ok


def test_require_pulse_request_raises_for_investigate_only_template():
    with pytest.raises(PulsePolicyError, match="Pulse|pulse"):
        require_pulse_request("TPL_PEER_OS", {})


def test_require_pulse_request_accepts_category_roll_up_empty_params():
    """Overview snapshot maps to this template + empty params (query_service)."""
    require_pulse_request("TPL_CATEGORY_ROLLUP", {})
