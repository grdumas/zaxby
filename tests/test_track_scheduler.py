"""
Tests for track scheduler module (RPOPC-1166).

Tests scheduled and on-demand query execution, baseline auto-detection,
result persistence, and execution logging.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.track_kpis import BaselineConfig, BenchmarkDelta, TrackKpiResult
from src.track_scheduler import TrackScheduler, get_scheduler


@pytest.fixture
def mock_client():
    """Create a mock OpenSearch client."""
    client = MagicMock()
    client.search_results = MagicMock()
    return client


@pytest.fixture
def temp_results_dir():
    """Create a temporary directory for test results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def scheduler(mock_client, temp_results_dir):
    """Create a scheduler instance for testing."""
    return TrackScheduler(
        client=mock_client,
        schedule_hour=6,
        schedule_minute=0,
        results_dir=temp_results_dir,
        enabled=False,  # Disable actual scheduling in tests
    )


def test_scheduler_initialization(scheduler, temp_results_dir):
    """Test scheduler initialization."""
    assert scheduler.schedule_hour == 6
    assert scheduler.schedule_minute == 0
    assert scheduler.enabled is False
    assert scheduler.results_dir == Path(temp_results_dir)
    assert scheduler.results_dir.exists()


def test_scheduler_disabled_no_jobs(scheduler):
    """Test that disabled scheduler doesn't add jobs."""
    assert len(scheduler.scheduler.get_jobs()) == 0


def test_scheduler_enabled_adds_job(mock_client, temp_results_dir):
    """Test that enabled scheduler adds cron job."""
    scheduler = TrackScheduler(
        client=mock_client,
        schedule_hour=6,
        schedule_minute=0,
        results_dir=temp_results_dir,
        enabled=True,
    )

    jobs = scheduler.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "track_nightly_comparison"
    assert jobs[0].name == "Daily baseline vs nightly comparison"


def test_auto_detect_baseline_from_env(scheduler):
    """Test baseline auto-detection from environment variables."""
    with patch.dict(
        os.environ,
        {
            "TRACK_BASELINE_ID": "test-baseline",
            "TRACK_BASELINE_START_DATE": "2025-01-01T00:00:00",
            "TRACK_BASELINE_END_DATE": "2025-01-31T23:59:59",
        },
    ):
        config = scheduler._auto_detect_baseline()

        assert config is not None
        assert config.baseline_id == "test-baseline"
        assert config.date_range[0] == datetime(2025, 1, 1)
        assert config.date_range[1] == datetime(2025, 1, 31, 23, 59, 59)


def test_auto_detect_baseline_fallback(scheduler):
    """Test baseline auto-detection fallback to last 7 days."""
    with patch.dict(os.environ, {}, clear=True):
        config = scheduler._auto_detect_baseline()

        assert config is not None
        assert config.baseline_id.startswith("auto-baseline-")
        # Check that date range is approximately last 7 days
        start, end = config.date_range
        assert (end - start).days >= 6  # Allow for some variance


def test_persist_result(scheduler):
    """Test result persistence to disk."""
    # Create a test result
    baseline_config = BaselineConfig(
        baseline_id="test-baseline",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
        benchmark_filter=None,
    )

    deltas = [
        BenchmarkDelta(
            benchmark_name="test.benchmark",
            metric_name="throughput",
            baseline_mean=100.0,
            nightly_mean=90.0,
            percent_change=-10.0,
            absolute_change=-10.0,
            is_regression=True,
            status="changed",
        ),
    ]

    result = TrackKpiResult(
        baseline_config=baseline_config,
        nightly_timestamp=datetime(2025, 2, 1, 6, 0, 0),
        deltas=deltas,
        summary={
            "total_benchmarks": 1,
            "changed": 1,
            "regressions": 1,
        },
        source="opensearch",
        error=None,
    )

    # Persist result
    scheduler._persist_result(result)

    # Verify file was created
    result_files = list(scheduler.results_dir.glob("comparison_*.json"))
    assert len(result_files) == 1

    # Verify content
    with open(result_files[0], "r") as f:
        data = json.load(f)

    assert data["baseline_id"] == "test-baseline"
    assert len(data["deltas"]) == 1
    assert data["deltas"][0]["is_regression"] is True
    assert data["summary"]["regressions"] == 1


def test_log_execution(scheduler):
    """Test execution logging."""
    baseline_config = BaselineConfig(
        baseline_id="test-baseline",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
        benchmark_filter=None,
    )

    result = TrackKpiResult(
        baseline_config=baseline_config,
        nightly_timestamp=datetime(2025, 2, 1, 6, 0, 0),
        deltas=[],
        summary={
            "total_benchmarks": 10,
            "changed": 3,
            "regressions": 1,
        },
        source="opensearch",
        error=None,
    )

    # Log execution
    scheduler._log_execution(result, on_demand=False)

    # Verify log file was created
    log_file = scheduler.results_dir / "execution_log.jsonl"
    assert log_file.exists()

    # Verify log content
    with open(log_file, "r") as f:
        lines = f.readlines()

    assert len(lines) == 1
    log_entry = json.loads(lines[0])

    assert log_entry["execution_type"] == "scheduled"
    assert log_entry["baseline_id"] == "test-baseline"
    assert log_entry["regressions"] == 1
    assert log_entry["total_benchmarks"] == 10


def test_log_execution_on_demand(scheduler):
    """Test on-demand execution logging."""
    baseline_config = BaselineConfig(
        baseline_id="test-baseline",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
        benchmark_filter=None,
    )

    result = TrackKpiResult(
        baseline_config=baseline_config,
        nightly_timestamp=datetime(2025, 2, 1, 6, 0, 0),
        deltas=[],
        summary={},
        source="opensearch",
        error=None,
    )

    scheduler._log_execution(result, on_demand=True)

    log_file = scheduler.results_dir / "execution_log.jsonl"
    with open(log_file, "r") as f:
        log_entry = json.loads(f.readline())

    assert log_entry["execution_type"] == "on-demand"


def test_get_latest_result(scheduler):
    """Test retrieving latest result."""
    # Create multiple results
    for i in range(3):
        baseline_config = BaselineConfig(
            baseline_id=f"baseline-{i}",
            date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
            benchmark_filter=None,
        )

        result = TrackKpiResult(
            baseline_config=baseline_config,
            nightly_timestamp=datetime(2025, 2, 1 + i, 6, 0, 0),
            deltas=[],
            summary={"index": i},
            source="opensearch",
            error=None,
        )

        scheduler._persist_result(result)

    # Get latest result
    latest = scheduler.get_latest_result()

    assert latest is not None
    assert latest["summary"]["index"] == 2  # Last one created


def test_get_latest_result_no_results(scheduler):
    """Test retrieving latest result when none exist."""
    latest = scheduler.get_latest_result()
    assert latest is None


def test_on_demand_comparison_error_handling(scheduler, mock_client):
    """Test on-demand comparison error handling."""
    # Make client raise an exception
    mock_client.search_results.side_effect = Exception("OpenSearch unavailable")

    baseline_config = BaselineConfig(
        baseline_id="test-baseline",
        date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
        benchmark_filter=None,
    )

    result = scheduler.run_on_demand_comparison(baseline_config)

    assert result.error is not None
    # Error should contain both the stage context and root cause
    assert "Failed to fetch baseline results" in result.error
    assert "OpenSearch unavailable" in result.error
    assert "test-baseline" in result.error
    assert len(result.deltas) == 0


@patch.dict(
    os.environ,
    {
        "TRACK_SCHEDULER_ENABLED": "true",
        "TRACK_SCHEDULER_HOUR": "8",
        "TRACK_SCHEDULER_MINUTE": "30",
    },
)
def test_get_scheduler_singleton(mock_client):
    """Test scheduler singleton with environment configuration."""
    # Clear any existing instance
    import src.track_scheduler

    src.track_scheduler._scheduler_instance = None

    scheduler1 = get_scheduler(mock_client)
    scheduler2 = get_scheduler(mock_client)

    assert scheduler1 is scheduler2
    assert scheduler1.schedule_hour == 8
    assert scheduler1.schedule_minute == 30
    assert scheduler1.enabled is True


@patch.dict(os.environ, {"TRACK_SCHEDULER_ENABLED": "false"})
def test_get_scheduler_disabled(mock_client):
    """Test scheduler creation when disabled."""
    import src.track_scheduler

    src.track_scheduler._scheduler_instance = None

    scheduler = get_scheduler(mock_client)

    assert scheduler.enabled is False


def test_scheduler_start_stop(scheduler):
    """Test scheduler start and stop."""
    assert not scheduler.scheduler.running

    scheduler.start()
    # Scheduler is disabled in fixture, so it shouldn't actually start
    assert not scheduler.scheduler.running

    # Test with enabled scheduler
    scheduler.enabled = True
    scheduler.start()
    assert scheduler.scheduler.running

    scheduler.stop()
    assert not scheduler.scheduler.running


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
