"""
Tests for save_to_file() and save_to_jsonl() performance and reliability fixes.

Tests verify:
1. Memory-efficient file copying using shutil.copyfileobj instead of read()
2. Atomic file replacement using os.replace instead of os.replace
   (os.replace works cross-platform, os.rename fails on Windows when target exists)
"""

import json
import gzip
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.synthetic_data import SyntheticDataGenerator


@pytest.fixture
def generator():
    """Create a SyntheticDataGenerator instance."""
    return SyntheticDataGenerator(seed=42)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        {"id": 1, "name": "test1", "value": 100},
        {"id": 2, "name": "test2", "value": 200},
        {"id": 3, "name": "test3", "value": 300},
    ]


class TestSaveToFileCompression:
    """Test save_to_file() compression functionality."""

    def test_compressed_file_is_valid_gzip(self, generator, sample_documents, tmp_path):
        """Verify that compressed files can be read back correctly."""
        output_file = tmp_path / "test.json"

        # Force compression by setting threshold to 0
        generator.save_to_file(sample_documents, str(output_file), compress_threshold_mb=0)

        # Should create .gz file
        compressed_file = Path(str(output_file) + ".gz")
        assert compressed_file.exists()
        assert not output_file.exists()

        # Verify file is valid gzip and content matches
        with gzip.open(compressed_file, 'rt') as f:
            loaded_data = json.load(f)

        assert loaded_data == sample_documents

    def test_uncompressed_file_is_valid_json(self, generator, sample_documents, tmp_path):
        """Verify that uncompressed files are valid JSON."""
        output_file = tmp_path / "test.json"

        # Force no compression by setting very high threshold
        generator.save_to_file(sample_documents, str(output_file), compress_threshold_mb=1000)

        # Should create uncompressed file
        assert output_file.exists()
        assert not Path(str(output_file) + ".gz").exists()

        # Verify file is valid JSON
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)

        assert loaded_data == sample_documents


class TestSaveToJsonlCompression:
    """Test save_to_jsonl() compression functionality."""

    def test_compressed_jsonl_is_valid(self, generator, sample_documents, tmp_path):
        """Verify that compressed JSONL files can be read back correctly."""
        output_file = tmp_path / "test.jsonl"

        # Force compression by setting threshold to 0
        generator.save_to_jsonl(sample_documents, str(output_file), compress_threshold_mb=0)

        # Should create .gz file
        compressed_file = Path(str(output_file) + ".gz")
        assert compressed_file.exists()
        assert not output_file.exists()

        # Verify file is valid gzip and content matches (JSONL format)
        with gzip.open(compressed_file, 'rt') as f:
            loaded_data = [json.loads(line) for line in f]

        assert loaded_data == sample_documents

    def test_uncompressed_jsonl_is_valid(self, generator, sample_documents, tmp_path):
        """Verify that uncompressed JSONL files are valid."""
        output_file = tmp_path / "test.jsonl"

        # Force no compression by setting very high threshold
        generator.save_to_jsonl(sample_documents, str(output_file), compress_threshold_mb=1000)

        # Should create uncompressed file
        assert output_file.exists()
        assert not Path(str(output_file) + ".gz").exists()

        # Verify file is valid JSONL
        with open(output_file, 'r') as f:
            loaded_data = [json.loads(line) for line in f]

        assert loaded_data == sample_documents


class TestSaveToFileRerunability:
    """Test save_to_file() can be re-run to the same path."""

    def test_can_overwrite_existing_uncompressed_file(self, generator, sample_documents, tmp_path):
        """Verify that save_to_file() can overwrite an existing uncompressed file."""
        output_file = tmp_path / "test.json"

        # First save
        generator.save_to_file(sample_documents, str(output_file), compress_threshold_mb=1000)
        assert output_file.exists()

        # Modify documents
        modified_docs = [{"id": 99, "name": "modified", "value": 999}]

        # Second save to same path should succeed
        generator.save_to_file(modified_docs, str(output_file), compress_threshold_mb=1000)

        # Verify new content
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)

        assert loaded_data == modified_docs

    def test_can_overwrite_existing_compressed_file(self, generator, sample_documents, tmp_path):
        """Verify that save_to_file() can overwrite an existing compressed file."""
        output_file = tmp_path / "test.json"
        compressed_file = Path(str(output_file) + ".gz")

        # First save (compressed)
        generator.save_to_file(sample_documents, str(output_file), compress_threshold_mb=0)
        assert compressed_file.exists()

        # Modify documents
        modified_docs = [{"id": 99, "name": "modified", "value": 999}]

        # Second save to same path should succeed
        generator.save_to_file(modified_docs, str(output_file), compress_threshold_mb=0)

        # Verify new content
        with gzip.open(compressed_file, 'rt') as f:
            loaded_data = json.load(f)

        assert loaded_data == modified_docs


class TestSaveToJsonlRerunability:
    """Test save_to_jsonl() can be re-run to the same path."""

    def test_can_overwrite_existing_uncompressed_jsonl(self, generator, sample_documents, tmp_path):
        """Verify that save_to_jsonl() can overwrite an existing uncompressed file."""
        output_file = tmp_path / "test.jsonl"

        # First save
        generator.save_to_jsonl(sample_documents, str(output_file), compress_threshold_mb=1000)
        assert output_file.exists()

        # Modify documents
        modified_docs = [{"id": 99, "name": "modified", "value": 999}]

        # Second save to same path should succeed
        generator.save_to_jsonl(modified_docs, str(output_file), compress_threshold_mb=1000)

        # Verify new content
        with open(output_file, 'r') as f:
            loaded_data = [json.loads(line) for line in f]

        assert loaded_data == modified_docs

    def test_can_overwrite_existing_compressed_jsonl(self, generator, sample_documents, tmp_path):
        """Verify that save_to_jsonl() can overwrite an existing compressed file."""
        output_file = tmp_path / "test.jsonl"
        compressed_file = Path(str(output_file) + ".gz")

        # First save (compressed)
        generator.save_to_jsonl(sample_documents, str(output_file), compress_threshold_mb=0)
        assert compressed_file.exists()

        # Modify documents
        modified_docs = [{"id": 99, "name": "modified", "value": 999}]

        # Second save to same path should succeed
        generator.save_to_jsonl(modified_docs, str(output_file), compress_threshold_mb=0)

        # Verify new content
        with gzip.open(compressed_file, 'rt') as f:
            loaded_data = [json.loads(line) for line in f]

        assert loaded_data == modified_docs


class TestMemoryEfficientCopying:
    """Test that file copying uses shutil.copyfileobj instead of read()."""

    def test_save_to_file_uses_copyfileobj_for_compression(self, generator, sample_documents, tmp_path):
        """Verify that save_to_file uses shutil.copyfileobj instead of read() for memory efficiency."""
        output_file = tmp_path / "test.json"

        # Mock shutil.copyfileobj to verify it gets called
        with patch('src.synthetic_data.shutil.copyfileobj') as mock_copyfileobj:
            # Configure mock to actually copy the data
            def side_effect(src, dst, *args, **kwargs):
                # Read and write in chunks like the real copyfileobj
                while True:
                    chunk = src.read(16 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

            mock_copyfileobj.side_effect = side_effect

            # Force compression
            generator.save_to_file(sample_documents, str(output_file), compress_threshold_mb=0)

            # Verify copyfileobj was called
            assert mock_copyfileobj.called, "shutil.copyfileobj should be used for memory-efficient copying"

    def test_save_to_jsonl_uses_copyfileobj_for_compression(self, generator, sample_documents, tmp_path):
        """Verify that save_to_jsonl uses shutil.copyfileobj instead of read() for memory efficiency."""
        output_file = tmp_path / "test.jsonl"

        # Mock shutil.copyfileobj to verify it gets called
        with patch('src.synthetic_data.shutil.copyfileobj') as mock_copyfileobj:
            # Configure mock to actually copy the data
            def side_effect(src, dst, *args, **kwargs):
                # Read and write in chunks like the real copyfileobj
                while True:
                    chunk = src.read(16 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

            mock_copyfileobj.side_effect = side_effect

            # Force compression
            generator.save_to_jsonl(sample_documents, str(output_file), compress_threshold_mb=0)

            # Verify copyfileobj was called
            assert mock_copyfileobj.called, "shutil.copyfileobj should be used for memory-efficient copying"


class TestAtomicFileReplacement:
    """Test that file replacement uses os.replace instead of os.rename for cross-platform compatibility."""

    def test_save_to_file_uses_replace_not_rename(self, generator, sample_documents, tmp_path):
        """Verify that save_to_file uses os.replace instead of os.rename."""
        output_file = tmp_path / "test.json"

        with patch('src.synthetic_data.os.replace') as mock_replace, \
             patch('src.synthetic_data.os.rename') as mock_rename:

            # Force uncompressed to trigger rename/replace
            generator.save_to_file(sample_documents, str(output_file), compress_threshold_mb=1000)

            # Verify os.replace was called, not os.rename
            assert mock_replace.called, "os.replace should be used instead of os.rename"
            assert not mock_rename.called, "os.rename should not be used (use os.replace for cross-platform compatibility)"

    def test_save_to_jsonl_uses_replace_not_rename(self, generator, sample_documents, tmp_path):
        """Verify that save_to_jsonl uses os.replace instead of os.rename."""
        output_file = tmp_path / "test.jsonl"

        with patch('src.synthetic_data.os.replace') as mock_replace, \
             patch('src.synthetic_data.os.rename') as mock_rename:

            # Force uncompressed to trigger rename/replace
            generator.save_to_jsonl(sample_documents, str(output_file), compress_threshold_mb=1000)

            # Verify os.replace was called, not os.rename
            assert mock_replace.called, "os.replace should be used instead of os.rename"
            assert not mock_rename.called, "os.rename should not be used (use os.replace for cross-platform compatibility)"
