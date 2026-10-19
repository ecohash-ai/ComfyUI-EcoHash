"""Explicit, server-side request mappings for nonstandard dedicated services.

Mappings are deployment data in connections.json, never a model-family registry
or workflow setting. Only typed input substitution is supported; no code runs.
"""

import copy
import json
import math

from . import client, connections

_INPUTS = {"model", "prompt", "duration", "resolution", "aspect_ratio", "width", "height", "short_edge", "size"}
_CAPABILITIES = {"category", "input_modalities", "output_modalities", "supported_resolutions", "supported_sizes",
                 "video_min_duration_seconds", "video_max_duration_seconds"}


def configured(connection_id):
    return connections._store().get(connection_id, {}).get("video_requests", {})


def for_endpoint(endpoint, model):
    mappings = configured(endpoint.connection_id)
    if not isinstance(mappings, dict):
        raise client.EcoHashError("Invalid video request mappings in the server's connection settings.")
    contract = mappings.get(model)
    if contract is None:
        return None
    if not isinstance(contract, dict):
        raise client.EcoHashError("Invalid video request mapping in the server's connection settings.")
    # A saved mapping cannot follow a connection to a different API origin/prefix.
    if contract.get("base_url") != endpoint.base_url:
        return None
    if set(contract) - {"base_url", "request", "requires", "capabilities"}:
        raise client.EcoHashError("Unknown video request mapping fields in the server's connection settings.")
    if not isinstance(contract.get("request"), dict):
        raise client.EcoHashError("Video request mapping must contain a JSON request object.")
    requires, capabilities = contract.get("requires", {}), contract.get("capabilities", {})
    if (not isinstance(requires, dict) or not requires or not isinstance(capabilities, dict) or
            set(capabilities) - _CAPABILITIES or
            any(not isinstance(k, str) or isinstance(v, (dict, list)) for k, v in requires.items())):
        raise client.EcoHashError("Invalid video request mapping capability metadata.")
    try:
        encoded = json.dumps(contract, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        raise client.EcoHashError("Video request mapping must contain finite JSON values only.") from None
    if len(encoded) > 65536:
        raise client.EcoHashError("Video request mapping exceeds the supported metadata size.")
    _substitute(contract["request"], {name: None for name in _INPUTS})
    return copy.deepcopy(contract)


def matches(contract, model_metadata):
    return all(model_metadata.get(key) == value for key, value in contract.get("requires", {}).items())


def _substitute(value, inputs, depth=0):
    if depth > 12:
        raise client.EcoHashError("Video request mapping is nested too deeply.")
    if isinstance(value, dict):
        if "$input" in value:
            name = value["$input"]
            if set(value) != {"$input"} or not isinstance(name, str) or name not in inputs:
                raise client.EcoHashError("Video request mapping contains an unsupported input reference.")
            return inputs[name]
        return {key: _substitute(item, inputs, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [_substitute(item, inputs, depth + 1) for item in value]
    if value is None or isinstance(value, (str, bool, int)) or isinstance(value, float) and math.isfinite(value):
        return value
    raise client.EcoHashError("Video request mapping must contain JSON values only.")


def prepare(endpoint, model, prompt, duration, resolution, width, height, *, aspect_ratio=None):
    contract = for_endpoint(endpoint, model)
    if contract is None:
        return None
    # Verify current service identity before a billable POST; never infer an
    # adapter from an ID, path, pipeline name or failed submission response.
    from . import discovery
    result = discovery.models(endpoint.connection_id, refresh=True)
    metadata = next((item for item in result["models"] if item["id"] == model), None)
    if metadata is None or not matches(contract, metadata):
        raise client.EcoHashError("The dedicated service no longer matches its saved video request mapping. Update the server-side connection metadata. No video was submitted.")
    capabilities = contract.get("capabilities", {})
    for field, compare in (("video_min_duration_seconds", lambda v: duration < v),
                           ("video_max_duration_seconds", lambda v: duration > v)):
        limit = capabilities.get(field)
        if isinstance(limit, int) and not isinstance(limit, bool) and limit > 0 and compare(limit):
            raise client.EcoHashError(f"Requested video duration conflicts with {field}={limit} declared for this connection. No video was submitted.")
    resolutions = capabilities.get("supported_resolutions")
    if isinstance(resolutions, list) and resolutions and resolution not in resolutions:
        raise client.EcoHashError("Choose a resolution declared by this dedicated service. No video was submitted.")
    divisor = math.gcd(width, height)
    inputs = {"model": model, "prompt": prompt, "duration": duration, "resolution": resolution,
              "width": width, "height": height, "short_edge": min(width, height),
              "aspect_ratio": aspect_ratio or f"{width // divisor}:{height // divisor}", "size": f"{width}x{height}"}
    body = _substitute(contract["request"], inputs)
    if body.get("model") != model or body.get("prompt") != prompt:
        raise client.EcoHashError("Video request mappings must preserve the selected model ID and prompt. No video was submitted.")
    return body
