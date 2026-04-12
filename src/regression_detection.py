"""
Regression detection helpers (Phase 1, P1-D).

Implements the percent-change formula, default thresholds, and tri-band labels
described in ``docs/guides/REGRESSION_DETECTION.md`` §1.2–§3. Centralizing this
logic keeps processor paths and tests aligned with the spec.
"""

from __future__ import annotations

# Draft defaults — see REGRESSION_DETECTION.md §2
REGRESSION_THRESHOLD_REL: float = -5.0
STABILITY_BAND_PCT: float = 10.0
# Lower-is-better metrics (e.g. latency): regression when pct_change exceeds +T (§3.2)
REGRESSION_THRESHOLD_LATENCY: float = 5.0


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
