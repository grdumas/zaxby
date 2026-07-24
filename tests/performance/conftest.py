"""
Performance test fixtures.

Session-scoped fixtures for synthetic data generation at three scales (1k, 10k, 100k)
to support both pytest-benchmark function-level benchmarks and Locust HTTP load tests.
"""

from __future__ import annotations

import contextlib
import io
import logging
import os
from typing import Any, Dict, List

import pandas as pd
import pytest

from src.data_processing import BenchmarkDataProcessor
from src.synthetic_data import SyntheticDataGenerator

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def synthetic_generator() -> SyntheticDataGenerator:
    """
    Shared synthetic data generator with fixed seed for reproducibility.

    Returns:
        SyntheticDataGenerator instance with seed=42.
    """
    return SyntheticDataGenerator(seed=42)


@pytest.fixture(scope="session")
def documents_1k(synthetic_generator: SyntheticDataGenerator) -> List[Dict[str, Any]]:
    """
    1K-scale document dataset (~912 documents).

    Uses iterations_per_scenario=1 to generate all 912 base scenarios once.
    Generation is deterministic (seeded) and consistent across runs.

    Args:
        synthetic_generator: Shared generator instance.

    Returns:
        List of benchmark result documents.
    """
    logger.info("Generating 1K-scale documents...")
    # Suppress generator debug output
    with contextlib.redirect_stdout(io.StringIO()):
        documents = synthetic_generator.generate_dataset(
            iterations_per_scenario=1,
            include_temporal_trends=False,
            include_failures=True
        )
    logger.info(f"Generated {len(documents)} documents")
    return documents


@pytest.fixture(scope="session")
def documents_10k(synthetic_generator: SyntheticDataGenerator) -> List[Dict[str, Any]]:
    """
    10K-scale document dataset (~10,032 documents).

    Uses iterations_per_scenario=11 to generate all scenarios 11 times.

    Args:
        synthetic_generator: Shared generator instance.

    Returns:
        List of benchmark result documents.
    """
    logger.info("Generating 10K-scale documents...")
    with contextlib.redirect_stdout(io.StringIO()):
        documents = synthetic_generator.generate_dataset(
            iterations_per_scenario=11,
            include_temporal_trends=False,
            include_failures=True
        )
    logger.info(f"Generated {len(documents)} documents")
    return documents


@pytest.fixture(scope="session")
def documents_100k(synthetic_generator: SyntheticDataGenerator) -> List[Dict[str, Any]]:
    """
    100K-scale document dataset (~100,320 documents).

    Uses iterations_per_scenario=110 to generate all scenarios 110 times.
    Generation takes ~5 seconds. Session scope ensures this cost is paid once.

    Args:
        synthetic_generator: Shared generator instance.

    Returns:
        List of benchmark result documents.
    """
    logger.info("Generating 100K-scale documents (this may take ~5 seconds)...")
    with contextlib.redirect_stdout(io.StringIO()):
        documents = synthetic_generator.generate_dataset(
            iterations_per_scenario=110,
            include_temporal_trends=False,
            include_failures=True
        )
    logger.info(f"Generated {len(documents)} documents")
    return documents


@pytest.fixture(scope="session")
def benchmark_processor() -> BenchmarkDataProcessor:
    """
    Shared BenchmarkDataProcessor instance.

    Returns:
        BenchmarkDataProcessor instance.
    """
    return BenchmarkDataProcessor()


@pytest.fixture(scope="session")
def dataframe_1k(
    benchmark_processor: BenchmarkDataProcessor,
    documents_1k: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    1K-scale DataFrame built from documents.

    Mirrors the production data loading path.

    Args:
        benchmark_processor: Shared processor instance.
        documents_1k: 1K-scale documents.

    Returns:
        DataFrame with ~912 rows.
    """
    logger.info("Converting 1K documents to DataFrame...")
    df = benchmark_processor.documents_to_dataframe(documents_1k)
    logger.info(f"DataFrame shape: {df.shape}")
    return df


@pytest.fixture(scope="session")
def dataframe_10k(
    benchmark_processor: BenchmarkDataProcessor,
    documents_10k: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    10K-scale DataFrame built from documents.

    Args:
        benchmark_processor: Shared processor instance.
        documents_10k: 10K-scale documents.

    Returns:
        DataFrame with ~10,032 rows.
    """
    logger.info("Converting 10K documents to DataFrame...")
    df = benchmark_processor.documents_to_dataframe(documents_10k)
    logger.info(f"DataFrame shape: {df.shape}")
    return df


@pytest.fixture(scope="session")
def dataframe_100k(
    benchmark_processor: BenchmarkDataProcessor,
    documents_100k: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    100K-scale DataFrame built from documents.

    Args:
        benchmark_processor: Shared processor instance.
        documents_100k: 100K-scale documents.

    Returns:
        DataFrame with ~100,320 rows.
    """
    logger.info("Converting 100K documents to DataFrame...")
    df = benchmark_processor.documents_to_dataframe(documents_100k)
    logger.info(f"DataFrame shape: {df.shape}")
    return df


@pytest.fixture
def scale_documents(request) -> List[Dict[str, Any]]:
    """
    Parametrized fixture for accessing document datasets by scale label.

    Use with @pytest.mark.parametrize("scale_documents", ["1k", "10k", "100k"], indirect=True).

    Args:
        request: pytest fixture request with param = "1k", "10k", or "100k".

    Returns:
        Document list at the requested scale.
    """
    scale = request.param
    if scale == "1k":
        return request.getfixturevalue("documents_1k")
    elif scale == "10k":
        return request.getfixturevalue("documents_10k")
    elif scale == "100k":
        return request.getfixturevalue("documents_100k")
    else:
        raise ValueError(f"Unknown scale: {scale}. Must be '1k', '10k', or '100k'")


@pytest.fixture
def scale_dataframe(request) -> pd.DataFrame:
    """
    Parametrized fixture for accessing DataFrames by scale label.

    Use with @pytest.mark.parametrize("scale_dataframe", ["1k", "10k", "100k"], indirect=True).

    Args:
        request: pytest fixture request with param = "1k", "10k", or "100k".

    Returns:
        DataFrame at the requested scale.
    """
    scale = request.param
    if scale == "1k":
        return request.getfixturevalue("dataframe_1k")
    elif scale == "10k":
        return request.getfixturevalue("dataframe_10k")
    elif scale == "100k":
        return request.getfixturevalue("dataframe_100k")
    else:
        raise ValueError(f"Unknown scale: {scale}. Must be '1k', '10k', or '100k'")


@pytest.fixture
def resource_monitor():
    """
    Optional resource monitoring fixture using psutil.

    Captures CPU time and RSS memory before/after each test.
    Falls back gracefully if psutil is not installed.

    Yields:
        None (monitoring happens automatically).
    """
    try:
        import psutil
        process = psutil.Process()

        # Capture before
        cpu_before = process.cpu_times()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        yield

        # Capture after
        cpu_after = process.cpu_times()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB

        cpu_delta = (cpu_after.user - cpu_before.user) + (cpu_after.system - cpu_before.system)
        memory_delta = memory_after - memory_before

        logger.info(f"CPU time: {cpu_delta:.3f}s, Memory delta: {memory_delta:+.1f} MB")

    except ImportError:
        # psutil not installed, skip monitoring
        logger.debug("psutil not installed, skipping resource monitoring")
        yield


# --- OpenSearch Performance Test Fixtures ---


@pytest.fixture(scope="session")
def opensearch_client():
    """
    OpenSearch client for performance tests.

    Requires RUN_OPENSEARCH_QUERY_BENCHMARKS=1 environment variable to run.
    This prevents accidental execution against production clusters.

    Skips the entire session of OpenSearch tests if:
    - RUN_OPENSEARCH_QUERY_BENCHMARKS is not set to "1"
    - Connection fails
    - OpenSearch is unavailable

    Returns:
        BenchmarkDataSource instance connected to OpenSearch.
    """
    # Check opt-in flag
    if os.getenv("RUN_OPENSEARCH_QUERY_BENCHMARKS") != "1":
        pytest.skip(
            "OpenSearch query benchmarks require RUN_OPENSEARCH_QUERY_BENCHMARKS=1. "
            "Set this environment variable to explicitly opt-in to running these tests."
        )

    try:
        from src.opensearch_client import BenchmarkDataSource
        client = BenchmarkDataSource()
        logger.info("OpenSearch client connected for performance tests")
        return client
    except Exception as exc:
        logger.debug(f"OpenSearch connection failed: {exc}")
        pytest.skip("OpenSearch not available")


@pytest.fixture(scope="session")
def opensearch_results_count(opensearch_client) -> int:
    """
    Document count in the results index.

    Used by tests to calibrate expectations and skip if insufficient data.

    Args:
        opensearch_client: OpenSearch client fixture.

    Returns:
        Number of documents in results index.
    """
    try:
        count_resp = opensearch_client.client.count(index=opensearch_client.results_index)
        count = count_resp.get("count", 0)
        logger.info(f"Results index contains {count} documents")
        return count
    except Exception as exc:
        logger.debug(f"Failed to count results index: {exc}")
        pytest.skip("Cannot count results index")


@pytest.fixture(scope="session")
def opensearch_timeseries_count(opensearch_client) -> int:
    """
    Document count in the timeseries index.

    Skips if timeseries index is not configured or empty.

    Args:
        opensearch_client: OpenSearch client fixture.

    Returns:
        Number of documents in timeseries index.
    """
    if not opensearch_client.timeseries_index:
        pytest.skip("Timeseries index not configured (OPENSEARCH_INDEX_TIMESERIES)")

    try:
        count_resp = opensearch_client.client.count(index=opensearch_client.timeseries_index)
        count = count_resp.get("count", 0)
        logger.info(f"Timeseries index contains {count} documents")
        if count == 0:
            pytest.skip("Timeseries index is empty")
        return count
    except Exception as exc:
        logger.debug(f"Failed to count timeseries index: {exc}")
        pytest.skip("Cannot count timeseries index")


@pytest.fixture(scope="session")
def sample_document_ids(opensearch_client) -> List[str]:
    """
    Extract sample document IDs from results index for timeseries lookups.

    Fetches 10 sample documents and extracts their metadata.document_id values.

    Args:
        opensearch_client: OpenSearch client fixture.

    Returns:
        List of document IDs (max 10).
    """
    try:
        sample_docs = opensearch_client.get_sample_documents(limit=10)
        doc_ids = []
        for doc in sample_docs:
            # Defensive handling: if metadata is explicitly null, (doc.get("metadata") or {})
            # ensures we get {} instead of None, preventing AttributeError on the second .get()
            doc_id = (doc.get("metadata") or {}).get("document_id")
            if doc_id:
                doc_ids.append(doc_id)

        if not doc_ids:
            pytest.skip("No valid document IDs found in sample documents")

        logger.info(f"Extracted {len(doc_ids)} sample document IDs")
        return doc_ids
    except Exception as exc:
        logger.debug(f"Failed to fetch sample documents: {exc}")
        pytest.skip("Cannot fetch sample documents")


@pytest.fixture
def cluster_health_snapshot(opensearch_client):
    """
    Capture OpenSearch cluster health before and after test.

    Logs delta in shard count, pending tasks, and other cluster metrics.
    Tests must explicitly request this fixture to enable monitoring.

    Args:
        opensearch_client: OpenSearch client fixture.

    Yields:
        None (monitoring happens automatically).
    """
    try:
        # Capture before
        health_before = opensearch_client.client.cluster.health()

        yield

        # Capture after
        health_after = opensearch_client.client.cluster.health()

        # Log deltas
        shards_before = health_before.get("active_shards", 0)
        shards_after = health_after.get("active_shards", 0)
        pending_before = health_before.get("number_of_pending_tasks", 0)
        pending_after = health_after.get("number_of_pending_tasks", 0)

        logger.info(
            f"Cluster health: active_shards={shards_before}→{shards_after}, "
            f"pending_tasks={pending_before}→{pending_after}"
        )

    except Exception as exc:
        logger.warning(f"Failed to capture cluster health: {exc}")
        yield


@pytest.fixture
def opensearch_resource_monitor(opensearch_client):
    """
    Capture OpenSearch node resource metrics before and after test.

    Monitors JVM heap, OS memory, and CPU usage.
    Tests must explicitly request this fixture to enable monitoring.

    Args:
        opensearch_client: OpenSearch client fixture.

    Yields:
        None (monitoring happens automatically).
    """
    try:
        # Capture before
        stats_before = opensearch_client.client.nodes.stats(metric="jvm,os")

        yield

        # Capture after
        stats_after = opensearch_client.client.nodes.stats(metric="jvm,os")

        # Extract and log deltas (first node only for simplicity)
        nodes_before = stats_before.get("nodes", {})
        nodes_after = stats_after.get("nodes", {})

        if nodes_before and nodes_after:
            node_id = list(nodes_before.keys())[0]
            jvm_before = nodes_before[node_id].get("jvm", {}).get("mem", {})
            jvm_after = nodes_after[node_id].get("jvm", {}).get("mem", {})

            heap_used_before = jvm_before.get("heap_used_in_bytes", 0) / 1024 / 1024  # MB
            heap_used_after = jvm_after.get("heap_used_in_bytes", 0) / 1024 / 1024  # MB

            logger.info(
                f"OpenSearch node metrics: JVM heap {heap_used_before:.1f}MB → {heap_used_after:.1f}MB "
                f"(delta: {heap_used_after - heap_used_before:+.1f}MB)"
            )

    except Exception as exc:
        logger.warning(f"Failed to capture OpenSearch resource metrics: {exc}")
        yield
