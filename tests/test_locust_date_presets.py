"""
Test that date presets in locustfiles match the synthetic dataset timeframe.

This test validates that hard-coded date ranges used in load tests are realistic
to the actual synthetic data, ensuring filters will return data and not be empty.
"""

import json
import re
from datetime import datetime
from pathlib import Path


def extract_synthetic_date_range():
    """Extract the date range from synthetic dataset metadata."""
    # Read a sample of benchmark_results.json to find test_timestamp range
    benchmark_file = Path(__file__).parent.parent / "data/synthetic/benchmark_results.json"

    # Parse first few records to find date range
    with open(benchmark_file) as f:
        # Read first 100KB to avoid loading full 6.6MB file
        content = f.read(100_000)

    # Extract all test_timestamp values using regex
    timestamps = re.findall(r'"test_timestamp":\s*"([^"]+)"', content)

    if not timestamps:
        raise ValueError("No test_timestamp found in synthetic data")

    # Parse timestamps to get year/month range (strip timezone for comparison)
    dates = [datetime.fromisoformat(ts.replace("Z", "")).replace(tzinfo=None) for ts in timestamps]
    min_date = min(dates)
    max_date = max(dates)

    return min_date, max_date


def extract_pulse_date_presets():
    """Extract date range presets from locustfile_pulse.py."""
    pulse_file = Path(__file__).parent / "performance/locustfile_pulse.py"

    with open(pulse_file) as f:
        content = f.read()

    # Find the date preset arrays in change_filters task
    # Looking for: start_dates = ["2025-01-01", "2025-03-01", "2025-06-01"]
    start_match = re.search(r'start_dates = \[(.*?)\]', content)
    end_match = re.search(r'end_dates = \[(.*?)\]', content)

    if not start_match or not end_match:
        raise ValueError("Could not find date presets in locustfile_pulse.py")

    # Extract quoted date strings
    start_dates = re.findall(r'"([^"]+)"', start_match.group(1))
    end_dates = re.findall(r'"([^"]+)"', end_match.group(1))

    # Parse to datetime objects
    start_dates_dt = [datetime.fromisoformat(d) for d in start_dates]
    end_dates_dt = [datetime.fromisoformat(d) for d in end_dates]

    return start_dates_dt, end_dates_dt


def extract_track_date_presets():
    """Extract date range presets from locustfile_track.py."""
    track_file = Path(__file__).parent / "performance/locustfile_track.py"

    with open(track_file) as f:
        content = f.read()

    # Find the date_range_presets array in on_start
    # Looking for tuples like: ("2026-01-01", ...) or ("2026-01-01T00:00:00Z", ...)
    preset_match = re.search(
        r'self\.date_range_presets = \[(.*?)\]',
        content,
        re.DOTALL
    )

    if not preset_match:
        raise ValueError("Could not find date_range_presets in locustfile_track.py")

    # Extract all quoted dates (may be YYYY-MM-DD or ISO 8601 with time)
    all_dates = re.findall(r'"([^"]+)"', preset_match.group(1))

    # Each preset is a 4-tuple (baseline_start, baseline_end, nightly_start, nightly_end)
    # Parse all dates, stripping timezone and time for comparison
    dates_dt = []
    for d in all_dates:
        # Handle both "2026-01-01" and "2026-01-01T00:00:00Z" formats
        date_str = d.replace("Z", "").split("T")[0]
        dates_dt.append(datetime.fromisoformat(date_str))

    return dates_dt


def test_pulse_dates_match_synthetic_data():
    """
    Test that Pulse locustfile date presets are within synthetic data range.

    Validates:
    - All start_dates use the correct year (2026, not 2025)
    - All end_dates use the correct year (2026, not 2025)
    - Date ranges overlap with actual synthetic data timeframe
    """
    min_synthetic, max_synthetic = extract_synthetic_date_range()
    start_dates, end_dates = extract_pulse_date_presets()

    # All dates should use 2026 (matching synthetic data)
    expected_year = 2026

    for start_date in start_dates:
        assert start_date.year == expected_year, (
            f"Pulse start date {start_date.date()} uses year {start_date.year}, "
            f"but synthetic data is in {expected_year}"
        )

    for end_date in end_dates:
        assert end_date.year == expected_year, (
            f"Pulse end date {end_date.date()} uses year {end_date.year}, "
            f"but synthetic data is in {expected_year}"
        )

    # At least one date range should overlap with synthetic data
    # (synthetic data is 2026-01-25, so January 2026 range should work)
    overlaps = False
    for start, end in zip(start_dates, end_dates):
        if start <= max_synthetic and end >= min_synthetic:
            overlaps = True
            break

    assert overlaps, (
        f"No Pulse date preset overlaps with synthetic data range "
        f"{min_synthetic.date()} to {max_synthetic.date()}"
    )


def test_track_dates_match_synthetic_data():
    """
    Test that Track locustfile date presets are within synthetic data range.

    Validates:
    - All baseline and nightly dates use the correct year (2026, not 2025)
    - At least one date range overlaps with actual synthetic data
    """
    min_synthetic, max_synthetic = extract_synthetic_date_range()
    all_dates = extract_track_date_presets()

    # All dates should use 2026 (matching synthetic data)
    expected_year = 2026

    for date in all_dates:
        assert date.year == expected_year, (
            f"Track date {date.date()} uses year {date.year}, "
            f"but synthetic data is in {expected_year}"
        )

    # At least one date should overlap with synthetic data range
    overlaps = any(
        min_synthetic.date() <= date.date() <= max_synthetic.date()
        for date in all_dates
    )

    assert overlaps, (
        f"No Track date preset overlaps with synthetic data range "
        f"{min_synthetic.date()} to {max_synthetic.date()}"
    )
