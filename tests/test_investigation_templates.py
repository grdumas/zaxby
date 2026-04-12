"""Tests for investigation template resolution and OpenSearch body building (P1-A)."""

import pytest

from src.investigation_templates import (
    FIELD_OS_DISTRIBUTION,
    FIELD_OS_VERSION,
    FIELD_TEST_NAME,
    InvestigationTemplateError,
    build_zathras_results_search_body,
    normalize_investigation_params,
    resolve_and_build_opensearch_query,
    resolve_ui_investigation_to_template,
)
from src.query_service import MAX_SEARCH_HITS, MAX_PAGE_SIZE


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


def test_build_unknown_template_raises():
    with pytest.raises(InvestigationTemplateError, match="No OpenSearch query builder"):
        build_zathras_results_search_body("TPL_PEER_OS", {}, size=10)
