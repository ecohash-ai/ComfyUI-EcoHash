"""Server-side credential cache invalidation and dedicated connection selection."""

import hashlib
import json

try:
    from ..ecohash import client, connections
except ImportError:
    from ecohash import client, connections


MODEL_INPUT = ("STRING", {
    "default": "",
    "tooltip": "Exact model ID served by your dedicated endpoint; it need not appear in the public EcoHash catalog.",
})


def model_id(model):
    model = model.strip()
    if not model:
        raise client.EcoHashError("Enter the deployed model ID in the dedicated node's model field.")
    return model


class PublicNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        try:
            key = client.load_api_key()
        except client.EcoHashError:
            return "unconfigured:global"
        return hashlib.sha256(key.encode()).hexdigest()


class DedicatedNode:
    CATEGORY = "EcoHash/DedicatedModels"

    @classmethod
    def connection_input(cls):
        return ([""] + connections.connection_ids(dedicated_only=True), {"default": ""})

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Credential changes must invalidate cached inference without exposing the
        # secret in ComfyUI's cache metadata or workflow JSON.
        connection = kwargs.get("connection", "dedicated")
        try:
            endpoint = client.load_dedicated_endpoint(connection)
        except client.EcoHashError:
            # Validation below reports the selected connection before execution.
            return f"unconfigured:{connection}"
        settings = json.dumps([endpoint.base_url, endpoint.api_key, endpoint.timeout])
        return hashlib.sha256(settings.encode()).hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, connection=""):
        # Dynamic connection combos need a mapping error when a shared workflow's
        # connection ID does not exist on the recipient's ComfyUI server.
        if not connection:
            return "Select a dedicated connection, or add one in EcoHash connections."
        if connection not in connections.connection_ids(dedicated_only=True):
            return f"Connection '{connection}' is not configured. Open EcoHash connections and select or add a connection."
        try:
            client.load_dedicated_endpoint(connection)
        except client.EcoHashError as exc:
            return str(exc)
        return True
