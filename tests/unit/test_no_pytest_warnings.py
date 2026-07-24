"""
TDD test to verify pytest warnings are eliminated.

This test runs pytest on test_helpers_import.py and verifies no warnings are produced.
"""
import subprocess
import sys


def test_helpers_import_produces_no_warnings():
    """
    Verify that test_helpers_import.py runs without pytest warnings.

    This test will FAIL initially (proving the warning exists), then PASS
    after we fix the return value issue.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/test_helpers_import.py", "-v"],
        capture_output=True,
        text=True,
        cwd="/home/gdumas/repos/zaxby"
    )

    # Check test passed
    assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"

    # Check no warnings in output
    assert "PytestReturnNotNoneWarning" not in result.stdout, \
        f"Found pytest return value warning: {result.stdout}"
    assert "warning" not in result.stdout.lower() or "0 warnings" in result.stdout or "warnings summary" not in result.stdout.lower(), \
        f"Found warnings in output: {result.stdout}"


if __name__ == "__main__":
    test_helpers_import_produces_no_warnings()
    print("✓ Test passed: no pytest warnings")
