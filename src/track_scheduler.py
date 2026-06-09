"""
Scheduler for automated baseline vs nightly comparisons (RPOPC-1166).

Provides scheduled execution of Track mode queries with configurable timing,
baseline auto-detection, and result persistence.
"""

import json
import logging
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.track_kpis import (
    BaselineConfig,
    TrackKpiResult,
    calculate_delta,
    fetch_baseline_results,
    fetch_nightly_results,
)

logger = logging.getLogger(__name__)


class TrackScheduler:
    """
    Background scheduler for automated baseline vs nightly comparisons.

    Executes queries on a configurable schedule (default: daily at 6 AM local),
    auto-detects baselines, and persists results for quick retrieval.
    """

    def __init__(
        self,
        client: Any,
        schedule_hour: int = 6,
        schedule_minute: int = 0,
        results_dir: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize the scheduler.

        Args:
            client: OpenSearch client (BenchmarkDataSource)
            schedule_hour: Hour to run daily comparison (0-23, default: 6 AM)
            schedule_minute: Minute to run comparison (0-59, default: 0)
            results_dir: Directory to store query results (default: ./track_results)
            enabled: Whether scheduler is enabled (default: True)
        """
        self.client = client
        self.schedule_hour = schedule_hour
        self.schedule_minute = schedule_minute
        self.enabled = enabled

        # Set up results directory
        if results_dir is None:
            results_dir = os.path.join(os.getcwd(), "track_results")
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self._setup_schedule()

    def _setup_schedule(self):
        """Configure the scheduler with cron trigger."""
        if not self.enabled:
            logger.info("Track scheduler is disabled")
            return

        # Create cron trigger for daily execution
        trigger = CronTrigger(
            hour=self.schedule_hour,
            minute=self.schedule_minute,
        )

        # Add job to scheduler
        self.scheduler.add_job(
            self.run_scheduled_comparison,
            trigger,
            id="track_nightly_comparison",
            name="Daily baseline vs nightly comparison",
            replace_existing=True,
        )

        logger.info(
            f"Track scheduler configured to run daily at {self.schedule_hour:02d}:{self.schedule_minute:02d}"
        )

    def start(self):
        """Start the background scheduler."""
        if not self.enabled:
            logger.info("Track scheduler is disabled, not starting")
            return

        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Track scheduler started")

    def stop(self):
        """Stop the background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Track scheduler stopped")

    def run_scheduled_comparison(self):
        """
        Execute scheduled baseline vs nightly comparison.

        This is the main scheduled job that:
        1. Auto-detects the baseline configuration
        2. Fetches baseline and nightly results
        3. Calculates deltas
        4. Persists results
        5. Logs execution metadata
        """
        logger.info("Starting scheduled baseline vs nightly comparison")

        try:
            # Auto-detect baseline configuration
            baseline_config = self._auto_detect_baseline()
            if baseline_config is None:
                logger.error("Failed to auto-detect baseline configuration")
                return

            # Fetch data
            logger.info(
                f"Fetching baseline data for baseline_id={baseline_config.baseline_id}"
            )
            baseline_df = fetch_baseline_results(self.client, baseline_config)

            logger.info("Fetching nightly results")
            nightly_df = fetch_nightly_results(self.client)

            if baseline_df.empty:
                logger.warning("Baseline dataset is empty, skipping comparison")
                return

            if nightly_df.empty:
                logger.warning("Nightly dataset is empty, skipping comparison")
                return

            # Calculate deltas
            logger.info("Calculating deltas")
            result = calculate_delta(baseline_df, nightly_df, baseline_config)

            # Persist results
            self._persist_result(result)

            # Log execution
            self._log_execution(result)

            logger.info(
                f"Scheduled comparison completed: {result.summary.get('regressions', 0)} regressions found"
            )

        except Exception as exc:
            logger.error(f"Scheduled comparison failed: {exc}", exc_info=True)

    def run_on_demand_comparison(
        self,
        baseline_config: BaselineConfig,
    ) -> TrackKpiResult:
        """
        Execute on-demand baseline vs nightly comparison.

        Args:
            baseline_config: Configuration specifying which baseline to use

        Returns:
            TrackKpiResult with deltas and summary
        """
        logger.info(
            f"Starting on-demand comparison with baseline_id={baseline_config.baseline_id}"
        )

        try:
            # Fetch data
            baseline_df = fetch_baseline_results(self.client, baseline_config)
            nightly_df = fetch_nightly_results(
                self.client, baseline_config.benchmark_filter
            )

            # Calculate deltas
            result = calculate_delta(baseline_df, nightly_df, baseline_config)

            # Persist results
            self._persist_result(result)

            # Log execution
            self._log_execution(result, on_demand=True)

            logger.info(
                f"On-demand comparison completed: {result.summary.get('regressions', 0)} regressions found"
            )

            return result

        except Exception as exc:
            logger.error(f"On-demand comparison failed: {exc}", exc_info=True)
            return TrackKpiResult(
                baseline_config=baseline_config,
                nightly_timestamp=None,
                deltas=[],
                summary={},
                source="opensearch",
                error=str(exc),
            )

    def _auto_detect_baseline(self) -> Optional[BaselineConfig]:
        """
        Auto-detect baseline configuration.

        Uses environment variable or recent stable release as baseline.

        Returns:
            BaselineConfig or None if detection fails
        """
        # Check for explicit baseline configuration in environment
        baseline_id = os.getenv("TRACK_BASELINE_ID")
        baseline_start = os.getenv("TRACK_BASELINE_START_DATE")
        baseline_end = os.getenv("TRACK_BASELINE_END_DATE")

        if baseline_id and baseline_start and baseline_end:
            try:
                start_date = datetime.fromisoformat(baseline_start)
                end_date = datetime.fromisoformat(baseline_end)

                logger.info(
                    f"Using configured baseline: {baseline_id} ({start_date} to {end_date})"
                )

                return BaselineConfig(
                    baseline_id=baseline_id,
                    date_range=(start_date, end_date),
                    benchmark_filter=None,
                )
            except ValueError as exc:
                logger.error(f"Invalid baseline date format: {exc}")

        # Fallback: use last 7 days as baseline
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        baseline_id = f"auto-baseline-{start_date.strftime('%Y%m%d')}"

        logger.info(
            f"Auto-detected baseline: {baseline_id} ({start_date} to {end_date})"
        )

        return BaselineConfig(
            baseline_id=baseline_id,
            date_range=(start_date, end_date),
            benchmark_filter=None,
        )

    def _persist_result(self, result: TrackKpiResult):
        """
        Persist comparison result to disk.

        Args:
            result: TrackKpiResult to persist
        """
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            baseline_id = result.baseline_config.baseline_id.replace("/", "_")
            filename = f"comparison_{baseline_id}_{timestamp}.json"
            filepath = self.results_dir / filename

            # Serialize result to JSON
            data = {
                "baseline_id": result.baseline_config.baseline_id,
                "baseline_date_range": [
                    result.baseline_config.date_range[0].isoformat(),
                    result.baseline_config.date_range[1].isoformat(),
                ],
                "nightly_timestamp": (
                    result.nightly_timestamp.isoformat()
                    if result.nightly_timestamp
                    else None
                ),
                "summary": result.summary,
                "deltas": [
                    {
                        "benchmark_name": d.benchmark_name,
                        "metric_name": d.metric_name,
                        "baseline_mean": d.baseline_mean,
                        "nightly_mean": d.nightly_mean,
                        "percent_change": d.percent_change,
                        "absolute_change": d.absolute_change,
                        "is_regression": d.is_regression,
                        "status": d.status,
                    }
                    for d in result.deltas
                ],
                "source": result.source,
                "error": result.error,
                "timestamp": timestamp,
            }

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Persisted comparison result to {filepath}")

        except Exception as exc:
            logger.error(f"Failed to persist result: {exc}")

    def _log_execution(self, result: TrackKpiResult, on_demand: bool = False):
        """
        Log query execution metadata.

        Args:
            result: TrackKpiResult from execution
            on_demand: Whether this was an on-demand execution
        """
        execution_type = "on-demand" if on_demand else "scheduled"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "execution_type": execution_type,
            "baseline_id": result.baseline_config.baseline_id,
            "baseline_date_range": [
                result.baseline_config.date_range[0].isoformat(),
                result.baseline_config.date_range[1].isoformat(),
            ],
            "nightly_timestamp": (
                result.nightly_timestamp.isoformat() if result.nightly_timestamp else None
            ),
            "total_benchmarks": result.summary.get("total_benchmarks", 0),
            "regressions": result.summary.get("regressions", 0),
            "changed": result.summary.get("changed", 0),
            "added": result.summary.get("added", 0),
            "removed": result.summary.get("removed", 0),
            "source": result.source,
            "error": result.error,
        }

        logger.info(
            f"Query execution [{execution_type}]: "
            f"baseline_id={log_entry['baseline_id']}, "
            f"regressions={log_entry['regressions']}/{log_entry['changed']} changed, "
            f"total={log_entry['total_benchmarks']}"
        )

        # Also persist to execution log file
        log_file = self.results_dir / "execution_log.jsonl"
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as exc:
            logger.error(f"Failed to write execution log: {exc}")

    def get_latest_result(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent comparison result.

        Returns:
            Dictionary with result data or None if no results exist
        """
        try:
            # Find most recent result file
            result_files = sorted(
                self.results_dir.glob("comparison_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if not result_files:
                return None

            # Load most recent result
            with open(result_files[0], "r") as f:
                return json.load(f)

        except Exception as exc:
            logger.error(f"Failed to retrieve latest result: {exc}")
            return None


# Global scheduler instance
_scheduler_instance: Optional[TrackScheduler] = None


def get_scheduler(client: Any) -> TrackScheduler:
    """
    Get or create the global scheduler instance.

    Args:
        client: OpenSearch client

    Returns:
        TrackScheduler singleton instance
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        # Read configuration from environment
        enabled = os.getenv("TRACK_SCHEDULER_ENABLED", "true").lower() == "true"
        schedule_hour = int(os.getenv("TRACK_SCHEDULER_HOUR", "6"))
        schedule_minute = int(os.getenv("TRACK_SCHEDULER_MINUTE", "0"))
        results_dir = os.getenv("TRACK_RESULTS_DIR")

        _scheduler_instance = TrackScheduler(
            client=client,
            schedule_hour=schedule_hour,
            schedule_minute=schedule_minute,
            results_dir=results_dir,
            enabled=enabled,
        )

    return _scheduler_instance
