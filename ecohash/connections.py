"""Server-side connection profiles. Only redacted summaries cross the settings API."""

import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import urlsplit

from . import client

CONNECTIONS_PATH = Path(__file__).resolve().parent.parent / "connections.json"
_LOCK = threading.RLock()
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
BUILTINS = {"public": "EcoHash public API", "dedicated": "Default dedicated endpoint"}
_OPERATION_PATHS = ("/images/generations", "/images/edits", "/chat/completions", "/audio/transcriptions", "/audio/speech", "/video/generations", "/videos")


def uses_global_key(base_url):
    """Only the exact EcoHash HTTPS origin may receive the account key."""
    try:
        client._validate_http_url(base_url, base_url=True)
        parsed = urlsplit(base_url)
        return parsed.scheme == "https" and parsed.hostname == "api.ecohash.com" and parsed.port in (None, 443)
    except (client.EcoHashError, ValueError):
        return False


def normalize_base_url(value, *, validate=True):
    """Accept a copied inference endpoint while storing its API prefix."""
    value = value.strip().rstrip("/")
    if not value:
        return value
    if validate:
        client._validate_http_url(value, base_url=True)
    for suffix in _OPERATION_PATHS:
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def _store():
    try:
        data = json.loads(CONNECTIONS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, UnicodeError):
        raise client.EcoHashError("Cannot read connections.json. Check its JSON syntax and permissions.") from None
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("connections"), dict):
        raise client.EcoHashError("Invalid connections.json format. Expected version 1 and a connections object.")
    if any(not _valid_id(key) or not isinstance(value, dict) for key, value in data["connections"].items()):
        raise client.EcoHashError("Invalid connection entry in connections.json.")
    return data["connections"]


def _valid_id(value):
    return isinstance(value, str) and _ID.fullmatch(value)


def connection_ids(*, dedicated_only=False):
    config = client._read_config()
    names = set(_store())
    names.update(section[11:] for section in config.sections() if section.startswith("connection:") and _valid_id(section[11:]))
    names.difference_update(BUILTINS)
    return (["dedicated"] if dedicated_only else ["public", "dedicated"]) + sorted(names)


def values(connection_id):
    if not _valid_id(connection_id):
        raise client.EcoHashError("Invalid connection ID. Use 1–64 letters, digits, underscores or hyphens.")
    config = client._read_config()
    saved = _store().get(connection_id)
    section = {"public": "ecohash", "dedicated": "dedicated"}.get(connection_id, f"connection:{connection_id}")
    if connection_id not in BUILTINS and saved is None and not config.has_section(section):
        raise client.EcoHashError(
            f"Connection '{connection_id}' is not configured. Open EcoHash connections and create or map this connection ID."
        )
    saved = saved or {}
    result, sources = {}, {}
    defaults = {"name": BUILTINS.get(connection_id, connection_id), "base_url": "", "api_key": "", "timeout": "180" if connection_id == "public" else "300"}
    for field, default in defaults.items():
        if field in ("base_url", "timeout") and connection_id == "public":
            result[field], sources[field] = (client.BASE_URL if field == "base_url" else "180"), "fixed"
            continue
        env_name = ""
        if connection_id == "public" and field == "api_key":
            env_name = "ECOHASH_API_KEY"
        elif connection_id == "dedicated" and field in ("base_url", "api_key", "timeout"):
            env_name = f"ECOHASH_DEDICATED_{field.upper()}"
        env_value = os.environ.get(env_name, "").strip() if env_name else ""
        if env_value:
            value, source = env_value, "environment"
        elif field in saved:
            value, source = saved[field], "settings"
        elif config.has_option(section, field):
            value, source = config.get(section, field), "config.ini"
        else:
            value, source = default, "default"
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise client.EcoHashError(f"Invalid {field} in connection '{connection_id}'.")
        result[field], sources[field] = str(value).strip(), source
    result["base_url"] = normalize_base_url(result["base_url"], validate=False)
    if connection_id != "public" and uses_global_key(result["base_url"]):
        result["api_key"] = values("public")["api_key"]
        sources["api_key"] = "global"
    result["sources"] = sources
    return result


def _timeout(value):
    try:
        result = float(value)
        if not math.isfinite(result) or result <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise client.EcoHashError("Dedicated inference timeout must be a positive number of seconds.") from None
    return result


def resolve(connection_id="dedicated"):
    data = values(connection_id)
    if not data["base_url"]:
        raise client.EcoHashError(
            f"Connection '{connection_id}' has no API URL. Select your saved connection in the node's Connection selector, "
            "or open EcoHash connections and save an API URL for this connection (for example https://api.ecohash.com/v1)."
        )
    client._validate_http_url(data["base_url"], base_url=True)
    key = data["api_key"]
    if not key or key in ("YOUR_DEDICATED_KEY_HERE", "eco_YOUR_KEY_HERE"):
        if connection_id == "public" or uses_global_key(data["base_url"]):
            hint = "Set the global EcoHash API Key in EcoHash settings, ECOHASH_API_KEY or [ecohash] api_key."
        else:
            hint = "Set ECOHASH_DEDICATED_API_KEY or [dedicated] api_key." if connection_id == "dedicated" else "Open EcoHash connections and configure its endpoint key under Advanced connection settings."
        raise client.EcoHashAuthError(f"Connection '{connection_id}' API key not found. {hint}")
    return client.DedicatedEndpoint(data["base_url"], key, _timeout(data["timeout"]), connection_id)


def summary(connection_id):
    data = values(connection_id)
    message, configured = "Configured; connection has not been tested.", True
    try:
        resolve(connection_id)
    except client.EcoHashError as exc:
        message, configured = str(exc), False
    return {
        "id": connection_id, "name": data["name"], "base_url": data["base_url"],
        "timeout": data["timeout"], "has_api_key": bool(data["api_key"] and data["api_key"] not in ("YOUR_DEDICATED_KEY_HERE", "eco_YOUR_KEY_HERE")),
        "uses_global_key": connection_id == "public" or uses_global_key(data["base_url"]),
        "sources": data["sources"], "configured": configured, "message": message,
        "builtin": connection_id in BUILTINS,
        "can_delete": connection_id not in BUILTINS and not client._read_config().has_section(f"connection:{connection_id}"),
    }


def list_connections():
    return [summary(name) for name in connection_ids()]


def _write_store(data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CONNECTIONS_PATH.parent, prefix=".ecohash-", delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            json.dump({"version": 1, "connections": data}, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, CONNECTIONS_PATH)
    except OSError:
        raise client.EcoHashError("Cannot save connections.json. Check write permissions on the plugin folder.") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def save_connection(connection_id, payload):
    if not _valid_id(connection_id):
        raise client.EcoHashError("Invalid connection ID. Use 1–64 letters, digits, underscores or hyphens.")
    if not isinstance(payload, dict) or set(payload) - {"name", "base_url", "api_key", "timeout"}:
        raise client.EcoHashError("Invalid connection fields.")
    with _LOCK:
        store = _store()
        if connection_id not in store and len(store) >= 100:
            raise client.EcoHashError("At most 100 connections can be saved.")
        record = dict(store.get(connection_id, {}))
        for field, value in payload.items():
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                raise client.EcoHashError(f"Invalid {field}.")
            value = str(value).strip()
            if field == "api_key" and not value:
                continue  # A blank password field preserves the existing secret.
            if field == "api_key" and (len(value) > 8192 or "\n" in value or "\r" in value):
                raise client.EcoHashError("Invalid API key format.")
            if field == "name" and (not value or len(value) > 100):
                raise client.EcoHashError("Connection name must contain 1–100 characters.")
            if field == "base_url":
                value = normalize_base_url(value)
                if connection_id == "public":
                    if value != client.BASE_URL:
                        raise client.EcoHashError("The public EcoHash API URL is fixed. Create a dedicated connection for another service.")
                elif value:
                    if len(value) > 2048:
                        raise client.EcoHashError("API URL is too long.")
                    client._validate_http_url(value, base_url=True)
            if field == "timeout":
                value = _timeout(value)
            record[field] = value
        # EcoHash connections reference the global credential, never a copy.
        config = client._read_config()
        section = "dedicated" if connection_id == "dedicated" else f"connection:{connection_id}"
        env_url = os.environ.get("ECOHASH_DEDICATED_BASE_URL", "").strip() if connection_id == "dedicated" else ""
        effective_url = env_url or record.get("base_url", config.get(section, "base_url", fallback=""))
        if connection_id != "public" and uses_global_key(normalize_base_url(effective_url, validate=False)):
            if str(payload.get("api_key", "")).strip():
                raise client.EcoHashError("EcoHash connections use the global API Key. Save it once in EcoHash settings instead of on a connection.")
            record.pop("api_key", None)
        store[connection_id] = record
        _write_store(store)
    return summary(connection_id)


def delete_connection(connection_id):
    if connection_id in BUILTINS:
        raise client.EcoHashError("Built-in connections cannot be deleted.")
    if client._read_config().has_section(f"connection:{connection_id}"):
        raise client.EcoHashError("This connection is also defined in config.ini. Remove that section before deleting the saved connection.")
    with _LOCK:
        store = _store()
        if connection_id not in store:
            raise client.EcoHashError("This connection is not stored in the settings file. Edit its config.ini section instead.")
        del store[connection_id]
        _write_store(store)
