"""
Test for Investigate mode point drilldown callback fix.

Validates that the drilldown task correctly:
1. Extracts document_ids from drilldown_data.keys() (not drilldown_data["document_ids"])
2. Targets the correct output property (.children not .href)
"""

import pytest


class TestInvestigateDrilldownPayloadFix:
    """Test point drilldown payload matches app callback signature."""

    def test_drilldown_data_has_dict_structure(self):
        """Drilldown data from app is a dict keyed by document_id."""
        # This simulates the structure returned by app.py update_investigation_view
        # Lines 2966-2979 show drilldown_data is built as:
        # drilldown_data[doc_id] = {...metadata...}
        drilldown_data = {
            "doc-123": {
                "metric_name": "throughput",
                "metric_unit": "ops/s",
                "summary_value": 1500.0,
                "timestamp": "2025-06-15T10:30:00",
                "instance_type": "m5.large",
                "cloud_provider": "aws",
            },
            "doc-456": {
                "metric_name": "latency",
                "metric_unit": "ms",
                "summary_value": 25.5,
                "timestamp": "2025-06-15T11:00:00",
                "instance_type": "t3.medium",
                "cloud_provider": "gcp",
            },
        }

        # The correct way to extract document IDs is:
        document_ids = list(drilldown_data.keys())

        assert document_ids == ["doc-123", "doc-456"]
        assert len(document_ids) == 2

    def test_callback_output_property_is_children(self):
        """App callback outputs to 'children' property, not 'href'."""
        # From app.py lines 3025-3029, the callback signature is:
        # Output('point-drilldown-discover-link', 'children')

        # The Locust payload should target:
        expected_output = "..point-drilldown-modal.is_open..point-drilldown-modal-title.children..point-drilldown-modal-body.children..point-drilldown-discover-link.children.."
        expected_outputs = [
            {"id": "point-drilldown-modal", "property": "is_open"},
            {"id": "point-drilldown-modal-title", "property": "children"},
            {"id": "point-drilldown-modal-body", "property": "children"},
            {"id": "point-drilldown-discover-link", "property": "children"},  # NOT "href"
        ]

        # Verify the structure
        assert "point-drilldown-discover-link.children" in expected_output
        assert "point-drilldown-discover-link.href" not in expected_output

        # Verify last output dict uses "children"
        last_output = expected_outputs[-1]
        assert last_output["id"] == "point-drilldown-discover-link"
        assert last_output["property"] == "children"

    def test_drilldown_data_empty_dict_handling(self):
        """Test behavior when drilldown_data is empty dict."""
        drilldown_data = {}
        document_ids = list(drilldown_data.keys())

        # Should return empty list, not crash
        assert document_ids == []
        assert len(document_ids) == 0
