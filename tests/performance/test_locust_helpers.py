"""
Tests for locust_helpers module.
"""

import pytest
from tests.performance.locust_helpers import _dash_payload


class TestDashPayload:
    """Tests for _dash_payload helper function."""

    def test_basic_single_output(self):
        """Test basic payload with single output."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = [{"id": "input-id", "property": "value", "value": "test"}]
        changed = ["input-id.value"]

        result = _dash_payload(output, outputs, inputs, changed)

        assert result == {
            "output": "output-id.value",
            "outputs": {"id": "output-id", "property": "value"},
            "inputs": [{"id": "input-id", "property": "value", "value": "test"}],
            "changedPropIds": ["input-id.value"],
        }

    def test_multi_output(self):
        """Test payload with multiple outputs."""
        output = "..output1-id.value..output2-id.children.."
        outputs = [
            {"id": "output1-id", "property": "value"},
            {"id": "output2-id", "property": "children"},
        ]
        inputs = [{"id": "input-id", "property": "value", "value": "test"}]
        changed = ["input-id.value"]

        result = _dash_payload(output, outputs, inputs, changed)

        assert result == {
            "output": "..output1-id.value..output2-id.children..",
            "outputs": [
                {"id": "output1-id", "property": "value"},
                {"id": "output2-id", "property": "children"},
            ],
            "inputs": [{"id": "input-id", "property": "value", "value": "test"}],
            "changedPropIds": ["input-id.value"],
        }

    def test_multiple_inputs(self):
        """Test payload with multiple inputs."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = [
            {"id": "input1-id", "property": "value", "value": "test1"},
            {"id": "input2-id", "property": "n_clicks", "value": 1},
        ]
        changed = ["input1-id.value"]

        result = _dash_payload(output, outputs, inputs, changed)

        assert result["inputs"] == inputs
        assert len(result["inputs"]) == 2

    def test_multiple_changed_props(self):
        """Test payload with multiple changedPropIds."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = [
            {"id": "input1-id", "property": "value", "value": "test1"},
            {"id": "input2-id", "property": "value", "value": "test2"},
        ]
        changed = ["input1-id.value", "input2-id.value"]

        result = _dash_payload(output, outputs, inputs, changed)

        assert result["changedPropIds"] == ["input1-id.value", "input2-id.value"]

    def test_with_state(self):
        """Test payload with optional state parameter."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = [{"id": "input-id", "property": "value", "value": "test"}]
        changed = ["input-id.value"]
        state = [{"id": "state-id", "property": "data", "value": {"key": "value"}}]

        result = _dash_payload(output, outputs, inputs, changed, state=state)

        assert result == {
            "output": "output-id.value",
            "outputs": {"id": "output-id", "property": "value"},
            "inputs": [{"id": "input-id", "property": "value", "value": "test"}],
            "changedPropIds": ["input-id.value"],
            "state": [{"id": "state-id", "property": "data", "value": {"key": "value"}}],
        }

    def test_without_state(self):
        """Test that state is not included when not provided."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = [{"id": "input-id", "property": "value", "value": "test"}]
        changed = ["input-id.value"]

        result = _dash_payload(output, outputs, inputs, changed)

        assert "state" not in result

    def test_state_none_explicit(self):
        """Test that state is not included when explicitly set to None."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = [{"id": "input-id", "property": "value", "value": "test"}]
        changed = ["input-id.value"]

        result = _dash_payload(output, outputs, inputs, changed, state=None)

        assert "state" not in result

    def test_empty_inputs(self):
        """Test payload with empty inputs list."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = []
        changed = []

        result = _dash_payload(output, outputs, inputs, changed)

        assert result["inputs"] == []
        assert result["changedPropIds"] == []

    def test_complex_input_values(self):
        """Test payload with complex input values (dicts, lists)."""
        output = "output-id.value"
        outputs = {"id": "output-id", "property": "value"}
        inputs = [
            {
                "id": "input-id",
                "property": "value",
                "value": {"nested": {"data": [1, 2, 3]}},
            }
        ]
        changed = ["input-id.value"]

        result = _dash_payload(output, outputs, inputs, changed)

        assert result["inputs"][0]["value"] == {"nested": {"data": [1, 2, 3]}}
