"""
TDD test to verify helpers can be imported from shared module.

This ensures unit tests validate the actual production code rather than copies.
"""


def test_can_import_helpers_from_shared_module():
    """
    Verify that _timed_query and _compute_latency_stats can be imported
    from tests.performance.helpers module.

    This test will FAIL initially (proving helpers need extraction), then PASS
    after we create the shared module.
    """
    try:
        from tests.performance.helpers import _timed_query, _compute_latency_stats

        # Verify they are callable
        assert callable(_timed_query), "_timed_query is not callable"
        assert callable(_compute_latency_stats), "_compute_latency_stats is not callable"

        # Quick smoke test
        result = _compute_latency_stats([10.0, 20.0, 30.0])
        assert "mean" in result
        assert "p50" in result

        print("✓ Helpers successfully imported from shared module")
        return True
    except ImportError as e:
        raise AssertionError(f"Cannot import helpers from shared module: {e}")


if __name__ == "__main__":
    test_can_import_helpers_from_shared_module()
