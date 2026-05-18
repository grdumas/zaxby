"""Tests for Track KPI calculations (RPOPC-1162)."""

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.track_kpis import (
    BaselineConfig,
    BenchmarkDelta,
    TrackKpiResult,
    calculate_delta,
    calculate_delta_from_dataframes,
    fetch_baseline_results,
    fetch_nightly_results,
)


@pytest.fixture
def baseline_config():
    """Create a baseline configuration for testing."""
    return BaselineConfig(
        baseline_id="baseline_v1",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
        benchmark_filter=None,
    )


@pytest.fixture
def synthetic_baseline_df():
    """Create synthetic baseline dataset."""
    return pd.DataFrame(
        [
            {
                "test_name": "coremark",
                "test_timestamp": pd.Timestamp("2025-01-15", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 100.0,
                "primary_metric_name": "iterations/sec",
            },
            {
                "test_name": "coremark",
                "test_timestamp": pd.Timestamp("2025-01-16", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 110.0,
                "primary_metric_name": "iterations/sec",
            },
            {
                "test_name": "streams",
                "test_timestamp": pd.Timestamp("2025-01-15", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 50000.0,
                "primary_metric_name": "MB/s",
            },
            {
                "test_name": "pyperf",
                "test_timestamp": pd.Timestamp("2025-01-15", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 1.5,
                "primary_metric_name": "seconds",
            },
        ]
    )


@pytest.fixture
def synthetic_nightly_df():
    """Create synthetic nightly dataset."""
    return pd.DataFrame(
        [
            {
                "test_name": "coremark",
                "test_timestamp": pd.Timestamp("2025-02-01", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 95.0,  # Regression: -9.5%
                "primary_metric_name": "iterations/sec",
            },
            {
                "test_name": "streams",
                "test_timestamp": pd.Timestamp("2025-02-01", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 52000.0,  # Improvement: +4%
                "primary_metric_name": "MB/s",
            },
            {
                "test_name": "pyperf",
                "test_timestamp": pd.Timestamp("2025-02-01", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 1.6,  # Regression for lower-is-better: +6.67%
                "primary_metric_name": "seconds",
            },
            {
                "test_name": "passmark",
                "test_timestamp": pd.Timestamp("2025-02-01", tz="UTC"),
                "cloud_provider": "aws",
                "os_vendor": "rhel",
                "instance_type": "m5.24xlarge",
                "status": "PASS",
                "primary_metric_value": 8000.0,  # New benchmark
                "primary_metric_name": "score",
            },
        ]
    )


def test_baseline_config_creation():
    """Test BaselineConfig dataclass creation."""
    config = BaselineConfig(
        baseline_id="test_baseline",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
        benchmark_filter={"cloud_provider": "aws"},
    )
    assert config.baseline_id == "test_baseline"
    assert config.date_range == (datetime(2025, 1, 1), datetime(2025, 1, 31))
    assert config.benchmark_filter == {"cloud_provider": "aws"}


def test_baseline_config_frozen():
    """Test that BaselineConfig is immutable."""
    config = BaselineConfig(
        baseline_id="test",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
    )
    with pytest.raises(AttributeError):
        config.baseline_id = "new_id"


def test_calculate_delta_from_synthetic_data(
    synthetic_baseline_df, synthetic_nightly_df, baseline_config
):
    """Test delta calculation with synthetic baseline and nightly datasets."""
    result = calculate_delta(synthetic_baseline_df, synthetic_nightly_df, baseline_config)

    assert isinstance(result, TrackKpiResult)
    assert result.error is None
    assert len(result.deltas) == 4  # coremark, streams, pyperf, passmark
    assert result.baseline_config == baseline_config


def test_calculate_delta_detects_regression(
    synthetic_baseline_df, synthetic_nightly_df, baseline_config
):
    """Test that delta calculation detects regressions correctly."""
    result = calculate_delta(synthetic_baseline_df, synthetic_nightly_df, baseline_config)

    # Find coremark delta (should be regression: -9.5%)
    coremark_delta = next(d for d in result.deltas if d.benchmark_name == "coremark")
    assert coremark_delta.is_regression is True
    assert coremark_delta.percent_change is not None
    assert coremark_delta.percent_change < -5.0  # Below regression threshold


def test_calculate_delta_handles_added_benchmarks(
    synthetic_baseline_df, synthetic_nightly_df, baseline_config
):
    """Test handling of benchmarks added in nightly."""
    result = calculate_delta(synthetic_baseline_df, synthetic_nightly_df, baseline_config)

    # Find passmark delta (added in nightly)
    passmark_delta = next(d for d in result.deltas if d.benchmark_name == "passmark")
    assert passmark_delta.status == "added"
    assert passmark_delta.baseline_mean is None
    assert passmark_delta.nightly_mean == 8000.0
    assert passmark_delta.percent_change is None
    assert passmark_delta.is_regression is False


def test_calculate_delta_handles_removed_benchmarks(baseline_config):
    """Test handling of benchmarks removed in nightly."""
    baseline_df = pd.DataFrame(
        [
            {
                "test_name": "old_benchmark",
                "test_timestamp": pd.Timestamp("2025-01-15", tz="UTC"),
                "status": "PASS",
                "primary_metric_value": 100.0,
                "primary_metric_name": "score",
            }
        ]
    )
    nightly_df = pd.DataFrame(
        [
            {
                "test_name": "new_benchmark",
                "test_timestamp": pd.Timestamp("2025-02-01", tz="UTC"),
                "status": "PASS",
                "primary_metric_value": 200.0,
                "primary_metric_name": "score",
            }
        ]
    )

    result = calculate_delta(baseline_df, nightly_df, baseline_config)

    # Find old_benchmark delta (removed in nightly)
    old_delta = next(d for d in result.deltas if d.benchmark_name == "old_benchmark")
    assert old_delta.status == "removed"
    assert old_delta.baseline_mean == 100.0
    assert old_delta.nightly_mean is None


def test_calculate_delta_filters_non_pass_status(baseline_config):
    """Test that non-PASS status is filtered out."""
    baseline_df = pd.DataFrame(
        [
            {
                "test_name": "test1",
                "status": "PASS",
                "primary_metric_value": 100.0,
                "primary_metric_name": "score",
            },
            {
                "test_name": "test1",
                "status": "FAIL",
                "primary_metric_value": 50.0,
                "primary_metric_name": "score",
            },
        ]
    )
    nightly_df = pd.DataFrame(
        [
            {
                "test_name": "test1",
                "status": "PASS",
                "primary_metric_value": 95.0,
                "primary_metric_name": "score",
            }
        ]
    )

    result = calculate_delta(baseline_df, nightly_df, baseline_config)

    # Baseline mean should be 100.0 (FAIL excluded), not 75.0
    test1_delta = next(d for d in result.deltas if d.benchmark_name == "test1")
    assert test1_delta.baseline_mean == 100.0


def test_calculate_delta_summary_statistics(
    synthetic_baseline_df, synthetic_nightly_df, baseline_config
):
    """Test that summary statistics are calculated correctly."""
    result = calculate_delta(synthetic_baseline_df, synthetic_nightly_df, baseline_config)

    assert result.summary["total_benchmarks"] == 4
    assert result.summary["added"] == 1  # passmark
    assert result.summary["removed"] == 0
    assert result.summary["changed"] == 3  # coremark, streams, pyperf
    assert result.summary["regressions"] >= 1  # At least coremark


def test_calculate_delta_percentage_and_absolute_change(
    synthetic_baseline_df, synthetic_nightly_df, baseline_config
):
    """Test percentage and absolute change calculations."""
    result = calculate_delta(synthetic_baseline_df, synthetic_nightly_df, baseline_config)

    # Check coremark: baseline mean = 105.0, nightly = 95.0
    coremark_delta = next(d for d in result.deltas if d.benchmark_name == "coremark")
    assert coremark_delta.baseline_mean == pytest.approx(105.0)  # (100 + 110) / 2
    assert coremark_delta.nightly_mean == pytest.approx(95.0)
    assert coremark_delta.absolute_change == pytest.approx(-10.0)
    assert coremark_delta.percent_change == pytest.approx(-9.523809, rel=1e-4)


def test_calculate_delta_handles_zero_baseline(baseline_config):
    """Test handling of zero baseline (should not crash)."""
    baseline_df = pd.DataFrame(
        [
            {
                "test_name": "test1",
                "status": "PASS",
                "primary_metric_value": 0.0,
                "primary_metric_name": "score",
            }
        ]
    )
    nightly_df = pd.DataFrame(
        [
            {
                "test_name": "test1",
                "status": "PASS",
                "primary_metric_value": 100.0,
                "primary_metric_name": "score",
            }
        ]
    )

    result = calculate_delta(baseline_df, nightly_df, baseline_config)

    test1_delta = next(d for d in result.deltas if d.benchmark_name == "test1")
    assert test1_delta.percent_change is None  # Cannot calculate with zero baseline
    assert test1_delta.absolute_change == pytest.approx(100.0)


def test_calculate_delta_lower_is_better_metric(
    synthetic_baseline_df, synthetic_nightly_df, baseline_config
):
    """Test regression detection for lower-is-better metrics (pyperf)."""
    result = calculate_delta(synthetic_baseline_df, synthetic_nightly_df, baseline_config)

    # pyperf is lower-is-better: baseline 1.5s, nightly 1.6s (+6.67%) should be regression
    pyperf_delta = next(d for d in result.deltas if d.benchmark_name == "pyperf")
    assert pyperf_delta.percent_change is not None
    assert pyperf_delta.percent_change > 0  # Positive change for lower-is-better
    assert pyperf_delta.is_regression is True  # Should exceed +5% threshold


def test_calculate_delta_empty_baseline(baseline_config):
    """Test with empty baseline dataset."""
    baseline_df = pd.DataFrame()
    nightly_df = pd.DataFrame(
        [
            {
                "test_name": "test1",
                "status": "PASS",
                "primary_metric_value": 100.0,
                "primary_metric_name": "score",
            }
        ]
    )

    result = calculate_delta(baseline_df, nightly_df, baseline_config)

    assert len(result.deltas) == 1
    assert result.deltas[0].status == "added"


def test_calculate_delta_empty_nightly(baseline_config):
    """Test with empty nightly dataset."""
    baseline_df = pd.DataFrame(
        [
            {
                "test_name": "test1",
                "status": "PASS",
                "primary_metric_value": 100.0,
                "primary_metric_name": "score",
            }
        ]
    )
    nightly_df = pd.DataFrame()

    result = calculate_delta(baseline_df, nightly_df, baseline_config)

    assert len(result.deltas) == 1
    assert result.deltas[0].status == "removed"


def test_calculate_delta_from_dataframes(synthetic_baseline_df, synthetic_nightly_df):
    """Test calculate_delta_from_dataframes wrapper function."""
    result = calculate_delta_from_dataframes(
        synthetic_baseline_df, synthetic_nightly_df, baseline_id="test_baseline"
    )

    assert result.source == "synthetic"
    assert result.baseline_config.baseline_id == "test_baseline"
    assert len(result.deltas) > 0


def test_fetch_baseline_results_with_mock_client(baseline_config):
    """Test fetch_baseline_results with mocked OpenSearch client."""
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "metadata": {
                            "test_timestamp": "2025-01-15T00:00:00Z",
                            "cloud_provider": "aws",
                        },
                        "test": {"name": "coremark"},
                        "results": {
                            "status": "PASS",
                            "primary_metric": {"value": 100.0, "name": "score"},
                        },
                    }
                }
            ]
        }
    }

    df = fetch_baseline_results(mock_client, baseline_config)

    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]["test_name"] == "coremark"
    assert df.iloc[0]["primary_metric_value"] == 100.0
    mock_client.search_results.assert_called_once()


def test_fetch_nightly_results_with_mock_client():
    """Test fetch_nightly_results with mocked OpenSearch client."""
    mock_client = MagicMock()
    mock_client.search_results.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "metadata": {
                            "test_timestamp": "2025-02-01T00:00:00Z",
                            "cloud_provider": "aws",
                        },
                        "test": {"name": "streams"},
                        "results": {
                            "status": "PASS",
                            "primary_metric": {"value": 50000.0, "name": "MB/s"},
                        },
                    }
                }
            ]
        }
    }

    df = fetch_nightly_results(mock_client)

    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]["test_name"] == "streams"
    mock_client.search_results.assert_called_once()


def test_fetch_baseline_results_with_filters(baseline_config):
    """Test fetch_baseline_results applies filters correctly."""
    config_with_filters = BaselineConfig(
        baseline_id="filtered_baseline",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
        benchmark_filter={"cloud_provider": "aws", "test.name": ["coremark", "streams"]},
    )

    mock_client = MagicMock()
    mock_client.search_results.return_value = {"hits": {"hits": []}}

    fetch_baseline_results(mock_client, config_with_filters)

    # Verify filters were applied
    call_args = mock_client.search_results.call_args[0][0]
    assert "bool" in call_args["query"]
    assert len(call_args["query"]["bool"]["must"]) >= 2  # Date range + filters


def test_fetch_baseline_results_handles_exception(baseline_config):
    """Test fetch_baseline_results handles exceptions gracefully."""
    mock_client = MagicMock()
    mock_client.search_results.side_effect = Exception("Connection error")

    df = fetch_baseline_results(mock_client, baseline_config)

    assert df.empty


def test_fetch_nightly_results_handles_exception():
    """Test fetch_nightly_results handles exceptions gracefully."""
    mock_client = MagicMock()
    mock_client.search_results.side_effect = Exception("Connection error")

    df = fetch_nightly_results(mock_client)

    assert df.empty


def test_benchmark_delta_dataclass():
    """Test BenchmarkDelta dataclass creation and immutability."""
    delta = BenchmarkDelta(
        benchmark_name="coremark",
        metric_name="iterations/sec",
        baseline_mean=100.0,
        nightly_mean=95.0,
        percent_change=-5.0,
        absolute_change=-5.0,
        is_regression=True,
        status="changed",
    )

    assert delta.benchmark_name == "coremark"
    assert delta.is_regression is True

    with pytest.raises(AttributeError):
        delta.is_regression = False


def test_track_kpi_result_dataclass(baseline_config):
    """Test TrackKpiResult dataclass creation."""
    result = TrackKpiResult(
        baseline_config=baseline_config,
        nightly_timestamp=datetime(2025, 2, 1),
        deltas=[],
        summary={},
        source="opensearch",
        error=None,
    )

    assert result.baseline_config == baseline_config
    assert result.source == "opensearch"
    assert result.error is None


def test_regression_rate_calculation_no_changed_benchmarks(baseline_config):
    """Test regression rate when no benchmarks changed."""
    baseline_df = pd.DataFrame()
    nightly_df = pd.DataFrame(
        [
            {
                "test_name": "new_test",
                "status": "PASS",
                "primary_metric_value": 100.0,
                "primary_metric_name": "score",
            }
        ]
    )

    result = calculate_delta(baseline_df, nightly_df, baseline_config)

    # All benchmarks are "added", none "changed"
    assert result.summary["regression_rate"] == 0.0


def test_calculate_delta_nightly_timestamp_extracted(
    synthetic_baseline_df, synthetic_nightly_df, baseline_config
):
    """Test that nightly timestamp is extracted correctly."""
    result = calculate_delta(synthetic_baseline_df, synthetic_nightly_df, baseline_config)

    assert result.nightly_timestamp is not None
    assert result.nightly_timestamp == pd.Timestamp("2025-02-01", tz="UTC")
