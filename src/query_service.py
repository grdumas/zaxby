"""
Server-side OpenSearch queries for bounded payloads (Pulse-style prototypes).

Investigate / large pulls use explicit pagination limits; this module documents
the contract and implements small aggregation paths that do not scale with
full-index scroll size in the browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd

from src.pulse_policy import validate_pulse_request

# --- Pagination contract (Investigate / bounded search) ----------------------------

# Maximum hits per search request for interactive drill-down; tune with cluster limits.
MAX_PAGE_SIZE: int = 500

# Hard ceiling for any single search (defense in depth; callers should chunk below this).
MAX_SEARCH_HITS: int = 10000

"""
Pagination strategy (draft for Phase 1 Investigate):

- Prefer ``search_after`` with a stable sort (e.g. ``metadata.test_timestamp`` desc,
  ``metadata.document_id`` keyword) for deep pages.
- Avoid offset-based paging for large ``from`` values (OpenSearch degrades).
- Cap ``size`` at :data:`MAX_PAGE_SIZE` for UI-driven requests unless a dedicated
  export path uses scroll/Point in Time APIs with ops approval.
"""

# Template declared for the results-index overview snapshot (total + per-cloud counts).
# Non-comparative index health counts; Pulse-allowed when params do not imply
# cross-cloud comparative cohorts (see COMPARISON_POLICY.md §3, TPL_CATEGORY_ROLLUP).
PULSE_RESULTS_OVERVIEW_TEMPLATE_ID = "TPL_CATEGORY_ROLLUP"


def build_results_overview_aggregation_body() -> Dict[str, Any]:
    """
    OpenSearch body: ``size: 0``, track total hits, terms agg on cloud provider.

    Uses ``metadata.cloud_provider.keyword`` for the terms field (typical keyword
    subfield for mapped strings). If a cluster maps ``metadata.cloud_provider`` as
    pure ``keyword``, mapping may expose the field without ``.keyword`` — adjust
    query in that environment.
    """
    return {
        "size": 0,
        "track_total_hits": True,
        "query": {"match_all": {}},
        "aggs": {
            "by_cloud": {
                "terms": {
                    "field": "metadata.cloud_provider.keyword",
                    "size": 50,
                    "order": {"_count": "desc"},
                }
            }
        },
    }


def parse_overview_aggregation_response(response: Dict[str, Any]) -> Tuple[int, List[Tuple[str, int]]]:
    """Extract total doc count and (cloud_provider, doc_count) buckets from a search response."""
    raw_total = response.get("hits", {}).get("total", 0)
    if isinstance(raw_total, dict):
        total = int(raw_total.get("value", 0) or 0)
    else:
        total = int(raw_total or 0)

    buckets = (
        response.get("aggregations", {})
        .get("by_cloud", {})
        .get("buckets", [])
    )
    pairs: List[Tuple[str, int]] = []
    for b in buckets:
        key = b.get("key")
        if key is None:
            continue
        pairs.append((str(key), int(b.get("doc_count", 0))))
    return total, pairs


@dataclass
class ResultsOverviewSnapshot:
    """Small, JSON-serializable snapshot for the dashboard (not full scroll)."""

    total: int | None
    by_cloud: List[Tuple[str, int]]
    source: str  # "opensearch" | "synthetic"
    error: str | None = None


def aggregate_results_overview_from_dataframe(df: pd.DataFrame) -> ResultsOverviewSnapshot:
    """Compute the same shape as :func:`fetch_results_overview_aggregates` from the in-memory DataFrame."""
    if df is None or df.empty:
        return ResultsOverviewSnapshot(total=0, by_cloud=[], source="synthetic", error=None)
    if "cloud_provider" not in df.columns:
        return ResultsOverviewSnapshot(total=len(df), by_cloud=[], source="synthetic", error=None)
    sub = df.dropna(subset=["cloud_provider"])
    if sub.empty:
        return ResultsOverviewSnapshot(total=len(df), by_cloud=[], source="synthetic", error=None)
    counts = sub.groupby("cloud_provider").size().sort_values(ascending=False)
    pairs = [(str(k), int(v)) for k, v in counts.items()]
    return ResultsOverviewSnapshot(total=len(df), by_cloud=pairs, source="synthetic", error=None)


def fetch_results_overview_aggregates(client: Any) -> ResultsOverviewSnapshot:
    """
    Run server-side aggregation on the results index via ``BenchmarkDataSource.search_results``.

    Pulse policy (P1-B): validates :data:`PULSE_RESULTS_OVERVIEW_TEMPLATE_ID` with
    empty params before any OpenSearch call.

    Args:
        client: :class:`src.opensearch_client.BenchmarkDataSource` instance.
    """
    vr = validate_pulse_request(PULSE_RESULTS_OVERVIEW_TEMPLATE_ID, {})
    if not vr.ok:
        return ResultsOverviewSnapshot(
            total=None,
            by_cloud=[],
            source="opensearch",
            error="Pulse policy: " + "; ".join(vr.errors),
        )
    body = build_results_overview_aggregation_body()
    try:
        resp = client.search_results(body)
    except Exception as exc:  # noqa: BLE001 — surface message to UI; OpenSearch errors vary
        return ResultsOverviewSnapshot(
            total=None,
            by_cloud=[],
            source="opensearch",
            error=str(exc),
        )
    total, pairs = parse_overview_aggregation_response(resp)
    return ResultsOverviewSnapshot(total=total, by_cloud=pairs, source="opensearch", error=None)
