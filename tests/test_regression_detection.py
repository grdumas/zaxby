"""Tests for regression_detection (P1-D) vs REGRESSION_DETECTION.md."""

import pandas as pd
import pytest

from src.regression_detection import (
    REGRESSION_THRESHOLD_LATENCY,
    REGRESSION_THRESHOLD_REL,
    STABILITY_BAND_PCT,
    change_category_tri_band,
    filter_dataframe_for_regression_math,
    is_improvement_for_test_name,
    is_regression_for_test_name,
    is_regression_higher_is_better,
    is_regression_lower_is_better,
    percent_change,
    regression_severity_score,
    sort_regressions_worst_first,
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


def test_change_category_tri_band_lower_is_better_pyperf():
    """Mean time up → Regression label; mean time down → Improvement (§3.2)."""
    assert change_category_tri_band(11.0, test_name="pyperf") == "Regression"
    assert change_category_tri_band(-11.0, test_name="pyperf") == "Improvement"
    assert change_category_tri_band(0.0, test_name="pyperf") == "Stable"
    assert change_category_tri_band(10.0, test_name="pyperf") == "Stable"
    assert change_category_tri_band(-10.0, test_name="pyperf") == "Stable"


def test_change_category_tri_band_custom_band_lower_is_better_pyperf():
    assert change_category_tri_band(6.0, band_pct=5.0, test_name="pyperf") == "Regression"
    assert change_category_tri_band(-6.0, band_pct=5.0, test_name="pyperf") == "Improvement"


def test_constants_align_with_regression_detection_doc():
    assert REGRESSION_THRESHOLD_REL == -5.0
    assert STABILITY_BAND_PCT == 10.0
    assert REGRESSION_THRESHOLD_LATENCY == 5.0


def test_is_regression_for_test_name_higher_is_better_default():
    assert is_regression_for_test_name(-6.0, "streams") is True
    assert is_regression_for_test_name(-4.0, "streams") is False


def test_is_regression_for_test_name_lower_is_better(monkeypatch):
    monkeypatch.setattr(
        "src.metric_registry.LOWER_IS_BETTER_TEST_NAMES",
        frozenset({"latency_probe"}),
    )
    assert is_regression_for_test_name(6.0, "latency_probe") is True
    assert is_regression_for_test_name(-6.0, "latency_probe") is False
    assert is_regression_for_test_name(4.0, "latency_probe") is False


def test_is_improvement_for_test_name_higher_is_better():
    assert is_improvement_for_test_name(11.0, "streams") is True
    assert is_improvement_for_test_name(10.0, "streams") is False


def test_is_improvement_for_test_name_lower_is_better(monkeypatch):
    monkeypatch.setattr(
        "src.metric_registry.LOWER_IS_BETTER_TEST_NAMES",
        frozenset({"latency_probe"}),
    )
    assert is_improvement_for_test_name(-11.0, "latency_probe") is True
    assert is_improvement_for_test_name(-10.0, "latency_probe") is False
    assert is_improvement_for_test_name(11.0, "latency_probe") is False


def test_pyperf_is_regression_for_test_name_mean_time_worse():
    """pyperf is lower-is-better: higher mean time → positive pct_change → regression."""
    assert is_regression_for_test_name(6.0, "pyperf") is True
    assert is_regression_for_test_name(-6.0, "pyperf") is False
    assert is_regression_for_test_name(4.0, "pyperf") is False


def test_pyperf_is_improvement_for_test_name_mean_time_better():
    assert is_improvement_for_test_name(-11.0, "pyperf") is True
    assert is_improvement_for_test_name(11.0, "pyperf") is False


def test_none_test_name_dispatches_higher_is_better():
    """Missing test_name uses higher-is-better path (same as unknown benchmark)."""
    assert is_regression_for_test_name(-6.0, None) is True
    assert is_regression_for_test_name(-4.0, None) is False
    assert is_improvement_for_test_name(11.0, None) is True
    assert is_improvement_for_test_name(10.0, None) is False


def test_is_regression_for_test_name_custom_regression_threshold_latency(monkeypatch):
    monkeypatch.setattr(
        "src.metric_registry.LOWER_IS_BETTER_TEST_NAMES",
        frozenset({"latency_probe"}),
    )
    assert is_regression_for_test_name(
        8.0,
        "latency_probe",
        regression_threshold_latency=7.0,
    ) is True
    assert is_regression_for_test_name(
        6.0,
        "latency_probe",
        regression_threshold_latency=7.0,
    ) is False


def test_percent_change_zero_baseline_raises():
    """Callers must exclude zero baseline (REGRESSION_DETECTION.md §5)."""
    with pytest.raises(ZeroDivisionError):
        percent_change(0.0, 1.0)


def test_filter_regression_math_pass_only():
    df = pd.DataFrame(
        {
            "status": ["PASS", "FAIL", "UNKNOWN", None, "pass"],
            "primary_metric_value": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )
    out = filter_dataframe_for_regression_math(df)
    assert len(out) == 2
    assert out["primary_metric_value"].tolist() == [1.0, 5.0]
    assert out is not df


def test_filter_regression_math_no_status_column_unchanged_values():
    df = pd.DataFrame({"primary_metric_value": [1.0, 2.0]})
    out = filter_dataframe_for_regression_math(df)
    pd.testing.assert_frame_equal(out, df)
    assert out is not df


def test_filter_regression_math_all_pass_no_exclusions():
    df = pd.DataFrame({"status": ["PASS", "PASS"], "x": [1, 2]})
    out = filter_dataframe_for_regression_math(df)
    pd.testing.assert_frame_equal(out, df)
    assert out is not df
    assert len(out) == 2


def test_filter_regression_math_empty():
    df = pd.DataFrame()
    out = filter_dataframe_for_regression_math(df)
    assert out.empty
    assert out is not df


def test_regression_severity_score_higher_is_better():
    assert regression_severity_score(-20.0, "streams") == pytest.approx(20.0)
    assert regression_severity_score(-5.0, "streams") == pytest.approx(5.0)


def test_regression_severity_score_lower_is_better(monkeypatch):
    monkeypatch.setattr(
        "src.metric_registry.LOWER_IS_BETTER_TEST_NAMES",
        frozenset({"latency_probe"}),
    )
    assert regression_severity_score(30.0, "latency_probe") == pytest.approx(30.0)
    assert regression_severity_score(10.0, "latency_probe") == pytest.approx(10.0)


def test_sort_regressions_worst_first_prefers_severe_latency(monkeypatch):
    """Ascending pct_change would put +8% before +25% for lower-is-better tests."""
    monkeypatch.setattr(
        "src.metric_registry.LOWER_IS_BETTER_TEST_NAMES",
        frozenset({"latency_probe"}),
    )
    df = pd.DataFrame(
        [
            {"test_name": "latency_probe", "percent_change": 8.0, "is_regression": True},
            {"test_name": "latency_probe", "percent_change": 25.0, "is_regression": True},
        ]
    )
    out = sort_regressions_worst_first(df)
    assert out.iloc[0]["percent_change"] == pytest.approx(25.0)
    assert out.iloc[1]["percent_change"] == pytest.approx(8.0)


def test_sort_regressions_worst_first_mixed_hib_and_lib(monkeypatch):
    monkeypatch.setattr(
        "src.metric_registry.LOWER_IS_BETTER_TEST_NAMES",
        frozenset({"latency_probe"}),
    )
    df = pd.DataFrame(
        [
            {"test_name": "streams", "percent_change": -20.0, "is_regression": True},
            {"test_name": "latency_probe", "percent_change": 25.0, "is_regression": True},
            {"test_name": "latency_probe", "percent_change": 8.0, "is_regression": True},
        ]
    )
    out = sort_regressions_worst_first(df)
    assert out.iloc[0]["percent_change"] == pytest.approx(25.0)
    assert out.iloc[1]["percent_change"] == pytest.approx(-20.0)
    assert out.iloc[2]["percent_change"] == pytest.approx(8.0)


def test_sort_regressions_worst_first_preserves_unrelated_severity_column():
    """
    Scratch sort column is __regression_sort_key__; a caller column named _severity
    must not be overwritten or dropped (PR #19).
    """
    df = pd.DataFrame(
        [
            {
                "test_name": "streams",
                "percent_change": -10.0,
                "is_regression": True,
                "_severity": 999.0,
            },
            {
                "test_name": "streams",
                "percent_change": -20.0,
                "is_regression": True,
                "_severity": 888.0,
            },
        ]
    )
    out = sort_regressions_worst_first(df)
    assert "_severity" in out.columns
    assert out.iloc[0]["percent_change"] == pytest.approx(-20.0)
    assert out.iloc[0]["_severity"] == pytest.approx(888.0)
    assert out.iloc[1]["percent_change"] == pytest.approx(-10.0)
    assert out.iloc[1]["_severity"] == pytest.approx(999.0)
