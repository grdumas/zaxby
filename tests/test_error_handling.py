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


def test_oserror_returns_empty_dict_with_warning(caplog, tmp_path, monkeypatch):
    """Test that OS errors (permission denied, etc.) return empty dict."""
    # Create a file that exists (so we pass the os.path.exists check)
    # but monkeypatch open/gzip.open to raise OSError when trying to read it
    filepath = tmp_path / "timeseries.json"
    filepath.write_text("[]")  # Create the file so it exists

    # Monkeypatch the builtin open to raise OSError
    original_open = open
    def mock_open(*args, **kwargs):
        # Only raise for our specific test file
        if args and str(args[0]) == str(filepath):
            raise OSError("Permission denied")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    caplog.clear()
    result = load_synthetic_timeseries(str(filepath))

    # Should return empty dict, not crash
    assert result == {}

    # Should log a warning about failed to load
    assert any("failed" in record.message.lower() for record in caplog.records)


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


def test_oserror_on_gzip_file_returns_empty_dict_with_warning(caplog, tmp_path, monkeypatch):
    """Test that OS errors when reading gzip files return empty dict."""
    # Create a gzip file that exists but will fail to open
    filepath = tmp_path / "timeseries.json.gz"

    # Create actual gzip file so it exists
    with gzip.open(filepath, 'wt') as gz:
        json.dump([], gz)

    # Monkeypatch gzip.open to raise OSError
    original_gzip_open = gzip.open
    def mock_gzip_open(*args, **kwargs):
        if args and str(args[0]) == str(filepath):
            raise OSError("I/O error")
        return original_gzip_open(*args, **kwargs)

    monkeypatch.setattr("gzip.open", mock_gzip_open)

    caplog.clear()
    result = load_synthetic_timeseries(str(filepath))

    # Should return empty dict, not crash
    assert result == {}

    # Should log a warning about failed to load
    assert any("failed" in record.message.lower() for record in caplog.records)


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


def test_excessive_file_size_returns_empty_dict_with_warning(caplog, tmp_path):
    """Test that files exceeding size limit are rejected with warning."""
    # Create a file
    filepath = tmp_path / "large_timeseries.json"
    filepath.write_text("[]")

    # Note: MAX_TIMESERIES_FILE_SIZE_MB will be defined in data_processing.py
    # This test verifies defensive file size checking before loading into memory

    # For now, this test documents expected behavior:
    # Files larger than a reasonable threshold (e.g., 100MB) should be rejected
    # to prevent memory exhaustion

    # The actual implementation will check file size before attempting json.load
    # This is a defensive guardrail for when the dataset grows beyond current size

    # Test will be implemented once size limit is defined
    pytest.skip("Size limit not yet implemented - documents expected behavior")


def test_invalid_sequence_type_skips_with_warning(caplog):
    """Test that records with non-numeric sequence values are skipped with warning."""
    data = [
        # Valid record with int sequence
        {
            "metadata": {"document_id": "doc1", "sequence": 0},
            "results": {"value": 10}
        },
        # Invalid: sequence is a string
        {
            "metadata": {"document_id": "doc1", "sequence": "not_a_number"},
            "results": {"value": 20}
        },
        # Invalid: sequence is a list
        {
            "metadata": {"document_id": "doc2", "sequence": [1, 2, 3]},
            "results": {"value": 30}
        },
        # Valid record with float sequence (should be coerced)
        {
            "metadata": {"document_id": "doc2", "sequence": 1.0},
            "results": {"value": 40}
        },
        # Invalid: sequence is null
        {
            "metadata": {"document_id": "doc3", "sequence": None},
            "results": {"value": 50}
        },
        # Valid record with int sequence
        {
            "metadata": {"document_id": "doc3", "sequence": 0},
            "results": {"value": 60}
        },
        # Invalid: sequence is a boolean (bool is subclass of int in Python)
        {
            "metadata": {"document_id": "doc4", "sequence": True},
            "results": {"value": 70}
        },
        # Invalid: sequence is a boolean False
        {
            "metadata": {"document_id": "doc4", "sequence": False},
            "results": {"value": 80}
        },
        # Valid record for doc4
        {
            "metadata": {"document_id": "doc4", "sequence": 1},
            "results": {"value": 90}
        },
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        filepath = f.name

    try:
        caplog.clear()
        result = load_synthetic_timeseries(filepath)

        # Should return only records with valid sequence values
        assert len(result) == 4  # doc1, doc2, doc3, doc4
        assert "doc1" in result
        assert "doc2" in result
        assert "doc3" in result
        assert "doc4" in result
        assert len(result["doc1"]) == 1  # Only the valid record
        assert len(result["doc2"]) == 1  # Only the float record (coerced)
        assert len(result["doc3"]) == 1  # Only the int record
        assert len(result["doc4"]) == 1  # Only the int record, not booleans

        # Verify the correct records were kept
        assert result["doc1"][0]["results"]["value"] == 10
        assert result["doc2"][0]["results"]["value"] == 40
        assert result["doc3"][0]["results"]["value"] == 60
        assert result["doc4"][0]["results"]["value"] == 90

        # Should log warnings about skipped records with invalid sequence types
        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("skipping" in msg.lower() or "malformed" in msg.lower()
                   for msg in warning_messages)
    finally:
        os.unlink(filepath)
