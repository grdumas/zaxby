"""
P1-E: Keep docs/guides/REGRESSION_DETECTION.md §1.1.1 in sync with code.

The canonical map is PRIMARY_METRIC_FALLBACK_KEYS in src/metric_registry.py; the
markdown table is a human-readable mirror. This test fails if a row or metric key
is added/changed in code without updating the doc (or vice versa).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.metric_registry import PRIMARY_METRIC_FALLBACK_KEYS

_REGRESSION_DOC = (
    Path(__file__).resolve().parents[1] / "docs" / "guides" / "REGRESSION_DETECTION.md"
)


@pytest.fixture(scope="module")
def regression_doc_text() -> str:
    assert _REGRESSION_DOC.is_file(), f"Missing {_REGRESSION_DOC}"
    return _REGRESSION_DOC.read_text(encoding="utf-8")


def test_regression_detection_doc_lists_every_registered_test_name(regression_doc_text: str) -> None:
    for test_name in sorted(PRIMARY_METRIC_FALLBACK_KEYS.keys()):
        assert (
            f"| `{test_name}` |" in regression_doc_text
        ), f"REGRESSION_DETECTION.md §1.1.1 missing row for test.name={test_name!r}"


def test_regression_detection_doc_mentions_every_fallback_key(regression_doc_text: str) -> None:
    for test_name, keys in PRIMARY_METRIC_FALLBACK_KEYS.items():
        for key in keys:
            assert key in regression_doc_text, (
                f"REGRESSION_DETECTION.md must document metric key {key!r} for {test_name!r}"
            )
