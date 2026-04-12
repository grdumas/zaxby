"""Tests for primary metric registry (P1-E)."""

from src.metric_registry import (
    PRIMARY_METRIC_FALLBACK_KEYS,
    fallback_keys_for_test,
    registered_test_names,
)


def test_fallback_keys_pyperf_mean():
    assert fallback_keys_for_test("pyperf") == ["mean"]
    assert fallback_keys_for_test("PyPerf") == ["mean"]


def test_fallback_keys_unknown_test_empty():
    assert fallback_keys_for_test("unknown_benchmark_xyz") == []
    assert fallback_keys_for_test(None) == []
    assert fallback_keys_for_test("") == []
    assert fallback_keys_for_test("   ") == []


def test_fallback_keys_streams_order_preserved():
    keys = fallback_keys_for_test("streams")
    assert keys[0] == "triad__mb_per_sec"
    assert len(keys) == 3


def test_registry_exposes_same_keys_as_dict():
    assert "coremark" in PRIMARY_METRIC_FALLBACK_KEYS
    assert registered_test_names() == frozenset(PRIMARY_METRIC_FALLBACK_KEYS.keys())
