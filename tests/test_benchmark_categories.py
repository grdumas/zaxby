"""Tests for benchmark category map (P1-C)."""

import json

from src import benchmark_categories as bc


def test_category_for_test_name_known():
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
