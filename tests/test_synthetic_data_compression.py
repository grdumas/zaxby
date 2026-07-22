"""
Tests for synthetic data compression and metadata features.
"""

import json
import gzip
import os
import tempfile
from datetime import datetime
from src.synthetic_data import SyntheticDataGenerator


def test_compression_forced_with_zero_threshold():
    """Test that compression is applied deterministically when threshold is 0.

    This tests compression logic independent of dataset size by forcing
    compression regardless of file size. More reliable than assuming a
    specific dataset will exceed a size threshold.
    """
    generator = SyntheticDataGenerator(seed=42)

    # Create minimal test data - we're testing compression logic, not data generation
    # Just need enough to verify compression/decompression works correctly
    documents = [
        {"metadata": {"id": i, "test": "compression"}, "data": f"test_{i}"}
        for i in range(3)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "compressed_file.json")

        # Force compression with threshold=0 (any file size triggers compression)
        generator.save_to_file(documents, output_file, compress_threshold_mb=0)

        # Should create .gz file even for tiny data
        assert os.path.exists(output_file + ".gz"), "Compressed file should exist"
        assert not os.path.exists(output_file), "Uncompressed file should not exist"

        # Verify can read back the compressed data
        with gzip.open(output_file + ".gz", 'rt') as f:
            loaded_data = json.load(f)

        assert len(loaded_data) == len(documents), "Should preserve all documents"
        # Verify document structure is preserved
        assert loaded_data[0]["metadata"]["id"] == documents[0]["metadata"]["id"]
        assert loaded_data[2]["data"] == documents[2]["data"]


def test_save_with_compression_for_large_files():
    """Test that compression is applied when file size exceeds threshold.

    Uses compress_threshold_mb=0 to deterministically trigger compression,
    avoiding brittleness from assumptions about generated dataset size.
    """
    generator = SyntheticDataGenerator(seed=42)

    # Create moderate test data - testing compression threshold logic
    # Using a small dataset since we force compression with threshold=0
    documents = [
        {
            "metadata": {"id": i, "test": "compression"},
            "data": f"test_data_{i}" * 100  # Some content to compress
        }
        for i in range(10)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "large_file.json")

        # Force compression with threshold=0 (deterministic behavior)
        generator.save_to_file(documents, output_file, compress_threshold_mb=0)

        # Should create .gz file when threshold=0
        assert os.path.exists(output_file + ".gz"), "Compressed file should exist"
        assert not os.path.exists(output_file), "Uncompressed file should not exist"

        # Verify can read back the compressed data
        with gzip.open(output_file + ".gz", 'rt') as f:
            loaded_data = json.load(f)

        assert len(loaded_data) == len(documents), "Should preserve all documents"
        assert loaded_data[5]["data"] == documents[5]["data"], "Should preserve document content"


def test_no_compression_when_below_threshold():
    """Test that files below threshold are not compressed.

    Uses a high threshold to deterministically prevent compression,
    avoiding brittleness from assumptions about generated dataset size.
    """
    generator = SyntheticDataGenerator(seed=42)

    # Create small test data
    documents = [
        {"metadata": {"id": i}, "data": f"test_{i}"}
        for i in range(5)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "small_file.json")

        # Use very high threshold to ensure no compression (deterministic behavior)
        generator.save_to_file(documents, output_file, compress_threshold_mb=999)

        # Should create regular JSON file when below threshold
        assert os.path.exists(output_file), "Uncompressed file should exist"
        assert not os.path.exists(output_file + ".gz"), "Should not create .gz for small files"

        # Verify can read back the uncompressed data
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)

        assert len(loaded_data) == len(documents), "Should preserve all documents"
        assert loaded_data[3]["data"] == documents[3]["data"], "Should preserve document content"


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
    assert "avg_points_per_passing_result" in metadata
    assert "unique_timeseries_sequences" in metadata
    assert "dataset_characteristics" in metadata

    # Verify values
    assert metadata["result_document_count"] == len(result_docs)
    assert metadata["timeseries_document_count"] == len(timeseries_docs)
    assert metadata["avg_points_per_passing_result"] > 0

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
