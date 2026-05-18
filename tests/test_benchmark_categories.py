"""Tests for benchmark category map (P1-C)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src import benchmark_categories as bc


def test_category_for_test_name_known():
    # pyperf: listed in metric_registry for primary metric, not in category JSON — expect Other
    assert bc.category_for_test_name("pyperf") == "Other"
    assert bc.category_for_test_name("uperf") == "Networking"
    assert bc.category_for_test_name("streams") == "HPC/Compute"
    assert bc.category_for_test_name("fio") == "Storage/IO"


def test_category_for_test_name_case_insensitive():
    assert bc.category_for_test_name("CoreMark") == "System"
    assert bc.category_for_test_name("UPerf") == "Networking"


def test_category_for_test_name_empty_other():
    assert bc.category_for_test_name("") == "Other"
    assert bc.category_for_test_name(None) == "Other"


def test_category_for_test_name_unmapped_benchmark():
    """Unmapped benchmarks should resolve to 'Other' category."""
    assert bc.category_for_test_name("unknown_benchmark_xyz") == "Other"
    assert bc.category_for_test_name("completely_unmapped") == "Other"


def test_benchmark_groups_matches_json_file():
    path = bc._JSON_PATH
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    assert bc.benchmark_groups() == {k: list(v) for k, v in raw.items()}


def test_reset_cache_for_tests_reloads_same_data():
    g1 = bc.benchmark_groups()
    bc.reset_benchmark_groups_cache_for_tests()
    g2 = bc.benchmark_groups()
    assert g1 == g2
    assert "Networking" in g2


def test_benchmark_groups_returns_independent_copies():
    g1 = bc.benchmark_groups()
    g2 = bc.benchmark_groups()
    assert g1 is not g2
    assert g1["Networking"] is not g2["Networking"]
    g1["Networking"].append("__mutation_probe__")
    assert "__mutation_probe__" not in bc.benchmark_groups()["Networking"]


def test_single_benchmark_category():
    """Test categories with exactly one benchmark work correctly."""
    groups = bc.benchmark_groups()
    # Networking has only one benchmark: uperf
    assert "Networking" in groups
    assert len(groups["Networking"]) == 1
    assert "uperf" in groups["Networking"]
    # Verify it resolves correctly
    assert bc.category_for_test_name("uperf") == "Networking"


def test_empty_category_handling():
    """Test that empty categories (if they exist) don't break the system."""
    bc.reset_benchmark_groups_cache_for_tests()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"EmptyCategory": [], "ValidCategory": ["test1"]}, f)
        temp_path = f.name

    try:
        with patch.object(bc, '_JSON_PATH', Path(temp_path)):
            bc.reset_benchmark_groups_cache_for_tests()
            groups = bc.benchmark_groups()
            # Empty categories should still be present
            assert "EmptyCategory" in groups
            assert len(groups["EmptyCategory"]) == 0
            # Unmapped benchmarks should still go to "Other"
            assert bc.category_for_test_name("some_test") == "Other"
    finally:
        Path(temp_path).unlink()
        bc.reset_benchmark_groups_cache_for_tests()


def test_load_groups_file_not_found():
    """Test error handling when JSON file doesn't exist."""
    bc.reset_benchmark_groups_cache_for_tests()
    with patch.object(bc, '_JSON_PATH', Path('/nonexistent/path/file.json')):
        bc.reset_benchmark_groups_cache_for_tests()
        groups = bc.benchmark_groups()
        # Should return empty dict on error
        assert groups == {}


def test_load_groups_invalid_json():
    """Test error handling for malformed JSON."""
    bc.reset_benchmark_groups_cache_for_tests()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{invalid json content")
        temp_path = f.name

    try:
        with patch.object(bc, '_JSON_PATH', Path(temp_path)):
            bc.reset_benchmark_groups_cache_for_tests()
            groups = bc.benchmark_groups()
            # Should return empty dict on JSON decode error
            assert groups == {}
    finally:
        Path(temp_path).unlink()
        bc.reset_benchmark_groups_cache_for_tests()


def test_load_groups_non_dict_data():
    """Test error handling when JSON is not a dict at top level."""
    bc.reset_benchmark_groups_cache_for_tests()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(["list", "instead", "of", "dict"], f)
        temp_path = f.name

    try:
        with patch.object(bc, '_JSON_PATH', Path(temp_path)):
            bc.reset_benchmark_groups_cache_for_tests()
            groups = bc.benchmark_groups()
            # Should return empty dict for non-dict data
            assert groups == {}
    finally:
        Path(temp_path).unlink()
        bc.reset_benchmark_groups_cache_for_tests()


def test_load_groups_invalid_category_entries():
    """Test that invalid category/test entries are skipped."""
    bc.reset_benchmark_groups_cache_for_tests()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "ValidCategory": ["test1", "test2"],
            123: ["should_be_skipped"],  # non-string category key
            "InvalidTests": "not_a_list",  # non-list value
            "MixedTypes": ["valid", 123, None, "also_valid"]  # mixed types in list
        }, f)
        temp_path = f.name

    try:
        with patch.object(bc, '_JSON_PATH', Path(temp_path)):
            bc.reset_benchmark_groups_cache_for_tests()
            groups = bc.benchmark_groups()
            # ValidCategory should be present
            assert "ValidCategory" in groups
            assert groups["ValidCategory"] == ["test1", "test2"]
            # Invalid entries should be skipped
            assert 123 not in groups
            assert "InvalidTests" not in groups
            # MixedTypes should only keep string entries
            assert "MixedTypes" in groups
            assert groups["MixedTypes"] == ["valid", "also_valid"]
    finally:
        Path(temp_path).unlink()
        bc.reset_benchmark_groups_cache_for_tests()
