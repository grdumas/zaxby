"""Tests for synthetic data generation."""

import random as global_random
import pytest
from src.synthetic_data import SyntheticDataGenerator


def test_generate_dataset_deterministic():
    """Test that generate_dataset produces identical output for the same seed.

    This verifies the regression fix from PR #60 commit ccfe5e1:
    All random.* calls must use instance RNG (self._rng) to ensure determinism.
    """
    # Generate dataset with first generator (seed=100)
    gen1 = SyntheticDataGenerator(seed=100)
    docs1 = gen1.generate_dataset(
        num_scenarios=5,
        iterations_per_scenario=2,
        include_temporal_trends=True,
        include_failures=True
    )

    # Interfere with global random state (simulates another test/code using random)
    gen_interference = SyntheticDataGenerator(seed=999)
    _ = gen_interference.generate_dataset(
        num_scenarios=3,
        iterations_per_scenario=1
    )

    # Also call global random functions
    for _ in range(200):
        global_random.random()
        global_random.randint(1, 100)
        global_random.choice([1, 2, 3])
        global_random.uniform(0.5, 1.5)

    # Generate dataset with second generator (same seed=100)
    # If using instance RNG, this should produce identical output to gen1
    # If using global random, interference will cause different output
    gen2 = SyntheticDataGenerator(seed=100)
    docs2 = gen2.generate_dataset(
        num_scenarios=5,
        iterations_per_scenario=2,
        include_temporal_trends=True,
        include_failures=True
    )

    # Same seed should produce identical results despite interference
    assert len(docs1) == len(docs2), \
        "Same seed should produce same number of documents"

    # Check that critical fields are identical
    for idx, (doc1, doc2) in enumerate(zip(docs1, docs2)):
        # Check scenario-level fields (these should be deterministic)
        assert doc1["metadata"]["os_vendor"] == doc2["metadata"]["os_vendor"], \
            f"Doc {idx}: OS vendor should be identical"
        assert doc1["metadata"]["cloud_provider"] == doc2["metadata"]["cloud_provider"], \
            f"Doc {idx}: Cloud provider should be identical"
        assert doc1["metadata"]["instance_type"] == doc2["metadata"]["instance_type"], \
            f"Doc {idx}: Instance type should be identical"
        assert doc1["test"]["name"] == doc2["test"]["name"], \
            f"Doc {idx}: Test name should be identical"

        # Check results status (PASS/FAIL determination)
        assert doc1["results"]["status"] == doc2["results"]["status"], \
            f"Doc {idx}: Status should be identical"

        # For PASS results, check primary metric value (this exercises random variance)
        if doc1["results"]["status"] == "PASS":
            metric_val1 = doc1["results"]["primary_metric"]["value"]
            metric_val2 = doc2["results"]["primary_metric"]["value"]
            assert metric_val1 == metric_val2, \
                f"Doc {idx}: Primary metric value should be identical ({metric_val1} vs {metric_val2})"

            # Check run_0 metrics (exercises all the random.uniform calls)
            metrics1 = doc1["results"]["runs"]["run_0"]["metrics"]
            metrics2 = doc2["results"]["runs"]["run_0"]["metrics"]
            assert metrics1.keys() == metrics2.keys(), \
                f"Doc {idx}: Metrics keys should match"
            for metric_name in metrics1:
                assert metrics1[metric_name] == metrics2[metric_name], \
                    f"Doc {idx}: Metric {metric_name} should be identical"

        # For FAIL results, check failure type (if present)
        if doc1["results"]["status"] == "FAIL":
            failure_reason1 = doc1["results"].get("failure_reason")
            failure_reason2 = doc2["results"].get("failure_reason")
            assert failure_reason1 == failure_reason2, \
                f"Doc {idx}: Failure reason should be identical"

        # Check system info (exercises random.choice for CPU model)
        cpu1 = doc1["system_under_test"]["hardware"]["cpu"]["model"]
        cpu2 = doc2["system_under_test"]["hardware"]["cpu"]["model"]
        assert cpu1 == cpu2, \
            f"Doc {idx}: CPU model should be identical"

        # Check hostname (exercises random.randint)
        hostname1 = doc1["system_under_test"]["operating_system"]["hostname"]
        hostname2 = doc2["system_under_test"]["operating_system"]["hostname"]
        assert hostname1 == hostname2, \
            f"Doc {idx}: Hostname should be identical"
