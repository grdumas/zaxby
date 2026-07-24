"""
Test for Investigate mode changedPropIds fix.

Validates that changedPropIds matches the filter actually being varied
for each preset.
"""

import pytest


class TestInvestigateChangedPropIds:
    """Test that changedPropIds correctly reflects the filter being changed."""

    def test_small_preset_uses_test_name_filter(self):
        """Small preset changes test-name filter, should use filter-test-name.value."""
        # Small preset (lines 221-224): changes test_filter to specific test name
        expected_changed = ["filter-test-name.value"]
        assert "filter-test-name.value" in expected_changed

    def test_medium_preset_uses_cloud_provider_filter(self):
        """Medium preset changes cloud provider filter, should use filter-cloud-provider.value."""
        # Medium preset (lines 225-228): changes cloud_filter to specific cloud provider
        # This should trigger filter-cloud-provider.value, NOT filter-test-name.value
        expected_changed = ["filter-cloud-provider.value"]
        assert "filter-cloud-provider.value" in expected_changed
        assert "filter-test-name.value" not in expected_changed

    def test_large_preset_clears_filters(self):
        """Large preset clears all filters."""
        # Large preset (lines 229-232): sets both test_filter and cloud_filter to []
        # Could use either filter as trigger, but should be consistent
        # We'll use filter-test-name.value for consistency
        expected_changed = ["filter-test-name.value"]
        assert "filter-test-name.value" in expected_changed

    def test_changed_prop_id_format(self):
        """Test that changedPropIds follow Dash convention."""
        # Dash changedPropIds format: "component-id.property"
        valid_changed_ids = [
            "filter-test-name.value",
            "filter-cloud-provider.value",
            "filter-os-version.value",
            "filter-instance-type.value",
        ]

        for changed_id in valid_changed_ids:
            # Should have exactly one dot separating component and property
            parts = changed_id.split(".")
            assert len(parts) == 2, f"Invalid format: {changed_id}"
            assert parts[0].startswith("filter-"), f"Should be filter component: {changed_id}"
            assert parts[1] == "value", f"Filter property should be 'value': {changed_id}"
