"""
Locust load test for Track Mode (Baseline vs Nightly Comparison).

Simulates 2 concurrent CPT release owner users running baseline vs nightly
comparisons with varying date ranges and baseline configurations.

Prerequisites:
1. Start the app in synthetic mode:
   DATA_MODE=synthetic python app.py

Usage:
  Single-mode headless (2 users, 1/s spawn rate, 60s):
    locust -f tests/performance/locustfile_track.py --headless -u 2 -r 1 -t 60s --host http://localhost:8050

  Combined with other modes (Pulse + Investigate + Track = 17 users):
    locust -f tests/performance/test_pulse_load.py,tests/performance/locustfile_investigate.py,tests/performance/locustfile_track.py \
      --headless -u 17 -r 3 -t 120s --host http://localhost:8050

  Web UI mode:
    locust -f tests/performance/locustfile_track.py --host http://localhost:8050
    # Then open http://localhost:8089

  Reproducible runs (seeded random date selection):
    LOCUST_SEED=42 locust -f tests/performance/locustfile_track.py --headless -u 2 -r 1 -t 60s --host http://localhost:8050

Performance SLA Thresholds (p95):
  - Page load: < 500ms
  - Navigation: < 500ms
  - Track comparison: < 5000ms (heavy aggregation operation)

Optimization Recommendations:
1. **Pre-validate date inputs once**: The run_track_comparison callback (app.py:3159) parses
   ISO date strings on every call using datetime.fromisoformat. Under concurrent load, this
   parsing overhead adds up. Recommend parsing and validating inputs once at the callback
   entry point and caching the datetime objects.

2. **Pre-computed DataFrame indices**: In synthetic mode, the baseline and nightly DataFrames
   are filtered twice using boolean indexing (app.py:3236-3247). For large datasets (10k+ rows),
   recommend maintaining pre-computed indices or partitioned DataFrames keyed by date range
   to speed up filtering.

3. **Incremental baseline updates**: The current design fetches the full baseline dataset on
   every comparison. For frequently-used baselines (e.g., "rhel-9.5-baseline"), consider
   caching the baseline aggregates and only re-fetching if the baseline filter changes.

4. **Async aggregation for OpenSearch**: The fetch_baseline_comparison_aggregates function
   (query_service.py) runs baseline and nightly queries sequentially. These could be
   parallelized using asyncio or ThreadPoolExecutor to reduce total latency.

Note on TrackScheduler:
  The TrackScheduler background service (src/track_scheduler.py) runs as an APScheduler job
  within the app process. It cannot be triggered via HTTP endpoints. The load tests cover the
  user-facing btn-run-track-comparison callback, which exercises the same underlying data
  pipeline (fetch_baseline_comparison_aggregates / aggregate_baseline_comparison_from_dataframe).

  To benchmark the scheduler's run_scheduled_comparison method directly, use the existing
  pytest-benchmark pattern from test_data_processing_benchmark.py.
"""

from __future__ import annotations

import os
import random
from locust import HttpUser, task, between, events

from tests.performance.locust_helpers import _dash_payload


class TrackUser(HttpUser):
    """
    Simulated CPT release owner running baseline vs nightly comparisons.

    Interaction pattern:
    - Slow, deliberate actions (5-15s think time between operations)
    - Long-running comparison queries
    - Infrequent but high-value operations

    Task weights reflect CPT workflow:
    - run_comparison (5): Primary operation — baseline vs nightly comparison
    - run_comparison_varied (3): Testing different date ranges
    - load_page (1): Initial visit
    - navigate_to_track (1): Switching to Track mode
    - navigate_back (1): Returning to overview
    """

    fixed_count = 2  # Ticket spec: 2 concurrent Track users
    wait_time = between(5, 15)  # CPT operations are infrequent, deliberate

    def on_start(self):
        """
        Initialize session by loading the main page and navigating to Track mode.

        Seeds per-user RNG for reproducible date range selection.
        """
        # Support optional seeding via LOCUST_SEED environment variable
        seed_str = os.environ.get("LOCUST_SEED")
        if seed_str:
            try:
                seed = int(seed_str)
                self.rng = random.Random(seed)
            except ValueError:
                raise ValueError(f"LOCUST_SEED must be an integer, got: {seed_str}")
        else:
            self.rng = random.Random(42)  # Default seed for reproducibility

        # Load main page
        response = self.client.get("/", name="Page Load")
        if response.status_code != 200:
            raise Exception(
                f"App not reachable. "
                f"Ensure app is running with: DATA_MODE=synthetic python app.py "
                f"and --host flag is set (e.g., --host http://localhost:8050)"
            )

        # Precomputed date range sets matching synthetic data timeframe
        # Each set is (baseline_start, baseline_end, nightly_start, nightly_end)
        # Dates are timezone-aware ISO format (YYYY-MM-DDTHH:MM:SSZ) for compatibility
        # with run_track_comparison callback (app.py:3234-3243)
        self.date_range_presets = [
            ("2026-01-01T00:00:00Z", "2026-03-31T23:59:59Z", "2026-06-01T00:00:00Z", "2026-06-30T23:59:59Z"),  # Q1 baseline vs Q2 nightly
            ("2026-02-01T00:00:00Z", "2026-04-30T23:59:59Z", "2026-07-01T00:00:00Z", "2026-07-31T23:59:59Z"),  # Feb-Apr baseline vs July nightly
            ("2026-03-01T00:00:00Z", "2026-05-31T23:59:59Z", "2026-08-01T00:00:00Z", "2026-08-31T23:59:59Z"),  # Mar-May baseline vs Aug nightly
        ]

        self.baseline_ids = [
            "rhel-9.5-baseline",
            "rhel-10.0-baseline",
            "manual-baseline",
        ]

        # Navigate to Track mode (must be done before comparison tasks)
        # Triggers handle_navigation callback (app.py:2635), which sets
        # navigation-state to Track view and invalidates Pulse cache
        nav_payload = _dash_payload(
            output="navigation-state.data",
            outputs={"id": "navigation-state", "property": "data"},
            inputs=[
                {"id": "q1-major-graph", "property": "clickData", "value": None},
                {"id": "q1-rhel9-graph", "property": "clickData", "value": None},
                {"id": "q1-rhel10-graph", "property": "clickData", "value": None},
                {"id": "btn-view-benchmarks", "property": "n_clicks", "value": None},
                {"id": "btn-view-comparisons", "property": "n_clicks", "value": None},
                {"id": "btn-view-table", "property": "n_clicks", "value": None},
                {"id": "btn-track-mode", "property": "n_clicks", "value": 1},
            ],
            state=[
                {"id": "navigation-state", "property": "data", "value": {"view": "overview", "investigation_params": None}},
                {"id": "analysis-results-store", "property": "data", "value": None},
            ],
            changed=["btn-track-mode.n_clicks"],
        )

        nav_response = self.client.post(
            "/_dash-update-component",
            json=nav_payload,
            name="Navigate to Track",
            headers={"Content-Type": "application/json"},
        )

        if nav_response.status_code != 200:
            raise Exception(
                f"Failed to navigate to Track mode. "
                f"Check that app is running and Track mode is accessible."
            )

        self.in_track_mode = True

    @task(2)
    def load_page(self):
        """Load main page (GET /)."""
        self.client.get("/", name="Page Load")

    @task(5)
    def run_comparison(self):
        """
        Run baseline vs nightly comparison with first date range preset.

        Triggers run_track_comparison callback (app.py:3159), which:
        - Validates date inputs
        - In OpenSearch mode: fetches baseline and nightly data via client queries
        - In synthetic mode: filters DataFrame by date ranges
        - Calculates deltas (regressions, improvements, missing, added)
        - Renders summary metrics and exception table

        This is the heaviest Track operation, exercising:
        - Date range filtering
        - Baseline selection
        - Exception table loading
        """
        # Guard: only run if in Track mode
        if not self.in_track_mode:
            return

        # Use first preset
        baseline_start, baseline_end, nightly_start, nightly_end = self.date_range_presets[0]
        baseline_id = self.baseline_ids[0]

        payload = _dash_payload(
            output="..track-summary-metrics.children..track-exception-table.children..",
            outputs=[
                {"id": "track-summary-metrics", "property": "children"},
                {"id": "track-exception-table", "property": "children"},
            ],
            inputs=[
                {"id": "btn-run-track-comparison", "property": "n_clicks", "value": 1},
            ],
            state=[
                {"id": "track-baseline-date-range", "property": "start_date", "value": baseline_start},
                {"id": "track-baseline-date-range", "property": "end_date", "value": baseline_end},
                {"id": "track-baseline-id", "property": "value", "value": baseline_id},
                {"id": "track-nightly-date-range", "property": "start_date", "value": nightly_start},
                {"id": "track-nightly-date-range", "property": "end_date", "value": nightly_end},
            ],
            changed=["btn-run-track-comparison.n_clicks"],
        )

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Run Track Comparison",
            headers={"Content-Type": "application/json"},
        )

    @task(3)
    def run_comparison_varied(self):
        """
        Run baseline vs nightly comparison with randomized date ranges.

        Tests varying data volumes by using different date range presets and
        baseline IDs. This exercises the comparison logic with different
        dataset sizes and overlap patterns.
        """
        # Guard: only run if in Track mode
        if not self.in_track_mode:
            return

        # Randomly select date range preset and baseline ID
        baseline_start, baseline_end, nightly_start, nightly_end = self.rng.choice(self.date_range_presets)
        baseline_id = self.rng.choice(self.baseline_ids)

        payload = _dash_payload(
            output="..track-summary-metrics.children..track-exception-table.children..",
            outputs=[
                {"id": "track-summary-metrics", "property": "children"},
                {"id": "track-exception-table", "property": "children"},
            ],
            inputs=[
                {"id": "btn-run-track-comparison", "property": "n_clicks", "value": 1},
            ],
            state=[
                {"id": "track-baseline-date-range", "property": "start_date", "value": baseline_start},
                {"id": "track-baseline-date-range", "property": "end_date", "value": baseline_end},
                {"id": "track-baseline-id", "property": "value", "value": baseline_id},
                {"id": "track-nightly-date-range", "property": "start_date", "value": nightly_start},
                {"id": "track-nightly-date-range", "property": "end_date", "value": nightly_end},
            ],
            changed=["btn-run-track-comparison.n_clicks"],
        )

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Run Track Comparison (Varied)",
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def navigate_back(self):
        """
        Navigate back to overview from Track mode.

        Triggers handle_back_to_overview callback (app.py:2714), which resets
        navigation-state to overview and invalidates Track cache.
        """
        payload = _dash_payload(
            output="navigation-state.data",
            outputs={"id": "navigation-state", "property": "data"},
            inputs=[
                {"id": "btn-back-to-overview", "property": "n_clicks", "value": None},
                {"id": "btn-back-to-overview-track", "property": "n_clicks", "value": 1},
            ],
            changed=["btn-back-to-overview-track.n_clicks"],
        )

        response = self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Navigate Back from Track",
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            self.in_track_mode = False


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print summary statistics after the test completes.

    Includes per-task percentile breakdown and bottleneck analysis.
    """
    print("\n" + "=" * 80)
    print("TRACK MODE LOAD TEST SUMMARY")
    print("=" * 80)
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {environment.stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {environment.stats.total.total_rps:.2f}")

    if environment.stats.total.num_requests > 0:
        print(f"\nOverall Percentiles:")
        print(f"  50th percentile: {environment.stats.total.get_response_time_percentile(0.50):.2f}ms")
        print(f"  95th percentile: {environment.stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"  99th percentile: {environment.stats.total.get_response_time_percentile(0.99):.2f}ms")

        print(f"\nPer-Task Percentiles:")
        for entry in environment.stats.entries.values():
            if entry.num_requests > 0:
                p50 = entry.get_response_time_percentile(0.50)
                p95 = entry.get_response_time_percentile(0.95)
                p99 = entry.get_response_time_percentile(0.99)
                print(f"  {entry.name}:")
                print(f"    Requests: {entry.num_requests}, Failures: {entry.num_failures}")
                print(f"    p50={p50:.0f}ms, p95={p95:.0f}ms, p99={p99:.0f}ms")

        # Bottleneck analysis
        print(f"\nBOTTLENECK ANALYSIS (p95 vs SLA thresholds):")
        thresholds = {
            "Page Load": 500,
            "Navigate to Track": 500,
            "Run Track Comparison": 5000,
            "Run Track Comparison (Varied)": 5000,
            "Navigate Back from Track": 500,
        }

        violations = []
        for entry in environment.stats.entries.values():
            if entry.num_requests > 0 and entry.name in thresholds:
                p95 = entry.get_response_time_percentile(0.95)
                threshold = thresholds[entry.name]
                status = "✓ PASS" if p95 < threshold else "✗ VIOLATION"
                print(f"  {entry.name}: p95={p95:.0f}ms (threshold: {threshold}ms) {status}")
                if p95 >= threshold:
                    violations.append((entry.name, p95, threshold))

        if violations:
            print(f"\nPerformance violations detected:")
            for task, p95, threshold in violations:
                print(f"  - {task}: {p95:.0f}ms exceeds {threshold}ms by {p95 - threshold:.0f}ms")
        else:
            print(f"\nAll tasks within SLA thresholds.")

    print("=" * 80 + "\n")
