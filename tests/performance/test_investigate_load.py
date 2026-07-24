"""
Locust load test for Investigate Mode (Regression Drill-Down).

Simulates 5 concurrent engineer users drilling into RHEL regression details with
template-based investigation queries, pagination, and point-level drilldown.

Prerequisites:
1. Start the app in synthetic mode:
   DATA_MODE=synthetic python app.py

Usage:
  Single-mode headless (5 users, 1/s spawn rate, 60s):
    locust -f tests/performance/test_investigate_load.py --headless -u 5 -r 1 -t 60s --host http://localhost:8050

  Combined with other modes (Pulse + Investigate + Track = 17 users):
    locust -f tests/performance/test_pulse_load.py,tests/performance/test_investigate_load.py,tests/performance/test_track_load.py \
      --headless -u 17 -r 3 -t 120s --host http://localhost:8050

  Web UI mode:
    locust -f tests/performance/test_investigate_load.py --host http://localhost:8050
    # Then open http://localhost:8089

  Reproducible runs (seeded random test selection):
    LOCUST_SEED=42 locust -f tests/performance/test_investigate_load.py --headless -u 5 -r 1 -t 60s --host http://localhost:8050

Performance SLA Thresholds (p95):
  - Page load: < 500ms
  - Filter update: < 1000ms
  - Investigation view: < 3000ms
  - Point drilldown: < 1500ms

Optimization Recommendations:
1. **Cache investigation queries by params**: The update_investigation_view callback (app.py:2738)
   re-fetches investigation documents from OpenSearch on every navigation-state change, even if
   the same test_name/baseline/comparison params were already fetched. Recommend caching keyed
   by normalized investigation params to avoid redundant queries.

2. **Push LIMIT into OpenSearch query**: The investigation table is capped at .head(50) (app.py:2864)
   but the full DataFrame is fetched, processed, and filtered first. For large result sets (500+
   rows), recommend passing size=50 to the OpenSearch query to reduce data transfer and processing.

3. **Lazy-load drilldown metadata**: Drilldown options and metadata are computed for all 50 table
   rows (app.py:2872-2915) even if the user never clicks "View Points". Recommend computing
   drilldown data on-demand when the modal is opened, not during the initial view render.

4. **Deep link URL generation**: OpenSearch Discover URLs are generated server-side for every
   document (app.py:2875-2915). These could be generated client-side in the DataTable to reduce
   server rendering overhead.
"""

from __future__ import annotations

import os
import random
from locust import HttpUser, task, between, events


def _dash_payload(output, outputs, inputs, changed, state=None):
    """
    Build standard Dash /_dash-update-component POST body.

    Args:
        output: Single output string "component-id.property" or multi-output "..id.prop..id.prop.."
        outputs: Single output dict {"id": "...", "property": "..."} or list of dicts
        inputs: List of input dicts [{"id": "...", "property": "...", "value": ...}, ...]
        changed: List of changedPropIds ["component-id.property", ...]
        state: Optional list of state dicts (for State() inputs in callbacks)

    Returns:
        Dict payload for Dash callback POST request.
    """
    payload = {
        "output": output,
        "outputs": outputs,
        "inputs": inputs,
        "changedPropIds": changed,
    }
    if state:
        payload["state"] = state
    return payload


class InvestigateUser(HttpUser):
    """
    Simulated engineer user investigating RHEL regressions.

    Interaction pattern:
    - Fast navigation (1-3s think time between actions)
    - Active clicking through regression data
    - Frequent view switches and drilldowns
    - Data-intensive workflows

    Task weights reflect typical engineer usage:
    - render_investigation_view (4): Most common — viewing investigation details
    - navigate_to_investigation (3): Clicking bar charts to drill in
    - update_filters_and_analyze (2): Adjusting filters and triggering analysis
    - point_drilldown (2): Viewing individual data points
    - navigate_back (1): Returning to overview
    - load_page (1): Initial visit
    """

    fixed_count = 5  # Ticket spec: 5 concurrent Investigate users
    wait_time = between(1, 3)  # Engineers work fast

    def on_start(self):
        """
        Initialize session by loading the main page and priming analysis store.

        Seeds per-user RNG for reproducible test name selection.
        Runs filter+analysis chain to populate analysis-results-store for navigation.
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

        # Prime filtered data store with empty filters
        filter_response = self.client.post(
            "/_dash-update-component",
            json=_dash_payload(
                output="filtered-data-store.data",
                outputs={"id": "filtered-data-store", "property": "data"},
                inputs=[
                    {"id": "filter-os-version", "property": "value", "value": []},
                    {"id": "filter-instance-type", "property": "value", "value": []},
                    {"id": "filter-test-name", "property": "value", "value": []},
                    {"id": "filter-cloud-provider", "property": "value", "value": []},
                    {"id": "header-date-range", "property": "start_date", "value": None},
                    {"id": "header-date-range", "property": "end_date", "value": None},
                    {"id": "filter-status", "property": "value", "value": []},
                ],
                changed=["filter-os-version.value"],
            ),
            name="Prime Filters",
            headers={"Content-Type": "application/json"},
        )

        # Store filtered data for analyze task
        self.filtered_data_store = None
        if filter_response.status_code == 200:
            try:
                result = filter_response.json()
                if "response" in result and "filtered-data-store" in result["response"]:
                    self.filtered_data_store = result["response"]["filtered-data-store"]["data"]
            except Exception:
                pass

        # Prime analysis store
        analysis_response = self.client.post(
            "/_dash-update-component",
            json=_dash_payload(
                output="analysis-results-store.data",
                outputs={"id": "analysis-results-store", "property": "data"},
                inputs=[
                    {"id": "filtered-data-store", "property": "data", "value": self.filtered_data_store}
                ],
                changed=["filtered-data-store.data"],
            ),
            name="Prime Analysis",
            headers={"Content-Type": "application/json"},
        )

        # Store analysis results for navigation task
        self.analysis_json = None
        if analysis_response.status_code == 200:
            try:
                result = analysis_response.json()
                if "response" in result and "analysis-results-store" in result["response"]:
                    self.analysis_json = result["response"]["analysis-results-store"]["data"]
            except Exception:
                pass

        # Precomputed test names for randomized navigation
        self.test_names = [
            "coremark",
            "pyperf",
            "fio_randread",
            "iperf_tcp",
            "pgbench",
        ]

        # Current investigation state
        self.investigation_nav_state = None
        self.drilldown_data = None

    @task(1)
    def load_page(self):
        """Load main page (GET /)."""
        self.client.get("/", name="Page Load")

    @task(2)
    def update_filters_and_analyze(self):
        """
        Update filters and trigger RHEL regression analysis (chained callbacks).

        Simulates varying data volumes by using different filter combinations:
        - Small: specific test name (100-200 rows)
        - Medium: cloud provider filter (300-500 rows)
        - Large: no filters (800-1000 rows)

        Triggers update_filtered_data (app.py:1503) followed by analyze chain.
        """
        # Randomly choose filter preset
        filter_preset = self.rng.choice(["small", "medium", "large"])

        if filter_preset == "small":
            # Specific test name
            test_filter = [self.rng.choice(self.test_names)]
            cloud_filter = []
            changed_filter = "filter-test-name.value"
        elif filter_preset == "medium":
            # Cloud provider only
            test_filter = []
            cloud_filter = [self.rng.choice(["aws", "gcp", "azure"])]
            changed_filter = "filter-cloud-provider.value"  # Matches actual filter change
        else:  # large
            # No filters
            test_filter = []
            cloud_filter = []
            changed_filter = "filter-test-name.value"  # Arbitrary, both filters cleared

        # Update filters
        filter_response = self.client.post(
            "/_dash-update-component",
            json=_dash_payload(
                output="filtered-data-store.data",
                outputs={"id": "filtered-data-store", "property": "data"},
                inputs=[
                    {"id": "filter-os-version", "property": "value", "value": []},
                    {"id": "filter-instance-type", "property": "value", "value": []},
                    {"id": "filter-test-name", "property": "value", "value": test_filter},
                    {"id": "filter-cloud-provider", "property": "value", "value": cloud_filter},
                    {"id": "header-date-range", "property": "start_date", "value": None},
                    {"id": "header-date-range", "property": "end_date", "value": None},
                    {"id": "filter-status", "property": "value", "value": []},
                ],
                changed=[changed_filter],
            ),
            name=f"Update Filters ({filter_preset})",
            headers={"Content-Type": "application/json"},
        )

        # Update stored filtered data
        if filter_response.status_code == 200:
            try:
                result = filter_response.json()
                if "response" in result and "filtered-data-store" in result["response"]:
                    self.filtered_data_store = result["response"]["filtered-data-store"]["data"]
            except Exception:
                pass

        # Trigger analysis
        analysis_response = self.client.post(
            "/_dash-update-component",
            json=_dash_payload(
                output="analysis-results-store.data",
                outputs={"id": "analysis-results-store", "property": "data"},
                inputs=[
                    {"id": "filtered-data-store", "property": "data", "value": self.filtered_data_store}
                ],
                changed=["filtered-data-store.data"],
            ),
            name="Analyze Data",
            headers={"Content-Type": "application/json"},
        )

        # Update analysis store
        if analysis_response.status_code == 200:
            try:
                result = analysis_response.json()
                if "response" in result and "analysis-results-store" in result["response"]:
                    self.analysis_json = result["response"]["analysis-results-store"]["data"]
            except Exception:
                pass

    @task(3)
    def navigate_to_investigation(self):
        """
        Navigate to investigation view by clicking a bar chart.

        Triggers handle_navigation callback (app.py:2635), which extracts test_name
        from clickData and sets navigation-state to investigation view with params.

        Simulates clicking bars on q1-major-graph (RHEL major version comparison).
        """
        if not self.analysis_json:
            return

        # Randomly choose a test name to investigate
        test_name = self.rng.choice(self.test_names)

        # Simulate bar chart click data
        click_data = {"points": [{"y": test_name}]}

        payload = _dash_payload(
            output="navigation-state.data",
            outputs={"id": "navigation-state", "property": "data"},
            inputs=[
                {"id": "q1-major-graph", "property": "clickData", "value": click_data},
                {"id": "q1-rhel9-graph", "property": "clickData", "value": None},
                {"id": "q1-rhel10-graph", "property": "clickData", "value": None},
                {"id": "btn-view-benchmarks", "property": "n_clicks", "value": None},
                {"id": "btn-view-comparisons", "property": "n_clicks", "value": None},
                {"id": "btn-view-table", "property": "n_clicks", "value": None},
                {"id": "btn-track-mode", "property": "n_clicks", "value": None},
            ],
            state=[
                {"id": "navigation-state", "property": "data", "value": {"view": "overview", "investigation_params": None}},
                {"id": "analysis-results-store", "property": "data", "value": self.analysis_json},
            ],
            changed=["q1-major-graph.clickData"],
        )

        response = self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Navigate to Investigation",
            headers={"Content-Type": "application/json"},
        )

        # Store navigation state for render task
        if response.status_code == 200:
            try:
                result = response.json()
                if "response" in result and "navigation-state" in result["response"]:
                    self.investigation_nav_state = result["response"]["navigation-state"]["data"]
            except Exception:
                pass

    @task(4)
    def render_investigation_view(self):
        """
        Render investigation drill-down view with multiple outputs.

        Triggers update_investigation_view callback (app.py:2738), which:
        - Fetches investigation documents via template-based query
        - Generates summary, comparison chart, timeline chart
        - Builds data table (capped at 50 rows)
        - Computes drilldown options and metadata

        This is the heaviest operation in Investigate mode, testing pagination
        and deep link generation implicitly.
        """
        if not self.investigation_nav_state or self.investigation_nav_state.get("view") != "investigation":
            # No investigation active, skip
            return

        payload = _dash_payload(
            output="..investigation-summary.children..investigation-comparison-chart.figure..investigation-timeline-chart.figure..investigation-table.children..point-drilldown-select.options..point-drilldown-data-store.data..",
            outputs=[
                {"id": "investigation-summary", "property": "children"},
                {"id": "investigation-comparison-chart", "property": "figure"},
                {"id": "investigation-timeline-chart", "property": "figure"},
                {"id": "investigation-table", "property": "children"},
                {"id": "point-drilldown-select", "property": "options"},
                {"id": "point-drilldown-data-store", "property": "data"},
            ],
            inputs=[
                {"id": "navigation-state", "property": "data", "value": self.investigation_nav_state},
                {"id": "filtered-data-store", "property": "data", "value": self.filtered_data_store},
                {"id": "colorblind-mode-store", "property": "data", "value": False},
            ],
            changed=["navigation-state.data"],
        )

        response = self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Render Investigation View",
            headers={"Content-Type": "application/json"},
        )

        # Store drilldown data for point drilldown task
        if response.status_code == 200:
            try:
                result = response.json()
                if "response" in result and "point-drilldown-data-store" in result["response"]:
                    self.drilldown_data = result["response"]["point-drilldown-data-store"]["data"]
            except Exception:
                pass

    @task(2)
    def point_drilldown(self):
        """
        Open point drilldown modal to view individual timeseries data.

        Triggers handle_point_drilldown callback (app.py:3025), which validates
        document_id and fetches timeseries points from OpenSearch or synthetic data.
        """
        if not self.drilldown_data or not isinstance(self.drilldown_data, dict):
            return

        # Extract document IDs from drilldown_data keys (app.py returns dict keyed by doc_id)
        document_ids = list(self.drilldown_data.keys())
        if not document_ids:
            return

        # Randomly select a document to drilldown into
        document_id = self.rng.choice(document_ids)

        payload = _dash_payload(
            output="..point-drilldown-modal.is_open..point-drilldown-modal-title.children..point-drilldown-modal-body.children..point-drilldown-discover-link.children..",
            outputs=[
                {"id": "point-drilldown-modal", "property": "is_open"},
                {"id": "point-drilldown-modal-title", "property": "children"},
                {"id": "point-drilldown-modal-body", "property": "children"},
                {"id": "point-drilldown-discover-link", "property": "children"},  # Matches app.py:3029
            ],
            inputs=[
                {"id": "btn-view-points", "property": "n_clicks", "value": 1},
                {"id": "btn-point-drilldown-close", "property": "n_clicks", "value": None},
            ],
            state=[
                {"id": "point-drilldown-modal", "property": "is_open", "value": False},
                {"id": "point-drilldown-select", "property": "value", "value": document_id},
                {"id": "colorblind-mode-store", "property": "data", "value": False},
                {"id": "point-drilldown-data-store", "property": "data", "value": self.drilldown_data},
                {"id": "navigation-state", "property": "data", "value": self.investigation_nav_state},
            ],
            changed=["btn-view-points.n_clicks"],
        )

        self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Point Drilldown",
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def navigate_back(self):
        """
        Navigate back to overview from investigation view.

        Triggers handle_back_to_overview callback (app.py:2714), which resets
        navigation-state to overview and invalidates Track cache.
        """
        payload = _dash_payload(
            output="navigation-state.data",
            outputs={"id": "navigation-state", "property": "data"},
            inputs=[
                {"id": "btn-back-to-overview", "property": "n_clicks", "value": 1},
                {"id": "btn-back-to-overview-track", "property": "n_clicks", "value": None},
            ],
            changed=["btn-back-to-overview.n_clicks"],
        )

        response = self.client.post(
            "/_dash-update-component",
            json=payload,
            name="Navigate Back",
            headers={"Content-Type": "application/json"},
        )

        # Clear investigation state
        self.investigation_nav_state = None
        self.drilldown_data = None


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print summary statistics after the test completes.

    Includes per-task percentile breakdown and bottleneck analysis.
    """
    print("\n" + "=" * 80)
    print("INVESTIGATE MODE LOAD TEST SUMMARY")
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
            "Prime Filters": 1000,
            "Prime Analysis": 3000,
            "Update Filters": 1000,  # Filter update operations (review feedback)
            "Analyze Data": 3000,    # Analysis chain operations (review feedback)
            "Navigate to Investigation": 500,
            "Render Investigation View": 3000,
            "Point Drilldown": 1500,
            "Navigate Back": 500,
        }

        violations = []
        for entry in environment.stats.entries.values():
            if entry.num_requests > 0:
                # Extract base task name (without filter preset suffix)
                task_name = entry.name
                if " (" in task_name:
                    task_name = task_name.split(" (")[0]

                if task_name in thresholds or entry.name in thresholds:
                    p95 = entry.get_response_time_percentile(0.95)
                    threshold = thresholds.get(task_name) or thresholds.get(entry.name)
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
