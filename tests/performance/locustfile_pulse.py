"""
Locust load test for Pulse Mode (Executive KPI Panel).

Simulates 10 concurrent executive users viewing the Pulse KPI dashboard with
realistic interaction patterns: initial page load, KPI fetch, filter changes,
cache hit/miss scenarios, and colorblind mode toggling.

Prerequisites:
1. Start the app in synthetic mode:
   DATA_MODE=synthetic python app.py

Usage:
  Single-mode headless (10 users, 2/s spawn rate, 60s):
    locust -f tests/performance/locustfile_pulse.py --headless -u 10 -r 2 -t 60s --host http://localhost:8050

  Combined with other modes (Pulse + Investigate + Track = 17 users):
    locust -f tests/performance/locustfile_pulse.py,tests/performance/locustfile_investigate.py,tests/performance/locustfile_track.py \
      --headless -u 17 -r 3 -t 120s --host http://localhost:8050

  Web UI mode:
    locust -f tests/performance/locustfile_pulse.py --host http://localhost:8050
    # Then open http://localhost:8089

  Reproducible runs (seeded random filter selection):
    LOCUST_SEED=42 locust -f tests/performance/locustfile_pulse.py --headless -u 10 -r 2 -t 60s --host http://localhost:8050

Performance SLA Thresholds (p95):
  - Page load: < 500ms
  - Pulse KPI fetch: < 2000ms
  - Filter update: < 1000ms
  - Render operations: < 500ms

Optimization Recommendations:
1. **Parallelize OpenSearch aggregations**: The fetch_server_snapshot callback (app.py:1166)
   runs 4 OpenSearch aggregations sequentially. Recommend using asyncio.gather() or
   ThreadPoolExecutor to run them in parallel, potentially reducing fetch time by 50-75%.

2. **Memoize KPI panel rendering**: The render_server_snapshot callback (app.py:1201) re-renders
   the full KPI panel on every pulse-kpi-bundle-store update, including colorblind toggles.
   Recommend memoizing the rendered component keyed by (bundle_hash, colorblind_mode) to skip
   render when data hasn't changed.

3. **Server-side ETag caching**: The Pulse KPI bundle is serialized to a dcc.Store as JSON (~50KB).
   For large bundles, consider server-side caching with content hash-based ETags to skip
   re-serialization and re-transmission when data is unchanged.
"""

from __future__ import annotations

import os
import random
from locust import HttpUser, task, between, events

from tests.performance.locust_helpers import _dash_payload


class PulseUser(HttpUser):
    """
    Simulated executive user viewing Pulse KPI panel.

    Interaction pattern:
    - Low frequency visits (2-8s think time between actions)
    - Primary focus on KPI viewing and refresh
    - Occasional filter changes to adjust date range or cloud provider
    - Colorblind mode toggling for accessibility

    Task weights reflect realistic executive usage:
    - render_pulse_panel (4): Most common — triggered by any store update
    - fetch_pulse_kpis (3): Auto-refresh and manual refresh clicks
    - refresh_kpis (2): Manual refresh after filter changes
    - change_filters (2): Adjusting date/cloud filters
    - toggle_colorblind (1): Accessibility toggle
    - load_page (1): Initial visit
    """

    fixed_count = 10  # Ticket spec: 10 concurrent Pulse users
    wait_time = between(2, 8)  # Executives browse slowly

    def on_start(self):
        """
        Initialize session by loading the main page and priming the cache.

        Validates connectivity and seeds per-user RNG for reproducible filter selection.
        Performs initial KPI fetch to populate cache for subsequent render tasks.
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

        # Prime cache with initial KPI fetch
        payload = _dash_payload(
            output="pulse-kpi-bundle-store.data",
            outputs={"id": "pulse-kpi-bundle-store", "property": "data"},
            inputs=[
                {"id": "server-snapshot-init", "property": "n_intervals", "value": 1},
                {"id": "btn-refresh-server-snapshot", "property": "n_clicks", "value": None},
            ],
            changed=["server-snapshot-init.n_intervals"],
        )

        prime_response = self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Prime Cache",
            headers={"Content-Type": "application/json"},
        )

        # Store cached bundle for render tasks
        self.cached_bundle = None
        if prime_response.status_code == 200:
            try:
                result = prime_response.json()
                if "response" in result and "pulse-kpi-bundle-store" in result["response"]:
                    self.cached_bundle = result["response"]["pulse-kpi-bundle-store"]["data"]
            except Exception:
                pass

    @task(1)
    def load_page(self):
        """
        Load main page (GET /).

        Simulates page refresh or return to dashboard.
        """
        self.client.get("/", name="Page Load")

    @task(3)
    def fetch_pulse_kpis(self):
        """
        Fetch Pulse KPI bundle via interval trigger (cache hit scenario).

        Triggers fetch_server_snapshot callback (app.py:1166), which runs 4 OpenSearch
        aggregations (or DataFrame aggregations in synthetic mode):
        - overview: total runs, reporting window
        - category_mix: benchmark category distribution
        - activity_timeline: monthly run counts
        - scope: data source metadata

        This is the most expensive server-side operation on page load.
        """
        payload = _dash_payload(
            output="pulse-kpi-bundle-store.data",
            outputs={"id": "pulse-kpi-bundle-store", "property": "data"},
            inputs=[
                {"id": "server-snapshot-init", "property": "n_intervals", "value": 1},
                {"id": "btn-refresh-server-snapshot", "property": "n_clicks", "value": None},
            ],
            changed=["server-snapshot-init.n_intervals"],
        )

        response = self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Fetch Pulse KPIs",
            headers={"Content-Type": "application/json"},
        )

        # Update cached bundle for render tasks
        if response.status_code == 200:
            try:
                result = response.json()
                if "response" in result and "pulse-kpi-bundle-store" in result["response"]:
                    self.cached_bundle = result["response"]["pulse-kpi-bundle-store"]["data"]
            except Exception:
                pass

    @task(4)
    def render_pulse_panel(self):
        """
        Render Pulse KPI panel from cached bundle (render-only operation).

        Triggers render_server_snapshot callback (app.py:1201), which deserializes
        the bundle and builds the KPI panel layout with charts and metrics.

        This is triggered most frequently because any pulse-kpi-bundle-store update
        or colorblind-mode-store change will re-render the panel.
        """
        if not self.cached_bundle:
            # If cache not primed yet, skip render
            return

        payload = _dash_payload(
            output="server-snapshot-content.children",
            outputs={"id": "server-snapshot-content", "property": "children"},
            inputs=[
                {"id": "pulse-kpi-bundle-store", "property": "data", "value": self.cached_bundle},
                {"id": "colorblind-mode-store", "property": "data", "value": False},
            ],
            changed=["pulse-kpi-bundle-store.data"],
        )

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Render Pulse Panel",
            headers={"Content-Type": "application/json"},
        )

    @task(2)
    def change_filters(self):
        """
        Update filters to trigger cache invalidation (cache miss scenario).

        Triggers update_filtered_data callback (app.py:1503), which filters the
        DataFrame and clears the cache service. This simulates an executive
        changing date range or cloud provider filters.

        Subsequent fetch_pulse_kpis or refresh_kpis will be cache misses.
        """
        # Randomly choose filter to change
        filter_choice = self.rng.choice(["cloud_provider", "date_range"])

        if filter_choice == "cloud_provider":
            filter_value = self.rng.choice([["aws"], ["gcp"], ["azure"], []])
            component_id = "cloud-provider"

            payload = _dash_payload(
                output="filtered-data-store.data",
                outputs={"id": "filtered-data-store", "property": "data"},
                inputs=[
                    {"id": "filter-os-version", "property": "value", "value": []},
                    {"id": "filter-instance-type", "property": "value", "value": []},
                    {"id": "filter-test-name", "property": "value", "value": []},
                    {"id": "filter-cloud-provider", "property": "value", "value": filter_value},
                    {"id": "header-date-range", "property": "start_date", "value": None},
                    {"id": "header-date-range", "property": "end_date", "value": None},
                    {"id": "filter-status", "property": "value", "value": []},
                ],
                changed=[f"filter-{component_id}.value"],
            )
        else:  # date_range
            # Set a random 30-day date range in 2025
            start_dates = ["2025-01-01", "2025-03-01", "2025-06-01"]
            end_dates = ["2025-01-31", "2025-03-31", "2025-06-30"]
            idx = self.rng.randint(0, len(start_dates) - 1)

            payload = _dash_payload(
                output="filtered-data-store.data",
                outputs={"id": "filtered-data-store", "property": "data"},
                inputs=[
                    {"id": "filter-os-version", "property": "value", "value": []},
                    {"id": "filter-instance-type", "property": "value", "value": []},
                    {"id": "filter-test-name", "property": "value", "value": []},
                    {"id": "filter-cloud-provider", "property": "value", "value": []},
                    {"id": "header-date-range", "property": "start_date", "value": start_dates[idx]},
                    {"id": "header-date-range", "property": "end_date", "value": end_dates[idx]},
                    {"id": "filter-status", "property": "value", "value": []},
                ],
                changed=["header-date-range.start_date"],
            )

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Change Filters",
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def toggle_colorblind(self):
        """
        Toggle colorblind mode (render-only, no data refetch).

        Triggers render_server_snapshot callback (app.py:1201) with colorblind_mode=True.
        This tests the render path in isolation without re-fetching data.
        """
        if not self.cached_bundle:
            return

        payload = _dash_payload(
            output="server-snapshot-content.children",
            outputs={"id": "server-snapshot-content", "property": "children"},
            inputs=[
                {"id": "pulse-kpi-bundle-store", "property": "data", "value": self.cached_bundle},
                {"id": "colorblind-mode-store", "property": "data", "value": True},
            ],
            changed=["colorblind-mode-store.data"],
        )

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Toggle Colorblind",
            headers={"Content-Type": "application/json"},
        )

    @task(2)
    def refresh_kpis(self):
        """
        Manually refresh KPIs via button click (cache miss scenario).

        Triggers fetch_server_snapshot callback (app.py:1166) via btn-refresh-server-snapshot.
        This simulates an executive clicking the Refresh button after filter changes.

        Because change_filters clears the cache, this will be a cache miss.
        """
        payload = _dash_payload(
            output="pulse-kpi-bundle-store.data",
            outputs={"id": "pulse-kpi-bundle-store", "property": "data"},
            inputs=[
                {"id": "server-snapshot-init", "property": "n_intervals", "value": None},
                {"id": "btn-refresh-server-snapshot", "property": "n_clicks", "value": 1},
            ],
            changed=["btn-refresh-server-snapshot.n_clicks"],
        )

        response = self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Refresh KPIs",
            headers={"Content-Type": "application/json"},
        )

        # Update cached bundle
        if response.status_code == 200:
            try:
                result = response.json()
                if "response" in result and "pulse-kpi-bundle-store" in result["response"]:
                    self.cached_bundle = result["response"]["pulse-kpi-bundle-store"]["data"]
            except Exception:
                pass


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print summary statistics after the test completes.

    Includes per-task percentile breakdown and bottleneck analysis comparing
    p95 latencies against SLA thresholds.
    """
    print("\n" + "=" * 80)
    print("PULSE MODE LOAD TEST SUMMARY")
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
            "Prime Cache": 2000,
            "Fetch Pulse KPIs": 2000,
            "Refresh KPIs": 2000,
            "Change Filters": 1000,
            "Render Pulse Panel": 500,
            "Toggle Colorblind": 500,
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
