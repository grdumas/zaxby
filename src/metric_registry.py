"""
Primary metric registry (Phase 1, P1-E).

When ``results.primary_metric.value`` is missing, :meth:`BenchmarkDataProcessor._resolve_primary_metric`
in ``data_processing`` looks up metric keys in ``results.runs[*].metrics`` using this registry,
keyed by lowercase ``test.name`` from OpenSearch documents.

See :doc:`docs/guides/REGRESSION_DETECTION.md` §1.1 and companion appendix.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Keys are lowercase ``test.name`` values; values are preferred order of run metric keys.
PRIMARY_METRIC_FALLBACK_KEYS: Dict[str, List[str]] = {
    "coremark": ["iterations_per_second", "score"],
    "coremark_pro": ["multicore_score", "SUMM_CPU"],
    "streams": ["triad__mb_per_sec", "triad_mb_per_sec", "add__mb_per_sec"],
    "auto_hpl": ["gflops"],
    "specjbb": ["MULTICORE_THROUGHPUT"],
    "sysbench": ["events_per_second", "total_events"],
    "fio": ["read_iops", "write_iops", "read_bw", "write_bw"],
    "uperf": ["throughput_gbps", "throughput_mb_per_sec"],
    "passmark": ["cpu_mark", "mark"],
    "phoronix": ["result", "value"],
    "pyperf": ["mean"],
}


def fallback_keys_for_test(test_name: Optional[str]) -> List[str]:
    """
    Return the ordered list of run-metric keys to try for ``test_name``, or an empty list.

    ``test_name`` is normalized with the same rules as ``_resolve_primary_metric``
    (lowercase, strip).
    """
    tn = (test_name or "").lower().strip()
    if not tn:
        return []
    return list(PRIMARY_METRIC_FALLBACK_KEYS.get(tn, []))


def registered_test_names() -> frozenset[str]:
    """Frozen set of ``test.name`` keys present in :data:`PRIMARY_METRIC_FALLBACK_KEYS`."""
    return frozenset(PRIMARY_METRIC_FALLBACK_KEYS.keys())
