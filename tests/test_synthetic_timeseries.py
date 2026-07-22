"""Tests for synthetic timeseries document generation."""

import pytest
from src.synthetic_data import SyntheticDataGenerator


@pytest.fixture
def generator():
    """Fixture for SyntheticDataGenerator with fixed seed."""
    return SyntheticDataGenerator(seed=42)


@pytest.fixture
def sample_results():
    """Lightweight handcrafted sample of result documents.

    Includes:
    - 2 PASS results (one passmark aggregate-only, one uperf with regular metrics)
    - 1 FAIL result (for test_skips_failed_results)
    """
    return [
        # PASS result #1 - passmark (aggregate-only test type)
        {
            "metadata": {
                "document_id": "passmark_test_001",
                "document_type": "zathras_test_result",
                "test_timestamp": "2026-01-25T10:00:00Z",
                "os_vendor": "redhat",
                "cloud_provider": "aws",
                "instance_type": "m5.2xlarge"
            },
            "test": {
                "name": "passmark",
                "version": "v10.0"
            },
            "results": {
                "status": "PASS",
                "total_runs": 1,
                "runs": {
                    "run_0": {
                        "run_number": 0,
                        "status": "PASS",
                        "metrics": {
                            "CPU_INTEGER_MATH_mean": 386194.17,
                            "CPU_FLOATINGPOINT_MATH_mean": 208830.92,
                            "CPU_PRIME_mean": 264614.52,
                            "ME_WRITE_mean": 14303.49,
                            "ME_READ_mean": 15733.84,
                            "ME_LATENCY_mean": 121.58
                        }
                    }
                }
            }
        },
        # PASS result #2 - uperf (regular test type)
        {
            "metadata": {
                "document_id": "uperf_test_002",
                "document_type": "zathras_test_result",
                "test_timestamp": "2026-01-25T11:00:00Z",
                "os_vendor": "ubuntu",
                "cloud_provider": "gcp",
                "instance_type": "c2-standard-4"
            },
            "test": {
                "name": "uperf",
                "version": "v1.22"
            },
            "results": {
                "status": "PASS",
                "total_runs": 1,
                "runs": {
                    "run_0": {
                        "run_number": 0,
                        "status": "PASS",
                        "metrics": {
                            "tcp_stream_bw_gbs": 7.70,
                            "tcp_stream_bw_gbs_mean": 7.70,
                            "tcp_stream_bw_gbs_min": 7.43,
                            "tcp_stream_bw_gbs_max": 7.97,
                            "tcp_stream_bw_gbs_stddev": 0.11,
                            "tcp_rr_trans_per_sec": 40540.97,
                            "tcp_rr_trans_per_sec_mean": 40540.97,
                            "tcp_rr_trans_per_sec_min": 39022.93,
                            "tcp_rr_trans_per_sec_max": 41248.24,
                            "tcp_rr_trans_per_sec_stddev": 482.70
                        }
                    }
                }
            }
        },
        # PASS result #3 - coremark_pro (another aggregate-only test type)
        {
            "metadata": {
                "document_id": "coremark_pro_test_003",
                "document_type": "zathras_test_result",
                "test_timestamp": "2026-01-25T12:00:00Z",
                "os_vendor": "amazon",
                "cloud_provider": "aws",
                "instance_type": "c6i.xlarge"
            },
            "test": {
                "name": "coremark_pro",
                "version": "v1.1.2743"
            },
            "results": {
                "status": "PASS",
                "total_runs": 1,
                "runs": {
                    "run_0": {
                        "run_number": 0,
                        "status": "PASS",
                        "metrics": {
                            "cjpeg_rose7_ijg_mean": 50.25,
                            "core_mean": 0.52,
                            "linear_alg_mid_100x100_sp_mean": 14.89,
                            "loops_all_mid_10k_sp_mean": 0.63,
                            "nnet_test_mean": 1.26,
                            "parser_125k_mean": 9.12,
                            "radix2_big_64k_mean": 26.59,
                            "sha_test_mean": 52.43,
                            "zip_test_mean": 20.18
                        }
                    }
                }
            }
        },
        # FAIL result - for test_skips_failed_results
        {
            "metadata": {
                "document_id": "fio_test_004_failed",
                "document_type": "zathras_test_result",
                "test_timestamp": "2026-01-25T13:00:00Z",
                "os_vendor": "redhat",
                "cloud_provider": "aws",
                "instance_type": "m5.large"
            },
            "test": {
                "name": "fio",
                "version": "v3.30"
            },
            "results": {
                "status": "FAIL",
                "total_runs": 0,
                "runs": {}
            }
        }
    ]


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


def test_point_metrics_non_empty(generator, sample_results):
    """Every timeseries point has non-empty point_metrics."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Check that all timeseries docs have non-empty point_metrics
    for ts_doc in timeseries_docs:
        point_metrics = ts_doc["results"]["point_metrics"]
        parent_id = ts_doc["metadata"]["document_id"]

        assert point_metrics, \
            f"Timeseries point for parent {parent_id} has empty point_metrics"
        assert len(point_metrics) > 0, \
            f"Timeseries point for parent {parent_id} should have at least one metric"


def test_aggregate_only_metrics_included(generator, sample_results):
    """Test types with only _mean metrics (coremark_pro, passmark) have non-empty point_metrics."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Find timeseries for coremark_pro or passmark parents
    aggregate_only_test_types = ["coremark_pro", "passmark"]

    # Build lookup of parent test types
    parent_test_types = {}
    for result_doc in sample_results:
        doc_id = result_doc["metadata"]["document_id"]
        test_name = result_doc["test"]["name"]
        parent_test_types[doc_id] = test_name

    # Check timeseries for aggregate-only test types
    found_aggregate_only = False
    for ts_doc in timeseries_docs:
        parent_id = ts_doc["metadata"]["document_id"]
        test_type = parent_test_types.get(parent_id)

        if test_type in aggregate_only_test_types:
            found_aggregate_only = True
            point_metrics = ts_doc["results"]["point_metrics"]

            # Should have non-empty point_metrics with expected _mean keys
            assert point_metrics, \
                f"{test_type} timeseries should have non-empty point_metrics"

            # Check that at least one _mean metric is present
            mean_metrics = [k for k in point_metrics.keys() if k.endswith("_mean")]
            assert mean_metrics, \
                f"{test_type} timeseries should include _mean metrics, got: {list(point_metrics.keys())}"

    # Verify we actually tested some aggregate-only test types
    if not found_aggregate_only:
        pytest.skip("No coremark_pro or passmark results in sample")


def test_aggregate_metrics_excluded_when_base_exists(generator, sample_results):
    """Aggregate metrics are excluded when their base metric exists."""
    timeseries_docs = generator.generate_timeseries_documents(sample_results)

    # Build lookup of parent metrics
    parent_metrics = {}
    for result_doc in sample_results:
        doc_id = result_doc["metadata"]["document_id"]
        if result_doc["results"]["status"] == "PASS":
            parent_metrics[doc_id] = result_doc["results"]["runs"]["run_0"]["metrics"]

    # Check timeseries for test types with base metrics (e.g., uperf)
    found_base_metrics = False
    found_aggregate_only = False

    for ts_doc in timeseries_docs:
        parent_id = ts_doc["metadata"]["document_id"]
        if parent_id not in parent_metrics:
            continue

        parent = parent_metrics[parent_id]
        point = ts_doc["results"]["point_metrics"]

        # Check for test types with base metrics
        base_metrics = [k for k in parent.keys() if not k.endswith(("_mean", "_min", "_max", "_stddev"))]
        if base_metrics:
            found_base_metrics = True
            for base_metric in base_metrics:
                # Base metric should be in point_metrics
                assert base_metric in point, \
                    f"Base metric {base_metric} should be in point_metrics, got: {list(point.keys())}"

                # Aggregate variants should NOT be in point_metrics
                for suffix in ["_mean", "_min", "_max", "_stddev"]:
                    aggregate_key = f"{base_metric}{suffix}"
                    assert aggregate_key not in point, \
                        f"Aggregate {aggregate_key} should be excluded when base {base_metric} exists"

        # Check for aggregate-only test types (coremark_pro, passmark)
        aggregate_only_metrics = [k for k in parent.keys() if k.endswith(("_mean", "_min", "_max", "_stddev"))]
        if aggregate_only_metrics and not base_metrics:
            found_aggregate_only = True
            for agg_metric in aggregate_only_metrics:
                # Extract base name
                for suffix in ["_mean", "_min", "_max", "_stddev"]:
                    if agg_metric.endswith(suffix):
                        base_name = agg_metric.rsplit(suffix, 1)[0]
                        # Verify base metric doesn't exist
                        assert base_name not in parent, \
                            f"Expected {base_name} to not exist for aggregate-only test type"
                        # Aggregate should be preserved in point_metrics
                        assert agg_metric in point, \
                            f"Aggregate-only metric {agg_metric} should be in point_metrics, got: {list(point.keys())}"
                        break

    # Verify we tested both cases
    assert found_base_metrics, "Should have found at least one test type with base metrics (e.g., uperf)"
    assert found_aggregate_only, "Should have found at least one aggregate-only test type (e.g., coremark_pro, passmark)"


def test_integer_metrics_preserved(generator):
    """Integer-valued metrics remain integers and constant after variance."""
    # Create a parent result with integer metric (sysbench cpu_threads)
    parent_result = {
        "metadata": {
            "document_id": "sysbench_test_001",
            "document_type": "zathras_test_result",
            "test_timestamp": "2026-01-25T10:00:00Z",
            "os_vendor": "redhat",
            "cloud_provider": "aws",
            "instance_type": "m5.2xlarge"
        },
        "test": {
            "name": "sysbench",
            "version": "v1.0"
        },
        "results": {
            "status": "PASS",
            "total_runs": 1,
            "runs": {
                "run_0": {
                    "run_number": 0,
                    "status": "PASS",
                    "metrics": {
                        "events_per_sec": 125000.0,
                        "latency_ms": 0.08,
                        "cpu_threads": 96  # Integer metric
                    }
                }
            }
        }
    }

    timeseries_docs = generator.generate_timeseries_documents([parent_result])

    # Should have generated timeseries points
    assert len(timeseries_docs) > 0, "Should generate timeseries for passing result"

    # Check all timeseries points
    for ts_doc in timeseries_docs:
        point_metrics = ts_doc["results"]["point_metrics"]

        # cpu_threads should be present
        assert "cpu_threads" in point_metrics, "cpu_threads should be in point_metrics"

        # Should remain an integer type
        assert isinstance(point_metrics["cpu_threads"], int), \
            f"cpu_threads should be int, got {type(point_metrics['cpu_threads'])}"

        # Should remain constant (no variance for integer fields)
        assert point_metrics["cpu_threads"] == 96, \
            f"cpu_threads should remain 96, got {point_metrics['cpu_threads']}"

        # Float metrics should still vary
        assert "events_per_sec" in point_metrics
        assert isinstance(point_metrics["events_per_sec"], float)
        # Not checking for variance here as it's probabilistic
