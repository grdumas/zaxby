"""
Closed-set comparison template validation (Phase 0, P0-E).

Contract: docs/guides/COMPARISON_POLICY.md §4–5. Phase 1 will extend validation with
field-level rules (e.g. cross-cloud checks on concrete params).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Literal, Mapping, Optional

Mode = Literal["pulse", "investigate"]

_VALID_MODES: frozenset[str] = frozenset(("pulse", "investigate"))


# Template IDs — must stay in sync with docs/guides/COMPARISON_POLICY.md §5
VALID_TEMPLATE_IDS: FrozenSet[str] = frozenset(
    {
        "TPL_RHEL_MINOR_SAME_HW",
        "TPL_RHEL_MAJOR_SAME_HW",
        "TPL_OS_SEQUENTIAL_MINOR",
        "TPL_PEER_OS",
        "TPL_CLOUD_SCALE_SAME_OS",
        "TPL_TIME_WINDOW",
        "TPL_ITERATION_REPEATABILITY",
        "TPL_ARCH_EXPLICIT",
        "TPL_SCENARIO_ABLATION",
        "TPL_CATEGORY_ROLLUP",
        "TPL_SINGLE_RUN_LOOKUP",
        "TPL_PROVIDER_INTERNAL_REGION",
        "TPL_GEN_UPLIFT",
    }
)

# Pulse-allowed templates — COMPARISON_POLICY.md §5 "Pulse-allowed" = Yes
PULSE_ALLOWED_TEMPLATE_IDS: FrozenSet[str] = frozenset(
    {
        "TPL_RHEL_MINOR_SAME_HW",
        "TPL_RHEL_MAJOR_SAME_HW",
        "TPL_OS_SEQUENTIAL_MINOR",
        "TPL_CLOUD_SCALE_SAME_OS",
        "TPL_TIME_WINDOW",
        # Policy §5: Pulse only if single-provider / no cross-cloud delta; enforce via params in Phase 1
        "TPL_CATEGORY_ROLLUP",
        "TPL_SINGLE_RUN_LOOKUP",
        "TPL_PROVIDER_INTERNAL_REGION",
    }
)


@dataclass(frozen=True)
class ValidationResult:
    """Result of :func:`validate_comparison_request`."""

    ok: bool
    errors: tuple[str, ...]


def validate_comparison_request(
    template_id: str,
    _params: Optional[Mapping[str, object]] = None,
    *,
    mode: Mode = "investigate",
) -> ValidationResult:
    """
    Validate a comparison request against the canonical template allowlist.

    Args:
        template_id: Must match a row in COMPARISON_POLICY.md §5.
        _params: Reserved for Phase 1 field checks (fixed dimensions, baseline/candidate).
        mode: ``pulse`` rejects templates not marked Pulse-allowed in the policy doc.

    Returns:
        ``ValidationResult`` with ``ok`` and human-readable ``errors``.

    Raises:
        ValueError: if ``mode`` is not ``pulse`` or ``investigate``.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            f"mode must be 'pulse' or 'investigate', not {mode!r}"
        )
    errors: list[str] = []
    tid = (template_id or "").strip()
    if not tid:
        return ValidationResult(False, ("template_id is required",))

    if tid not in VALID_TEMPLATE_IDS:
        return ValidationResult(False, (f"Unknown template_id: {tid!r}",))

    if mode == "pulse" and tid not in PULSE_ALLOWED_TEMPLATE_IDS:
        errors.append(
            f"Template {tid!r} is not allowed in Pulse mode "
            f"(see docs/guides/COMPARISON_POLICY.md §5)"
        )

    return ValidationResult(ok=len(errors) == 0, errors=tuple(errors))
