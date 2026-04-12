"""Tests for OpenSearch Dashboards deep link helpers (P0-D)."""

import pytest

from src.opensearch_links import (
    _rison_escape_for_single_quoted_string,
    opensearch_discover_url_for_document,
    opensearch_discover_url_for_timeseries_id,
    results_index_name,
    timeseries_index_name,
)


def test_results_index_name_prefers_opensearch_index_results(monkeypatch):
    monkeypatch.setenv("OPENSEARCH_INDEX_RESULTS", "canonical")
    monkeypatch.setenv("OPENSEARCH_INDEX", "legacy")
    assert results_index_name() == "canonical"


def test_results_index_name_falls_back_to_legacy_index(monkeypatch):
    monkeypatch.delenv("OPENSEARCH_INDEX_RESULTS", raising=False)
    monkeypatch.setenv("OPENSEARCH_INDEX", "legacy-only")
    assert results_index_name() == "legacy-only"


def test_timeseries_index_name_from_env(monkeypatch):
    monkeypatch.setenv("OPENSEARCH_INDEX_TIMESERIES", "zathras-timeseries")
    assert timeseries_index_name() == "zathras-timeseries"


def test_timeseries_index_name_empty_when_unset(monkeypatch):
    monkeypatch.delenv("OPENSEARCH_INDEX_TIMESERIES", raising=False)
    assert timeseries_index_name() == ""


def test_opensearch_discover_url_for_document_contains_index_and_query():
    url = opensearch_discover_url_for_document(
        "https://osd.example.com:5601",
        "zathras-results",
        "coremark_abc123",
    )
    assert url.startswith("https://osd.example.com:5601/app/discover#/?")
    assert "zathras-results" in url
    assert "metadata.document_id" in url
    assert "coremark_abc123" in url


def test_rison_escape_for_single_quoted_string():
    assert _rison_escape_for_single_quoted_string("a'b") == "a!'b"
    assert _rison_escape_for_single_quoted_string("a!b") == "a!!b"
    assert _rison_escape_for_single_quoted_string("a!'b") == "a!!!'b"


def test_opensearch_discover_url_for_document_escapes_quotes_in_id():
    url = opensearch_discover_url_for_document(
        "https://x.com",
        "idx",
        'weird"id',
    )
    assert '\\"' in url or "%22" in url or "weird" in url


def test_opensearch_discover_url_rison_escapes_index_single_quote():
    url = opensearch_discover_url_for_document(
        "https://x.com",
        "zathras'results",
        "doc1",
    )
    assert "index:'zathras!'results'" in url


def test_opensearch_discover_url_rison_escapes_exclamation_in_document_id():
    url = opensearch_discover_url_for_document(
        "https://x.com",
        "idx",
        "run!id",
    )
    assert "metadata.document_id: \"run!!id\"" in url or "run!!id" in url


def test_opensearch_discover_url_requires_base():
    with pytest.raises(ValueError, match="dashboards_base_url"):
        opensearch_discover_url_for_document("", "idx", "id1")


def test_opensearch_discover_url_requires_index():
    with pytest.raises(ValueError, match="index_name"):
        opensearch_discover_url_for_document("https://x.com", "", "id1")


def test_opensearch_discover_url_requires_document_id():
    with pytest.raises(ValueError, match="document_id"):
        opensearch_discover_url_for_document("https://x.com", "idx", "")


def test_opensearch_discover_url_for_timeseries_id_contains_query():
    url = opensearch_discover_url_for_timeseries_id(
        "https://osd.example.com:5601",
        "zathras-timeseries",
        "ts-uuid-123",
    )
    assert url.startswith("https://osd.example.com:5601/app/discover#/?")
    assert "zathras-timeseries" in url
    assert "metadata.timeseries_id" in url
    assert "ts-uuid-123" in url


def test_opensearch_discover_url_for_timeseries_id_requires_id():
    with pytest.raises(ValueError, match="timeseries_id"):
        opensearch_discover_url_for_timeseries_id("https://x.com", "idx", "")
