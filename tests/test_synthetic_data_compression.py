"""
Tests for synthetic data compression and metadata features.
"""

import json
import gzip
import os
import tempfile
from datetime import datetime
from src.synthetic_data import SyntheticDataGenerator


def test_save_with_compression_for_large_files():
    """Test that files > 10MB are automatically compressed with gzip."""
    generator = SyntheticDataGenerator(seed=42)

    # Create a large enough dataset (will be > 10MB)
    documents = generator.generate_dataset(
        num_scenarios=100,
        iterations_per_scenario=10,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "large_file.json")

        # Save with compression
        generator.save_to_file(documents, output_file, compress_threshold_mb=10)

        # Should create .gz file for large data
        assert os.path.exists(output_file + ".gz"), "Compressed file should exist"

        # Verify can read back the compressed data
        with gzip.open(output_file + ".gz", 'rt') as f:
            loaded_data = json.load(f)

        assert len(loaded_data) == len(documents), "Should preserve all documents"


def test_no_compression_for_small_files():
    """Test that files < 10MB are not compressed."""
    generator = SyntheticDataGenerator(seed=42)

    # Create a small dataset
    documents = generator.generate_dataset(
        num_scenarios=5,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "small_file.json")

        # Save without compression (below threshold)
        generator.save_to_file(documents, output_file, compress_threshold_mb=10)

        # Should create regular JSON file
        assert os.path.exists(output_file), "Uncompressed file should exist"
        assert not os.path.exists(output_file + ".gz"), "Should not create .gz for small files"


def test_save_to_jsonl_format():
    """Test saving documents in JSONL format (one JSON per line)."""
    generator = SyntheticDataGenerator(seed=42)

    documents = generator.generate_dataset(
        num_scenarios=3,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=False
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "output.jsonl")

        # Save as JSONL
        generator.save_to_jsonl(documents, output_file)

        assert os.path.exists(output_file), "JSONL file should be created"

        # Verify JSONL format (one JSON per line)
        with open(output_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == len(documents), "Should have one line per document"

        # Each line should be valid JSON
        for line in lines:
            doc = json.loads(line)
            assert "metadata" in doc
            assert "test" in doc


def test_generation_metadata_structure():
    """Test that generation metadata has correct structure."""
    generator = SyntheticDataGenerator(seed=42)

    result_docs = generator.generate_dataset(
        num_scenarios=10,
        iterations_per_scenario=2,
        include_temporal_trends=True,
        include_failures=True
    )

    timeseries_docs = generator.generate_timeseries_documents(
        result_docs,
        short_sequence_range=(10, 20),
        long_sequence_range=(50, 100),
        long_sequence_probability=0.20,
        point_interval_seconds=30
    )

    metadata = generator.build_generation_metadata(result_docs, timeseries_docs)

    # Required fields
    assert "generation_timestamp" in metadata
    assert "result_document_count" in metadata
    assert "timeseries_document_count" in metadata
    assert "avg_points_per_result" in metadata
    assert "unique_timeseries_sequences" in metadata
    assert "dataset_characteristics" in metadata

    # Verify values
    assert metadata["result_document_count"] == len(result_docs)
    assert metadata["timeseries_document_count"] == len(timeseries_docs)
    assert metadata["avg_points_per_result"] > 0

    # Timestamp should be valid ISO format
    datetime.fromisoformat(metadata["generation_timestamp"].replace("Z", "+00:00"))


def test_metadata_includes_sequence_length_distribution():
    """Test that metadata includes distribution of sequence lengths."""
    generator = SyntheticDataGenerator(seed=42)

    result_docs = generator.generate_dataset(
        num_scenarios=20,
        iterations_per_scenario=2,
        include_temporal_trends=False,
        include_failures=True
    )

    timeseries_docs = generator.generate_timeseries_documents(
        result_docs,
        short_sequence_range=(10, 20),
        long_sequence_range=(50, 100),
        long_sequence_probability=0.20,
        point_interval_seconds=30
    )

    metadata = generator.build_generation_metadata(result_docs, timeseries_docs)

    # Should include sequence length distribution
    characteristics = metadata["dataset_characteristics"]
    assert "short_sequences_count" in characteristics
    assert "long_sequences_count" in characteristics
    assert "short_sequence_range" in characteristics
    assert "long_sequence_range" in characteristics

    # Verify reasonable distribution (roughly 80/20 split)
    short_count = characteristics["short_sequences_count"]
    long_count = characteristics["long_sequences_count"]
    total_sequences = short_count + long_count

    if total_sequences > 0:
        short_pct = short_count / total_sequences
        # Should be roughly 80% short sequences (allow some variance)
        assert 0.6 <= short_pct <= 0.95, f"Expected ~80% short sequences, got {short_pct*100:.1f}%"
