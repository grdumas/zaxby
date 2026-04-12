"""
Closed-set comparison template validation (Phase 0, P0-E; Phase 1 param rules).

Contract: docs/guides/COMPARISON_POLICY.md §3–5. Pulse mode enforces forbidden axes
on ``params`` (e.g. no cross–public-cloud comparative cohorts) when the template
is Pulse-allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Literal, Mapping, Optional

Mode = Literal["pulse", "investigate"]

_VALID_MODES: frozenset[str] = frozenset(("pulse", "investigate"))

# Hyperscalers named in COMPARISON_POLICY.md §3.1 (baseline vs candidate / cohort rules)
PUBLIC_CLOUD_PROVIDERS: FrozenSet[str] = frozenset(("aws", "azure", "gcp"))


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


def _canonical_public_cloud_slug(value: object) -> Optional[str]:
    """Return normalized provider slug if ``value`` is a recognized public cloud, else None."""
    if not isinstance(value, str):
        return None
    s = value.lower().strip()
    if s in PUBLIC_CLOUD_PROVIDERS:
        return s
    return None


def _pulse_violations_for_public_cloud_axes(params: Mapping[str, object]) -> list[str]:
    """
    COMPARISON_POLICY.md §3.1 — Pulse must not compare cohorts across hyperscalers.

    Recognized optional keys:
    - ``baseline_cloud_provider`` / ``candidate_cloud_provider``: both public and
      different → violation.
    - ``cloud_providers``: iterable of strings; must be ``list``, ``tuple``,
      ``set``, or ``frozenset`` (other types are ignored). More than one distinct
      recognized public cloud → violation (comparative rollup across providers).
    """
    errors: list[str] = []
    b = _canonical_public_cloud_slug(params.get("baseline_cloud_provider"))
    c = _canonical_public_cloud_slug(params.get("candidate_cloud_provider"))
    if b is not None and c is not None and b != c:
        errors.append(
            "Pulse cannot compare baseline vs candidate across different public "
            "cloud providers (COMPARISON_POLICY.md §3.1)"
        )

    raw = params.get("cloud_providers")
    if isinstance(raw, (list, tuple, set, frozenset)):
        seen: set[str] = set()
        for item in raw:
            slug = _canonical_public_cloud_slug(item)
            if slug is not None:
                seen.add(slug)
        if len(seen) > 1:
            errors.append(
                "Pulse cannot aggregate comparative metrics across multiple public "
                "cloud providers (COMPARISON_POLICY.md §3.1; use a single-provider scope)"
            )
    return errors


def validate_comparison_request(
    template_id: str,
    params: Optional[Mapping[str, object]] = None,
    *,
    mode: Mode = "investigate",
) -> ValidationResult:
    """
    Validate a comparison request against the canonical template allowlist.

    Args:
        template_id: Must match a row in COMPARISON_POLICY.md §5.
        params: Optional request parameters. For ``mode='pulse'``, values that
            imply cross–public-cloud comparative cohorts are rejected; see
            COMPARISON_POLICY.md §3.1. Supported keys include ``baseline_cloud_provider``,
            ``candidate_cloud_provider``, and ``cloud_providers`` (the latter as
            ``list``, ``tuple``, ``set``, or ``frozenset`` of provider slugs).
        mode: ``pulse`` rejects templates not marked Pulse-allowed in the policy doc
            and enforces §3 forbidden axes on ``params``.

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

    if mode == "pulse":
        if tid not in PULSE_ALLOWED_TEMPLATE_IDS:
            errors.append(
                f"Template {tid!r} is not allowed in Pulse mode "
                f"(see docs/guides/COMPARISON_POLICY.md §5)"
            )
        else:
            # Template is Pulse-allowed; enforce §3 forbidden axes on params. (We do not
            # run this when the template is already Pulse-rejected — avoid piling on errors.)
            errors.extend(_pulse_violations_for_public_cloud_axes(params or {}))

    return ValidationResult(ok=len(errors) == 0, errors=tuple(errors))
