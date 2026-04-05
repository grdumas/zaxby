"""
OpenSearch Dashboards deep links (Discover) for operator drill-down from the Dash UI.

URL shape follows the hash-routed Discover app (`/app/discover#/?_g=...&_a=...`).
Index pattern names in Dashboards must align with the linked index name; adjust
`.env` or Dashboards if your pattern id differs from the raw index string.

Rison (used in ``_g`` / ``_a`` URL state) escapes ``!`` as ``!!`` and ``'`` as ``!'`` inside
single-quoted strings — not backslashes.
"""

from __future__ import annotations

import os


def _rison_escape_for_single_quoted_string(s: str) -> str:
    """
    Escape text placed inside Rison single-quoted strings.

    Rison uses ``!`` as the escape character: literal ``!`` → ``!!``, literal ``'`` → ``!'``.
    Order: escape ``!`` first, then ``'``, so sequences like ``!'`` in input encode correctly.
    """
    return s.replace("!", "!!").replace("'", "!'")


def results_index_name() -> str:
    """Same resolution as the run/results index in ``BenchmarkDataSource`` (env-only)."""
    return (os.getenv("OPENSEARCH_INDEX_RESULTS") or os.getenv("OPENSEARCH_INDEX") or "").strip()


def opensearch_discover_url_for_document(
    dashboards_base_url: str,
    index_name: str,
    document_id: str,
) -> str:
    """
    Build a Discover URL that pre-fills a Kuery filter on ``metadata.document_id``.

    Args:
        dashboards_base_url: e.g. ``https://opensearch.example.com:5601`` (no trailing path).
        index_name: Index or index-pattern id as shown in Discover (often matches ``zathras-results``).
        document_id: Run id from ``metadata.document_id`` in results documents.

    Returns:
        Full URL suitable for ``target="_blank"`` from the dashboard.
    """
    if not dashboards_base_url or not str(dashboards_base_url).strip():
        raise ValueError("dashboards_base_url is required")
    if not index_name or not str(index_name).strip():
        raise ValueError("index_name is required")
    if document_id is None or str(document_id).strip() == "":
        raise ValueError("document_id is required")

    base = str(dashboards_base_url).strip().rstrip("/")
    doc = str(document_id).strip()
    # Kuery: escape backslashes and double-quotes inside the quoted document id value
    esc = doc.replace("\\", "\\\\").replace('"', '\\"')
    kuery = f'metadata.document_id: "{esc}"'
    idx = _rison_escape_for_single_quoted_string(str(index_name).strip())
    kuery_rison = _rison_escape_for_single_quoted_string(kuery)

    _a = (
        f"(columns:!(_source),filters:!(),index:'{idx}',interval:auto,"
        f"query:(language:kuery,query:'{kuery_rison}'))"
    )
    _g = "(time:(from:now-15y,to:now))"
    return f"{base}/app/discover#/?_g={_g}&_a={_a}"
