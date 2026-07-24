"""
Helper utilities for Locust load tests.
"""


def _dash_payload(output, outputs, inputs, changed, state=None):
    """
    Build standard Dash /_dash-update-component POST body.

    Args:
        output: Single output string "component-id.property" or multi-output "..id.prop..id.prop.."
        outputs: Single output dict {"id": "...", "property": "..."} or list of dicts
        inputs: List of input dicts [{"id": "...", "property": "...", "value": ...}, ...]
        changed: List of changedPropIds ["component-id.property", ...]
        state: Optional list of state dicts (for State() inputs in callbacks)

    Returns:
        Dict payload for Dash callback POST request.
    """
    payload = {
        "output": output,
        "outputs": outputs,
        "inputs": inputs,
        "changedPropIds": changed,
    }
    if state:
        payload["state"] = state
    return payload
