"""
Investigation template engine (Phase 1, P1-A).

Maps UI ``investigation_params`` (see ``app.py`` ``navigation_state``) to a
``template_id`` from :mod:`src.comparison_policy`, validates via
:func:`src.comparison_policy.validate_comparison_request`, and builds OpenSearch
``search`` bodies for ``zathras-results`` (bounded hit size).

This module starts with the RHEL regression chart drill-down
(``TPL_RHEL_MINOR_SAME_HW``). Other templates can add builders alongside
:data:`TEMPLATE_BUILDERS`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol

from src.comparison_policy import validate_comparison_request
from src.query_service import MAX_PAGE_SIZE, MAX_SEARCH_HITS


class _SearchResultsClient(Protocol):
    """Minimal protocol for :func:`fetch_investigation_documents`."""

    def search_results(self, body: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        ...


# OpenSearch field paths — align with docs/guides/COMPARISON_POLICY.md §6 and SCHEMA.md
FIELD_TEST_NAME = "test.name.keyword"
FIELD_OS_DISTRIBUTION = "system_under_test.operating_system.distribution.keyword"
FIELD_OS_VERSION = "system_under_test.operating_system.version.keyword"
FIELD_CLOUD_PROVIDER = "metadata.cloud_provider.keyword"
FIELD_INSTANCE_TYPE = "metadata.instance_type.keyword"
FIELD_SCENARIO_NAME = "metadata.scenario_name.keyword"


class InvestigationTemplateError(ValueError):
    """Raised when UI parameters cannot be mapped or validation fails."""


def _req_str(params: Mapping[str, Any], key: str) -> str:
    raw = params.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise InvestigationTemplateError(f"Missing or empty investigation parameter: {key!r}")
    return str(raw).strip()


def _opt_str(params: Mapping[str, Any], key: str) -> Optional[str]:
    raw = params.get(key)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def normalize_investigation_params(ui_params: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize dashboard ``investigation_params`` for ``TPL_RHEL_MINOR_SAME_HW``.

    Required keys: ``test_name``, ``baseline_version``, ``comparison_version``,
    ``os_distribution``.

    Optional: ``cloud_provider``, ``instance_type``, ``scenario_name`` (same-hardware
    scope per policy when provided).
    """
    test_name = _req_str(ui_params, "test_name")
    baseline_version = _req_str(ui_params, "baseline_version")
    comparison_version = _req_str(ui_params, "comparison_version")
    os_distribution = _req_str(ui_params, "os_distribution").lower()

    out: Dict[str, Any] = {
        "test_name": test_name,
        "baseline_version": baseline_version,
        "comparison_version": comparison_version,
        "os_distribution": os_distribution,
    }
    for opt in ("cloud_provider", "instance_type", "scenario_name"):
        v = _opt_str(ui_params, opt)
        if v is not None:
            out[opt] = v
    return out


def resolve_ui_investigation_to_template(
    ui_params: Mapping[str, Any],
) -> tuple[str, Dict[str, Any]]:
    """
    Map UI investigation payload to a comparison template id and normalized params.

    Returns:
        ``(template_id, params)`` suitable for :func:`build_zathras_results_search_body`
        and policy validation (Investigate mode).

    Raises:
        InvestigationTemplateError: If required keys are missing or validation fails.
    """
    normalized = normalize_investigation_params(ui_params)
    template_id = "TPL_RHEL_MINOR_SAME_HW"

    vr = validate_comparison_request(template_id, normalized, mode="investigate")
    if not vr.ok:
        raise InvestigationTemplateError("; ".join(vr.errors))

    return template_id, normalized


def _build_rhel_minor_same_hw_body(params: Mapping[str, Any], *, size: int) -> Dict[str, Any]:
    filters: list[Dict[str, Any]] = [
        {"term": {FIELD_TEST_NAME: params["test_name"]}},
        {"term": {FIELD_OS_DISTRIBUTION: params["os_distribution"]}},
    ]
    if "cloud_provider" in params:
        filters.append({"term": {FIELD_CLOUD_PROVIDER: params["cloud_provider"]}})
    if "instance_type" in params:
        filters.append({"term": {FIELD_INSTANCE_TYPE: params["instance_type"]}})
    if "scenario_name" in params:
        filters.append({"term": {FIELD_SCENARIO_NAME: params["scenario_name"]}})

    should = [
        {"term": {FIELD_OS_VERSION: params["baseline_version"]}},
        {"term": {FIELD_OS_VERSION: params["comparison_version"]}},
    ]

    return {
        "size": size,
        "track_total_hits": True,
        "query": {
            "bool": {
                "filter": filters,
                "should": should,
                "minimum_should_match": 1,
            }
        },
        "sort": [
            {"metadata.test_timestamp": {"order": "desc"}},
            {"metadata.document_id.keyword": {"order": "asc"}},
        ],
    }


# Builders have signature ``(params: Mapping, *, size: int) -> dict`` and are always
# called as ``builder(params, size=…)`` (keyword-only size — not positional ``int``).
TEMPLATE_BUILDERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "TPL_RHEL_MINOR_SAME_HW": _build_rhel_minor_same_hw_body,
}


def build_zathras_results_search_body(
    template_id: str,
    params: Mapping[str, Any],
    *,
    size: int = MAX_PAGE_SIZE,
) -> Dict[str, Any]:
    """
    Build an OpenSearch request body for ``BenchmarkDataSource.search_results``.

    Only templates registered in :data:`TEMPLATE_BUILDERS` are supported.

    Args:
        template_id: Canonical template id (e.g. ``TPL_RHEL_MINOR_SAME_HW``).
        params: Normalized params from :func:`resolve_ui_investigation_to_template`.
        size: Hit cap (clamped to :data:`src.query_service.MAX_SEARCH_HITS`).
    """
    builder = TEMPLATE_BUILDERS.get(template_id)
    if builder is None:
        raise InvestigationTemplateError(
            f"No OpenSearch query builder for template_id={template_id!r}"
        )
    cap = max(1, min(int(size), MAX_SEARCH_HITS))
    return builder(params, size=cap)


def resolve_and_build_opensearch_query(
    ui_params: Mapping[str, Any],
    *,
    size: Optional[int] = None,
) -> tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Resolve UI params to a template and return ``(template_id, normalized_params, search_body)``.
    """
    tid, normalized = resolve_ui_investigation_to_template(ui_params)
    sz = size if size is not None else MAX_PAGE_SIZE
    body = build_zathras_results_search_body(tid, normalized, size=sz)
    return tid, normalized, body


def fetch_investigation_documents(
    ui_params: Mapping[str, Any],
    search_client: _SearchResultsClient,
    *,
    size: Optional[int] = None,
) -> tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Resolve UI params, run ``search_client.search_results`` on the results index, and
    return ``(template_id, normalized_params, sources)`` where ``sources`` are document
    bodies (``_source``) for :meth:`BenchmarkDataProcessor.documents_to_dataframe`.
    """
    tid, normalized, body = resolve_and_build_opensearch_query(ui_params, size=size)
    resp = search_client.search_results(body)
    hits = resp.get("hits", {}).get("hits", [])
    sources: List[Dict[str, Any]] = []
    for h in hits:
        src = h.get("_source")
        if isinstance(src, dict):
            sources.append(src)
    return tid, normalized, sources
