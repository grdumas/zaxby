"""Tests for Task #6 (deterministic metadata timestamp) and Task #8 (makedirs fix)."""

import os
import tempfile
from datetime import datetime, timezone
import pytest
from src.synthetic_data import SyntheticDataGenerator


class TestTask6DeterministicTimestamp:
    """Test that build_generation_metadata() produces deterministic timestamps."""

    def test_reproducible_metadata_with_fixed_seed_and_timestamp(self):
        """Test full reproducibility: same seed + same timestamp = identical metadata."""
        # Generate two identical datasets
        gen1 = SyntheticDataGenerator(seed=100)
        docs1 = gen1.generate_dataset(num_scenarios=3, iterations_per_scenario=1)
        ts_docs1 = gen1.generate_timeseries_documents(docs1)

        gen2 = SyntheticDataGenerator(seed=100)
        docs2 = gen2.generate_dataset(num_scenarios=3, iterations_per_scenario=1)
        ts_docs2 = gen2.generate_timeseries_documents(docs2)

        # Use same explicit timestamp
        fixed_timestamp = "2026-01-15T12:00:00Z"

        metadata1 = gen1.build_generation_metadata(docs1, ts_docs1, fixed_timestamp)
        metadata2 = gen2.build_generation_metadata(docs2, ts_docs2, fixed_timestamp)

        # All metadata fields should be identical
        assert metadata1 == metadata2

class TestTask6DeterministicTimestampOriginal:
    """Test that build_generation_metadata() produces deterministic timestamps."""

    def test_default_timestamp_uses_now(self):
        """Test that default behavior uses datetime.now()."""
        generator = SyntheticDataGenerator(seed=42)

        # Create minimal test data
        result_docs = []
        timeseries_docs = []

        # Call without explicit timestamp
        metadata1 = generator.build_generation_metadata(result_docs, timeseries_docs)

        # Should have a timestamp
        assert "generation_timestamp" in metadata1

        # Parse timestamp to verify it's valid ISO format with Z suffix
        timestamp_str = metadata1["generation_timestamp"]
        assert timestamp_str.endswith("Z")

        # Should be parseable as ISO datetime
        parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None  # Should have timezone info

    def test_explicit_timestamp_is_deterministic(self):
        """Test that providing explicit timestamp makes metadata deterministic."""
        generator = SyntheticDataGenerator(seed=42)

        # Create minimal test data
        result_docs = []
        timeseries_docs = []

        # Use explicit timestamp
        fixed_timestamp = "2026-01-15T12:00:00Z"

        # Generate metadata twice with same timestamp
        metadata1 = generator.build_generation_metadata(
            result_docs,
            timeseries_docs,
            generation_timestamp=fixed_timestamp
        )
        metadata2 = generator.build_generation_metadata(
            result_docs,
            timeseries_docs,
            generation_timestamp=fixed_timestamp
        )

        # Timestamps should be identical
        assert metadata1["generation_timestamp"] == fixed_timestamp
        assert metadata2["generation_timestamp"] == fixed_timestamp
        assert metadata1["generation_timestamp"] == metadata2["generation_timestamp"]

    def test_explicit_timestamp_in_metadata_structure(self):
        """Test that explicit timestamp appears correctly in full metadata structure."""
        generator = SyntheticDataGenerator(seed=42)

        # Create realistic test data with one passing result
        result_docs = [{
            "metadata": {
                "document_id": "test_001",
                "test_timestamp": "2026-01-15T10:00:00Z",
                "cloud_provider": "aws",
                "instance_type": "m5.xlarge",
                "os_vendor": "rhel"
            },
            "results": {
                "status": "PASS",
                "runs": {
                    "run_0": {
                        "metrics": {
                            "score": 100.0
                        }
                    }
                }
            },
            "test": {
                "name": "coremark"
            }
        }]

        # One timeseries sequence with 10 points
        timeseries_docs = []
        for seq in range(10):
            timeseries_docs.append({
                "metadata": {
                    "timeseries_id": "ts_001",
                    "document_id": "test_001",
                    "sequence": seq
                }
            })

        fixed_timestamp = "2026-01-15T12:00:00Z"

        metadata = generator.build_generation_metadata(
            result_docs,
            timeseries_docs,
            generation_timestamp=fixed_timestamp
        )

        # Verify structure and timestamp
        assert metadata["generation_timestamp"] == fixed_timestamp
        assert metadata["result_document_count"] == 1
        assert metadata["timeseries_document_count"] == 10
        assert metadata["unique_timeseries_sequences"] == 1


class TestTask8MakedirsWithNoDir:
    """Test that save_to_file() handles filenames without directory component."""

    def test_save_to_file_with_no_directory(self):
        """Test that save_to_file works with filename in current directory."""
        generator = SyntheticDataGenerator(seed=42)

        # Create minimal test data
        docs = [{
            "metadata": {"id": "test_1"},
            "test": {"name": "coremark"},
            "results": {"status": "PASS"}
        }]

        # Use temporary directory as working directory
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # This should not raise an error even with no directory component
                # save_to_file should check if dirname is empty before calling makedirs
                filename = "output.json"
                generator.save_to_file(docs, filename)

                # Verify file was created
                assert os.path.exists(filename)
                assert os.path.isfile(filename)

                # Verify content
                import json
                with open(filename, 'r') as f:
                    loaded = json.load(f)
                assert len(loaded) == 1
                assert loaded[0]["metadata"]["id"] == "test_1"

            finally:
                os.chdir(original_cwd)

    def test_save_to_jsonl_with_no_directory(self):
        """Test that save_to_jsonl works with filename in current directory."""
        generator = SyntheticDataGenerator(seed=42)

        # Create minimal test data
        docs = [{
            "metadata": {"id": "test_1"},
            "test": {"name": "coremark"},
            "results": {"status": "PASS"}
        }]

        # Use temporary directory as working directory
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # This should not raise an error even with no directory component
                filename = "output.jsonl"
                generator.save_to_jsonl(docs, filename)

                # Verify file was created
                assert os.path.exists(filename)
                assert os.path.isfile(filename)

                # Verify content (JSONL format)
                import json
                with open(filename, 'r') as f:
                    lines = f.readlines()
                assert len(lines) == 1
                loaded = json.loads(lines[0])
                assert loaded["metadata"]["id"] == "test_1"

            finally:
                os.chdir(original_cwd)

    def test_save_to_file_with_directory_still_works(self):
        """Test that save_to_file still works with directory component."""
        generator = SyntheticDataGenerator(seed=42)

        # Create minimal test data
        docs = [{
            "metadata": {"id": "test_1"},
            "test": {"name": "coremark"},
            "results": {"status": "PASS"}
        }]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use subdirectory path
            filename = os.path.join(tmpdir, "subdir", "output.json")
            generator.save_to_file(docs, filename)

            # Verify file was created
            assert os.path.exists(filename)
            assert os.path.isfile(filename)

            # Verify parent directory was created
            assert os.path.exists(os.path.join(tmpdir, "subdir"))
            assert os.path.isdir(os.path.join(tmpdir, "subdir"))

    def test_save_to_file_with_compression_no_directory(self):
        """Test save_to_file with compression (forced via threshold=0) when filename has no directory."""
        generator = SyntheticDataGenerator(seed=42)

        # Create minimal test data (compression forced via threshold=0)
        docs = [
            {"metadata": {"id": "test_1"}, "test": {"name": "coremark"}, "results": {"status": "PASS"}},
            {"metadata": {"id": "test_2"}, "test": {"name": "dhrystone"}, "results": {"status": "PASS"}},
            {"metadata": {"id": "test_3"}, "test": {"name": "iperf3"}, "results": {"status": "FAIL"}}
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Force compression by setting threshold to 0
                filename = "large_output.json"
                generator.save_to_file(docs, filename, compress_threshold_mb=0)

                # Should create compressed file
                compressed_filename = filename + ".gz"
                assert os.path.exists(compressed_filename)

                # Verify it's actually gzip compressed
                import gzip
                with gzip.open(compressed_filename, 'rb') as f:
                    content = f.read()
                    assert len(content) > 0

            finally:
                os.chdir(original_cwd)
