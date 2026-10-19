"""Read-only model discovery, capability hints and non-generating connection checks."""

import time

from . import catalog, client, connections

_CACHE = {}
_TTL = 300


def _normalize_model(model):
    if not isinstance(model, dict):
        return None
    model_id = model.get("model_id") or model.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    name = model.get("display_name")
    result = {"id": model_id, "name": name if isinstance(name, str) and name else model_id}
    # Forward only known, nonsecret capability metadata; preserve unknown capability
    # as unknown instead of guessing from a private model's name.
    if isinstance(model.get("category"), str):
        result["category"] = model["category"]
    if isinstance(model.get("supports_image_edit"), bool):
        result["supports_image_edit"] = model["supports_image_edit"]
    steps = model.get("default_image_steps")
    if isinstance(steps, int) and not isinstance(steps, bool) and steps > 0:
        result["default_image_steps"] = steps
    for key in ("supported_sizes", "supported_resolutions", "voices", "input_modalities", "output_modalities", "supported_features", "supported_sampling_parameters"):
        items = model.get(key)
        if isinstance(items, list):
            result[key] = [item for item in items if isinstance(item, str)]
    maximum = model.get("video_max_duration_seconds")
    if isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0:
        result["video_max_duration_seconds"] = maximum
    if isinstance(model.get("openai_compatible"), bool):
        result["openai_compatible"] = model["openai_compatible"]
    return result


def _private_models(endpoint):
    # A 404 on /models proves that a server responded, not that credentials or the
    # image routes are valid. Keep that distinction visible to the user.
    # EcoLink defaults to chat-only. Ask for the whole catalog; standard
    # OpenAI servers may ignore the optional category parameter.
    response = client._request("GET", "/models", endpoint=endpoint, params={"category": "all"}, timeout=min(endpoint.timeout, 10))
    try:
        payload = response.json()
    except ValueError:
        raise client.EcoHashError("Model discovery returned invalid JSON. Check the API prefix; you can still enter a model ID manually.") from None
    items = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise client.EcoHashError("Model discovery requires a models array or a JSON object with a data array.")
    return [item for model in items if (item := _normalize_model(model)) is not None]


def models(connection_id="public", *, refresh=False):
    if connection_id == "public":
        data = catalog.get_catalog(force_refresh=refresh)
        return {
            "connection": "public", "models": [item for m in data if (item := _normalize_model(m)) is not None],
            "discovery_supported": True, **catalog.status(),
        }
    endpoint = connections.resolve(connection_id)
    fingerprint = (endpoint.base_url, endpoint.api_key, endpoint.timeout)
    cached = _CACHE.get(connection_id)
    if not refresh and cached and cached["fingerprint"] == fingerprint and time.monotonic() - cached["ts"] < _TTL:
        return {**cached["result"], "source": "cache"}
    try:
        result = {"connection": connection_id, "models": _private_models(endpoint), "discovery_supported": True, "source": "live", "error": None}
    except client.EcoHashError as exc:
        if "(404)" not in str(exc) and "405" not in str(exc) and "501" not in str(exc):
            raise
        result = {
            "connection": connection_id, "models": [], "discovery_supported": False, "source": "unavailable",
            "error": "The server responded but does not expose /models. Verify the API prefix and enter the model ID manually. Authentication and inference are not verified.",
        }
    if len(_CACHE) > 100:
        _CACHE.clear()
    _CACHE[connection_id] = {"fingerprint": fingerprint, "ts": time.monotonic(), "result": result}
    return result


def test_connection(connection_id):
    endpoint = connections.resolve(connection_id)
    if connection_id == "public":
        # The public catalog is unauthenticated, so it cannot validate a key.
        response = client._request("GET", "/models", timeout=10)
        try:
            payload = response.json()
        except ValueError:
            raise client.EcoHashError("Connection responded with invalid JSON. Inference has not been tested.") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise client.EcoHashError("The public API returned an unexpected model-list response.")
        return {"status": "ok", "message": "Connected and authenticated. No inference request was sent.", "model_count": len(payload["data"])}
    result = models(connection_id, refresh=True)
    return {
        "status": "ok" if result["discovery_supported"] else "reachable",
        "message": "Connected and authenticated. No inference request was sent." if result["discovery_supported"] else result["error"],
        "model_count": len(result["models"]),
    }
