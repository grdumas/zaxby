"""
Investigation template engine (Phase 1, P1-A).

Maps UI ``investigation_params`` (see ``app.py`` ``navigation_state``) to a
``template_id`` from :mod:`src.comparison_policy`, validates via
:func:`src.comparison_policy.validate_comparison_request`, and builds OpenSearch
``search`` bodies for ``zathras-results`` (bounded hit size).

Supported templates (see ``docs/guides/COMPARISON_POLICY.md`` §5):

- ``TPL_RHEL_MINOR_SAME_HW`` (default when ``template_id`` omitted): two OS
  versions, same test and distribution; optional cloud/instance/scenario scope.
- ``TPL_RHEL_MAJOR_SAME_HW`` / ``TPL_OS_SEQUENTIAL_MINOR``: same parameter shape
  and query as minor template; distinct ids for policy routing.
- ``TPL_TIME_WINDOW``: fixed scope + two timestamp cohorts;
  :func:`normalize_time_window_params`.
- ``TPL_PEER_OS``: baseline vs peer OS on same cloud/instance/test;
  :func:`normalize_peer_os_params`.
- ``TPL_CLOUD_SCALE_SAME_OS``: multiple ``instance_types`` at fixed OS/test;
  :func:`normalize_cloud_scale_params`.
- ``TPL_SCENARIO_ABLATION``: two ``scenario_name`` values; fixed OS/hardware/test;
  :func:`normalize_scenario_ablation_params`.
- ``TPL_SINGLE_RUN_LOOKUP``: ``document_id`` only;
  :func:`normalize_single_run_lookup_params`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol

from src.comparison_policy import validate_comparison_request
from src.query_service import MAX_PAGE_SIZE, MAX_SEARCH_HITS, RESULTS_ACTIVITY_TIMESTAMP_FIELD


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
FIELD_DOCUMENT_ID = "metadata.document_id.keyword"


def _parse_iso_timestamp_to_datetime(value: object, *, field_label: str) -> datetime:
    """Parse a date or datetime string to a :class:`~datetime.datetime` (for ordering and ISO export)."""
    if value is None:
        raise InvestigationTemplateError(f"Missing or empty investigation parameter: {field_label!r}")
    raw = str(value).strip()
    if not raw:
        raise InvestigationTemplateError(f"Missing or empty investigation parameter: {field_label!r}")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InvestigationTemplateError(
            f"Invalid ISO 8601 datetime for {field_label!r}: {value!r}"
        ) from exc


def _instant_for_ordering(dt: datetime) -> datetime:
    """Map naive or aware datetimes to UTC for consistent start/end comparison."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=timezone.utc)


def _ensure_window_order(start: datetime, end: datetime, *, label: str) -> None:
    """Reject start > end using instants, not lexicographic ISO strings (mixed tz formats)."""
    if _instant_for_ordering(start) > _instant_for_ordering(end):
        raise InvestigationTemplateError(
            f"Time window {label}: start ({start.isoformat()!r}) must be <= end ({end.isoformat()!r})"
        )


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


def normalize_time_window_params(ui_params: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize ``investigation_params`` for ``TPL_TIME_WINDOW`` (COMPARISON_POLICY.md §5).

    Required: ``test_name``, ``cloud_provider``, ``instance_type``, ``os_distribution``,
    ``os_version``, ``baseline_window_start``, ``baseline_window_end``,
    ``candidate_window_start``, ``candidate_window_end`` (ISO 8601 date or datetime).

    Optional: ``scenario_name`` (same grain as other templates when present).

    **Overlapping windows:** Baseline and candidate intervals may overlap in time; documents
    in the overlap match both ``should`` range clauses. Splitting rows into cohorts is a
    downstream concern; this helper does not reject overlap.
    """
    test_name = _req_str(ui_params, "test_name")
    cloud_provider = _req_str(ui_params, "cloud_provider")
    instance_type = _req_str(ui_params, "instance_type")
    os_distribution = _req_str(ui_params, "os_distribution").lower()
    os_version = _req_str(ui_params, "os_version")

    bs = _parse_iso_timestamp_to_datetime(
        _req_str(ui_params, "baseline_window_start"), field_label="baseline_window_start"
    )
    be = _parse_iso_timestamp_to_datetime(
        _req_str(ui_params, "baseline_window_end"), field_label="baseline_window_end"
    )
    cs = _parse_iso_timestamp_to_datetime(
        _req_str(ui_params, "candidate_window_start"), field_label="candidate_window_start"
    )
    ce = _parse_iso_timestamp_to_datetime(
        _req_str(ui_params, "candidate_window_end"), field_label="candidate_window_end"
    )

    _ensure_window_order(bs, be, label="baseline")
    _ensure_window_order(cs, ce, label="candidate")

    out: Dict[str, Any] = {
        "test_name": test_name,
        "cloud_provider": cloud_provider,
        "instance_type": instance_type,
        "os_distribution": os_distribution,
        "os_version": os_version,
        "baseline_window_start": bs.isoformat(),
        "baseline_window_end": be.isoformat(),
        "candidate_window_start": cs.isoformat(),
        "candidate_window_end": ce.isoformat(),
    }
    v = _opt_str(ui_params, "scenario_name")
    if v is not None:
        out["scenario_name"] = v
    return out


def normalize_single_run_lookup_params(ui_params: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize ``investigation_params`` for ``TPL_SINGLE_RUN_LOOKUP`` (policy §5)."""
    doc_id = _req_str(ui_params, "document_id")
    return {"document_id": doc_id}


def normalize_peer_os_params(ui_params: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize ``investigation_params`` for ``TPL_PEER_OS``.

    Required: ``test_name``, ``cloud_provider``, ``instance_type``,
    ``baseline_os_distribution``, ``baseline_os_version``,
    ``candidate_os_distribution``, ``candidate_os_version``.

    Optional: ``scenario_name``.
    """
    test_name = _req_str(ui_params, "test_name")
    cloud_provider = _req_str(ui_params, "cloud_provider")
    instance_type = _req_str(ui_params, "instance_type")
    bd = _req_str(ui_params, "baseline_os_distribution").lower()
    bv = _req_str(ui_params, "baseline_os_version")
    cd = _req_str(ui_params, "candidate_os_distribution").lower()
    cv = _req_str(ui_params, "candidate_os_version")

    out: Dict[str, Any] = {
        "test_name": test_name,
        "cloud_provider": cloud_provider,
        "instance_type": instance_type,
        "baseline_os_distribution": bd,
        "baseline_os_version": bv,
        "candidate_os_distribution": cd,
        "candidate_os_version": cv,
    }
    v = _opt_str(ui_params, "scenario_name")
    if v is not None:
        out["scenario_name"] = v
    return out


def _req_nonempty_str_list(params: Mapping[str, Any], key: str) -> list[str]:
    raw = params.get(key)
    if raw is None:
        raise InvestigationTemplateError(f"Missing investigation parameter: {key!r}")
    if isinstance(raw, str):
        items = [raw.strip()] if raw.strip() else []
    elif isinstance(raw, (list, tuple)):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        raise InvestigationTemplateError(
            f"Investigation parameter {key!r} must be a non-empty list or tuple of strings"
        )
    if not items:
        raise InvestigationTemplateError(f"Missing or empty investigation parameter: {key!r}")
    return items


def normalize_cloud_scale_params(ui_params: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize ``investigation_params`` for ``TPL_CLOUD_SCALE_SAME_OS``.

    Required: ``test_name``, ``os_distribution``, ``os_version``,
    ``cloud_provider``, ``instance_types`` (non-empty list of instance type strings).

    Optional: ``scenario_name``.
    """
    test_name = _req_str(ui_params, "test_name")
    os_distribution = _req_str(ui_params, "os_distribution").lower()
    os_version = _req_str(ui_params, "os_version")
    cloud_provider = _req_str(ui_params, "cloud_provider")
    instance_types = _req_nonempty_str_list(ui_params, "instance_types")

    out: Dict[str, Any] = {
        "test_name": test_name,
        "os_distribution": os_distribution,
        "os_version": os_version,
        "cloud_provider": cloud_provider,
        "instance_types": instance_types,
    }
    v = _opt_str(ui_params, "scenario_name")
    if v is not None:
        out["scenario_name"] = v
    return out


def normalize_scenario_ablation_params(ui_params: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize ``investigation_params`` for ``TPL_SCENARIO_ABLATION``.

    Required: ``test_name``, ``cloud_provider``, ``instance_type``,
    ``os_distribution``, ``os_version``, ``baseline_scenario_name``,
    ``candidate_scenario_name`` (must differ).
    """
    test_name = _req_str(ui_params, "test_name")
    cloud_provider = _req_str(ui_params, "cloud_provider")
    instance_type = _req_str(ui_params, "instance_type")
    os_distribution = _req_str(ui_params, "os_distribution").lower()
    os_version = _req_str(ui_params, "os_version")
    bs = _req_str(ui_params, "baseline_scenario_name")
    cs = _req_str(ui_params, "candidate_scenario_name")
    if bs == cs:
        raise InvestigationTemplateError(
            "baseline_scenario_name and candidate_scenario_name must differ for scenario ablation"
        )
    return {
        "test_name": test_name,
        "cloud_provider": cloud_provider,
        "instance_type": instance_type,
        "os_distribution": os_distribution,
        "os_version": os_version,
        "baseline_scenario_name": bs,
        "candidate_scenario_name": cs,
    }


def resolve_ui_investigation_to_template(
    ui_params: Mapping[str, Any],
) -> tuple[str, Dict[str, Any]]:
    """
    Map UI investigation payload to a comparison template id and normalized params.

    Dispatch:

    - Explicit ``template_id`` selects normalizer + policy check (Investigate mode).
    - When ``template_id`` is omitted, defaults to ``TPL_RHEL_MINOR_SAME_HW``.

    Returns:
        ``(template_id, params)`` suitable for :func:`build_zathras_results_search_body`.

    Raises:
        InvestigationTemplateError: If required keys are missing or validation fails.
    """
    requested = (ui_params.get("template_id") or "").strip()

    if requested == "TPL_TIME_WINDOW":
        normalized = normalize_time_window_params(ui_params)
        tid = "TPL_TIME_WINDOW"
    elif requested == "TPL_SINGLE_RUN_LOOKUP":
        normalized = normalize_single_run_lookup_params(ui_params)
        tid = "TPL_SINGLE_RUN_LOOKUP"
    elif requested == "TPL_PEER_OS":
        normalized = normalize_peer_os_params(ui_params)
        tid = "TPL_PEER_OS"
    elif requested == "TPL_CLOUD_SCALE_SAME_OS":
        normalized = normalize_cloud_scale_params(ui_params)
        tid = "TPL_CLOUD_SCALE_SAME_OS"
    elif requested == "TPL_SCENARIO_ABLATION":
        normalized = normalize_scenario_ablation_params(ui_params)
        tid = "TPL_SCENARIO_ABLATION"
    elif requested in ("TPL_RHEL_MAJOR_SAME_HW", "TPL_OS_SEQUENTIAL_MINOR"):
        normalized = normalize_investigation_params(ui_params)
        tid = requested
    elif requested == "TPL_RHEL_MINOR_SAME_HW":
        normalized = normalize_investigation_params(ui_params)
        tid = "TPL_RHEL_MINOR_SAME_HW"
    elif requested:
        raise InvestigationTemplateError(
            f"Unsupported template_id for UI resolution: {requested!r} "
            f"(no resolver/query builder; implemented: {', '.join(sorted(TEMPLATE_BUILDERS))})"
        )
    else:
        normalized = normalize_investigation_params(ui_params)
        tid = "TPL_RHEL_MINOR_SAME_HW"

    vr = validate_comparison_request(tid, normalized, mode="investigate")
    if not vr.ok:
        raise InvestigationTemplateError("; ".join(vr.errors))

    return tid, normalized


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


def _build_time_window_body(params: Mapping[str, Any], *, size: int) -> Dict[str, Any]:
    """OpenSearch body: fixed scope + two optional timestamp cohorts (bool ``should``)."""
    filters: list[Dict[str, Any]] = [
        {"term": {FIELD_TEST_NAME: params["test_name"]}},
        {"term": {FIELD_OS_DISTRIBUTION: params["os_distribution"]}},
        {"term": {FIELD_OS_VERSION: params["os_version"]}},
        {"term": {FIELD_CLOUD_PROVIDER: params["cloud_provider"]}},
        {"term": {FIELD_INSTANCE_TYPE: params["instance_type"]}},
    ]
    if "scenario_name" in params:
        filters.append({"term": {FIELD_SCENARIO_NAME: params["scenario_name"]}})

    should = [
        {
            "range": {
                RESULTS_ACTIVITY_TIMESTAMP_FIELD: {
                    "gte": params["baseline_window_start"],
                    "lte": params["baseline_window_end"],
                }
            }
        },
        {
            "range": {
                RESULTS_ACTIVITY_TIMESTAMP_FIELD: {
                    "gte": params["candidate_window_start"],
                    "lte": params["candidate_window_end"],
                }
            }
        },
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


def _build_peer_os_body(params: Mapping[str, Any], *, size: int) -> Dict[str, Any]:
    """Baseline vs candidate OS (distribution + version) on shared hardware/test grain."""
    filters: list[Dict[str, Any]] = [
        {"term": {FIELD_TEST_NAME: params["test_name"]}},
        {"term": {FIELD_CLOUD_PROVIDER: params["cloud_provider"]}},
        {"term": {FIELD_INSTANCE_TYPE: params["instance_type"]}},
    ]
    if "scenario_name" in params:
        filters.append({"term": {FIELD_SCENARIO_NAME: params["scenario_name"]}})

    should = [
        {
            "bool": {
                "filter": [
                    {"term": {FIELD_OS_DISTRIBUTION: params["baseline_os_distribution"]}},
                    {"term": {FIELD_OS_VERSION: params["baseline_os_version"]}},
                ]
            }
        },
        {
            "bool": {
                "filter": [
                    {"term": {FIELD_OS_DISTRIBUTION: params["candidate_os_distribution"]}},
                    {"term": {FIELD_OS_VERSION: params["candidate_os_version"]}},
                ]
            }
        },
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


def _build_single_run_lookup_body(params: Mapping[str, Any], *, size: int) -> Dict[str, Any]:
    """Exact document lookup by ``metadata.document_id``."""
    return {
        "size": min(size, 1),
        "track_total_hits": True,
        "query": {"term": {FIELD_DOCUMENT_ID: params["document_id"]}},
        "sort": [
            {"metadata.test_timestamp": {"order": "desc"}},
            {"metadata.document_id.keyword": {"order": "asc"}},
        ],
    }


def _build_cloud_scale_same_os_body(params: Mapping[str, Any], *, size: int) -> Dict[str, Any]:
    """Same OS build and test across multiple instance SKUs (single provider)."""
    filters: list[Dict[str, Any]] = [
        {"term": {FIELD_TEST_NAME: params["test_name"]}},
        {"term": {FIELD_OS_DISTRIBUTION: params["os_distribution"]}},
        {"term": {FIELD_OS_VERSION: params["os_version"]}},
        {"term": {FIELD_CLOUD_PROVIDER: params["cloud_provider"]}},
        {"terms": {FIELD_INSTANCE_TYPE: params["instance_types"]}},
    ]
    if "scenario_name" in params:
        filters.append({"term": {FIELD_SCENARIO_NAME: params["scenario_name"]}})

    return {
        "size": size,
        "track_total_hits": True,
        "query": {"bool": {"filter": filters}},
        "sort": [
            {"metadata.test_timestamp": {"order": "desc"}},
            {"metadata.document_id.keyword": {"order": "asc"}},
        ],
    }


def _build_scenario_ablation_body(params: Mapping[str, Any], *, size: int) -> Dict[str, Any]:
    """Fixed OS/hardware/test; baseline vs candidate scenario_name."""
    filters: list[Dict[str, Any]] = [
        {"term": {FIELD_TEST_NAME: params["test_name"]}},
        {"term": {FIELD_OS_DISTRIBUTION: params["os_distribution"]}},
        {"term": {FIELD_OS_VERSION: params["os_version"]}},
        {"term": {FIELD_CLOUD_PROVIDER: params["cloud_provider"]}},
        {"term": {FIELD_INSTANCE_TYPE: params["instance_type"]}},
    ]
    should = [
        {"term": {FIELD_SCENARIO_NAME: params["baseline_scenario_name"]}},
        {"term": {FIELD_SCENARIO_NAME: params["candidate_scenario_name"]}},
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
    "TPL_RHEL_MAJOR_SAME_HW": _build_rhel_minor_same_hw_body,
    "TPL_OS_SEQUENTIAL_MINOR": _build_rhel_minor_same_hw_body,
    "TPL_TIME_WINDOW": _build_time_window_body,
    "TPL_PEER_OS": _build_peer_os_body,
    "TPL_SINGLE_RUN_LOOKUP": _build_single_run_lookup_body,
    "TPL_CLOUD_SCALE_SAME_OS": _build_cloud_scale_same_os_body,
    "TPL_SCENARIO_ABLATION": _build_scenario_ablation_body,
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
