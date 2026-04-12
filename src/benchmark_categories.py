"""
Benchmark category map (Phase 1, P1-C).

Maps ``test.name`` values to high-level categories for grouping, filters, and UI.
Authoritative list: ``data/benchmark_categories.json`` (category → benchmark name tokens).

Benchmarks not listed there (e.g. ``pyperf``) resolve to ``\"Other\"``; that is intentional
unless product adds a token for them in the JSON.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "benchmark_categories.json"

_benchmark_groups_cache: Optional[Dict[str, List[str]]] = None


def _load_groups() -> Dict[str, List[str]]:
    try:
        with open(_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Could not load benchmark categories from %s: %s", _JSON_PATH, e)
        return {}
    if not isinstance(data, dict):
        logger.error("benchmark_categories.json must be a JSON object at top level")
        return {}
    out: Dict[str, List[str]] = {}
    for category, tests in data.items():
        if not isinstance(category, str) or not isinstance(tests, list):
            continue
        out[category] = [t for t in tests if isinstance(t, str)]
    return out


def benchmark_groups() -> Dict[str, List[str]]:
    """
    Return category → list of ``test.name`` tokens (order preserved).

    Data is loaded once and cached internally; each call returns a **new** dict and
    copied lists so callers cannot mutate the shared cache.
    """
    global _benchmark_groups_cache
    if _benchmark_groups_cache is None:
        _benchmark_groups_cache = _load_groups()
    return {k: list(v) for k, v in _benchmark_groups_cache.items()}


def category_for_test_name(test_name: Optional[str]) -> str:
    """
    Resolve a category label for ``test.name``, or ``Other`` if unknown.

    Matching follows the same substring rules as the former
    :class:`BenchmarkDataProcessor` inline map (case-insensitive).
    """
    if not test_name:
        return "Other"
    test_lower = test_name.lower()
    for category, tests in benchmark_groups().items():
        if any(test.lower() in test_lower or test_lower in test.lower() for test in tests):
            return category
    return "Other"


def reset_benchmark_groups_cache_for_tests() -> None:
    """Clear cached groups (pytest only)."""
    global _benchmark_groups_cache
    _benchmark_groups_cache = None
