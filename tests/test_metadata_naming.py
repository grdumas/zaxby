"""
Tests for metadata field naming accuracy.

Verifies that metadata fields have accurate names that reflect what they measure.
"""

import json
from src.synthetic_data import SyntheticDataGenerator


def test_metadata_uses_avg_points_per_passing_result():
    """
    Test that metadata uses 'avg_points_per_passing_result' not 'avg_points_per_result'.

    The field should be named accurately since it only counts passing results (FAIL results
    don't generate timeseries points). This is a regression test for the naming bug.
    """
    generator = SyntheticDataGenerator(seed=42)

    result_docs = generator.generate_dataset(
        num_scenarios=20,
        iterations_per_scenario=2,
        include_temporal_trends=False,
        include_failures=True  # Enable failures so we have both PASS and FAIL
    )

    timeseries_docs = generator.generate_timeseries_documents(
        result_docs,
        short_sequence_range=(10, 20),
        long_sequence_range=(50, 100),
        long_sequence_probability=0.20,
        point_interval_seconds=30
    )

    metadata = generator.build_generation_metadata(result_docs, timeseries_docs)

    # Field should be named accurately (only counts passing results)
    assert "avg_points_per_passing_result" in metadata, \
        "Should use 'avg_points_per_passing_result' not 'avg_points_per_result'"

    # The old field name should NOT exist
    assert "avg_points_per_result" not in metadata, \
        "Old field name 'avg_points_per_result' should not exist"

    # Verify the calculation is correct (only passing results)
    passing_count = sum(
        1 for doc in result_docs
        if doc["results"]["status"] == "PASS"
    )

    expected_avg = len(timeseries_docs) / passing_count if passing_count > 0 else 0

    assert metadata["avg_points_per_passing_result"] == round(expected_avg, 1), \
        f"Expected {round(expected_avg, 1)}, got {metadata['avg_points_per_passing_result']}"


def test_metadata_calculation_excludes_failed_results():
    """
    Test that the avg_points_per_passing_result calculation excludes FAIL results.

    This verifies the field name matches the implementation (only counts PASS results).
    """
    generator = SyntheticDataGenerator(seed=42)

    # Generate dataset with failures
    result_docs = generator.generate_dataset(
        num_scenarios=30,
        iterations_per_scenario=2,
        include_temporal_trends=False,
        include_failures=True
    )

    # Verify we have some failures
    fail_count = sum(1 for doc in result_docs if doc["results"]["status"] == "FAIL")
    pass_count = sum(1 for doc in result_docs if doc["results"]["status"] == "PASS")

    assert fail_count > 0, "Test needs some failed results"
    assert pass_count > 0, "Test needs some passing results"

    # Generate timeseries (only for passing results)
    timeseries_docs = generator.generate_timeseries_documents(
        result_docs,
        short_sequence_range=(10, 20),
        long_sequence_range=(50, 100),
        long_sequence_probability=0.20,
        point_interval_seconds=30
    )

    metadata = generator.build_generation_metadata(result_docs, timeseries_docs)

    # Calculate expected average (only passing results)
    expected_avg = len(timeseries_docs) / pass_count

    # The metadata should use passing results, not total results
    assert metadata["avg_points_per_passing_result"] == round(expected_avg, 1)

    # If we incorrectly used total results, the value would be different
    incorrect_avg = len(timeseries_docs) / len(result_docs)
    assert round(expected_avg, 1) != round(incorrect_avg, 1), \
        "Test scenario should have different values for correct vs incorrect calculation"
