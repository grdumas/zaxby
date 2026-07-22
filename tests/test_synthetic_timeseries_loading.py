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

from src.data_processing import (
    load_synthetic_timeseries,
    get_synthetic_timeseries_index,
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


if __name__ == '__main__':
    unittest.main()
