"""
Performance test fixtures.

Session-scoped fixtures for synthetic data generation at three scales (1k, 10k, 100k)
to support both pytest-benchmark function-level benchmarks and Locust HTTP load tests.
"""

from __future__ import annotations

import contextlib
import io
import logging
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
