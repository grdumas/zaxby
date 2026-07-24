"""
Test that Track mode date strings are timezone-aware.

This test validates that all date presets in locustfile_track.py use
timezone-aware ISO format strings (ending with Z or +00:00) that can be
parsed as datetime objects with timezone info.

Requirements:
1. All date strings must be timezone-aware (end with Z or +00:00)
2. All date strings must parse as datetime objects with tzinfo set
3. Start-of-day dates should use T00:00:00Z
4. End-of-day dates should use T23:59:59Z

This builds on Task #5 (date updates to 2026).
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone


def test_track_date_range_presets_are_timezone_aware():
    """
    Test that all date range presets in locustfile_track.py are timezone-aware.

    The run_track_comparison callback (app.py:3234-3243) parses date strings using
    datetime.fromisoformat(date.replace('Z', '+00:00')), which requires timezone-aware
    ISO strings.

    This test will FAIL with naive YYYY-MM-DD format and PASS with ISO format like:
    - Start of day: YYYY-MM-DDT00:00:00Z
    - End of day: YYYY-MM-DDT23:59:59Z
    """
    import re
    import os

    # Read the actual date presets from locustfile_track.py
    locustfile_path = os.path.join(os.path.dirname(__file__), 'locustfile_track.py')
    with open(locustfile_path, 'r') as f:
        content = f.read()

    # Extract the date_range_presets array using regex
    # Look for pattern: ("date", "date", "date", "date"),
    pattern = r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
    matches = re.findall(pattern, content)

    # Filter matches to only include those in the date_range_presets section
    # (Look for matches after "self.date_range_presets = [")
    presets_section_start = content.find('self.date_range_presets = [')
    presets_section_end = content.find(']', presets_section_start)
    presets_section = content[presets_section_start:presets_section_end]

    actual_presets = re.findall(pattern, presets_section)

    assert len(actual_presets) > 0, "No date range presets found in locustfile_track.py"

    # Parse each date string in each preset
    for preset_idx, preset in enumerate(actual_presets):
        baseline_start, baseline_end, nightly_start, nightly_end = preset

        # Test each date string in the preset
        for date_label, date_str in [
            (f"Preset {preset_idx} baseline_start", baseline_start),
            (f"Preset {preset_idx} baseline_end", baseline_end),
            (f"Preset {preset_idx} nightly_start", nightly_start),
            (f"Preset {preset_idx} nightly_end", nightly_end),
        ]:
            # Requirement 1: Date strings must be timezone-aware (end with Z or +00:00)
            assert date_str.endswith('Z') or '+00:00' in date_str, (
                f"{date_label}: Date string must end with Z or contain +00:00. "
                f"Got: {date_str}"
            )

            # Requirement 2: Date strings must parse as datetime with tzinfo
            parsed_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            assert parsed_dt.tzinfo is not None, (
                f"{date_label}: Parsed datetime must have timezone info. "
                f"Got tzinfo={parsed_dt.tzinfo}"
            )
            assert parsed_dt.tzinfo == timezone.utc, (
                f"{date_label}: Parsed datetime must be in UTC timezone. "
                f"Got tzinfo={parsed_dt.tzinfo}"
            )

            # Requirement 3: Start dates should use T00:00:00Z
            if 'start' in date_label:
                assert 'T00:00:00Z' in date_str, (
                    f"{date_label}: Start-of-day dates should use T00:00:00Z. "
                    f"Got: {date_str}"
                )

            # Requirement 4: End dates should use T23:59:59Z
            if 'end' in date_label:
                assert 'T23:59:59Z' in date_str, (
                    f"{date_label}: End-of-day dates should use T23:59:59Z. "
                    f"Got: {date_str}"
                )


def test_track_date_format_compatible_with_callback():
    """
    Test that date strings are compatible with run_track_comparison callback.

    The callback uses: datetime.fromisoformat(date.replace('Z', '+00:00'))
    This test verifies that our date format can be parsed this way.
    """
    test_dates = [
        "2026-01-01T00:00:00Z",
        "2026-03-31T23:59:59Z",
        "2026-06-01T00:00:00Z",
        "2026-06-30T23:59:59Z",
    ]

    for date_str in test_dates:
        # This is the exact parsing pattern used in app.py:3234-3243
        parsed_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

        # Verify it produces a timezone-aware datetime
        assert parsed_dt.tzinfo is not None, (
            f"Callback parsing failed for {date_str}: no timezone info"
        )
        assert parsed_dt.tzinfo == timezone.utc, (
            f"Callback parsing failed for {date_str}: expected UTC, got {parsed_dt.tzinfo}"
        )


def test_naive_date_format_fails():
    """
    Demonstrate that naive YYYY-MM-DD format produces datetime without timezone info.

    This test shows why the old format was incompatible with the callback.
    """
    naive_date = "2026-01-01"

    # Parse naive date
    parsed_dt = datetime.fromisoformat(naive_date)

    # Verify it's naive (no timezone info)
    assert parsed_dt.tzinfo is None, (
        "Naive date format should produce datetime without timezone info"
    )


def test_iso_format_produces_aware_datetime():
    """
    Demonstrate that ISO format with Z produces timezone-aware datetime.

    This test shows why the new format is compatible with the callback.
    """
    iso_date = "2026-01-01T00:00:00Z"

    # Parse ISO date (using same pattern as callback)
    parsed_dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))

    # Verify it's aware (has timezone info)
    assert parsed_dt.tzinfo is not None, (
        "ISO format should produce datetime with timezone info"
    )
    assert parsed_dt.tzinfo == timezone.utc, (
        "ISO format should produce UTC datetime"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
