"""
Server-side OpenSearch queries for bounded payloads (Pulse-style prototypes).

Investigate / large pulls use explicit pagination limits; this module documents
the contract and implements small aggregation paths that do not scale with
full-index scroll size in the browser.

Phase 2 (P2-A / P2-C): Pulse KPIs — category rollup, monthly activity timeline,
and :class:`PulseScopeFootnote` (document count + run date range for exec-safe
copy). Aggregations reuse the same Pulse policy anchor as the cloud overview
snapshot.
"""

from __future__ import annotations

import math
import time
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.benchmark_categories import category_for_test_name
from src.pulse_policy import validate_pulse_request

logger = logging.getLogger(__name__)


def get_cache_service():
    """
    Lazy import cache service to avoid circular dependencies.

    Returns singleton instance of CacheService.
    """
    from src.cache_service import get_cache_service as _get_cache_service
    return _get_cache_service()

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
#
# Policy anchor: ``fetch_results_overview_aggregates`` validates this id against
# :mod:`src.comparison_policy` before OpenSearch. Callers pass no runtime params today
# (``{}``), so failure is unexpected unless the template id drifts from the Pulse
# allowlist—then the error path surfaces a clear policy message. Future optional
# filter params should be threaded through the same ``validate_pulse_request`` call.
PULSE_RESULTS_OVERVIEW_TEMPLATE_ID = "TPL_CATEGORY_ROLLUP"

# Terms size for test.name buckets before mapping to dashboard categories. Rare
# tests beyond this tail are omitted from the OpenSearch path (synthetic mode uses
# the full DataFrame and is exact).
MAX_TEST_NAME_TERMS_FOR_CATEGORY_KPI: int = 200

# Hard ceiling for terms aggregation ``size`` in :func:`build_results_test_name_terms_aggregation_body`.
# OpenSearch allows up to ``2^31-1`` per request, but very large values stress shards; 500 is a
# conservative safety bound for this KPI path (tune with ops if needed).
MAX_TERMS_AGG_HARD_CAP: int = 500

# OpenSearch date field for run activity (see docs/guides/SCHEMA.md).
RESULTS_ACTIVITY_TIMESTAMP_FIELD = "metadata.test_timestamp"


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
    from_cache: bool = False
    cache_timestamp: Optional[float] = None


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
    empty params before any OpenSearch call (static contract / policy anchor; see
    constant docstring).

    This function uses caching to avoid expensive OpenSearch queries. Cache hits are logged
    with metadata and include a timestamp for staleness detection.

    Args:
        client: :class:`src.opensearch_client.BenchmarkDataSource` instance.
    """
    # Generate cache key from query parameters
    cache_params = {
        'query_type': 'category_rollup',
        'template_id': PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
        'filters': {},  # No runtime filters for this query
    }

    # Check cache first
    cache_service = get_cache_service()
    cached_result = cache_service.get(cache_params)

    if cached_result is not None:
        # Cache hit - return cached result with metadata
        cached_result.from_cache = True
        logger.info(
            "Cache HIT for results_overview_aggregates | "
            f"cache_age_seconds={time.time() - (cached_result.cache_timestamp or 0):.1f} | "
            f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
        )
        return cached_result

    # Cache miss - execute OpenSearch query
    logger.info(
        "Cache MISS for results_overview_aggregates | "
        f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
    )

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
    result = ResultsOverviewSnapshot(
        total=total,
        by_cloud=pairs,
        source="opensearch",
        error=None,
        from_cache=False,
        cache_timestamp=time.time(),
    )

    # Cache the result
    cache_service.set(cache_params, result)

    return result


# --- Phase 2 P2-A: benchmark category KPI (rollup counts) ------------------------


def build_results_test_name_terms_aggregation_body(
    *,
    max_terms: int = MAX_TEST_NAME_TERMS_FOR_CATEGORY_KPI,
) -> Dict[str, Any]:
    """
    OpenSearch body: ``size: 0``, terms aggregation on ``test.name.keyword``.

    Align field name with :mod:`src.investigation_templates` / SCHEMA keyword mappings.
    """
    cap = max(1, min(int(max_terms), MAX_TERMS_AGG_HARD_CAP))
    return {
        "size": 0,
        "track_total_hits": True,
        "query": {"match_all": {}},
        "aggs": {
            "by_test_name": {
                "terms": {
                    "field": "test.name.keyword",
                    "size": cap,
                    "order": {"_count": "desc"},
                }
            }
        },
    }


def parse_test_name_buckets_to_category_counts(
    response: Dict[str, Any],
) -> List[Tuple[str, int]]:
    """
    Sum ``doc_count`` from ``by_test_name`` buckets into dashboard category labels.

    Categories follow :func:`~src.benchmark_categories.category_for_test_name`.
    Returns ``(category, count)`` pairs sorted by count descending, then name.
    """
    buckets = (
        response.get("aggregations", {})
        .get("by_test_name", {})
        .get("buckets", [])
    )
    counts: Counter[str] = Counter()
    for b in buckets:
        key = b.get("key")
        if key is None:
            continue
        n = int(b.get("doc_count", 0))
        if n <= 0:
            continue
        cat = category_for_test_name(str(key))
        counts[cat] += n
    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return ordered


@dataclass
class CategoryKpiSnapshot:
    """Benchmark category document counts (Pulse / synthetic overview KPI strip)."""

    by_category: List[Tuple[str, int]]
    source: str  # "opensearch" | "synthetic"
    error: str | None = None
    from_cache: bool = False
    cache_timestamp: Optional[float] = None


def aggregate_category_kpis_from_dataframe(df: pd.DataFrame) -> CategoryKpiSnapshot:
    """Mirror :func:`fetch_results_category_kpis` using the loaded benchmark DataFrame."""
    if df is None or df.empty or "test_name" not in df.columns:
        return CategoryKpiSnapshot(by_category=[], source="synthetic", error=None)
    sub = df.dropna(subset=["test_name"])
    if sub.empty:
        return CategoryKpiSnapshot(by_category=[], source="synthetic", error=None)
    cats = sub["test_name"].apply(category_for_test_name)
    vc = cats.value_counts()  # descending by count by default
    pairs = [(str(k), int(v)) for k, v in vc.items()]
    return CategoryKpiSnapshot(by_category=pairs, source="synthetic", error=None)


def fetch_results_category_kpis(client: Any) -> CategoryKpiSnapshot:
    """
    Run a bounded ``test.name`` terms aggregation and roll counts up by benchmark category.

    Uses the same Pulse policy anchor as :func:`fetch_results_overview_aggregates`
    (:data:`PULSE_RESULTS_OVERVIEW_TEMPLATE_ID` / ``TPL_CATEGORY_ROLLUP``): index-wide
    descriptive counts, not baseline-vs-candidate cohort comparisons.

    This function uses caching to avoid expensive OpenSearch queries.

    Args:
        client: :class:`src.opensearch_client.BenchmarkDataSource` instance.
    """
    # Generate cache key from query parameters
    cache_params = {
        'query_type': 'category_rollup',
        'template_id': PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
        'aggregation_type': 'category_kpis',
        'filters': {},
    }

    # Check cache first
    cache_service = get_cache_service()
    cached_result = cache_service.get(cache_params)

    if cached_result is not None:
        cached_result.from_cache = True
        logger.info(
            "Cache HIT for results_category_kpis | "
            f"cache_age_seconds={time.time() - (cached_result.cache_timestamp or 0):.1f} | "
            f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
        )
        return cached_result

    # Cache miss
    logger.info(
        "Cache MISS for results_category_kpis | "
        f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
    )

    vr = validate_pulse_request(PULSE_RESULTS_OVERVIEW_TEMPLATE_ID, {})
    if not vr.ok:
        return CategoryKpiSnapshot(
            by_category=[],
            source="opensearch",
            error="Pulse policy: " + "; ".join(vr.errors),
        )
    body = build_results_test_name_terms_aggregation_body()
    try:
        resp = client.search_results(body)
        pairs = parse_test_name_buckets_to_category_counts(resp)
    except Exception as exc:  # noqa: BLE001 — network, malformed responses, parse edge cases
        return CategoryKpiSnapshot(by_category=[], source="opensearch", error=str(exc))

    result = CategoryKpiSnapshot(
        by_category=pairs,
        source="opensearch",
        error=None,
        from_cache=False,
        cache_timestamp=time.time(),
    )

    # Cache the result
    cache_service.set(cache_params, result)

    return result


# --- Phase 2 P2-A: document activity by month (trend window) -----------------------


def build_results_monthly_activity_histogram_body() -> Dict[str, Any]:
    """
    OpenSearch body: ``size: 0``, monthly ``date_histogram`` on test run timestamp.

    Uses ``calendar_interval: 1M`` and ``format: yyyy-MM`` for stable bucket labels.
    ``min_doc_count: 1`` omits empty months between first/last hits (aligned with
    :func:`aggregate_activity_timeline_from_dataframe`, which uses non-zero counts only).
    """
    return {
        "size": 0,
        "track_total_hits": True,
        "query": {"match_all": {}},
        "aggs": {
            "runs_by_month": {
                "date_histogram": {
                    "field": RESULTS_ACTIVITY_TIMESTAMP_FIELD,
                    "calendar_interval": "1M",
                    "format": "yyyy-MM",
                    "min_doc_count": 1,
                }
            }
        },
    }


def parse_monthly_activity_histogram_response(response: Dict[str, Any]) -> List[Tuple[str, int]]:
    """
    Extract ``(yyyy-MM, doc_count)`` from ``runs_by_month`` buckets, chronological order.

    Skips buckets with zero ``doc_count`` so behaviour stays consistent if a cluster
    returns them despite ``min_doc_count: 1``.
    """
    buckets = (
        response.get("aggregations", {})
        .get("runs_by_month", {})
        .get("buckets", [])
    )
    pairs: List[Tuple[str, int]] = []
    for b in buckets:
        label = b.get("key_as_string")
        if label is None:
            continue
        n = int(b.get("doc_count", 0))
        if n <= 0:
            continue
        s = str(label).strip()
        if len(s) >= 7:
            s = s[:7]
        pairs.append((s, n))
    return pairs


@dataclass
class ActivityTimelineSnapshot:
    """Monthly document counts for Pulse overview (bounded aggregation)."""

    by_month: List[Tuple[str, int]]  # ("yyyy-MM", count), ascending by month
    source: str
    error: str | None = None
    from_cache: bool = False
    cache_timestamp: Optional[float] = None


def aggregate_activity_timeline_from_dataframe(df: pd.DataFrame) -> ActivityTimelineSnapshot:
    """
    Mirror :func:`fetch_results_activity_timeline` using the ``timestamp`` column.

    That column is populated from ``metadata.test_timestamp`` in
    :meth:`src.data_processing.BenchmarkDataProcessor.documents_to_dataframe`, matching
    :data:`RESULTS_ACTIVITY_TIMESTAMP_FIELD` on OpenSearch.
    """
    if df is None or df.empty or "timestamp" not in df.columns:
        return ActivityTimelineSnapshot(by_month=[], source="synthetic", error=None)
    t = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    valid = t.notna()
    if not valid.any():
        return ActivityTimelineSnapshot(by_month=[], source="synthetic", error=None)
    month_bucket = t[valid].dt.strftime("%Y-%m")
    vc = month_bucket.value_counts().sort_index()
    pairs = [(str(k), int(v)) for k, v in vc.items()]
    return ActivityTimelineSnapshot(by_month=pairs, source="synthetic", error=None)


def fetch_results_activity_timeline(client: Any) -> ActivityTimelineSnapshot:
    """
    Monthly run counts via ``date_histogram`` (non-comparative index view; same Pulse anchor).

    This function uses caching to avoid expensive OpenSearch queries.

    Args:
        client: :class:`src.opensearch_client.BenchmarkDataSource` instance.
    """
    # Generate cache key from query parameters
    cache_params = {
        'query_type': 'activity_timeline',
        'template_id': PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
        'filters': {},
    }

    # Check cache first
    cache_service = get_cache_service()
    cached_result = cache_service.get(cache_params)

    if cached_result is not None:
        cached_result.from_cache = True
        logger.info(
            "Cache HIT for results_activity_timeline | "
            f"cache_age_seconds={time.time() - (cached_result.cache_timestamp or 0):.1f} | "
            f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
        )
        return cached_result

    # Cache miss
    logger.info(
        "Cache MISS for results_activity_timeline | "
        f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
    )

    vr = validate_pulse_request(PULSE_RESULTS_OVERVIEW_TEMPLATE_ID, {})
    if not vr.ok:
        return ActivityTimelineSnapshot(
            by_month=[],
            source="opensearch",
            error="Pulse policy: " + "; ".join(vr.errors),
        )
    body = build_results_monthly_activity_histogram_body()
    try:
        resp = client.search_results(body)
        pairs = parse_monthly_activity_histogram_response(resp)
    except Exception as exc:  # noqa: BLE001
        return ActivityTimelineSnapshot(by_month=[], source="opensearch", error=str(exc))

    result = ActivityTimelineSnapshot(
        by_month=pairs,
        source="opensearch",
        error=None,
        from_cache=False,
        cache_timestamp=time.time(),
    )

    # Cache the result
    cache_service.set(cache_params, result)

    return result


# --- Phase 2 P2-C: scope footnote (soundbite metadata) ----------------------------


def _epoch_ms_to_utc_date_str(value: Any) -> Optional[str]:
    """Format OpenSearch ``stats`` min/max epoch millis as ``YYYY-MM-DD`` (UTC)."""
    if value is None:
        return None
    try:
        ms = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(ms):
        return None
    try:
        sec = ms / 1000.0
        return datetime.fromtimestamp(sec, tz=timezone.utc).date().isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def build_results_run_timestamp_stats_body() -> Dict[str, Any]:
    """
    OpenSearch body: ``size: 0``, ``stats`` on run timestamp for index scope metadata.

    Used for Pulse copy that cites document count and date range (P2-C).
    """
    return {
        "size": 0,
        "query": {"match_all": {}},
        "aggs": {
            "run_time_stats": {
                "stats": {"field": RESULTS_ACTIVITY_TIMESTAMP_FIELD},
            }
        },
    }


def parse_run_timestamp_stats_response(response: Dict[str, Any]) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Return ``(count_with_field, min_date_utc, max_date_utc)`` from ``run_time_stats``.

    ``count`` is the number of documents that have a value for the field (may differ
    from total index size if some documents lack ``metadata.test_timestamp``).
    """
    raw = response.get("aggregations", {}).get("run_time_stats", {})
    if not isinstance(raw, dict):
        return None, None, None
    cnt = raw.get("count")
    doc_count: Optional[int]
    try:
        doc_count = int(cnt) if cnt is not None else None
    except (TypeError, ValueError):
        doc_count = None
    dmin = _epoch_ms_to_utc_date_str(raw.get("min"))
    dmax = _epoch_ms_to_utc_date_str(raw.get("max"))
    return doc_count, dmin, dmax


@dataclass
class PulseScopeFootnote:
    """
    Bounded metadata for Pulse narrative copy: how many documents and which run dates.

    Aligns with IMPLEMENTATION_PLAN P2-C (soundbite metadata).
    """

    document_count: Optional[int]
    run_date_min_utc: Optional[str]
    run_date_max_utc: Optional[str]
    source: str
    error: str | None = None
    from_cache: bool = False
    cache_timestamp: Optional[float] = None


def aggregate_pulse_scope_footnote_from_dataframe(df: pd.DataFrame) -> PulseScopeFootnote:
    """
    Derive scope footnote from the benchmark DataFrame (synthetic / loaded sample).

    ``document_count`` matches OpenSearch ``stats.count``: rows with a non-null,
    parseable ``timestamp`` (from ``metadata.test_timestamp`` in
    :meth:`~src.data_processing.BenchmarkDataProcessor.documents_to_dataframe`), not
    ``len(df)`` when some rows lack timestamps.
    """
    if df is None or df.empty:
        return PulseScopeFootnote(
            document_count=0,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source="synthetic",
            error=None,
        )
    if "timestamp" not in df.columns:
        return PulseScopeFootnote(
            document_count=0,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source="synthetic",
            error=None,
        )
    t = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    valid = t.notna()
    n_with_ts = int(valid.sum())
    if n_with_ts == 0:
        return PulseScopeFootnote(
            document_count=0,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source="synthetic",
            error=None,
        )
    ts = t[valid]
    dmin = ts.min().date().isoformat()
    dmax = ts.max().date().isoformat()
    return PulseScopeFootnote(
        document_count=n_with_ts,
        run_date_min_utc=dmin,
        run_date_max_utc=dmax,
        source="synthetic",
        error=None,
    )


def format_pulse_scope_footnote(foot: PulseScopeFootnote, *, data_mode: str) -> Optional[str]:
    """Single line of scope metadata for Pulse snapshot copy (Phase 2 P2-C). Unit-tested."""
    if foot.error:
        return None
    dm = (data_mode or "").lower()
    segments: list[str] = []
    if foot.document_count is not None:
        if dm == "opensearch":
            segments.append(
                f"{foot.document_count:,} documents with run timestamps "
                f"(OpenSearch stats on metadata.test_timestamp)"
            )
        else:
            segments.append(
                f"{foot.document_count:,} documents with run timestamps in loaded sample"
            )
    if foot.run_date_min_utc and foot.run_date_max_utc:
        if foot.run_date_min_utc == foot.run_date_max_utc:
            segments.append(f"runs on {foot.run_date_min_utc} (UTC)")
        else:
            segments.append(
                f"run dates from {foot.run_date_min_utc} to {foot.run_date_max_utc} (UTC)"
            )
    elif foot.run_date_min_utc:
        segments.append(f"earliest run {foot.run_date_min_utc} (UTC)")
    if not segments:
        return None
    return "Scope: " + " · ".join(segments)


def fetch_pulse_scope_footnote(client: Any) -> PulseScopeFootnote:
    """
    Run ``stats`` on ``metadata.test_timestamp`` for Pulse scope lines (P2-C).

    This function uses caching to avoid expensive OpenSearch queries.

    Args:
        client: :class:`src.opensearch_client.BenchmarkDataSource` instance.
    """
    # Generate cache key from query parameters
    cache_params = {
        'query_type': 'scope_footnote',
        'template_id': PULSE_RESULTS_OVERVIEW_TEMPLATE_ID,
        'filters': {},
    }

    # Check cache first
    cache_service = get_cache_service()
    cached_result = cache_service.get(cache_params)

    if cached_result is not None:
        cached_result.from_cache = True
        logger.info(
            "Cache HIT for pulse_scope_footnote | "
            f"cache_age_seconds={time.time() - (cached_result.cache_timestamp or 0):.1f} | "
            f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
        )
        return cached_result

    # Cache miss
    logger.info(
        "Cache MISS for pulse_scope_footnote | "
        f"hit_rate={cache_service.metrics.hit_rate:.1f}%"
    )

    vr = validate_pulse_request(PULSE_RESULTS_OVERVIEW_TEMPLATE_ID, {})
    if not vr.ok:
        return PulseScopeFootnote(
            document_count=None,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source="opensearch",
            error="Pulse policy: " + "; ".join(vr.errors),
        )
    body = build_results_run_timestamp_stats_body()
    try:
        resp = client.search_results(body)
        doc_count, dmin, dmax = parse_run_timestamp_stats_response(resp)
    except Exception as exc:  # noqa: BLE001
        return PulseScopeFootnote(
            document_count=None,
            run_date_min_utc=None,
            run_date_max_utc=None,
            source="opensearch",
            error=str(exc),
        )

    result = PulseScopeFootnote(
        document_count=doc_count,
        run_date_min_utc=dmin,
        run_date_max_utc=dmax,
        source="opensearch",
        error=None,
        from_cache=False,
        cache_timestamp=time.time(),
    )

    # Cache the result
    cache_service.set(cache_params, result)

    return result


# --- Phase 3 P3-C: baseline comparison aggregates (exception-oriented) --------


@dataclass
class BaselineComparisonSnapshot:
    """
    Exception-oriented baseline vs nightly comparison (bounded aggregation).

    Returns only deltas that exceed regression thresholds or represent missing
    benchmarks, with result set bounded regardless of total benchmark count.
    """

    baseline_id: str
    nightly_date: Optional[str]
    regressions: List[Tuple[str, float]]  # (benchmark_name, percent_change), worst-first
    improvements: List[Tuple[str, float]]  # (benchmark_name, percent_change), best-first
    missing: List[str]  # benchmark names present in baseline but not nightly
    added: List[str]  # benchmark names present in nightly but not baseline
    delta_count: int  # total deltas calculated (before exception filtering)
    exception_count: int  # count of exceptions (regressions + improvements + missing)
    source: str  # "opensearch" | "synthetic"
    error: str | None = None


def fetch_baseline_comparison_aggregates(
    client: Any,
    baseline_filter: Dict[str, Any],
    nightly_date_range: Tuple[str, str],
    *,
    baseline_id: str = "baseline",
    max_regressions: int = 50,
    max_improvements: int = 20,
    max_missing: int = 10,
) -> BaselineComparisonSnapshot:
    """
    Exception-oriented baseline comparison: fetch baseline and nightly data,
    calculate deltas, and return only exceptions (regressions/improvements/missing).

    Implementation: client-side join. Fetch baseline documents by filter, fetch
    nightly by date range, group by benchmark name, calculate percent_change,
    filter to only exceptions (regression threshold or missing benchmarks).

    Args:
        client: :class:`src.opensearch_client.BenchmarkDataSource` instance.
        baseline_filter: OpenSearch filter criteria for baseline documents
            (e.g., {"metadata.baseline_tag.keyword": "v1.0"}).
        nightly_date_range: Tuple of (start_date, end_date) ISO strings for nightly data.
        baseline_id: Identifier for the baseline dataset (metadata field).
        max_regressions: Bound on regression results (top N worst).
        max_improvements: Bound on improvement results (top N best).
        max_missing: Bound on missing benchmark results.

    Returns:
        BaselineComparisonSnapshot with exception-filtered deltas and metadata.
    """
    try:
        # Fetch baseline documents
        baseline_body = _build_baseline_query(baseline_filter)
        baseline_resp = client.search_results(baseline_body)
        baseline_docs = [hit["_source"] for hit in baseline_resp.get("hits", {}).get("hits", [])]

        # Fetch nightly documents
        nightly_body = _build_nightly_query(nightly_date_range)
        nightly_resp = client.search_results(nightly_body)
        nightly_docs = [hit["_source"] for hit in nightly_resp.get("hits", {}).get("hits", [])]

        # Parse to DataFrames (reuse track_kpis parsing logic pattern)
        baseline_df = _parse_comparison_documents_to_dataframe(baseline_docs)
        nightly_df = _parse_comparison_documents_to_dataframe(nightly_docs)

        # Client-side join and delta calculation
        result = _calculate_exception_deltas(
            baseline_df=baseline_df,
            nightly_df=nightly_df,
            baseline_id=baseline_id,
            max_regressions=max_regressions,
            max_improvements=max_improvements,
            max_missing=max_missing,
        )

        return BaselineComparisonSnapshot(
            baseline_id=baseline_id,
            nightly_date=result["nightly_date"],
            regressions=result["regressions"],
            improvements=result["improvements"],
            missing=result["missing"],
            added=result["added"],
            delta_count=result["delta_count"],
            exception_count=result["exception_count"],
            source="opensearch",
            error=None,
        )

    except Exception as exc:  # noqa: BLE001
        return BaselineComparisonSnapshot(
            baseline_id=baseline_id,
            nightly_date=None,
            regressions=[],
            improvements=[],
            missing=[],
            added=[],
            delta_count=0,
            exception_count=0,
            source="opensearch",
            error=str(exc),
        )


def _build_baseline_query(baseline_filter: Dict[str, Any]) -> Dict[str, Any]:
    """Build OpenSearch query for baseline documents."""
    must_clauses = []
    for field, value in baseline_filter.items():
        if isinstance(value, list):
            must_clauses.append({"terms": {field: value}})
        else:
            must_clauses.append({"term": {field: value}})

    return {
        "query": {"bool": {"must": must_clauses}},
        "size": MAX_SEARCH_HITS,
    }


def _build_nightly_query(date_range: Tuple[str, str]) -> Dict[str, Any]:
    """Build OpenSearch query for nightly documents by date range."""
    start_date, end_date = date_range
    return {
        "query": {
            "range": {
                RESULTS_ACTIVITY_TIMESTAMP_FIELD: {
                    "gte": start_date,
                    "lte": end_date,
                }
            }
        },
        "size": MAX_SEARCH_HITS,
    }


def _parse_comparison_documents_to_dataframe(documents: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Parse OpenSearch documents for baseline comparison (minimal fields).

    Extracts test.name, primary_metric.value, status, and timestamp.
    """
    if not documents:
        return pd.DataFrame()

    from src.regression_detection import filter_dataframe_for_regression_math

    rows = []
    for doc in documents:
        metadata = doc.get("metadata") or {}
        test = doc.get("test") or {}
        results = doc.get("results") or {}

        # Extract primary metric value
        primary_metric = results.get("primary_metric") or {}
        value = primary_metric.get("value")
        if value is None:
            value = results.get("value")

        row = {
            "test_name": test.get("name"),
            "test_timestamp": metadata.get("test_timestamp"),
            "status": results.get("status", "UNKNOWN"),
            "primary_metric_value": value,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Convert timestamp to datetime
    if "test_timestamp" in df.columns and not df.empty:
        df["test_timestamp"] = pd.to_datetime(df["test_timestamp"], utc=True)

    # Filter for PASS status only (reuse regression detection filter)
    return filter_dataframe_for_regression_math(df, context="baseline_comparison")


def _calculate_exception_deltas(
    baseline_df: pd.DataFrame,
    nightly_df: pd.DataFrame,
    baseline_id: str,
    max_regressions: int,
    max_improvements: int,
    max_missing: int,
) -> Dict[str, Any]:
    """
    Calculate deltas and filter to exceptions only.

    Returns dict with regressions, improvements, missing, added, and counts.
    """
    from src.regression_detection import (
        is_regression_for_test_name,
        is_improvement_for_test_name,
        percent_change,
        regression_severity_score,
    )
    from src.metric_registry import higher_is_better_for_test

    # Get nightly date
    nightly_date = None
    if not nightly_df.empty and "test_timestamp" in nightly_df.columns:
        ts = nightly_df["test_timestamp"].max()
        if pd.notna(ts):
            nightly_date = ts.date().isoformat()

    # Calculate means by test_name
    baseline_means = _calculate_test_means(baseline_df)
    nightly_means = _calculate_test_means(nightly_df)

    # Calculate deltas
    all_tests = set(baseline_means.keys()) | set(nightly_means.keys())
    regressions_list = []
    improvements_list = []
    missing_list = []
    added_list = []
    delta_count = 0

    for test_name in all_tests:
        baseline_mean = baseline_means.get(test_name)
        nightly_mean = nightly_means.get(test_name)

        if baseline_mean is None and nightly_mean is not None:
            # Benchmark added
            added_list.append(test_name)
        elif baseline_mean is not None and nightly_mean is None:
            # Benchmark missing
            missing_list.append(test_name)
        elif baseline_mean is not None and nightly_mean is not None:
            delta_count += 1
            # Calculate percent change
            if baseline_mean == 0:
                continue
            pct = percent_change(baseline_mean, nightly_mean)

            # Check for regression or improvement
            if is_regression_for_test_name(pct, test_name):
                regressions_list.append((test_name, pct))
            elif is_improvement_for_test_name(pct, test_name):
                improvements_list.append((test_name, pct))

    # Sort and bound results
    # Regressions: worst first (most negative for higher-is-better, most positive for lower-is-better)
    # Use regression_severity_score for consistent sorting
    regressions_scored = [
        (name, pct, regression_severity_score(pct, name))
        for name, pct in regressions_list
    ]
    regressions_scored.sort(key=lambda x: x[2], reverse=True)
    regressions = [(name, pct) for name, pct, _ in regressions_scored[:max_regressions]]

    # Improvements: best first (most positive for higher-is-better, most negative for lower-is-better)
    # Invert the severity score logic for improvements
    improvements_scored = [
        (name, pct, -pct if higher_is_better_for_test(name) else pct)
        for name, pct in improvements_list
    ]
    improvements_scored.sort(key=lambda x: x[2], reverse=True)
    improvements = [(name, pct) for name, pct, _ in improvements_scored[:max_improvements]]

    # Missing: alphabetical, bounded
    missing = sorted(missing_list)[:max_missing]

    # Added: alphabetical, bounded
    added = sorted(added_list)[:max_missing]

    exception_count = len(regressions) + len(improvements) + len(missing)

    return {
        "nightly_date": nightly_date,
        "regressions": regressions,
        "improvements": improvements,
        "missing": missing,
        "added": added,
        "delta_count": delta_count,
        "exception_count": exception_count,
    }


def _calculate_test_means(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate mean primary_metric_value for each test_name."""
    if df.empty or "test_name" not in df.columns:
        return {}

    means = {}
    for test_name, group in df.groupby("test_name"):
        if "primary_metric_value" not in group.columns:
            continue
        values = pd.to_numeric(group["primary_metric_value"], errors="coerce").dropna()
        if len(values) > 0:
            means[test_name] = float(values.mean())

    return means


def aggregate_baseline_comparison_from_dataframe(
    baseline_df: pd.DataFrame,
    nightly_df: pd.DataFrame,
    *,
    baseline_id: str = "synthetic",
    max_regressions: int = 50,
    max_improvements: int = 20,
    max_missing: int = 10,
) -> BaselineComparisonSnapshot:
    """
    Mirror :func:`fetch_baseline_comparison_aggregates` using pre-loaded DataFrames.

    Args:
        baseline_df: Baseline benchmark DataFrame.
        nightly_df: Nightly benchmark DataFrame.
        baseline_id: Identifier for baseline.
        max_regressions: Bound on regression results.
        max_improvements: Bound on improvement results.
        max_missing: Bound on missing results.

    Returns:
        BaselineComparisonSnapshot with synthetic source.
    """
    try:
        result = _calculate_exception_deltas(
            baseline_df=baseline_df,
            nightly_df=nightly_df,
            baseline_id=baseline_id,
            max_regressions=max_regressions,
            max_improvements=max_improvements,
            max_missing=max_missing,
        )

        return BaselineComparisonSnapshot(
            baseline_id=baseline_id,
            nightly_date=result["nightly_date"],
            regressions=result["regressions"],
            improvements=result["improvements"],
            missing=result["missing"],
            added=result["added"],
            delta_count=result["delta_count"],
            exception_count=result["exception_count"],
            source="synthetic",
            error=None,
        )

    except Exception as exc:  # noqa: BLE001
        return BaselineComparisonSnapshot(
            baseline_id=baseline_id,
            nightly_date=None,
            regressions=[],
            improvements=[],
            missing=[],
            added=[],
            delta_count=0,
            exception_count=0,
            source="synthetic",
            error=str(exc),
        )


# --- Cache warming strategy (optional, configurable via env) ----------------------


def warm_query_cache(client: Any) -> Dict[str, Any]:
    """
    Pre-cache common queries on application startup.

    This is an optional optimization that can be enabled via the ENABLE_CACHE_WARMING
    environment variable. When enabled, it executes all standard Pulse aggregation
    queries once to populate the cache, reducing initial load times for dashboard users.

    Performance impact: Cache warming executes 4 OpenSearch queries in sequence.
    On typical indexes, this completes in 1-3 seconds. Recommended for production
    environments with frequent dashboard access.

    Args:
        client: :class:`src.opensearch_client.BenchmarkDataSource` instance.

    Returns:
        Dictionary with warming results:
        - 'warmed': Number of queries successfully cached
        - 'failed': Number of queries that failed
        - 'duration_seconds': Total time taken
        - 'details': List of per-query results
    """
    import os

    if os.getenv('ENABLE_CACHE_WARMING', '').lower() not in ('1', 'true', 'yes'):
        logger.info("Cache warming disabled (ENABLE_CACHE_WARMING not set)")
        return {
            'warmed': 0,
            'failed': 0,
            'duration_seconds': 0.0,
            'details': [],
            'enabled': False,
        }

    logger.info("Cache warming started")
    start_time = time.time()
    warmed = 0
    failed = 0
    details = []

    # List of queries to warm
    queries = [
        ('results_overview_aggregates', lambda: fetch_results_overview_aggregates(client)),
        ('results_category_kpis', lambda: fetch_results_category_kpis(client)),
        ('results_activity_timeline', lambda: fetch_results_activity_timeline(client)),
        ('pulse_scope_footnote', lambda: fetch_pulse_scope_footnote(client)),
    ]

    for query_name, query_func in queries:
        query_start = time.time()
        try:
            result = query_func()
            query_duration = time.time() - query_start
            if result.error is None:
                warmed += 1
                details.append({
                    'query': query_name,
                    'status': 'success',
                    'duration_seconds': query_duration,
                })
                logger.info(
                    f"Cache warmed: {query_name} | "
                    f"duration={query_duration:.2f}s"
                )
            else:
                failed += 1
                details.append({
                    'query': query_name,
                    'status': 'error',
                    'error': result.error,
                    'duration_seconds': query_duration,
                })
                logger.warning(
                    f"Cache warming failed: {query_name} | "
                    f"error={result.error}"
                )
        except Exception as exc:
            query_duration = time.time() - query_start
            failed += 1
            details.append({
                'query': query_name,
                'status': 'exception',
                'error': str(exc),
                'duration_seconds': query_duration,
            })
            logger.error(
                f"Cache warming exception: {query_name} | "
                f"error={exc}"
            )

    total_duration = time.time() - start_time
    logger.info(
        f"Cache warming completed | "
        f"warmed={warmed} failed={failed} duration={total_duration:.2f}s"
    )

    # Log cache statistics
    cache_service = get_cache_service()
    metrics = cache_service.get_metrics()
    logger.info(
        f"Cache metrics after warming | "
        f"hits={metrics.hits} misses={metrics.misses} "
        f"hit_rate={metrics.hit_rate:.1f}% errors={metrics.errors}"
    )

    return {
        'warmed': warmed,
        'failed': failed,
        'duration_seconds': total_duration,
        'details': details,
        'enabled': True,
    }


def log_cache_statistics() -> Dict[str, Any]:
    """
    Log current cache statistics for monitoring.

    Returns cache hit rate, miss rate, total requests, and error count.
    Useful for periodic monitoring and performance analysis.

    Returns:
        Dictionary with cache statistics:
        - 'hits': Number of cache hits
        - 'misses': Number of cache misses
        - 'errors': Number of cache errors
        - 'total_requests': Total cache requests (hits + misses)
        - 'hit_rate': Cache hit rate as percentage (0-100)
        - 'miss_rate': Cache miss rate as percentage (0-100)
    """
    cache_service = get_cache_service()
    metrics = cache_service.get_metrics()

    stats = {
        'hits': metrics.hits,
        'misses': metrics.misses,
        'errors': metrics.errors,
        'total_requests': metrics.total_requests,
        'hit_rate': metrics.hit_rate,
        'miss_rate': 100.0 - metrics.hit_rate if metrics.total_requests > 0 else 0.0,
    }

    logger.info(
        f"Cache statistics | "
        f"hits={stats['hits']} misses={stats['misses']} "
        f"total={stats['total_requests']} "
        f"hit_rate={stats['hit_rate']:.1f}% "
        f"miss_rate={stats['miss_rate']:.1f}% "
        f"errors={stats['errors']}"
    )

    return stats
