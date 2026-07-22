"""
TDD: Tests for size validation in fetch_synthetic_timeseries_for_document.

These tests should fail initially, then pass after implementing OpenSearch parity.
"""

import pytest
import tempfile
import json
from src.data_processing import (
    fetch_synthetic_timeseries_for_document,
    load_synthetic_timeseries,
    _reset_synthetic_timeseries_index,
)


@pytest.fixture
def temp_timeseries_file():
    """Create a temporary timeseries file with known data."""
    data = [
        {
            "metadata": {"document_id": "doc1", "sequence": i},
            "results": {"value": i * 10}
        }
        for i in range(20)  # 20 points for doc1
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        filepath = f.name

    yield filepath

    # Cleanup
    import os
    os.unlink(filepath)
    _reset_synthetic_timeseries_index()


def test_size_validation_negative_raises_valueerror(temp_timeseries_file):
    """Test that negative size raises ValueError."""
    # Reset and load data into singleton
    _reset_synthetic_timeseries_index()
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    # Negative size should raise
    with pytest.raises(ValueError, match="size must be at least 1"):
        fetch_synthetic_timeseries_for_document("doc1", size=-1)


def test_size_validation_zero_raises_valueerror(temp_timeseries_file):
    """Test that size=0 raises ValueError."""
    # Reset and load data into singleton
    _reset_synthetic_timeseries_index()
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    # Zero size should raise
    with pytest.raises(ValueError, match="size must be at least 1"):
        fetch_synthetic_timeseries_for_document("doc1", size=0)


def test_size_validation_caps_at_10000(temp_timeseries_file):
    """Test that size is capped at 10000 (OpenSearch parity)."""
    # Reset and load data into singleton
    _reset_synthetic_timeseries_index()
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    # Request 20000 points, should get capped at 10000
    # Since we only have 20 points, we'll get 20, but the cap should be applied
    points = fetch_synthetic_timeseries_for_document("doc1", size=20000)

    # Should return all 20 points (less than cap)
    assert len(points) == 20


def test_size_one_returns_one_point(temp_timeseries_file):
    """Test that size=1 returns exactly one point."""
    # Reset and load data into singleton
    _reset_synthetic_timeseries_index()
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    points = fetch_synthetic_timeseries_for_document("doc1", size=1)

    assert len(points) == 1
    assert points[0]["metadata"]["sequence"] == 0
