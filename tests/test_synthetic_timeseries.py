"""Tests for synthetic timeseries document generation."""

import pytest
from src.synthetic_data import SyntheticDataGenerator


@pytest.fixture
def generator():
    """Fixture for SyntheticDataGenerator with fixed seed."""
    return SyntheticDataGenerator(seed=42)


@pytest.fixture
def sample_results(generator):
    """Generate a small sample of result documents."""
    return generator.generate_dataset(
        num_scenarios=5,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=True
    )


def test_generates_timeseries_for_each_passing_result(generator, sample_results):
    """Verify each passing result gets timeseries points."""
    passing_results = [doc for doc in sample_results if doc["results"]["status"] == "PASS"]

    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Extract unique parent document_ids from timeseries
    parent_ids_with_timeseries = set(
        ts_doc["metadata"]["document_id"]
        for ts_doc in timeseries_docs
    )

    # Every passing result should have at least one timeseries point
    for result_doc in passing_results:
        parent_id = result_doc["metadata"]["document_id"]
        assert parent_id in parent_ids_with_timeseries, \
            f"Passing result {parent_id} should have timeseries points"


def test_skips_failed_results(generator, sample_results):
    """Verify no timeseries generated for FAIL results."""
    failed_results = [doc for doc in sample_results if doc["results"]["status"] == "FAIL"]

    # Only proceed if we have failed results in the sample
    if not failed_results:
        pytest.skip("No failed results in sample")

    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Get all parent document_ids from timeseries
    parent_ids_with_timeseries = set(
        ts_doc["metadata"]["document_id"]
        for ts_doc in timeseries_docs
    )

    # No failed result should have timeseries
    for failed_doc in failed_results:
        failed_id = failed_doc["metadata"]["document_id"]
        assert failed_id not in parent_ids_with_timeseries, \
            f"Failed result {failed_id} should NOT have timeseries points"


def test_timeseries_ids_are_unique(generator, sample_results):
    """All timeseries_id values across all documents are unique."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    timeseries_ids = [doc["metadata"]["timeseries_id"] for doc in timeseries_docs]

    # Each sequence should have a unique timeseries_id, but points within
    # the same sequence share the same timeseries_id
    # So we check that each (timeseries_id, sequence) pair is unique
    id_sequence_pairs = [
        (doc["metadata"]["timeseries_id"], doc["metadata"]["sequence"])
        for doc in timeseries_docs
    ]

    assert len(id_sequence_pairs) == len(set(id_sequence_pairs)), \
        "Each (timeseries_id, sequence) pair must be unique"


def test_sequence_numbers_start_at_zero(generator, sample_results):
    """First point in each sequence has sequence=0."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Group by timeseries_id to find sequences
    sequences_by_id = {}
    for doc in timeseries_docs:
        ts_id = doc["metadata"]["timeseries_id"]
        if ts_id not in sequences_by_id:
            sequences_by_id[ts_id] = []
        sequences_by_id[ts_id].append(doc["metadata"]["sequence"])

    # Check that each sequence starts at 0
    for ts_id, sequences in sequences_by_id.items():
        assert 0 in sequences, f"Timeseries {ts_id} should have a point with sequence=0"
        assert min(sequences) == 0, f"Timeseries {ts_id} should start at sequence 0"


def test_sequence_numbers_are_sequential(generator, sample_results):
    """Points within a sequence are 0, 1, 2, ..."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Group by timeseries_id
    sequences_by_id = {}
    for doc in timeseries_docs:
        ts_id = doc["metadata"]["timeseries_id"]
        if ts_id not in sequences_by_id:
            sequences_by_id[ts_id] = []
        sequences_by_id[ts_id].append(doc["metadata"]["sequence"])

    # Check sequential ordering
    for ts_id, sequences in sequences_by_id.items():
        sorted_sequences = sorted(sequences)
        expected = list(range(len(sorted_sequences)))
        assert sorted_sequences == expected, \
            f"Timeseries {ts_id} should have sequential numbers: got {sorted_sequences}, expected {expected}"


def test_document_id_links_to_parent(generator, sample_results):
    """Each timeseries doc's document_id matches a result document."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Build set of valid parent document_ids
    parent_ids = set(doc["metadata"]["document_id"] for doc in sample_results)

    # Check every timeseries document links to a valid parent
    for ts_doc in timeseries_docs:
        parent_id = ts_doc["metadata"]["document_id"]
        assert parent_id in parent_ids, \
            f"Timeseries document_id {parent_id} must match a result document"


def test_point_metrics_have_variance(generator, sample_results):
    """Metrics differ from parent summary (not just copies)."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Build lookup of parent metrics
    parent_metrics = {}
    for result_doc in sample_results:
        if result_doc["results"]["status"] == "PASS":
            doc_id = result_doc["metadata"]["document_id"]
            run_0_metrics = result_doc["results"]["runs"]["run_0"]["metrics"]
            parent_metrics[doc_id] = run_0_metrics

    # Check that at least some timeseries points have different metrics
    variance_found = False
    for ts_doc in timeseries_docs:
        parent_id = ts_doc["metadata"]["document_id"]
        if parent_id not in parent_metrics:
            continue

        parent = parent_metrics[parent_id]
        point = ts_doc["results"]["point_metrics"]

        # Compare first metric value
        parent_metric_name = list(parent.keys())[0]
        if parent_metric_name in point:
            parent_val = parent[parent_metric_name]
            point_val = point[parent_metric_name]

            # Should have some variance (not exact copies)
            if abs(parent_val - point_val) > 0.001:
                variance_found = True
                break

    assert variance_found, "Timeseries points should have variance from parent metrics"


def test_point_metrics_are_realistic(generator, sample_results):
    """Metrics are within reasonable range of parent values."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Build lookup of parent metrics
    parent_metrics = {}
    for result_doc in sample_results:
        if result_doc["results"]["status"] == "PASS":
            doc_id = result_doc["metadata"]["document_id"]
            run_0_metrics = result_doc["results"]["runs"]["run_0"]["metrics"]
            parent_metrics[doc_id] = run_0_metrics

    # Check that point metrics are within ±20% of parent (with some variance)
    for ts_doc in timeseries_docs:
        parent_id = ts_doc["metadata"]["document_id"]
        if parent_id not in parent_metrics:
            continue

        parent = parent_metrics[parent_id]
        point = ts_doc["results"]["point_metrics"]

        # Check all shared metrics
        for metric_name, parent_val in parent.items():
            if metric_name.endswith(("_mean", "_min", "_max", "_stddev")):
                # Skip aggregate stats for this test
                continue

            if metric_name in point:
                point_val = point[metric_name]

                # Allow ±20% variance (realistic run-to-run variation)
                lower_bound = parent_val * 0.80
                upper_bound = parent_val * 1.20

                assert lower_bound <= point_val <= upper_bound, \
                    f"Point metric {metric_name} = {point_val} outside realistic range [{lower_bound}, {upper_bound}] for parent {parent_val}"


def test_length_distribution(generator):
    """Verify ~80/20 split between short and long sequences."""
    # Generate larger sample for distribution testing
    results = generator.generate_dataset(
        num_scenarios=50,
        iterations_per_scenario=1,
        include_temporal_trends=False,
        include_failures=False
    )

    timeseries_docs = generator.generate_timeseries_documents(results)

    # Count sequence lengths
    sequences_by_id = {}
    for doc in timeseries_docs:
        ts_id = doc["metadata"]["timeseries_id"]
        if ts_id not in sequences_by_id:
            sequences_by_id[ts_id] = 0
        sequences_by_id[ts_id] += 1

    lengths = list(sequences_by_id.values())

    # Classify as short (10-20) or long (50-100+)
    short_count = sum(1 for length in lengths if 10 <= length <= 20)
    long_count = sum(1 for length in lengths if length >= 50)

    total_classified = short_count + long_count

    if total_classified > 0:
        short_pct = short_count / total_classified
        long_pct = long_count / total_classified

        # Allow some tolerance (70-90% short, 10-30% long)
        assert 0.70 <= short_pct <= 0.90, \
            f"Expected ~80% short sequences, got {short_pct*100:.1f}%"
        assert 0.10 <= long_pct <= 0.30, \
            f"Expected ~20% long sequences, got {long_pct*100:.1f}%"


def test_common_metadata_included(generator, sample_results):
    """Verify cloud_provider, instance_type, os_vendor present."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Check first timeseries document has required fields
    assert len(timeseries_docs) > 0, "Should have generated timeseries documents"

    first_doc = timeseries_docs[0]
    metadata = first_doc["metadata"]

    assert "cloud_provider" in metadata, "cloud_provider should be in metadata"
    assert "instance_type" in metadata, "instance_type should be in metadata"
    assert "os_vendor" in metadata, "os_vendor should be in metadata"

    # Verify values are non-empty strings
    assert isinstance(metadata["cloud_provider"], str) and metadata["cloud_provider"], \
        "cloud_provider should be a non-empty string"
    assert isinstance(metadata["instance_type"], str) and metadata["instance_type"], \
        "instance_type should be a non-empty string"
    assert isinstance(metadata["os_vendor"], str) and metadata["os_vendor"], \
        "os_vendor should be a non-empty string"
