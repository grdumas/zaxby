"""
TDD: Tests for error handling in load_synthetic_timeseries.

These tests should initially fail, then pass after implementing robust error handling.
"""

import pytest
import tempfile
import json
import gzip
import os
from src.data_processing import (
    load_synthetic_timeseries,
    _reset_synthetic_timeseries_index,
)


def test_corrupted_json_returns_empty_dict_with_warning(caplog):
    """Test that corrupted JSON file returns empty dict and logs warning."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"incomplete": "json"')  # Invalid JSON
        filepath = f.name

    try:
        result = load_synthetic_timeseries(filepath)

        # Should return empty dict, not crash
        assert result == {}

        # Should log a warning about failure to load
        assert any("failed" in record.message.lower() for record in caplog.records)
    finally:
        os.unlink(filepath)


def test_malformed_record_schema_skips_with_warning(caplog):
    """Test that records missing required fields are skipped with warning."""
    data = [
        # Valid record
        {
            "metadata": {"document_id": "doc1", "sequence": 0},
            "results": {"value": 10}
        },
        # Missing metadata
        {
            "results": {"value": 20}
        },
        # Missing document_id
        {
            "metadata": {"sequence": 2},
            "results": {"value": 30}
        },
        # Missing sequence
        {
            "metadata": {"document_id": "doc2"},
            "results": {"value": 40}
        },
        # Another valid record
        {
            "metadata": {"document_id": "doc2", "sequence": 0},
            "results": {"value": 50}
        },
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        filepath = f.name

    try:
        caplog.clear()
        result = load_synthetic_timeseries(filepath)

        # Should return only valid records
        assert len(result) == 2  # doc1 and doc2
        assert "doc1" in result
        assert "doc2" in result
        assert len(result["doc1"]) == 1
        assert len(result["doc2"]) == 1

        # Should log warnings about skipped records
        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("skipping" in msg.lower() or "malformed" in msg.lower()
                   for msg in warning_messages)
    finally:
        os.unlink(filepath)


def test_oserror_returns_empty_dict_with_warning(caplog):
    """Test that OS errors (permission denied, etc.) return empty dict."""
    # Use a path that will trigger OSError on read
    filepath = "/proc/invalid/path/timeseries.json"

    result = load_synthetic_timeseries(filepath)

    # Should return empty dict, not crash
    assert result == {}

    # Should log a warning about file not found
    assert any("not found" in record.message.lower() for record in caplog.records)


def test_empty_json_array_returns_empty_dict():
    """Test that empty JSON array returns empty dict (valid edge case)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump([], f)
        filepath = f.name

    try:
        result = load_synthetic_timeseries(filepath)

        # Should return empty dict without errors
        assert result == {}
    finally:
        os.unlink(filepath)


def test_gzip_compressed_file_loads_correctly():
    """Test that gzip-compressed files are properly decompressed and loaded."""
    data = [
        {
            "metadata": {"document_id": "doc1", "sequence": 0},
            "results": {"value": 10}
        },
        {
            "metadata": {"document_id": "doc1", "sequence": 1},
            "results": {"value": 20}
        },
    ]

    with tempfile.NamedTemporaryFile(mode='wb', suffix='.json.gz', delete=False) as f:
        with gzip.open(f, 'wt') as gz:
            json.dump(data, gz)
        filepath = f.name

    try:
        result = load_synthetic_timeseries(filepath)

        # Should load and index correctly
        assert len(result) == 1
        assert "doc1" in result
        assert len(result["doc1"]) == 2
    finally:
        os.unlink(filepath)
