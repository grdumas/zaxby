"""
Pytest-style tests for synthetic timeseries loading and querying.

These tests use self-contained temp fixtures instead of relying on
the real 23MB timeseries_results.json file, making them CI-safe.
"""

import pytest
import json
import tempfile
import os
from unittest import mock
import pandas as pd

from src.data_processing import (
    load_synthetic_timeseries,
    get_synthetic_timeseries_index,
    fetch_synthetic_timeseries_for_document,
    _reset_synthetic_timeseries_index,
    load_synthetic_data,
    BenchmarkDataProcessor,
)


@pytest.fixture
def temp_timeseries_file():
    """Create a temporary timeseries file with controlled test data."""
    data = [
        # doc1: 3 points in sequence
        {
            "metadata": {"document_id": "doc1", "sequence": 0},
            "results": {"value": 100}
        },
        {
            "metadata": {"document_id": "doc1", "sequence": 1},
            "results": {"value": 110}
        },
        {
            "metadata": {"document_id": "doc1", "sequence": 2},
            "results": {"value": 120}
        },
        # doc2: 1 point
        {
            "metadata": {"document_id": "doc2", "sequence": 0},
            "results": {"value": 200}
        },
        # doc3: 7 points (for size limit testing)
        *[
            {
                "metadata": {"document_id": "doc3", "sequence": i},
                "results": {"value": 300 + i * 10}
            }
            for i in range(7)
        ],
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        filepath = f.name

    yield filepath

    # Cleanup
    os.unlink(filepath)
    _reset_synthetic_timeseries_index()


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test."""
    _reset_synthetic_timeseries_index()
    yield
    _reset_synthetic_timeseries_index()


# Tests for load_synthetic_timeseries()

def test_load_returns_indexed_dict(temp_timeseries_file):
    """Test that loading timeseries returns a dict indexed by document_id."""
    index = load_synthetic_timeseries(temp_timeseries_file)

    # Should return a dict
    assert isinstance(index, dict)

    # Dict should have 3 documents
    assert len(index) == 3

    # Keys should be document_id strings
    assert "doc1" in index
    assert "doc2" in index
    assert "doc3" in index

    # Values should be lists of dicts
    assert isinstance(index["doc1"], list)
    assert len(index["doc1"]) == 3
    assert isinstance(index["doc1"][0], dict)

    # Each point should have metadata and results
    assert 'metadata' in index["doc1"][0]
    assert 'results' in index["doc1"][0]

    # Metadata should have document_id and sequence
    assert index["doc1"][0]['metadata']['document_id'] == "doc1"
    assert 'sequence' in index["doc1"][0]['metadata']


def test_points_sorted_by_sequence(temp_timeseries_file):
    """Test that points within each document are sorted by sequence number."""
    index = load_synthetic_timeseries(temp_timeseries_file)

    # Check doc3 which has 7 points
    points = index["doc3"]
    sequences = [p['metadata']['sequence'] for p in points]

    # Sequences should be in ascending order
    assert sequences == sorted(sequences)
    # Should start at 0
    assert sequences[0] == 0
    # Should be consecutive (no gaps)
    assert sequences == list(range(7))


def test_missing_file_returns_empty_dict():
    """Test that missing timeseries file returns empty dict without crashing."""
    nonexistent_path = "/tmp/this_file_does_not_exist_12345.json"

    # Should not raise exception
    index = load_synthetic_timeseries(filepath=nonexistent_path)

    # Should return empty dict
    assert index == {}


def test_missing_file_logs_warning(caplog):
    """Test that missing file logs a warning."""
    nonexistent_path = "/tmp/this_file_does_not_exist_12345.json"

    load_synthetic_timeseries(filepath=nonexistent_path)

    # Should have logged a warning
    assert any("not found" in record.message for record in caplog.records)
    assert any(nonexistent_path in record.message for record in caplog.records)


# Tests for lazy singleton pattern

def test_lazy_singleton_loads_once():
    """Test that singleton loads data only once across multiple calls."""
    with mock.patch('src.data_processing.load_synthetic_timeseries') as mock_load:
        mock_load.return_value = {'test_doc': [{'seq': 0}]}

        # First call should trigger load
        result1 = get_synthetic_timeseries_index()
        assert mock_load.call_count == 1

        # Second call should use cached result
        result2 = get_synthetic_timeseries_index()
        assert mock_load.call_count == 1  # Still 1, not 2

        # Both calls should return same object
        assert result1 is result2


def test_reset_clears_singleton():
    """Test that reset helper clears the singleton."""
    with mock.patch('src.data_processing.load_synthetic_timeseries') as mock_load:
        mock_load.return_value = {'test_doc': [{'seq': 0}]}

        # First call
        get_synthetic_timeseries_index()
        assert mock_load.call_count == 1

        # Reset
        _reset_synthetic_timeseries_index()

        # Next call should reload
        get_synthetic_timeseries_index()
        assert mock_load.call_count == 2


# Tests for fetch_synthetic_timeseries_for_document()

def test_fetch_known_document_returns_points(temp_timeseries_file):
    """Test that fetching timeseries for a known document_id returns points."""
    # Load data into singleton
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    # Fetch via the public API
    points = fetch_synthetic_timeseries_for_document("doc1")

    # Should return list of dicts
    assert isinstance(points, list)
    assert len(points) == 3
    assert isinstance(points[0], dict)

    # Points should have correct structure
    assert 'metadata' in points[0]
    assert 'results' in points[0]
    assert points[0]['metadata']['document_id'] == "doc1"


def test_fetch_unknown_document_returns_empty(temp_timeseries_file):
    """Test that fetching timeseries for unknown document_id returns empty list."""
    # Load data into singleton
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    nonexistent_id = "this_document_id_does_not_exist_12345"
    points = fetch_synthetic_timeseries_for_document(nonexistent_id)

    # Should return empty list, not None or error
    assert points == []


def test_fetch_respects_size_limit(temp_timeseries_file):
    """Test that size parameter limits number of points returned."""
    # Load data into singleton
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    # doc3 has 7 points
    points = fetch_synthetic_timeseries_for_document("doc3", size=5)

    # Should return exactly 5 points
    assert len(points) == 5


def test_fetch_points_sorted_by_sequence(temp_timeseries_file):
    """Test that fetched points are sorted by sequence number."""
    # Load data into singleton
    import src.data_processing
    src.data_processing._synthetic_timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    # Fetch points for doc3 (has multiple points)
    points = fetch_synthetic_timeseries_for_document("doc3")

    # Sequences should be in ascending order
    sequences = [p['metadata']['sequence'] for p in points]
    assert sequences == sorted(sequences)
    # Should start at 0
    assert sequences[0] == 0


# Test data separation

def test_timeseries_index_separate_from_benchmark_data(temp_timeseries_file):
    """Test that timeseries index does not pollute benchmark results DataFrame."""
    # Load both datasets
    results = load_synthetic_data()
    timeseries_index = load_synthetic_timeseries(temp_timeseries_file)

    # Convert results to DataFrame
    processor = BenchmarkDataProcessor()
    df = processor.documents_to_dataframe(results)

    # DataFrame columns should NOT include timeseries-specific fields
    timeseries_specific_fields = ['point_metrics', 'timeseries_id']
    for field in timeseries_specific_fields:
        assert field not in df.columns, \
            f"Timeseries field '{field}' leaked into results DataFrame"

    # Timeseries index should be a separate data structure
    assert isinstance(timeseries_index, dict)
    assert not isinstance(timeseries_index, pd.DataFrame)


# Integration test with real file (optional - skip if file missing)

@pytest.mark.skipif(
    not os.path.exists("data/synthetic/zathras_timeseries.json.gz"),
    reason="Real timeseries file not available"
)
def test_integration_load_real_timeseries_file():
    """Integration test: load real timeseries file if available."""
    index = load_synthetic_timeseries()

    # Should return non-empty dict
    assert isinstance(index, dict)
    assert len(index) > 0

    # Keys should be document_id strings
    first_key = next(iter(index.keys()))
    assert isinstance(first_key, str)

    # Values should be lists of dicts
    first_value = index[first_key]
    assert isinstance(first_value, list)
    assert len(first_value) > 0
    assert isinstance(first_value[0], dict)

    # Each point should have metadata and results
    assert 'metadata' in first_value[0]
    assert 'results' in first_value[0]


def test_roundtrip_generate_save_load_verify(tmp_path):
    """Test full roundtrip: generate → save → load → verify."""
    import json
    from src.synthetic_data import SyntheticDataGenerator
    from src.data_processing import load_synthetic_timeseries

    # Create sample result documents
    sample_results = [
        {
            "metadata": {
                "document_id": "roundtrip_test_001",
                "test_timestamp": "2026-01-25T10:00:00Z",
                "cloud_provider": "aws",
                "instance_type": "m5.large",
                "os_vendor": "redhat"
            },
            "test": {"name": "uperf", "version": "v1.0"},
            "results": {
                "status": "PASS",
                "total_runs": 1,
                "runs": {
                    "run_0": {
                        "status": "PASS",
                        "metrics": {
                            "throughput": 1000.0,
                            "latency": 10.0
                        }
                    }
                }
            }
        },
        {
            "metadata": {
                "document_id": "roundtrip_test_002",
                "test_timestamp": "2026-01-25T11:00:00Z",
                "cloud_provider": "gcp",
                "instance_type": "c2-standard-4",
                "os_vendor": "ubuntu"
            },
            "test": {"name": "fio", "version": "v3.0"},
            "results": {
                "status": "PASS",
                "total_runs": 1,
                "runs": {
                    "run_0": {
                        "status": "PASS",
                        "metrics": {
                            "iops": 5000.0,
                            "bandwidth": 500.0
                        }
                    }
                }
            }
        }
    ]

    # Step 1: Generate timeseries
    generator = SyntheticDataGenerator(seed=42)
    timeseries_docs = generator.generate_timeseries_documents(
        sample_results,
        short_sequence_range=(3, 5)  # Small range for faster test
    )

    # Verify generation worked
    assert len(timeseries_docs) > 0, "Should generate timeseries docs"

    # Step 2: Save to temp file
    temp_file = tmp_path / "test_timeseries.json"
    with open(temp_file, 'w') as f:
        json.dump(timeseries_docs, f)

    # Step 3: Load back
    loaded_index = load_synthetic_timeseries(str(temp_file))

    # Step 4: Verify roundtrip preservation
    # Check document_id mapping
    assert "roundtrip_test_001" in loaded_index, \
        "Should have timeseries for first result"
    assert "roundtrip_test_002" in loaded_index, \
        "Should have timeseries for second result"

    # Check point count preserved
    original_by_doc_id = {}
    for doc in timeseries_docs:
        doc_id = doc["metadata"]["document_id"]
        if doc_id not in original_by_doc_id:
            original_by_doc_id[doc_id] = []
        original_by_doc_id[doc_id].append(doc)

    for doc_id in ["roundtrip_test_001", "roundtrip_test_002"]:
        original_count = len(original_by_doc_id[doc_id])
        loaded_count = len(loaded_index[doc_id])
        assert original_count == loaded_count, \
            f"Point count mismatch for {doc_id}: {original_count} vs {loaded_count}"

    # Check sequence ordering preserved
    for doc_id in ["roundtrip_test_001", "roundtrip_test_002"]:
        loaded_points = loaded_index[doc_id]
        sequences = [p["metadata"]["sequence"] for p in loaded_points]
        assert sequences == sorted(sequences), \
            f"Loaded points for {doc_id} should be sorted by sequence"

    # Check metric values preserved (sample first point)
    first_doc_id = "roundtrip_test_001"
    loaded_first_point = loaded_index[first_doc_id][0]
    assert "throughput" in loaded_first_point["results"]["point_metrics"], \
        "Metrics should be preserved in loaded data"
