"""
Pulse (executive-safe) server request guards (Phase 1, P1-B).

Server-side code paths that power Pulse-style surfaces must validate template id
and parameters against :mod:`src.comparison_policy` in **pulse** mode before
emitting OpenSearch queries that could imply forbidden comparisons.

Contract: ``docs/guides/COMPARISON_POLICY.md`` §2–3.
"""

from __future__ import annotations

from typing import Mapping, Optional

from src.comparison_policy import ValidationResult, validate_comparison_request


class PulsePolicyError(ValueError):
    """Raised when a Pulse-mode request violates comparison policy."""


def validate_pulse_request(
    template_id: str,
    params: Optional[Mapping[str, object]] = None,
) -> ValidationResult:
    """
    Validate ``template_id`` and optional ``params`` for Pulse (executive) mode.

    Thin wrapper around :func:`~src.comparison_policy.validate_comparison_request`
    with ``mode='pulse'`` so Pulse call sites have a single import.
    """
    return validate_comparison_request(template_id, params, mode="pulse")


def require_pulse_request(
    template_id: str,
    params: Optional[Mapping[str, object]] = None,
) -> None:
    """Raise :class:`PulsePolicyError` if :func:`validate_pulse_request` fails."""
    vr = validate_pulse_request(template_id, params)
    if not vr.ok:
        raise PulsePolicyError("; ".join(vr.errors))
