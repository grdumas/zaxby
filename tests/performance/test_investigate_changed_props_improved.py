"""
Test that changedPropIds in filter update payloads match the filter being varied.

This test validates that the update_filters_and_analyze task in locustfile_investigate.py
sets the changedPropIds field correctly based on which filter is actually being changed:
- Small preset (test name changed) → "filter-test-name.value"
- Medium preset (cloud provider changed) → "filter-cloud-provider.value"
- Large preset (both cleared) → should use a consistent convention

Since we can't import locust in the test environment, this test parses the source code
directly to validate the implementation.
"""

import re
import ast


class TestChangedPropIdsMatchFilterPreset:
    """Test that changedPropIds correctly reflects which filter is being varied."""

    LOCUSTFILE_PATH = "tests/performance/locustfile_investigate.py"

    def test_small_preset_uses_test_name_changed_prop(self):
        """Small preset changes test_name filter, so changedPropIds should be filter-test-name.value."""
        source = self._read_source()

        # Extract the small preset block
        small_pattern = r'if filter_preset == "small":.*?changed_filter = "(.*?)"'
        match = re.search(small_pattern, source, re.DOTALL)

        assert match is not None, "Could not find small preset block"
        changed_filter = match.group(1)

        assert changed_filter == "filter-test-name.value", \
            f"Small preset should set changed_filter to 'filter-test-name.value', got '{changed_filter}'"

        # Also verify test_filter is being set
        assert "test_filter = [" in match.group(0), \
            "Small preset should set test_filter"

    def test_medium_preset_uses_cloud_provider_changed_prop(self):
        """Medium preset changes cloud_provider filter, so changedPropIds should be filter-cloud-provider.value."""
        source = self._read_source()

        # Extract the medium preset block
        medium_pattern = r'elif filter_preset == "medium":.*?changed_filter = "(.*?)"'
        match = re.search(medium_pattern, source, re.DOTALL)

        assert match is not None, "Could not find medium preset block"
        changed_filter = match.group(1)

        assert changed_filter == "filter-cloud-provider.value", \
            f"Medium preset should set changed_filter to 'filter-cloud-provider.value', got '{changed_filter}'"

        # Also verify cloud_filter is being set
        assert "cloud_filter = [" in match.group(0), \
            "Medium preset should set cloud_filter"

    def test_large_preset_uses_consistent_changed_prop(self):
        """
        Large preset clears both filters, changedPropIds should be consistent.

        Current implementation picks filter-test-name.value when clearing.
        This test documents and validates that choice for consistency.
        """
        source = self._read_source()

        # Extract the large preset block
        large_pattern = r'else:.*?# large.*?changed_filter = "(.*?)"'
        match = re.search(large_pattern, source, re.DOTALL)

        assert match is not None, "Could not find large preset block"
        changed_filter = match.group(1)

        # Large preset should use a consistent value (arbitrarily filter-test-name.value)
        assert changed_filter == "filter-test-name.value", \
            f"Large preset should consistently use 'filter-test-name.value', got '{changed_filter}'"

        # Verify both filters are being cleared
        block_text = match.group(0)
        assert "test_filter = []" in block_text, \
            "Large preset should clear test_filter"
        assert "cloud_filter = []" in block_text, \
            "Large preset should clear cloud_filter"

    def test_changed_filter_passed_to_dash_payload(self):
        """Verify that changed_filter variable is passed to _dash_payload as changed parameter."""
        source = self._read_source()

        # Find the _dash_payload call after the filter preset logic
        # It should use changed=[changed_filter]
        pattern = r'_dash_payload\([^)]*changed=\[(changed_filter)\]'
        match = re.search(pattern, source)

        assert match is not None, \
            "Could not find _dash_payload call with changed=[changed_filter]"

        # Verify it's using the variable, not a hardcoded string
        assert match.group(1) == "changed_filter", \
            "The changed parameter should use the changed_filter variable"

    def test_all_presets_have_changed_filter_defined(self):
        """Verify that all three presets define changed_filter."""
        source = self._read_source()

        # Count how many times changed_filter is assigned in the preset logic
        preset_section = self._extract_preset_section(source)
        changed_filter_assignments = preset_section.count("changed_filter = ")

        assert changed_filter_assignments == 3, \
            f"Expected 3 changed_filter assignments (small/medium/large), found {changed_filter_assignments}"

    def _read_source(self):
        """Read the source code of locustfile_investigate.py."""
        with open(self.LOCUSTFILE_PATH, "r") as f:
            return f.read()

    def _extract_preset_section(self, source):
        """Extract the filter preset section from the source."""
        # Find the section between "filter_preset = self.rng.choice" and "# Update filters"
        pattern = r'filter_preset = self\.rng\.choice.*?# Update filters'
        match = re.search(pattern, source, re.DOTALL)
        assert match is not None, "Could not find filter preset section"
        return match.group(0)
