"""Tests for regression_detection (P1-D) vs REGRESSION_DETECTION.md."""

import pytest

from src.regression_detection import (
    REGRESSION_THRESHOLD_LATENCY,
    REGRESSION_THRESHOLD_REL,
    STABILITY_BAND_PCT,
    change_category_tri_band,
    is_regression_higher_is_better,
    is_regression_lower_is_better,
    percent_change,
)


def test_percent_change_formula():
    assert percent_change(100.0, 95.0) == pytest.approx(-5.0)
    assert percent_change(100.0, 110.0) == pytest.approx(10.0)


def test_is_regression_higher_is_better_default_threshold():
    assert is_regression_higher_is_better(-6.0) is True
    assert is_regression_higher_is_better(-5.0) is False
    assert is_regression_higher_is_better(-4.0) is False


def test_is_regression_higher_is_better_custom_threshold():
    assert is_regression_higher_is_better(-6.0, regression_threshold=-5.0) is True
    assert is_regression_higher_is_better(-3.0, regression_threshold=-5.0) is False
    assert is_regression_higher_is_better(-3.0, regression_threshold=-2.0) is True


def test_is_regression_lower_is_better_latency_style():
    # Latency went up 10% → worse
    assert is_regression_lower_is_better(10.0, regression_threshold_positive=5.0) is True
    assert is_regression_lower_is_better(4.0, regression_threshold_positive=5.0) is False


def test_is_regression_lower_is_better_boundary_strict():
    """Regression only when pct_change > T, not >= (exactly T is not regression)."""
    assert is_regression_lower_is_better(5.0, regression_threshold_positive=5.0) is False
    assert is_regression_lower_is_better(5.0001, regression_threshold_positive=5.0) is True


def test_change_category_tri_band_matches_doc_defaults():
    assert change_category_tri_band(-11.0) == "Regression"
    assert change_category_tri_band(11.0) == "Improvement"
    assert change_category_tri_band(0.0) == "Stable"
    assert change_category_tri_band(-10.0) == "Stable"
    assert change_category_tri_band(10.0) == "Stable"


def test_change_category_tri_band_custom_band_pct():
    assert change_category_tri_band(-6.0, band_pct=5.0) == "Regression"
    assert change_category_tri_band(6.0, band_pct=5.0) == "Improvement"
    assert change_category_tri_band(-5.0, band_pct=5.0) == "Stable"


def test_constants_align_with_regression_detection_doc():
    assert REGRESSION_THRESHOLD_REL == -5.0
    assert STABILITY_BAND_PCT == 10.0
    assert REGRESSION_THRESHOLD_LATENCY == 5.0


def test_percent_change_zero_baseline_raises():
    """Callers must exclude zero baseline (REGRESSION_DETECTION.md §5)."""
    with pytest.raises(ZeroDivisionError):
        percent_change(0.0, 1.0)
