"""
Test that Investigate mode point drilldown callback structure matches app.py.

This test validates:
1. The drilldown_data structure matches what update_investigation_view returns
2. The callback outputs match handle_point_drilldown's Output definitions
"""
import pytest
import ast
import re


def extract_callback_outputs_from_app():
    """
    Parse app.py to extract the Output structure from handle_point_drilldown callback.

    Returns:
        List of tuples: [(component_id, property), ...]
    """
    with open('/home/gdumas/repos/zaxby/app.py', 'r') as f:
        lines = f.readlines()

    # Find the handle_point_drilldown function (around line 3039)
    func_line = None
    for i, line in enumerate(lines):
        if 'def handle_point_drilldown(' in line:
            func_line = i
            break

    if func_line is None:
        pytest.fail("Could not find handle_point_drilldown function in app.py")

    # Look backwards for the @app.callback decorator (should be within 20 lines)
    callback_start = None
    for i in range(func_line - 1, max(0, func_line - 20), -1):
        if '@app.callback(' in lines[i]:
            callback_start = i
            break

    if callback_start is None:
        pytest.fail("Could not find @app.callback decorator for handle_point_drilldown")

    # Extract the decorator (it should be lines callback_start through func_line-1)
    decorator_text = ''.join(lines[callback_start:func_line])

    # Parse Output() calls - they should be in the first list after @app.callback(
    output_pattern = r"Output\('([^']+)',\s*'([^']+)'\)"
    outputs = re.findall(output_pattern, decorator_text)

    # Stop at the first Input or State
    final_outputs = []
    for output in outputs:
        final_outputs.append(output)

    return final_outputs


def extract_drilldown_data_structure_from_app():
    """
    Parse app.py to extract the structure of drilldown_data from update_investigation_view.

    Returns:
        str: 'dict_by_doc_id' or 'list_of_doc_ids'
    """
    with open('/home/gdumas/repos/zaxby/app.py', 'r') as f:
        lines = f.readlines()

    # Look at lines 2966-2979 where drilldown_data is built
    # drilldown_data = {}
    # ...
    # drilldown_data[doc_id] = {...}

    drilldown_section = ''.join(lines[2965:2980])

    # Check if it's a dict keyed by doc_id
    if 'drilldown_data = {}' in drilldown_section and 'drilldown_data[doc_id]' in drilldown_section:
        return 'dict_by_doc_id'
    elif 'document_ids' in drilldown_section and '.append' in drilldown_section:
        return 'list_of_doc_ids'
    else:
        pytest.fail("Could not determine drilldown_data structure from app.py")


def test_point_drilldown_callback_outputs_match():
    """
    Test that the point_drilldown method in locustfile_investigate.py uses
    the correct output properties that match app.py's handle_point_drilldown callback.
    """
    # Get expected outputs from app.py
    expected_outputs = extract_callback_outputs_from_app()

    # Read the locustfile to check the outputs
    with open('/home/gdumas/repos/zaxby/tests/performance/locustfile_investigate.py', 'r') as f:
        lines = f.readlines()

    # Find the point_drilldown method
    method_start = None
    for i, line in enumerate(lines):
        if 'def point_drilldown(self):' in line:
            method_start = i
            break

    if method_start is None:
        pytest.fail("Could not find point_drilldown method in locustfile_investigate.py")

    # Find the outputs list within this method (should be within 30 lines)
    method_section = ''.join(lines[method_start:method_start + 30])

    # Find the outputs list in point_drilldown method
    outputs_pattern = r'outputs=\[(.*?)\],'
    match = re.search(outputs_pattern, method_section, re.DOTALL)

    if not match:
        pytest.fail("Could not find outputs list in point_drilldown method")

    outputs_str = match.group(1)

    # Parse the output dicts
    output_dict_pattern = r'\{"id":\s*"([^"]+)",\s*"property":\s*"([^"]+)"\}'
    actual_outputs = re.findall(output_dict_pattern, outputs_str)

    # Verify they match
    assert len(actual_outputs) == len(expected_outputs), \
        f"Output count mismatch: locustfile has {len(actual_outputs)}, app.py has {len(expected_outputs)}"

    for i, (expected_id, expected_prop) in enumerate(expected_outputs):
        actual_id, actual_prop = actual_outputs[i]
        assert actual_id == expected_id, \
            f"Output {i} component_id mismatch: locustfile has '{actual_id}', app.py has '{expected_id}'"
        assert actual_prop == expected_prop, \
            f"Output {i} property mismatch: locustfile has '{actual_prop}', app.py has '{expected_prop}'"


def test_drilldown_data_structure_matches():
    """
    Test that the point_drilldown method correctly extracts document_ids from
    the drilldown_data structure that update_investigation_view returns.
    """
    # Get expected structure from app.py
    expected_structure = extract_drilldown_data_structure_from_app()

    # Read the locustfile to check how document_ids are extracted
    with open('/home/gdumas/repos/zaxby/tests/performance/locustfile_investigate.py', 'r') as f:
        locust_content = f.read()

    # Find the document_ids extraction line (around line 386)
    if expected_structure == 'dict_by_doc_id':
        # Should use: document_ids = list(self.drilldown_data.keys())
        assert 'document_ids = list(self.drilldown_data.keys())' in locust_content, \
            "point_drilldown should extract document_ids using list(self.drilldown_data.keys())"

        # Should NOT use the old incorrect pattern
        assert 'document_ids = self.drilldown_data.get("document_ids"' not in locust_content, \
            "point_drilldown should not use .get('document_ids') - drilldown_data is keyed by doc_id"

    elif expected_structure == 'list_of_doc_ids':
        # Should use: document_ids = self.drilldown_data.get("document_ids", [])
        assert 'document_ids = self.drilldown_data.get("document_ids"' in locust_content, \
            "point_drilldown should extract document_ids using .get('document_ids')"


def test_point_drilldown_output_string_format():
    """
    Test that the output string in _dash_payload matches the outputs list.

    The output string should be:
    "..point-drilldown-modal.is_open..point-drilldown-modal-title.children..point-drilldown-modal-body.children..point-drilldown-discover-link.children.."
    """
    with open('/home/gdumas/repos/zaxby/tests/performance/locustfile_investigate.py', 'r') as f:
        lines = f.readlines()

    # Find the point_drilldown method
    method_start = None
    for i, line in enumerate(lines):
        if 'def point_drilldown(self):' in line:
            method_start = i
            break

    if method_start is None:
        pytest.fail("Could not find point_drilldown method in locustfile_investigate.py")

    # Find the output string within this method
    method_section = ''.join(lines[method_start:method_start + 30])

    # Get expected outputs from app.py
    expected_outputs = extract_callback_outputs_from_app()

    # Build expected output string
    expected_parts = [f"{comp_id}.{prop}" for comp_id, prop in expected_outputs]
    expected_output_str = ".." + "..".join(expected_parts) + ".."

    # Check if this exact string appears in the method
    assert f'output="{expected_output_str}"' in method_section, \
        f"output string should be: {expected_output_str}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
