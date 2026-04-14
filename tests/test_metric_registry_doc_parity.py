"""
P1-E: Keep docs/guides/REGRESSION_DETECTION.md §1.1.1 in sync with code.

The canonical map is PRIMARY_METRIC_FALLBACK_KEYS in src/metric_registry.py; the
markdown table is a human-readable mirror.

Enforcement (see tests below):

- **Bidirectional ``test.name`` sets:** ``test_fallback_table_test_names_match_registry_both_ways``
  requires ``set(registry keys) == set(parsed §1.1.1 table first columns)``. That
  catches registry entries missing from the doc *and* extra doc-only rows (doc
  cannot drift ahead of code).

- **Keys scoped to each table row:** ``test_fallback_table_rows_document_registry_keys_with_backticks``
  checks each metric key appears as a Markdown `` `key` `` token in *that row's*
  second column only—not ``key in full_document``, which would false-pass for
  short tokens (``mean``, ``score``, etc.) in unrelated prose.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.metric_registry import PRIMARY_METRIC_FALLBACK_KEYS

_REGRESSION_DOC = (
    Path(__file__).resolve().parents[1] / "docs" / "guides" / "REGRESSION_DETECTION.md"
)

_SECTION_111_HEADING = "#### 1.1.1 Canonical"
_TABLE_TAIL = "Benchmarks not listed rely on"


def _extract_section_111_table_block(full_doc: str) -> str:
    """Return markdown fragment containing the §1.1.1 table (header + rows)."""
    if _SECTION_111_HEADING not in full_doc:
        pytest.fail("REGRESSION_DETECTION.md: missing §1.1.1 heading")
    after = full_doc.split(_SECTION_111_HEADING, 1)[1]
    if _TABLE_TAIL in after:
        return after.split(_TABLE_TAIL, 1)[0]
    if "### 1.2" in after:
        return after.split("### 1.2", 1)[0]
    pytest.fail("REGRESSION_DETECTION.md: could not bound §1.1.1 table (no tail marker)")


# Data rows: | `test_name` | `key1`, `key2` |
_ROW_RE = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|?\s*$",
)


def _parse_fallback_table_rows(table_block: str) -> dict[str, str]:
    """
    Parse data rows into ``test.name`` -> second-column text (metric keys cell).

    Skips the header row (first column ``test.name`` without leading backtick in
    the pattern we match) and separator lines.
    """
    rows: dict[str, str] = {}
    for line in table_block.splitlines():
        line = line.rstrip()
        m = _ROW_RE.match(line)
        if not m:
            continue
        test_name, second_col = m.group(1), m.group(2).strip()
        if test_name == "test.name":
            continue
        rows[test_name] = second_col
    return rows


@pytest.fixture(scope="module")
def regression_doc_text() -> str:
    if not _REGRESSION_DOC.is_file():
        pytest.fail(f"Missing {_REGRESSION_DOC}")
    return _REGRESSION_DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def section_111_table_block(regression_doc_text: str) -> str:
    return _extract_section_111_table_block(regression_doc_text)


@pytest.fixture(scope="module")
def parsed_fallback_table(section_111_table_block: str) -> dict[str, str]:
    return _parse_fallback_table_rows(section_111_table_block)


def test_fallback_table_test_names_match_registry_both_ways(parsed_fallback_table: dict[str, str]) -> None:
    """Doc §1.1.1 table and PRIMARY_METRIC_FALLBACK_KEYS must list the same test.name values (both ways)."""
    from_registry = set(PRIMARY_METRIC_FALLBACK_KEYS.keys())
    from_doc = set(parsed_fallback_table.keys())
    # Equality: doc-only rows -> only_in_doc non-empty; registry-only -> only_in_registry non-empty
    assert from_registry == from_doc, (
        "§1.1.1 table vs PRIMARY_METRIC_FALLBACK_KEYS mismatch: "
        f"only in registry={sorted(from_registry - from_doc)!r}, "
        f"only in doc={sorted(from_doc - from_registry)!r}"
    )


def test_fallback_table_rows_document_registry_keys_with_backticks(
    parsed_fallback_table: dict[str, str],
) -> None:
    """Each metric key must appear in its row as a Markdown backtick token (scoped, not whole-doc)."""
    for test_name, keys in PRIMARY_METRIC_FALLBACK_KEYS.items():
        row = parsed_fallback_table[test_name]
        for key in keys:
            assert f"`{key}`" in row, (
                f"§1.1.1 row for {test_name!r} must contain backtick-wrapped key {key!r}; row={row!r}"
            )
