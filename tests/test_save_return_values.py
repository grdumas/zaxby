"""
Tests for save_to_file() and save_to_jsonl() return values.

These tests verify that both save methods return the actual path written
(either the original filename or filename + '.gz' when compression is applied).
"""

import json
import gzip
import os
import tempfile
from src.synthetic_data import SyntheticDataGenerator


def test_save_to_file_returns_path_when_no_compression():
    """Test that save_to_file() returns the original path when no compression."""
    generator = SyntheticDataGenerator(seed=42)

    # Create a small dataset (< 10MB, no compression)
    documents = generator.generate_dataset(
        num_scenarios=5,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "small_file.json")

        # Save without compression
        actual_path = generator.save_to_file(documents, output_file, compress_threshold_mb=10)

        # Should return the original path
        assert actual_path == output_file, f"Expected {output_file}, got {actual_path}"
        assert os.path.exists(actual_path), "Returned path should exist"


def test_save_to_file_returns_compressed_path_when_compression():
    """Test that save_to_file() returns .gz path when compression is forced via threshold=0."""
    generator = SyntheticDataGenerator(seed=42)

    # Create a small dataset, force compression via threshold=0
    documents = generator.generate_dataset(
        num_scenarios=5,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "compressed_file.json")

        # Save with compression forced by threshold=0
        actual_path = generator.save_to_file(documents, output_file, compress_threshold_mb=0)

        # Should return the compressed path
        expected_path = output_file + ".gz"
        assert actual_path == expected_path, f"Expected {expected_path}, got {actual_path}"
        assert os.path.exists(actual_path), "Returned path should exist"


def test_save_to_jsonl_returns_path_when_no_compression():
    """Test that save_to_jsonl() returns the original path when no compression."""
    generator = SyntheticDataGenerator(seed=42)

    # Create a small dataset
    documents = generator.generate_dataset(
        num_scenarios=3,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "small_file.jsonl")

        # Save without compression
        actual_path = generator.save_to_jsonl(documents, output_file, compress_threshold_mb=10)

        # Should return the original path
        assert actual_path == output_file, f"Expected {output_file}, got {actual_path}"
        assert os.path.exists(actual_path), "Returned path should exist"


def test_save_to_jsonl_returns_compressed_path_when_compression():
    """Test that save_to_jsonl() returns .gz path when compression is forced via threshold=0."""
    generator = SyntheticDataGenerator(seed=42)

    # Create a small dataset, force compression via threshold=0
    documents = generator.generate_dataset(
        num_scenarios=5,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "compressed_file.jsonl")

        # Save with compression forced by threshold=0
        actual_path = generator.save_to_jsonl(documents, output_file, compress_threshold_mb=0)

        # Should return the compressed path
        expected_path = output_file + ".gz"
        assert actual_path == expected_path, f"Expected {expected_path}, got {actual_path}"
        assert os.path.exists(actual_path), "Returned path should exist"


def test_main_uses_returned_paths_for_size_checks():
    """
    Test that main() can use the returned paths for getsize() calls.

    This is a regression test for the FileNotFoundError bug where main()
    tried to getsize() on uncompressed paths when compression was applied.
    """
    generator = SyntheticDataGenerator(seed=42)

    # Create documents that will compress
    documents = generator.generate_dataset(
        num_scenarios=50,
        iterations_per_scenario=5,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_file.json")

        # Save and get the actual path
        actual_path = generator.save_to_file(documents, output_file, compress_threshold_mb=10)

        # This should NOT raise FileNotFoundError
        file_size = os.path.getsize(actual_path)
        assert file_size > 0, "File should have non-zero size"

        # Verify we got the compressed path
        if actual_path.endswith(".gz"):
            assert not os.path.exists(output_file), "Original file should not exist"
            assert os.path.exists(actual_path), "Compressed file should exist"
