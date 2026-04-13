"""
Regression detection helpers (Phase 1, P1-D).

Implements the percent-change formula, default thresholds, tri-band labels,
status filtering, and per-``test.name`` directionality described in
``docs/guides/REGRESSION_DETECTION.md`` §1.2–§4. Centralizing this logic keeps
processor paths and tests aligned with the spec.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from src.metric_registry import higher_is_better_for_test

logger = logging.getLogger(__name__)

# Draft defaults — see REGRESSION_DETECTION.md §2
REGRESSION_THRESHOLD_REL: float = -5.0
STABILITY_BAND_PCT: float = 10.0
# Lower-is-better metrics (e.g. latency): regression when pct_change exceeds +T (§3.2)
REGRESSION_THRESHOLD_LATENCY: float = 5.0


def _is_pass_status(val: object) -> bool:
    """True only for string PASS (case-insensitive); missing/NaN/non-PASS → False (§4)."""
    try:
        if pd.isna(val):
            return False
    except (TypeError, ValueError):
        return False
    return str(val).strip().upper() == "PASS"


def filter_dataframe_for_regression_math(
    df: pd.DataFrame,
    *,
    context: Optional[str] = None,
) -> pd.DataFrame:
    """
    Default regression aggregation includes **PASS** rows only (REGRESSION_DETECTION.md §4).

    FAIL and UNKNOWN are excluded; missing ``status`` is treated as non-PASS. If the
    ``status`` column is absent, no rows are dropped (same values as input), but the
    result is still a **copy** so mutating the return value never affects ``df``.

    Always returns a new DataFrame instance (bypass and filtered paths).
    """
    if df.empty or "status" not in df.columns:
        return df.copy()
    mask = df["status"].map(_is_pass_status)
    n_in = int(mask.sum())
    n_excl = int(len(df) - n_in)
    if n_excl:
        suffix = f" ({context})" if context else ""
        logger.info(
            "Regression math%s: %d PASS row(s), excluded %d non-PASS row(s)",
            suffix,
            n_in,
            n_excl,
        )
    return df.loc[mask].copy()


def percent_change(baseline_mean: float, comparison_mean: float) -> float:
    """
    Percent change of candidate vs baseline (§1.2).

    Positive values mean the candidate mean is higher than the baseline mean.
    Callers must skip ``baseline_mean == 0`` and invalid / missing means (§5).
    """
    return (comparison_mean - baseline_mean) / baseline_mean * 100.0


def is_regression_higher_is_better(
    pct_change: float,
    regression_threshold: float = REGRESSION_THRESHOLD_REL,
) -> bool:
    """
    Throughput / score style metrics: regression when change is sufficiently negative.

    Matches existing ``pct_change < regression_threshold`` with negative thresholds
    (e.g. -5 for -5%).
    """
    return pct_change < regression_threshold


def is_regression_lower_is_better(
    pct_change: float,
    regression_threshold_positive: float = REGRESSION_THRESHOLD_LATENCY,
) -> bool:
    """
    Latency / duration style metrics: regression when the metric got worse (higher).

    With the §1.2 formula, a longer latency yields a positive ``pct_change``; flag
    regression when that exceeds ``+T`` (§3.2).
    """
    return pct_change > regression_threshold_positive


def is_regression_for_test_name(
    pct_change: float,
    test_name: Optional[str],
    *,
    regression_threshold: float = REGRESSION_THRESHOLD_REL,
    regression_threshold_latency: float = REGRESSION_THRESHOLD_LATENCY,
) -> bool:
    """
    Whether ``pct_change`` counts as a regression for this ``test.name`` (§3).

    Uses :func:`higher_is_better_for_test` from ``metric_registry`` to choose
    between :func:`is_regression_higher_is_better` and :func:`is_regression_lower_is_better`.
    """
    if higher_is_better_for_test(test_name):
        return is_regression_higher_is_better(pct_change, regression_threshold)
    return is_regression_lower_is_better(pct_change, regression_threshold_latency)


def regression_severity_score(
    pct_change: float,
    test_name: Optional[str],
) -> float:
    """
    Scalar "how bad" the regression is for sorting worst-first in summaries.

    Higher-is-better metrics: regressions are negative ``pct_change``; more negative
    is worse → score is ``-pct_change`` (e.g. -20% → 20).

    Lower-is-better metrics: regressions are positive ``pct_change``; larger positive
    is worse → score is ``pct_change`` (e.g. +30% → 30).

    Only meaningful for rows already flagged as regressions; callers use this to sort
    mixed test types correctly (ascending ``percent_change`` alone would rank mild
    latency regressions above severe ones).
    """
    pc = float(pct_change)
    if higher_is_better_for_test(test_name):
        return -pc
    return pc


def sort_regressions_worst_first(
    regressions: pd.DataFrame,
    *,
    pct_col: str = "percent_change",
    test_col: str = "test_name",
) -> pd.DataFrame:
    """
    Sort regression rows so the most severe appear first (for ``head(k)`` summaries).

    Empty or missing-column frames are returned unchanged.
    """
    if regressions.empty:
        return regressions
    if pct_col not in regressions.columns:
        return regressions
    if test_col not in regressions.columns:
        return regressions.sort_values(pct_col, ascending=True)

    severity = regressions.apply(
        lambda r: regression_severity_score(r[pct_col], r[test_col]),
        axis=1,
    )
    return (
        regressions.assign(_severity=severity)
        .sort_values("_severity", ascending=False)
        .drop(columns=["_severity"])
    )


def is_improvement_for_test_name(
    pct_change: float,
    test_name: Optional[str],
    *,
    band_pct: float = STABILITY_BAND_PCT,
) -> bool:
    """
    Tri-band "Improvement" side, aligned with :func:`change_category_tri_band` (§2.2).

    Higher-is-better: improvement when ``pct_change > band_pct``.
    Lower-is-better (e.g. latency): improvement when ``pct_change < -band_pct`` (metric dropped enough).
    """
    if higher_is_better_for_test(test_name):
        return pct_change > band_pct
    return pct_change < -band_pct


def change_category_tri_band(
    pct_change: float,
    band_pct: float = STABILITY_BAND_PCT,
) -> str:
    """
    Labels used by :meth:`BenchmarkDataProcessor.calculate_comparison` (§2.2).

    Outside ``±band_pct`` → Regression or Improvement; otherwise Stable.

    **Policy:** With defaults, this uses ``±STABILITY_BAND_PCT`` (±10%) for display
    categories. Programmatic ``is_regression`` flags elsewhere use
    ``REGRESSION_THRESHOLD_REL`` (-5%). The wider band is intentional: UI "Regression"
    / "Improvement" is more conservative than the -5% regression detector — do not
    unify them without product sign-off (see REGRESSION_DETECTION.md §2).
    """
    if pct_change < -band_pct:
        return "Regression"
    if pct_change > band_pct:
        return "Improvement"
    return "Stable"
