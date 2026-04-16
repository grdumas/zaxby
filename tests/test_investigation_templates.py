"""Tests for investigation template resolution and OpenSearch body building (P1-A)."""

from typing import Any, Dict, Optional

import pytest

from src.investigation_templates import (
    FIELD_OS_DISTRIBUTION,
    FIELD_OS_VERSION,
    FIELD_TEST_NAME,
    InvestigationTemplateError,
    build_zathras_results_search_body,
    fetch_investigation_documents,
    normalize_investigation_params,
    normalize_time_window_params,
    resolve_and_build_opensearch_query,
    resolve_ui_investigation_to_template,
)
from src.query_service import MAX_SEARCH_HITS, MAX_PAGE_SIZE, RESULTS_ACTIVITY_TIMESTAMP_FIELD


def _minimal_ui_params(**kwargs):
    base = {
        "test_name": "coremark",
        "baseline_version": "9.4",
        "comparison_version": "9.5",
        "os_distribution": "rhel",
    }
    base.update(kwargs)
    return base


def test_normalize_requires_test_name():
    with pytest.raises(InvestigationTemplateError, match="test_name"):
        normalize_investigation_params({"baseline_version": "9.4", "comparison_version": "9.5", "os_distribution": "rhel"})


def test_normalize_lowercases_os_distribution():
    p = normalize_investigation_params(_minimal_ui_params(os_distribution="RHEL"))
    assert p["os_distribution"] == "rhel"


def test_resolve_ui_maps_to_rhel_minor_template():
    tid, params = resolve_ui_investigation_to_template(_minimal_ui_params())
    assert tid == "TPL_RHEL_MINOR_SAME_HW"
    assert params["test_name"] == "coremark"
    assert params["baseline_version"] == "9.4"
    assert params["comparison_version"] == "9.5"


def _time_window_ui_params(**kwargs):
    base = {
        "template_id": "TPL_TIME_WINDOW",
        "test_name": "coremark",
        "cloud_provider": "aws",
        "instance_type": "m5.large",
        "os_distribution": "rhel",
        "os_version": "9.4",
        "baseline_window_start": "2025-01-01T00:00:00",
        "baseline_window_end": "2025-01-15T23:59:59",
        "candidate_window_start": "2025-02-01T00:00:00",
        "candidate_window_end": "2025-02-15T23:59:59",
    }
    base.update(kwargs)
    return base


def test_normalize_time_window_parses_z_suffix():
    p = normalize_time_window_params(
        _time_window_ui_params(
            baseline_window_start="2025-01-01T12:00:00Z",
            baseline_window_end="2025-01-02T12:00:00Z",
            candidate_window_start="2025-02-01T12:00:00Z",
            candidate_window_end="2025-02-02T12:00:00Z",
        )
    )
    assert p["baseline_window_start"].endswith("+00:00")
    assert "2025-01-01T12:00:00" in p["baseline_window_start"]


def test_normalize_time_window_rejects_inverted_range():
    with pytest.raises(InvestigationTemplateError, match="baseline"):
        normalize_time_window_params(
            _time_window_ui_params(
                baseline_window_start="2025-02-01",
                baseline_window_end="2025-01-01",
                candidate_window_start="2025-03-01",
                candidate_window_end="2025-04-01",
            )
        )


@pytest.mark.parametrize(
    "omit_key",
    [
        "test_name",
        "cloud_provider",
        "instance_type",
        "os_distribution",
        "os_version",
        "baseline_window_start",
        "baseline_window_end",
        "candidate_window_start",
        "candidate_window_end",
    ],
)
def test_normalize_time_window_missing_required_field_raises(omit_key):
    params = dict(_time_window_ui_params())
    del params[omit_key]
    with pytest.raises(InvestigationTemplateError, match=omit_key):
        normalize_time_window_params(params)


def test_normalize_time_window_invalid_iso_raises():
    with pytest.raises(InvestigationTemplateError, match="Invalid ISO 8601"):
        normalize_time_window_params(_time_window_ui_params(baseline_window_start="not-a-date"))


def test_time_window_window_order_uses_datetimes_not_lexicographic_strings():
    """Mixed naive vs +00:00 same instant must not fail ordering (PR #30 review)."""
    p = normalize_time_window_params(
        _time_window_ui_params(
            baseline_window_start="2025-01-15T12:00:00",
            baseline_window_end="2025-01-15T12:00:00+00:00",
            candidate_window_start="2025-03-01",
            candidate_window_end="2025-03-31",
        )
    )
    assert "baseline_window_start" in p
    assert "candidate_window_end" in p


def test_resolve_time_window_template_and_body():
    tid, params = resolve_ui_investigation_to_template(_time_window_ui_params())
    assert tid == "TPL_TIME_WINDOW"
    body = build_zathras_results_search_body("TPL_TIME_WINDOW", params)
    q = body["query"]["bool"]
    assert q["minimum_should_match"] == 1
    assert len(q["should"]) == 2
    assert all("range" in s and RESULTS_ACTIVITY_TIMESTAMP_FIELD in s["range"] for s in q["should"])
    flat = _flatten_term_filters(q["filter"])
    assert flat[FIELD_TEST_NAME] == "coremark"
    assert flat["metadata.cloud_provider.keyword"] == "aws"


def test_resolve_time_window_optional_scenario():
    tid, params = resolve_ui_investigation_to_template(
        _time_window_ui_params(scenario_name="rhel_95_smoke")
    )
    assert tid == "TPL_TIME_WINDOW"
    body = build_zathras_results_search_body("TPL_TIME_WINDOW", params)
    flat = _flatten_term_filters(body["query"]["bool"]["filter"])
    assert flat["metadata.scenario_name.keyword"] == "rhel_95_smoke"


def test_resolve_unsupported_template_id_raises():
    with pytest.raises(InvestigationTemplateError, match="Unsupported template_id"):
        resolve_ui_investigation_to_template(_minimal_ui_params(template_id="TPL_PEER_OS"))


def test_explicit_rhel_minor_template_id_still_resolves():
    tid, params = resolve_ui_investigation_to_template(
        _minimal_ui_params(template_id="TPL_RHEL_MINOR_SAME_HW")
    )
    assert tid == "TPL_RHEL_MINOR_SAME_HW"
    assert params["test_name"] == "coremark"


def test_build_body_omits_optional_filters_when_absent():
    """Optional metadata filters must not appear when not in normalized params (PR #12)."""
    _, params = resolve_ui_investigation_to_template(_minimal_ui_params())
    body = build_zathras_results_search_body("TPL_RHEL_MINOR_SAME_HW", params)
    filters = body["query"]["bool"]["filter"]
    assert len(filters) == 2
    fields = {list(f["term"].keys())[0] for f in filters}
    assert fields == {FIELD_TEST_NAME, FIELD_OS_DISTRIBUTION}


def test_build_body_includes_filters_and_should_clauses():
    _, params = resolve_ui_investigation_to_template(
        _minimal_ui_params(cloud_provider="aws", instance_type="m5.large", scenario_name="rhel_95")
    )
    body = build_zathras_results_search_body("TPL_RHEL_MINOR_SAME_HW", params, size=100)
    assert body["size"] == 100
    assert body["track_total_hits"] is True
    q = body["query"]["bool"]
    assert all("term" in f for f in q["filter"])
    flat = _flatten_term_filters(q["filter"])
    assert flat[FIELD_TEST_NAME] == "coremark"
    assert flat[FIELD_OS_DISTRIBUTION] == "rhel"
    assert flat["metadata.cloud_provider.keyword"] == "aws"
    assert flat["metadata.instance_type.keyword"] == "m5.large"
    assert flat["metadata.scenario_name.keyword"] == "rhel_95"
    should_versions = [s["term"][FIELD_OS_VERSION] for s in q["should"]]
    assert set(should_versions) == {"9.4", "9.5"}
    assert q["minimum_should_match"] == 1


def _flatten_term_filters(filters: list) -> dict:
    out = {}
    for f in filters:
        t = f.get("term", {})
        for k, v in t.items():
            out[k] = v
    return out


def test_resolve_and_build_opensearch_query_roundtrip():
    tid, norm, body = resolve_and_build_opensearch_query(_minimal_ui_params(), size=50)
    assert tid == "TPL_RHEL_MINOR_SAME_HW"
    assert norm["test_name"] == "coremark"
    assert body["size"] == 50


def test_build_body_default_size_uses_max_page():
    _, params = resolve_ui_investigation_to_template(_minimal_ui_params())
    body = build_zathras_results_search_body("TPL_RHEL_MINOR_SAME_HW", params)
    assert body["size"] == MAX_PAGE_SIZE


def test_build_body_clamps_size_to_max_search_hits():
    _, params = resolve_ui_investigation_to_template(_minimal_ui_params())
    body = build_zathras_results_search_body("TPL_RHEL_MINOR_SAME_HW", params, size=MAX_SEARCH_HITS + 9999)
    assert body["size"] == MAX_SEARCH_HITS


@pytest.mark.parametrize("bad_size", [0, -1, -99])
def test_build_body_clamps_non_positive_size_to_one(bad_size):
    _, params = resolve_ui_investigation_to_template(_minimal_ui_params())
    body = build_zathras_results_search_body("TPL_RHEL_MINOR_SAME_HW", params, size=bad_size)
    assert body["size"] == 1


def test_resolve_and_build_opensearch_query_default_size_none_uses_max_page():
    _tid, _norm, body = resolve_and_build_opensearch_query(_minimal_ui_params(), size=None)
    assert body["size"] == MAX_PAGE_SIZE


def test_build_unknown_template_raises():
    with pytest.raises(InvestigationTemplateError, match="No OpenSearch query builder"):
        build_zathras_results_search_body("TPL_PEER_OS", {}, size=10)


class _FakeSearchClient:
    """Stub with ``search_results`` for :func:`fetch_investigation_documents` tests."""

    def __init__(self, response: Dict[str, Any]):
        self.response = response
        self.last_body: Optional[Dict[str, Any]] = None

    def search_results(self, body: Dict[str, Any], **kwargs):
        self.last_body = body
        return self.response


def test_fetch_investigation_documents_extracts_sources_and_forwards_body():
    """OpenSearch response hits are flattened to _source list; search body is from template."""
    os_response = {
        "hits": {
            "hits": [
                {"_source": {"test": {"name": "coremark"}, "metadata": {"document_id": "d1"}}},
                {"_source": {"test": {"name": "coremark"}, "metadata": {"document_id": "d2"}}},
            ]
        }
    }
    client = _FakeSearchClient(os_response)
    tid, norm, sources = fetch_investigation_documents(_minimal_ui_params(), client)
    assert tid == "TPL_RHEL_MINOR_SAME_HW"
    assert norm["test_name"] == "coremark"
    assert len(sources) == 2
    assert sources[0]["metadata"]["document_id"] == "d1"
    assert client.last_body is not None
    assert client.last_body["query"]["bool"]["filter"]  # template body present


def test_fetch_investigation_documents_skips_hits_without_source():
    client = _FakeSearchClient({"hits": {"hits": [{"_id": "x"}]}})
    _tid, _norm, sources = fetch_investigation_documents(_minimal_ui_params(), client)
    assert sources == []
