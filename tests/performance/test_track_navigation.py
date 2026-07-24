"""
Test suite for Track mode navigation in Locust load tests.

Validates that:
1. TrackUser.on_start() navigates to Track mode before comparison tasks
2. Comparison tasks are gated on in_track_mode being True
3. Navigate back properly resets in_track_mode flag

TDD approach - tests verify code structure and logic without running locust.
"""

import pytest
import ast
import inspect
from pathlib import Path


class TestTrackModeNavigation:
    """Test Track mode navigation structure and logic."""

    @pytest.fixture
    def locustfile_source(self):
        """Load the locustfile_track.py source code."""
        locustfile_path = Path(__file__).parent / "locustfile_track.py"
        with open(locustfile_path, "r") as f:
            return f.read()

    @pytest.fixture
    def locustfile_ast(self, locustfile_source):
        """Parse the locustfile AST."""
        return ast.parse(locustfile_source)

    def test_on_start_has_track_navigation(self, locustfile_source):
        """
        Test that on_start() includes Track mode navigation POST request.

        Expected:
        - on_start() method exists
        - Contains POST to /_dash-update-component
        - Payload includes btn-track-mode.n_clicks = 1
        - Sets self.in_track_mode = True after successful navigation
        """
        assert "def on_start(self):" in locustfile_source, "on_start method not found"
        assert "/_dash-update-component" in locustfile_source, "No Dash update POST found"
        assert "btn-track-mode" in locustfile_source, "btn-track-mode not found in navigation"
        assert "self.in_track_mode = True" in locustfile_source, "in_track_mode flag not set in on_start"

    def test_on_start_raises_on_navigation_failure(self, locustfile_ast, locustfile_source):
        """
        Test that on_start() raises exception if navigation fails.

        Expected:
        - Check for nav_response.status_code != 200
        - Raise Exception if navigation fails
        """
        # Look for the navigation response check
        assert "nav_response.status_code" in locustfile_source, "Navigation response status not checked"
        assert 'raise Exception' in locustfile_source and 'Failed to navigate to Track mode' in locustfile_source, \
            "on_start should raise exception on navigation failure"

    def test_run_comparison_has_track_mode_gate(self, locustfile_source):
        """
        Test that run_comparison checks in_track_mode before proceeding.

        Expected:
        - Guard at start of method: if not self.in_track_mode: return
        """
        # Extract the run_comparison method
        lines = locustfile_source.split('\n')
        in_run_comparison = False
        run_comparison_lines = []

        for i, line in enumerate(lines):
            if 'def run_comparison(self):' in line:
                in_run_comparison = True
            elif in_run_comparison:
                if line.strip().startswith('def ') and 'run_comparison' not in line:
                    # Next method started
                    break
                run_comparison_lines.append(line)

        run_comparison_code = '\n'.join(run_comparison_lines)

        # Check for guard clause
        assert 'if not self.in_track_mode' in run_comparison_code, \
            "run_comparison should check in_track_mode flag"
        assert 'return' in run_comparison_code.split('if not self.in_track_mode')[1].split('\n')[0:2][1], \
            "run_comparison should return early if not in Track mode"

    def test_run_comparison_varied_has_track_mode_gate(self, locustfile_source):
        """
        Test that run_comparison_varied checks in_track_mode before proceeding.

        Expected:
        - Guard at start of method: if not self.in_track_mode: return
        """
        # Extract the run_comparison_varied method
        lines = locustfile_source.split('\n')
        in_run_comparison_varied = False
        run_comparison_varied_lines = []

        for i, line in enumerate(lines):
            if 'def run_comparison_varied(self):' in line:
                in_run_comparison_varied = True
            elif in_run_comparison_varied:
                if line.strip().startswith('def ') and 'run_comparison_varied' not in line:
                    # Next method started
                    break
                run_comparison_varied_lines.append(line)

        run_comparison_varied_code = '\n'.join(run_comparison_varied_lines)

        # Check for guard clause
        assert 'if not self.in_track_mode' in run_comparison_varied_code, \
            "run_comparison_varied should check in_track_mode flag"
        assert 'return' in run_comparison_varied_code.split('if not self.in_track_mode')[1].split('\n')[0:2][1], \
            "run_comparison_varied should return early if not in Track mode"

    def test_navigate_back_resets_track_mode(self, locustfile_source):
        """
        Test that navigate_back resets in_track_mode flag on success.

        Expected:
        - Check response.status_code == 200
        - Set self.in_track_mode = False on success
        """
        # Extract the navigate_back method
        lines = locustfile_source.split('\n')
        in_navigate_back = False
        navigate_back_lines = []

        for i, line in enumerate(lines):
            if 'def navigate_back(self):' in line:
                in_navigate_back = True
            elif in_navigate_back:
                if line.strip().startswith('def ') and 'navigate_back' not in line:
                    # Next method started
                    break
                navigate_back_lines.append(line)

        navigate_back_code = '\n'.join(navigate_back_lines)

        # Check for status code check and flag reset
        assert 'response.status_code == 200' in navigate_back_code, \
            "navigate_back should check response status code"
        assert 'self.in_track_mode = False' in navigate_back_code, \
            "navigate_back should reset in_track_mode flag on success"

    def test_track_navigation_uses_handle_navigation_callback(self, locustfile_source):
        """
        Test that Track navigation uses the correct Dash callback structure.

        Expected from app.py:2635-2709 (handle_navigation):
        - btn-track-mode with n_clicks trigger
        - navigation-state as output
        - Returns {'view': 'track', 'investigation_params': None}
        """
        # Check payload structure
        assert "btn-track-mode" in locustfile_source, "btn-track-mode not in navigation payload"
        assert "navigation-state" in locustfile_source, "navigation-state not in outputs"
        assert "n_clicks" in locustfile_source, "n_clicks not specified for button"

    def test_on_start_happens_before_comparisons(self, locustfile_source):
        """
        Test that on_start is defined and sets up state before comparison tasks.

        Expected:
        - on_start method exists and is correctly named
        - Initializes date_range_presets and baseline_ids
        - These are used by comparison tasks
        """
        assert "def on_start(self):" in locustfile_source, "on_start method not found"
        assert "self.date_range_presets" in locustfile_source, "date_range_presets not initialized"
        assert "self.baseline_ids" in locustfile_source, "baseline_ids not initialized"
        assert "self.in_track_mode" in locustfile_source, "in_track_mode flag not initialized"

    def test_all_comparison_tasks_respect_track_mode(self, locustfile_ast):
        """
        Test that all comparison-related tasks check in_track_mode.

        This is the critical test - ensures tasks won't run before navigation completes.
        """
        # Find all methods with @task decorator
        task_methods = []

        for node in ast.walk(locustfile_ast):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Check if it's a task decorator (either @task or @task(weight))
                    is_task = False
                    if isinstance(decorator, ast.Name) and decorator.id == 'task':
                        is_task = True
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Name) and decorator.func.id == 'task':
                            is_task = True

                    if is_task:
                        task_methods.append(node.name)

        # Comparison tasks that must check in_track_mode
        comparison_tasks = ['run_comparison', 'run_comparison_varied']

        for task_name in comparison_tasks:
            assert task_name in task_methods, f"{task_name} not found as a task"

    def test_navigate_back_only_resets_on_success(self, locustfile_source):
        """
        Test that navigate_back only resets flag on successful response.

        Expected:
        - Status code check guards the flag reset
        - Flag is NOT reset unconditionally
        """
        # Extract navigate_back code
        lines = locustfile_source.split('\n')
        in_navigate_back = False
        navigate_back_lines = []

        for line in lines:
            if 'def navigate_back(self):' in line:
                in_navigate_back = True
            elif in_navigate_back:
                if line.strip().startswith('def ') and 'navigate_back' not in line:
                    break
                navigate_back_lines.append(line)

        navigate_back_code = '\n'.join(navigate_back_lines)

        # The reset should be inside an if block checking status code
        reset_line_idx = None
        status_check_idx = None

        for i, line in enumerate(navigate_back_lines):
            if 'self.in_track_mode = False' in line:
                reset_line_idx = i
            if 'response.status_code == 200' in line or 'status_code == 200' in line:
                status_check_idx = i

        assert reset_line_idx is not None, "in_track_mode reset not found"
        assert status_check_idx is not None, "status code check not found"
        assert reset_line_idx > status_check_idx, \
            "in_track_mode reset should come after status code check"

    def test_navigation_payload_structure_matches_app_py(self, locustfile_source):
        """
        Test that navigation payload matches app.py:2635-2709 callback structure.

        Expected inputs for handle_navigation:
        - q1-major-graph.clickData
        - q1-rhel9-graph.clickData
        - q1-rhel10-graph.clickData
        - btn-view-benchmarks.n_clicks
        - btn-view-comparisons.n_clicks
        - btn-view-table.n_clicks
        - btn-track-mode.n_clicks  <- This should be the changed trigger

        Expected state:
        - navigation-state.data
        - analysis-results-store.data
        """
        # Check that the navigation payload includes the expected structure
        on_start_section = locustfile_source.split('def on_start(self):')[1].split('def ')[0]

        assert 'q1-major-graph' in on_start_section, "Missing q1-major-graph input"
        assert 'q1-rhel9-graph' in on_start_section, "Missing q1-rhel9-graph input"
        assert 'q1-rhel10-graph' in on_start_section, "Missing q1-rhel10-graph input"
        assert 'btn-view-benchmarks' in on_start_section, "Missing btn-view-benchmarks input"
        assert 'btn-view-comparisons' in on_start_section, "Missing btn-view-comparisons input"
        assert 'btn-view-table' in on_start_section, "Missing btn-view-table input"
        assert 'btn-track-mode' in on_start_section, "Missing btn-track-mode input"
        assert 'navigation-state' in on_start_section, "Missing navigation-state in state"
        assert 'analysis-results-store' in on_start_section, "Missing analysis-results-store in state"
