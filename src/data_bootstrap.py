"""
Startup loading of benchmark documents for the Dash app (OpenSearch vs synthetic).

P1-F: When ``DATA_MODE=opensearch`` and the initial load fails, do not silently
fall back to synthetic. Callers may opt in via
``ZAXBY_USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE`` (see README / QUICKSTART).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

__all__ = ["load_initial_benchmark_documents"]


def load_initial_benchmark_documents(
    data_mode: str,
    *,
    use_synthetic_after_opensearch_failure: bool = False,
    max_opensearch_docs: int = 5000,
) -> Tuple[List[Dict[str, Any]], Optional[str], bool]:
    """
    Load raw benchmark documents for app startup.

    Parameters
    ----------
    data_mode:
        ``opensearch`` or ``synthetic`` (case-insensitive).
    use_synthetic_after_opensearch_failure:
        If True and OpenSearch raises, load synthetic data and return the error
        string for display (explicit opt-in — typically from env).
    max_opensearch_docs:
        Cap for ``scroll_results`` when using OpenSearch.

    Returns
    -------
    documents
        Raw benchmark dicts for :meth:`BenchmarkDataProcessor.documents_to_dataframe`.
    opensearch_error
        ``None`` on success or when not in OpenSearch mode. On OpenSearch failure,
        ``str(exc)`` (also when synthetic fallback is used). This may be an empty
        string for message-less exceptions — detect failure with ``is not None``,
        not truthiness.
    synthetic_after_failure
        True only when OpenSearch failed but synthetic data was loaded due to
        ``use_synthetic_after_opensearch_failure``.
    """
    mode = (data_mode or "synthetic").lower().strip()
    if mode != "opensearch":
        from src.data_processing import load_synthetic_data

        return load_synthetic_data(), None, False

    try:
        from src.opensearch_client import BenchmarkDataSource

        client = BenchmarkDataSource()
        documents = client.scroll_results(max_docs=max_opensearch_docs)
        return documents, None, False
    except Exception as exc:  # noqa: BLE001 — bootstrap; surface message to UI
        err = str(exc)
        if use_synthetic_after_opensearch_failure:
            from src.data_processing import load_synthetic_data

            return load_synthetic_data(), err, True
        return [], err, False
