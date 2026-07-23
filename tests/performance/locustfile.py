"""
Locust HTTP load tests for the Dash dashboard.

Simulates concurrent users interacting with the dashboard: page loads, filter
changes, tab navigation, and analysis requests.

Prerequisites:
1. Start the app in synthetic mode:
   DATA_MODE=synthetic python app.py

Usage:
  Headless mode (1 user, 60s):
    locust -f tests/performance/locustfile.py --headless -u 1 -r 1 -t 60s --host http://localhost:8050

  Headless mode (10 users, 2 spawn rate, 60s):
    locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8050

  Parameterized concurrency (50 users):
    locust -f tests/performance/locustfile.py --headless -u 50 -r 5 -t 120s --host http://localhost:8050

  Stress test (100 users):
    locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 180s --host http://localhost:8050

  Web UI mode:
    locust -f tests/performance/locustfile.py --host http://localhost:8050
    # Then open http://localhost:8089

Note: For 50+ user tests, run the app with gunicorn multi-process:
  gunicorn -w 4 -b 127.0.0.1:8050 app:server
  (Use 0.0.0.0 only when intentionally exposing to network)
"""

from __future__ import annotations

import random
from locust import HttpUser, task, between, events


class DashboardUser(HttpUser):
    """
    Simulated dashboard user.

    Tasks weighted by realistic frequency:
    - Page load: 1x (initial visit)
    - Pulse KPI fetch: 3x (auto-triggered, manual refresh)
    - Filter updates: 5x (most common interaction)
    - Analysis: 2x (tab navigation)
    - Nightly runs: 1x (less frequent)
    """

    wait_time = between(1, 5)  # 1-5 seconds between requests
    host = "http://localhost:8050"

    def on_start(self):
        """
        Initialize session by loading the main page.

        Validates connectivity and fetches initial layout.
        """
        response = self.client.get("/", name="Initial Page Load")
        if response.status_code != 200:
            raise Exception(
                f"App not reachable at {self.host}. "
                f"Ensure app is running with: DATA_MODE=synthetic python app.py"
            )

    @task(1)
    def load_page(self):
        """
        Load main page (GET /).

        Simulates initial page visit or refresh.
        """
        self.client.get("/", name="Page Load")

    @task(3)
    def fetch_pulse_kpis(self):
        """
        Fetch Pulse KPI bundle (POST /_dash-update-component).

        Triggers fetch_server_snapshot callback, which runs 4 OpenSearch
        aggregations in production or DataFrame aggregations in synthetic mode.

        This is the most expensive server-side operation on page load.
        """
        payload = {
            "output": "pulse-kpi-bundle-store.data",
            "outputs": {"id": "pulse-kpi-bundle-store", "property": "data"},
            "inputs": [
                {"id": "server-snapshot-init", "property": "n_intervals", "value": 1}
            ],
            "changedPropIds": ["server-snapshot-init.n_intervals"],
        }

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Fetch Pulse KPIs",
            headers={"Content-Type": "application/json"},
        )

    @task(5)
    def update_filters(self):
        """
        Update filters (POST /_dash-update-component).

        Triggers update_filtered_data callback, which filters the in-memory
        DataFrame and clears the cache. Most common user interaction.

        Varies filter combinations randomly to simulate realistic usage.
        """
        # Map filter names to component IDs (component IDs use hyphens, not underscores)
        filter_to_component_id = {
            "os_version": "os-version",
            "cloud_provider": "cloud-provider",
            "test_name": "test-name",
            "status": "status",
        }

        # Randomly choose which filter to update
        filter_choice = random.choice(["os_version", "cloud_provider", "test_name", "status"])

        # Build filter values based on choice
        if filter_choice == "os_version":
            filter_value = random.choice([["RHEL 9.6"], ["RHEL 10.1"], []])
        elif filter_choice == "cloud_provider":
            filter_value = random.choice([["aws"], ["gcp"], ["azure"], []])
        elif filter_choice == "test_name":
            filter_value = random.choice([["coremark"], ["pyperf"], []])
        else:  # status
            filter_value = random.choice([["pass"], ["fail"], []])

        # Map filter choice to component ID for changedPropIds
        component_id = filter_to_component_id[filter_choice]

        payload = {
            "output": "filtered-data-store.data",
            "outputs": {"id": "filtered-data-store", "property": "data"},
            "inputs": [
                {"id": "filter-os-version", "property": "value", "value": filter_value if filter_choice == "os_version" else []},
                {"id": "filter-instance-type", "property": "value", "value": []},
                {"id": "filter-test-name", "property": "value", "value": filter_value if filter_choice == "test_name" else []},
                {"id": "filter-cloud-provider", "property": "value", "value": filter_value if filter_choice == "cloud_provider" else []},
                {"id": "header-date-range", "property": "start_date", "value": None},
                {"id": "header-date-range", "property": "end_date", "value": None},
                {"id": "filter-status", "property": "value", "value": filter_value if filter_choice == "status" else []},
            ],
            "changedPropIds": [f"filter-{component_id}.value"],
        }

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Update Filters",
            headers={"Content-Type": "application/json"},
        )

    @task(2)
    def analyze_data(self):
        """
        Run RHEL regression analysis (POST /_dash-update-component).

        Triggers analyze_filtered_data callback, which runs
        analyze_rhel_simplified_regressions on the filtered DataFrame.

        This is the heaviest analysis operation, computing three regression
        comparisons with category grouping and statistical calculations.
        """
        # This callback depends on filtered-data-store being populated first,
        # but in Locust we simulate it directly. In a real session, the filter
        # update would have already populated the store.
        payload = {
            "output": "analysis-results-store.data",
            "outputs": {"id": "analysis-results-store", "property": "data"},
            "inputs": [
                {"id": "filtered-data-store", "property": "data", "value": None}
            ],
            "changedPropIds": ["filtered-data-store.data"],
        }

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Analyze Data",
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def fetch_nightly_runs(self):
        """
        Fetch recent nightly runs (POST /_dash-update-component).

        Triggers update_nightly_runs callback, which runs daily date_histogram
        aggregation with sub-aggregations for pass/fail counts and test category
        breakdown.
        """
        payload = {
            "output": "nightly-runs-store.data",
            "outputs": {"id": "nightly-runs-store", "property": "data"},
            "inputs": [
                {"id": "header-date-range", "property": "start_date", "value": None},
                {"id": "header-date-range", "property": "end_date", "value": None},
            ],
            "changedPropIds": ["header-date-range.start_date"],
        }

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Fetch Nightly Runs",
            headers={"Content-Type": "application/json"},
        )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print summary statistics after the test completes.

    Args:
        environment: Locust environment.
        **kwargs: Additional arguments.
    """
    print("\n" + "=" * 80)
    print("LOAD TEST SUMMARY")
    print("=" * 80)
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {environment.stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {environment.stats.total.total_rps:.2f}")

    if environment.stats.total.num_requests > 0:
        print(f"\nPercentiles:")
        print(f"  50th percentile: {environment.stats.total.get_response_time_percentile(0.50):.2f}ms")
        print(f"  95th percentile: {environment.stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"  99th percentile: {environment.stats.total.get_response_time_percentile(0.99):.2f}ms")

    print("=" * 80 + "\n")
