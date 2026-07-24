"""
TDD test to verify fixture scoping issue before fixing.

This test validates that autouse monitoring fixtures don't force
OpenSearch dependency on unrelated performance tests.
"""
import subprocess
import sys


def test_autouse_fixtures_dont_affect_unrelated_tests():
    """
    Verify that non-OpenSearch performance tests can run without OpenSearch.

    This test simulates running a non-OpenSearch performance test (e.g.,
    cache benchmark, synthetic data benchmark) without setting
    RUN_OPENSEARCH_QUERY_BENCHMARKS=1.

    Expected behavior:
    - Non-OpenSearch tests should run normally
    - They should NOT be skipped due to missing opensearch_client fixture

    This test will FAIL initially (proving the bug exists), then PASS
    after we remove autouse=True from monitoring fixtures.
    """
    # Create a minimal test file in tests/performance/ to test conftest scoping
    test_code = '''
import pytest

def test_simple_performance_without_opensearch():
    """A simple performance test that doesn't use OpenSearch."""
    result = sum(range(1000))
    assert result > 0
'''

    # Write test to tests/performance/ to pick up the conftest
    test_file = "tests/performance/test_non_opensearch_simple.py"
    with open(test_file, "w") as f:
        f.write(test_code)

    try:
        # Run test WITHOUT RUN_OPENSEARCH_QUERY_BENCHMARKS=1
        # This should succeed if autouse is removed, fail if autouse=True
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v"],
            capture_output=True,
            text=True,
            cwd="/home/gdumas/repos/zaxby",
            env={**subprocess.os.environ, "RUN_OPENSEARCH_QUERY_BENCHMARKS": "0"}
        )
    finally:
        # Clean up test file
        import os
        if os.path.exists(test_file):
            os.remove(test_file)

    # Check that test ran (not skipped)
    assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
    assert "PASSED" in result.stdout or "passed" in result.stdout, \
        f"Test was skipped when it should have run: {result.stdout}"
    assert "skipped" not in result.stdout.lower(), \
        f"Test was skipped due to autouse fixtures: {result.stdout}"


if __name__ == "__main__":
    # Run the test
    test_autouse_fixtures_dont_affect_unrelated_tests()
    print("✓ Test passed: autouse fixtures are properly scoped")
