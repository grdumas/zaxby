"""
Tests for synthetic timeseries loading and querying.

These tests cover the loading, indexing, and querying of synthetic
timeseries data from data/synthetic/timeseries_results.json.
"""

import unittest
from unittest import mock
import os
import json
import tempfile
from typing import Dict, List, Any
import pandas as pd

from src.data_processing import (
    load_synthetic_timeseries,
    get_synthetic_timeseries_index,
    fetch_synthetic_timeseries_for_document,
    _reset_synthetic_timeseries_index,
)


class TestLoadSyntheticTimeseries(unittest.TestCase):
    """Tests for load_synthetic_timeseries() function."""

    def test_load_returns_indexed_dict(self):
        """Test that loading timeseries returns a dict indexed by document_id."""
        # Load the real timeseries file
        index = load_synthetic_timeseries()

        # Should return a dict
        self.assertIsInstance(index, dict)

        # Dict should not be empty
        self.assertGreater(len(index), 0)

        # Keys should be document_id strings
        first_key = next(iter(index.keys()))
        self.assertIsInstance(first_key, str)

        # Values should be lists of dicts
        first_value = index[first_key]
        self.assertIsInstance(first_value, list)
        self.assertGreater(len(first_value), 0)
        self.assertIsInstance(first_value[0], dict)

        # Each point should have metadata and results
        self.assertIn('metadata', first_value[0])
        self.assertIn('results', first_value[0])

        # Metadata should have document_id and sequence
        self.assertIn('document_id', first_value[0]['metadata'])
        self.assertIn('sequence', first_value[0]['metadata'])

    def test_points_sorted_by_sequence(self):
        """Test that points within each document are sorted by sequence number."""
        index = load_synthetic_timeseries()

        # Pick a document with multiple points
        for doc_id, points in index.items():
            if len(points) > 1:
                sequences = [p['metadata']['sequence'] for p in points]
                # Sequences should be in ascending order
                self.assertEqual(sequences, sorted(sequences))
                # Should start at 0
                self.assertEqual(sequences[0], 0)
                # Should be consecutive (no gaps)
                for i in range(len(sequences) - 1):
                    self.assertEqual(sequences[i+1], sequences[i] + 1)
                # Only need to check one document
                break

    def test_missing_file_returns_empty_dict(self):
        """Test that missing timeseries file returns empty dict without crashing."""
        # Use a filepath that doesn't exist
        nonexistent_path = "/tmp/this_file_does_not_exist_12345.json"

        # Should not raise exception
        index = load_synthetic_timeseries(filepath=nonexistent_path)

        # Should return empty dict
        self.assertEqual(index, {})

    def test_missing_file_logs_warning(self):
        """Test that missing file logs a warning."""
        nonexistent_path = "/tmp/this_file_does_not_exist_12345.json"

        with self.assertLogs('src.data_processing', level='WARNING') as cm:
            load_synthetic_timeseries(filepath=nonexistent_path)

        # Should have logged a warning
        self.assertEqual(len(cm.output), 1)
        self.assertIn('not found', cm.output[0])
        self.assertIn(nonexistent_path, cm.output[0])


class TestLazySingletonTimeseries(unittest.TestCase):
    """Tests for lazy singleton pattern in get_synthetic_timeseries_index()."""

    def setUp(self):
        """Reset singleton before each test."""
        _reset_synthetic_timeseries_index()

    def tearDown(self):
        """Reset singleton after each test."""
        _reset_synthetic_timeseries_index()

    def test_lazy_singleton_loads_once(self):
        """Test that singleton loads data only once across multiple calls."""
        with mock.patch('src.data_processing.load_synthetic_timeseries') as mock_load:
            mock_load.return_value = {'test_doc': [{'seq': 0}]}

            # First call should trigger load
            result1 = get_synthetic_timeseries_index()
            self.assertEqual(mock_load.call_count, 1)

            # Second call should use cached result
            result2 = get_synthetic_timeseries_index()
            self.assertEqual(mock_load.call_count, 1)  # Still 1, not 2

            # Both calls should return same object
            self.assertIs(result1, result2)

    def test_reset_clears_singleton(self):
        """Test that reset helper clears the singleton."""
        with mock.patch('src.data_processing.load_synthetic_timeseries') as mock_load:
            mock_load.return_value = {'test_doc': [{'seq': 0}]}

            # First call
            get_synthetic_timeseries_index()
            self.assertEqual(mock_load.call_count, 1)

            # Reset
            _reset_synthetic_timeseries_index()

            # Next call should reload
            get_synthetic_timeseries_index()
            self.assertEqual(mock_load.call_count, 2)


class TestFetchSyntheticTimeseriesForDocument(unittest.TestCase):
    """Tests for fetch_synthetic_timeseries_for_document() function."""

    def setUp(self):
        """Reset singleton before each test."""
        _reset_synthetic_timeseries_index()

    def tearDown(self):
        """Reset singleton after each test."""
        _reset_synthetic_timeseries_index()

    def test_fetch_known_document_returns_points(self):
        """Test that fetching timeseries for a known document_id returns points."""
        # Use the real data - load it first to find a real document_id
        index = load_synthetic_timeseries()
        # Pick any document_id with points
        doc_id = next(iter(index.keys()))

        # Now fetch via the public API
        points = fetch_synthetic_timeseries_for_document(doc_id)

        # Should return list of dicts
        self.assertIsInstance(points, list)
        self.assertGreater(len(points), 0)
        self.assertIsInstance(points[0], dict)

        # Points should have correct structure
        self.assertIn('metadata', points[0])
        self.assertIn('results', points[0])
        self.assertIn('document_id', points[0]['metadata'])
        self.assertEqual(points[0]['metadata']['document_id'], doc_id)

    def test_fetch_unknown_document_returns_empty(self):
        """Test that fetching timeseries for unknown document_id returns empty list."""
        nonexistent_id = "this_document_id_does_not_exist_12345"

        points = fetch_synthetic_timeseries_for_document(nonexistent_id)

        # Should return empty list, not None or error
        self.assertEqual(points, [])

    def test_fetch_respects_size_limit(self):
        """Test that size parameter limits number of points returned."""
        # Load real data and find a document with many points
        index = load_synthetic_timeseries()

        # Find a document with > 5 points
        doc_id_with_many_points = None
        for doc_id, pts in index.items():
            if len(pts) > 5:
                doc_id_with_many_points = doc_id
                break

        self.assertIsNotNone(doc_id_with_many_points, "Need a document with >5 points for this test")

        # Fetch with size limit
        points = fetch_synthetic_timeseries_for_document(doc_id_with_many_points, size=5)

        # Should return exactly 5 points
        self.assertEqual(len(points), 5)

    def test_fetch_points_sorted_by_sequence(self):
        """Test that fetched points are sorted by sequence number."""
        # Load real data and find a document with multiple points
        index = load_synthetic_timeseries()

        # Find a document with multiple points
        doc_id = None
        for did, pts in index.items():
            if len(pts) > 1:
                doc_id = did
                break

        self.assertIsNotNone(doc_id, "Need a document with multiple points for this test")

        # Fetch points
        points = fetch_synthetic_timeseries_for_document(doc_id)

        # Sequences should be in ascending order
        sequences = [p['metadata']['sequence'] for p in points]
        self.assertEqual(sequences, sorted(sequences))

        # Should start at 0
        self.assertEqual(sequences[0], 0)


class TestTimeseriesSeparationFromResults(unittest.TestCase):
    """Test that timeseries data is kept separate from results DataFrame."""

    def test_timeseries_index_separate_from_benchmark_data(self):
        """Test that timeseries index does not pollute benchmark results DataFrame."""
        from src.data_processing import load_synthetic_data, BenchmarkDataProcessor

        # Load both datasets
        results = load_synthetic_data()
        timeseries_index = load_synthetic_timeseries()

        # Convert results to DataFrame
        processor = BenchmarkDataProcessor()
        df = processor.documents_to_dataframe(results)

        # DataFrame columns should NOT include timeseries-specific fields
        timeseries_specific_fields = ['point_metrics', 'timeseries_id']
        for field in timeseries_specific_fields:
            self.assertNotIn(field, df.columns,
                           f"Timeseries field '{field}' leaked into results DataFrame")

        # Timeseries index should be a separate data structure
        self.assertIsInstance(timeseries_index, dict)
        self.assertNotIsInstance(timeseries_index, pd.DataFrame)


if __name__ == '__main__':
    unittest.main()
